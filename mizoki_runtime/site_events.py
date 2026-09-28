"""Measurement without egress — aggregate, identity-free site events.

Run 1 item 1.F.1 (Strategic Eval Remediation, 2026-09-02). Behind the
``SITE_EVENTS`` flag (default OFF). ``POST /event`` and ``POST /shopify/event``
accept ``{event_name, path, variant, ts}`` and the server stores ONLY

    event_name, path, variant, ts_bucket_1h, referrer_class

to BigQuery ``unified.site_events_agg`` (additive table; DDL below). No IP, no
user-agent string, no cookie, no user id — ``ROW_FIELDS`` is the closed column
set and ``tests/test_site_events_and_pilot.py`` asserts the row schema and the DDL both
directions. ``referrer_class`` is derived server-side from the ``Referer`` HOST
only; the host itself is never stored (``classify_referrer`` returns the class
and drops the host on the floor).

Sink: ``google-cloud-bigquery`` is lazily imported (the journey_sinks.py
precedent — nothing is added to requirements.txt); an absent client library or
credentials is reported as ``not_configured`` and the endpoint answers 503.
Every write carries an idempotency key (``insert_id`` = sha256 of the stored
row + bucket) and goes through a circuit breaker.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

EVENT_ALLOWLIST = ("page_view", "pilot_cta_click", "calculator_complete", "outbound_click")
VARIANT_ALLOWLIST = ("a", "b", "c", "none")
REFERRER_CLASSES = ("direct", "search", "ai_answer_engine", "social", "other")
PATH_ALLOWLIST_PREFIXES = ("/", "/shopify", "/signal", "/marketing", "/media", "/learn")  # /learn: Lane 5 S4 citation KPI (pages behind LEARN_PAGES OFF)
MAX_BODY_BYTES = 512

# The closed column set. Adding a column here is a governance change: the
# privacy test enumerates this tuple and fails on any identity-shaped name.
ROW_FIELDS = ("event_name", "path", "variant", "ts_bucket_1h", "referrer_class")
FORBIDDEN_FIELD_TOKENS = ("ip", "user_agent", "ua", "cookie", "user_id", "visitor", "session", "email", "referrer_host", "referer")

DEFAULT_TABLE = "unified.site_events_agg"

# Additive DDL — a new table, nothing altered. Applied by the operator (not
# from the site process); kept here so the test can pin the column set.
DDL = """CREATE TABLE IF NOT EXISTS `unified.site_events_agg` (
  event_name      STRING NOT NULL,   -- closed allowlist: page_view | pilot_cta_click | calculator_complete | outbound_click
  path            STRING NOT NULL,   -- site path only, never a query string
  variant         STRING NOT NULL,   -- a | b | c | none
  ts_bucket_1h    TIMESTAMP NOT NULL,-- event time truncated to the hour (never the raw timestamp)
  referrer_class  STRING NOT NULL,   -- direct | search | ai_answer_engine | social | other (host never stored)
  insert_id       STRING NOT NULL    -- idempotency key: sha256(row)
)
PARTITION BY DATE(ts_bucket_1h)
OPTIONS (description = 'Aggregate, identity-free site events (SITE_EVENTS flag). No IP, UA, cookie or user id by schema.');
"""

_SEARCH_HOSTS = ("google.", "bing.", "duckduckgo.", "yahoo.", "baidu.", "yandex.", "ecosia.", "brave.", "startpage.")
_AI_HOSTS = ("chatgpt.com", "chat.openai.com", "openai.com", "perplexity.ai", "claude.ai", "anthropic.com",
             "gemini.google.com", "bard.google.com", "copilot.microsoft.com", "you.com", "phind.com", "poe.com")
_SOCIAL_HOSTS = ("facebook.", "instagram.", "linkedin.", "twitter.", "x.com", "t.co", "reddit.", "youtube.",
                 "tiktok.", "news.ycombinator", "threads.net", "bsky.app")


def classify_referrer(referer_header: str | None, own_host: str = "mizoki3.com") -> str:
    """Coarse class from the Referer HOST only. The host is not returned or logged."""
    if not referer_header:
        return "direct"
    try:
        host = (urlsplit(referer_header).hostname or "").lower()
    except ValueError:
        return "other"
    if not host:
        return "direct"
    if host == own_host or host.endswith("." + own_host):
        return "direct"
    if any(host == h or host.endswith("." + h) for h in _AI_HOSTS):
        return "ai_answer_engine"
    if any(h in host for h in _SEARCH_HOSTS):
        return "search"
    if any(host == h.rstrip(".") or h in host for h in _SOCIAL_HOSTS):
        return "social"
    return "other"


def _hour_bucket(ts: str) -> str | None:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    dt = dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:00:00Z")


def _clean_path(path: Any) -> str | None:
    if not isinstance(path, str) or not path.startswith("/") or len(path) > 200:
        return None
    path = path.split("?", 1)[0].split("#", 1)[0]
    if any(path == p or path.startswith(p.rstrip("/") + "/") for p in PATH_ALLOWLIST_PREFIXES if p != "/"):
        return path
    return path if path == "/" else None


def validate(payload: Any) -> tuple[dict[str, str] | None, str | None]:
    """Return (accepted fields, error). Rejects anything outside the closed vocabulary."""
    if not isinstance(payload, dict):
        return None, "body must be a JSON object"
    extra = set(payload) - {"event_name", "path", "variant", "ts"}
    if extra:
        return None, f"unknown field(s): {sorted(extra)}"
    name = payload.get("event_name")
    if name not in EVENT_ALLOWLIST:
        return None, "event_name not in allowlist"
    path = _clean_path(payload.get("path"))
    if path is None:
        return None, "path not allowed"
    variant = payload.get("variant", "none")
    if variant not in VARIANT_ALLOWLIST:
        return None, "variant not allowed"
    bucket = _hour_bucket(payload.get("ts", ""))
    if bucket is None:
        return None, "ts must be ISO-8601"
    return {"event_name": name, "path": path, "variant": variant, "ts_bucket_1h": bucket}, None


def build_row(fields: dict[str, str], referer_header: str | None, own_host: str = "mizoki3.com") -> dict[str, str]:
    row = {**fields, "referrer_class": classify_referrer(referer_header, own_host)}
    assert tuple(row) == ROW_FIELDS, tuple(row)
    row["insert_id"] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
    return row


class CircuitBreaker:
    """Open after ``threshold`` consecutive failures; half-open after ``cooldown_s``."""

    def __init__(self, threshold: int = 3, cooldown_s: float = 60.0) -> None:
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if time.monotonic() - self._opened_at >= self.cooldown_s:
                return True  # half-open: one probe through
            return False

    def record(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self._failures = 0
                self._opened_at = None
            else:
                self._failures += 1
                if self._failures >= self.threshold:
                    self._opened_at = time.monotonic()

    @property
    def state(self) -> str:
        with self._lock:
            if self._opened_at is None:
                return "closed"
            return "half_open" if time.monotonic() - self._opened_at >= self.cooldown_s else "open"


class BigQuerySiteEventsSink:
    """Streaming insert with an idempotency key. ``client`` may be injected for tests."""

    def __init__(self, table: str = DEFAULT_TABLE, client: Any = None, breaker: CircuitBreaker | None = None) -> None:
        self.table = table
        self._client = client
        self.breaker = breaker or CircuitBreaker()
        self.name = f"bigquery:{table}"

    def configured(self) -> bool:
        if self._client is not None:
            return True
        try:
            from google.cloud import bigquery  # noqa: F401  (lazy: optional dependency)
        except ImportError:
            return False
        try:
            import google.auth  # type: ignore

            google.auth.default()
        except Exception:  # noqa: BLE001 — any auth failure is "not configured"
            return False
        return True

    def _resolve(self) -> Any:
        if self._client is None:
            from google.cloud import bigquery  # lazy

            self._client = bigquery.Client()
        return self._client

    def write(self, row: dict[str, str]) -> str:
        if not self.breaker.allow():
            return "circuit_open"
        try:
            errors = self._resolve().insert_rows_json(self.table, [row], row_ids=[row["insert_id"]])
            ok = not errors
        except Exception:  # noqa: BLE001
            ok = False
        self.breaker.record(ok)
        return "written" if ok else "failed"


class NullSink:
    """The flag-OFF sink: never configured, never writes. Exists so callers have one shape."""

    name = "null"

    def configured(self) -> bool:
        return False

    def write(self, row: dict[str, str]) -> str:  # pragma: no cover - never reached when OFF
        return "dropped"
