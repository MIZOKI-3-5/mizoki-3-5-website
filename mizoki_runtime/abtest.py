"""Site A/B/C test infrastructure — SITE A/B/C TEST — DESIGN FIX (r1.0).

Implements the owner's design spec for making the /signal (A) · /marketing (B)
· /media (C) landing-page comparison measurable:

* **One canonical URL.** ``/signal`` is the single indexed landing. The two
  other landings stay directly reachable (the owner's side-by-side comparison
  directive stands) but carry ``rel=canonical`` → /signal and
  ``noindex,follow`` baked into their files.
* **Server-side variant rendering, dark by default.** ``MIZOKI_ABTEST_MODE``
  must be exactly ``on`` for randomized assignment; any other value (including
  unset) serves variant A to everyone with no cookie and no assignment events.
  Arming is a reviewed env change on the deploy workflow plus an
  owner-dispatched deploy — the same convention every other activation surface
  on this platform uses.
* **Deterministic assignment.** Cookie ``mv`` pins ``{variant}.{visitor}``;
  a cookieless client is assigned from a salted hash of (ip, user-agent), so
  the same client sees the same variant with or without cookies, and crawlers
  see stable content (no user-agent-conditional serving — bots get exactly
  what a cookieless human gets; they are only *flagged* in the event log).
* **Assignment-time logging.** Events are structured JSON lines on stdout
  (Cloud Run → Cloud Logging). No raw IP, user-agent, or referrer is logged —
  only a salted 16-hex visitor key, a coarse referrer class, and a bot flag.
* **Tracked outcomes.** ``/go/pilot?cta=…`` logs the click and 302s to the
  variant's own mailto destination with an ``[ref X]`` subject token so
  arriving inquiries identify their arm; ``/api/abtest/goal`` receives the
  tier-3 scroll beacon.

Analysis tooling (sample-ratio-mismatch check, power arithmetic) lives in
``scripts/abtest_stats.py``; the pre-registration document is
``docs/marketing/abtest-preregistration-signal-landing.md``. No result from
this test enters any claim ledger or customer-facing surface without meeting
the pre-registered criteria (TRUTH.md).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

# --- Test geometry ---------------------------------------------------------

CANONICAL_PATH = "/signal"
CANONICAL_URL = "https://mizoki3.com/signal"

VARIANTS = ("a", "b", "c")
VARIANT_FILES = {
    "a": "signal.html",            # ORACLE pre-conversion landing
    "b": "marketing/index.html",   # Causal Growth Control v1.3 landing
    "c": "media/index.html",       # MIZ OKI Media landing
}
VARIANT_PATHS = {"a": "/signal", "b": "/marketing", "c": "/media"}

COOKIE_NAME = "mv"
COOKIE_MAX_AGE = 90 * 24 * 3600  # 90 days, per the design spec
_COOKIE_RE = re.compile(r"^([abc])\.([0-9a-f]{16})$")

# The bucketing salt is not a security secret — it only decorrelates the
# visitor key from a bare (ip, ua) hash. Set it once; rotating it mid-test
# re-randomizes every cookieless assignment and invalidates the test.
_DEFAULT_SALT = "mizoki-abtest-2026"


def mode_on() -> bool:
    """True only when MIZOKI_ABTEST_MODE is exactly 'on' (fail-safe off)."""
    return os.environ.get("MIZOKI_ABTEST_MODE", "").strip().lower() == "on"


# --- Visitor identity and assignment --------------------------------------

def visitor_key(ip: str, user_agent: str) -> str:
    """Salted, truncated hash — pseudonymous, never reversible to the inputs
    without the exact (ip, ua) pair; raw values are never logged."""
    salt = os.environ.get("MIZOKI_ABTEST_SALT", _DEFAULT_SALT)
    digest = hashlib.sha256(f"{salt}|{ip}|{user_agent}".encode("utf-8"))
    return digest.hexdigest()[:16]


def assign(visitor: str) -> str:
    """Deterministic arm for a visitor key: hash(visitor_id) % 3 (spec §3.1)."""
    return VARIANTS[int(visitor, 16) % len(VARIANTS)]


def parse_cookie(raw: str | None) -> tuple[str, str] | None:
    """Return (variant, visitor) for a well-formed ``mv`` cookie, else None."""
    if not raw:
        return None
    match = _COOKIE_RE.match(raw.strip())
    if not match:
        return None
    return match.group(1), match.group(2)


def cookie_value(variant: str, visitor: str) -> str:
    return f"{variant}.{visitor}"


# --- Bot and referrer classification ---------------------------------------

# Serving is identical for bots (no cloaking); this flag only marks events so
# the analysis can exclude crawler traffic (spec checklist: bot filtering on
# assignment events). Empty user-agents are treated as bots.
_BOT_RE = re.compile(
    r"bot|crawl|spider|slurp|curl\b|wget|python-requests|python-urllib|httpx|"
    r"aiohttp|go-http-client|java/|libwww|headless|phantom|lighthouse|"
    r"pagespeed|pingdom|uptime|monitor|scan|probe|preview|embed|"
    r"facebookexternalhit|whatsapp|telegram|skype|slack|discord|linkedinbot|"
    r"twitterbot|bingpreview|vercel|render|feed",
    re.IGNORECASE,
)


def is_bot(user_agent: str | None) -> bool:
    if not user_agent or not user_agent.strip():
        return True
    return bool(_BOT_RE.search(user_agent))


_SEARCH_HOSTS = ("google.", "bing.", "duckduckgo.", "yahoo.", "baidu.",
                 "yandex.", "ecosia.", "brave.", "startpage.")
_SOCIAL_HOSTS = ("facebook.", "instagram.", "linkedin.", "twitter.", "x.com",
                 "t.co", "reddit.", "youtube.", "tiktok.", "news.ycombinator")


def classify_referrer(referrer: str | None, own_host: str) -> str:
    """Coarse class only — the raw referrer is never logged (privacy posture)."""
    if not referrer:
        return "direct"
    try:
        host = (urlsplit(referrer).hostname or "").lower()
    except ValueError:
        return "external"
    if not host:
        return "direct"
    if host == own_host or host.endswith("." + own_host):
        return "internal"
    if any(host == h.rstrip(".") or h in host for h in _SEARCH_HOSTS):
        return "search"
    if any(host == h.rstrip(".") or h in host for h in _SOCIAL_HOSTS):
        return "social"
    return "external"


# --- Head posture (canonical + robots) -------------------------------------

_CANONICAL_TAG_RE = re.compile(
    r"[ \t]*<link\s[^>]*rel=[\"']canonical[\"'][^>]*>\s*?\n?", re.IGNORECASE)
_ROBOTS_TAG_RE = re.compile(
    r"[ \t]*<meta\s[^>]*name=[\"']robots[\"'][^>]*>(?:<!--.*?-->)?\s*?\n?",
    re.IGNORECASE | re.DOTALL)
_OG_URL_RE = re.compile(
    r"(<meta\s[^>]*property=[\"']og:url[\"'][^>]*content=[\"'])[^\"']*([\"'])",
    re.IGNORECASE)
_HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)


def apply_head_posture(html: str, canonical_url: str, robots: str) -> str:
    """Strip any existing canonical/robots tags and inject the serving truth.

    Used by the /signal route so that WHICHEVER variant file is served at the
    canonical URL, the response carries canonical=/signal and the indexable
    robots value — a variant file's own baked ``noindex`` must never leak
    onto the canonical URL. Idempotent by construction (strip then inject).
    """
    text = _CANONICAL_TAG_RE.sub("", html)
    text = _ROBOTS_TAG_RE.sub("", text)
    text = _OG_URL_RE.sub(lambda m: m.group(1) + canonical_url + m.group(2), text)
    injection = (
        f'<link rel="canonical" href="{canonical_url}">\n'
        f'<meta name="robots" content="{robots}">\n'
    )
    if not _HEAD_CLOSE_RE.search(text):
        # A variant file with no <head> close would be a build defect; fail
        # loudly rather than serving an unpostured page at the canonical URL.
        raise ValueError("variant HTML has no </head> to inject posture into")
    return _HEAD_CLOSE_RE.sub(injection + "</head>", text, count=1)


# --- CTA registry (tracked redirects) ---------------------------------------

# /go/pilot?cta=<key> — closed-world registry; the destination is NEVER taken
# from the request (no open-redirect surface). Each entry keeps the variant
# page's pre-existing destination address and subject; the [ref] token is
# appended at redirect time so arriving inquiries identify their arm
# (spec defect §1.2: nothing else in a mailto inquiry names the variant).
CTA_REGISTRY: dict[str, dict[str, str]] = {
    "signal-briefing": {
        "page": "a",
        "address": "briefing@mediaintelligence.ai",
        "subject": "MIZ OKI Executive Briefing",
    },
    "marketing-header": {
        "page": "b",
        "address": "briefing@mediaintelligence.ai",
        "subject": "MIZ OKI Signal 90-Day Growth Pilot",
    },
    "marketing-hero": {
        "page": "b",
        "address": "briefing@mediaintelligence.ai",
        "subject": "MIZ OKI Signal 90-Day Growth Pilot",
    },
    "marketing-pilot": {
        "page": "b",
        "address": "briefing@mediaintelligence.ai",
        "subject": "MIZ OKI Signal 90-Day Growth Pilot",
    },
    "marketing-final": {
        "page": "b",
        "address": "briefing@mediaintelligence.ai",
        "subject": "MIZ OKI Signal 90-Day Growth Pilot",
    },
    "media-final": {
        "page": "c",
        "address": "contact@mizoki3.com",
        "subject": "MIZ OKI Media Pilot",
    },
    "media-footer": {
        "page": "c",
        "address": "contact@mizoki3.com",
        "subject": "MIZ OKI Media Pilot",
    },
}


def ref_token(assigned: str | None, page_variant: str) -> str:
    """Inquiry-attribution token for the mailto subject.

    Assigned visitors carry their ITT arm (``A``/``B``/``C``); a click with no
    assignment (direct navigation to a non-canonical path, cookies refused,
    or test mode off) is marked off-protocol with an ``X`` prefix so the
    pre-registered analysis can exclude it.
    """
    if assigned in VARIANTS:
        return assigned.upper()
    return "X" + page_variant.upper()


def cta_location(cta_key: str, assigned: str | None) -> str:
    entry = CTA_REGISTRY[cta_key]
    subject = f"{entry['subject']} [ref {ref_token(assigned, entry['page'])}]"
    return f"mailto:{entry['address']}?subject={quote(subject)}"


# --- Goal (tier-3) allowlist ------------------------------------------------

GOAL_NAME = "pilot-view"
_GOAL_PAGES = {"/signal", "/signal.html", "/marketing", "/media"}


def normalize_goal_page(page: object) -> str | None:
    """Return the canonical page path for a beacon payload, or None."""
    if not isinstance(page, str) or len(page) > 64:
        return None
    path = page.rstrip("/") or "/"
    if path == "/signal.html":
        path = "/signal"
    return path if path in _GOAL_PAGES else None


# --- Event log --------------------------------------------------------------

_EVENT_NAME = "mizoki_abtest"


def log_event(kind: str, **fields: object) -> dict:
    """Emit one structured JSON event line to stdout.

    Cloud Run ingests bare JSON stdout lines as jsonPayload, which makes the
    events filterable in Cloud Logging (`jsonPayload.event="mizoki_abtest"`).
    Instance memory is ephemeral (min-instances 0), so stdout→Cloud Logging
    is the durable sink; nothing is buffered in-process except the SRM
    convenience counters below.
    """
    record = {"event": _EVENT_NAME, "kind": kind, "ts": _utc_now(), **fields}
    sys.stdout.write(json.dumps(record, separators=(",", ":")) + "\n")
    sys.stdout.flush()
    return record


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --- In-process SRM convenience counters ------------------------------------

# Per-instance, reset on every cold start, and blind to other instances —
# useful only as a live smoke signal. The authoritative arm counts for the
# weekly SRM check come from the assignment log (scripts/abtest_stats.py srm).
_counter_lock = threading.Lock()
_assignment_counts: dict[str, int] = {v: 0 for v in VARIANTS}


def count_assignment(variant: str) -> None:
    with _counter_lock:
        _assignment_counts[variant] = _assignment_counts.get(variant, 0) + 1


def counters_snapshot() -> dict[str, int]:
    with _counter_lock:
        return dict(_assignment_counts)


def reset_counters() -> None:
    with _counter_lock:
        for v in VARIANTS:
            _assignment_counts[v] = 0


def srm_check(counts: dict[str, int]) -> dict[str, float | int | None]:
    """Chi-square goodness of fit against equal thirds.

    Three arms ⇒ df=2, where the survival function is exactly exp(-x/2) —
    no special-function machinery needed here. The general-df implementation
    (and the discard-don't-reweight guidance) lives in scripts/abtest_stats.py.
    """
    values = [counts.get(v, 0) for v in VARIANTS]
    total = sum(values)
    if total == 0:
        return {"n": 0, "chi2": None, "p": None}
    expected = total / len(values)
    chi2 = sum((v - expected) ** 2 / expected for v in values)
    return {"n": total, "chi2": round(chi2, 4), "p": round(math.exp(-chi2 / 2), 6)}


# --- Request-context resolution (framework-free, unit-testable) -------------

@dataclass(frozen=True)
class Resolution:
    """What the /signal route should do for one request."""
    variant: str            # arm whose file is served
    visitor: str            # 16-hex visitor key (cookie's, or derived)
    assigned: str | None    # ITT arm when the test is live, else None
    first_exposure: bool    # True → log an assignment event
    set_cookie: bool        # True → pin the assignment on the response


def resolve(cookie_raw: str | None, ip: str, user_agent: str,
            test_on: bool, bot: bool) -> Resolution:
    if not test_on:
        # Dark mode: everyone sees the canonical variant; no cookie, no
        # assignment events — /signal behaves as a plain page while the
        # outcome instrumentation (CTA + goal) collects baseline rates.
        return Resolution(variant="a", visitor=visitor_key(ip, user_agent),
                          assigned=None, first_exposure=False, set_cookie=False)
    parsed = parse_cookie(cookie_raw)
    if parsed:
        variant, visitor = parsed
        return Resolution(variant=variant, visitor=visitor, assigned=variant,
                          first_exposure=False, set_cookie=False)
    visitor = visitor_key(ip, user_agent)
    variant = assign(visitor)
    # Bots get the same deterministic content but no Set-Cookie; their
    # first-exposure events land bot-flagged and are excluded from analysis.
    return Resolution(variant=variant, visitor=visitor, assigned=variant,
                      first_exposure=True, set_cookie=not bot)
