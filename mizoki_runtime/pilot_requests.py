"""Two-field pilot request (email + store URL) — idempotent Firestore write +
SendGrid notification to the owner. Run 1 item 1.F.3 (2026-09-02).

Behind ``PILOT_FORM`` (default OFF). The document id is
``sha256(email|store)`` so a resubmission is a no-op (idempotent by
construction); the SendGrid call goes through a circuit breaker and the
stdlib ``urllib`` client (the ``connections.py`` precedent — no new
dependency). Secrets fail closed: no ``SENDGRID_API_KEY`` / no Firestore
client or credentials → ``configured() is False`` → the endpoint answers 503
``not_configured``. The API key is read at call time and never logged, echoed
or stored in the document.

Privacy statement text lives in repo-root ``docs/marketing/privacy_statement_pilot.md``
and is what the injected form links to.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlsplit

from .site_events import CircuitBreaker

COLLECTION = "pilot_requests"
SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"
SENDGRID_API_KEY_ENV = "SENDGRID_API_KEY"
OWNER_NOTIFY_ENV = "PILOT_NOTIFY_TO"          # owner's inbox (operator value)
FROM_ENV = "PILOT_NOTIFY_FROM"                # verified sender (operator value)
MAX_BODY_BYTES = 1024
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[A-Za-z]{2,}$")


def normalize_email(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    return value if _EMAIL.match(value) and len(value) <= 254 else None


def normalize_store(value: Any) -> str | None:
    """Store URL → bare host (``example.myshopify.com`` / ``shop.example.com``)."""
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().lower()
    if "://" not in raw:
        raw = "https://" + raw
    try:
        host = urlsplit(raw).hostname or ""
    except ValueError:
        return None
    if not host or "." not in host or len(host) > 253 or not re.fullmatch(r"[a-z0-9.-]+", host):
        return None
    return host


def request_id(email: str, store: str) -> str:
    return hashlib.sha256(f"{email}|{store}".encode()).hexdigest()


def validate(payload: Any) -> tuple[dict[str, str] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "body must be a JSON object"
    extra = set(payload) - {"email", "store"}
    if extra:
        return None, f"unknown field(s): {sorted(extra)}"
    email = normalize_email(payload.get("email"))
    if email is None:
        return None, "email is invalid"
    store = normalize_store(payload.get("store"))
    if store is None:
        return None, "store URL is invalid"
    return {"email": email, "store": store}, None


def build_document(fields: dict[str, str], source: str = "/shopify") -> tuple[str, dict[str, Any]]:
    doc_id = request_id(fields["email"], fields["store"])
    return doc_id, {
        "email": fields["email"],
        "store": fields["store"],
        "source": source,
        "received_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stage": "SOURCED",
        "request_id": doc_id,
        "notify": "pending",   # pending | sent | failed — retried on resubmission until sent
    }


class FirestorePilotStore:
    """``create`` (not ``set``) so a duplicate is a no-op: idempotent on the id."""

    def __init__(self, client: Any = None, collection: str = COLLECTION) -> None:
        self._client = client
        self.collection = collection

    def configured(self) -> bool:
        if self._client is not None:
            return True
        try:
            from google.cloud import firestore  # noqa: F401  (lazy)
            import google.auth  # type: ignore

            google.auth.default()
        except Exception:  # noqa: BLE001
            return False
        return True

    def _resolve(self) -> Any:
        if self._client is None:
            from google.cloud import firestore  # lazy

            self._client = firestore.Client()
        return self._client

    def create(self, doc_id: str, document: dict[str, Any]) -> str:
        ref = self._resolve().collection(self.collection).document(doc_id)
        try:
            ref.create(document)
        except Exception as exc:  # noqa: BLE001 — AlreadyExists is the idempotent no-op
            if exc.__class__.__name__ in ("AlreadyExists", "Conflict"):
                return "duplicate"
            raise
        return "created"

    def get(self, doc_id: str) -> dict[str, Any] | None:
        snap = self._resolve().collection(self.collection).document(doc_id).get()
        if not getattr(snap, "exists", False):
            return None
        return dict(snap.to_dict() or {})

    def set_notify(self, doc_id: str, state: str) -> None:
        """Best-effort: a failed state write never turns a sent mail into a 503."""
        try:
            self._resolve().collection(self.collection).document(doc_id).update({"notify": state})
        except Exception:  # noqa: BLE001
            pass


class SendGridNotifier:
    def __init__(self, opener: Any = None, breaker: CircuitBreaker | None = None, timeout: float = 10.0) -> None:
        self._opener = opener or urllib.request.urlopen
        self.breaker = breaker or CircuitBreaker()
        self.timeout = timeout

    def configured(self) -> bool:
        return bool(os.environ.get(SENDGRID_API_KEY_ENV)) and bool(os.environ.get(OWNER_NOTIFY_ENV)) \
            and bool(os.environ.get(FROM_ENV))

    def notify(self, document: dict[str, Any]) -> str:
        if not self.breaker.allow():
            return "circuit_open"
        key = os.environ.get(SENDGRID_API_KEY_ENV, "")
        body = {
            "personalizations": [{"to": [{"email": os.environ[OWNER_NOTIFY_ENV]}]}],
            "from": {"email": os.environ[FROM_ENV]},
            "subject": f"[MIZ OKI] Pilot request — {document['store']}",
            "content": [{"type": "text/plain",
                         "value": (f"Pilot request received via {document['source']} at {document['received_utc']}\n"
                                   f"store: {document['store']}\nemail: {document['email']}\n"
                                   f"request_id: {document['request_id']}\n")}],
            "custom_args": {"request_id": document["request_id"]},  # idempotency key on the mail
        }
        req = urllib.request.Request(SENDGRID_URL, data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {key}",
                                              "Content-Type": "application/json"})
        try:
            with self._opener(req, timeout=self.timeout) as resp:
                ok = 200 <= getattr(resp, "status", 200) < 300
        except (urllib.error.URLError, OSError, ValueError):
            ok = False
        self.breaker.record(ok)
        return "sent" if ok else "failed"


class PilotRequestService:
    """``on_sourced`` is the flag-OFF extension point for the design-partner
    pipeline (Strategy S1, Lane 6): an optional callable given the persisted
    document, invoked ONLY when the document was newly ``created`` — never on
    a duplicate, so the pipeline's ``SOURCED`` intake stays idempotent on the
    same ``sha256(email|store)`` id. Default ``None`` = inert (nothing here
    imports the pipeline). Wiring it happens at ``app.py::_pilot_service()``
    behind ``DESIGN_PARTNER_PIPELINE`` and is a separate, gated change. A
    hook failure never turns a received request into an error: it is
    swallowed after the document is persisted (the notification path is
    unaffected either way).
    """

    def __init__(self, store: Any = None, notifier: SendGridNotifier | None = None,
                 on_sourced: Callable[[dict[str, Any]], Any] | None = None) -> None:
        self.store = store if store is not None else FirestorePilotStore()
        self.notifier = notifier if notifier is not None else SendGridNotifier()
        self.on_sourced = on_sourced
        self._lock = threading.Lock()

    def configured(self) -> bool:
        return self.store.configured() and self.notifier.configured()

    def submit(self, fields: dict[str, str], source: str = "/shopify") -> dict[str, str]:
        """``notify`` is ``sent`` / ``already_sent`` / ``failed`` / ``circuit_open``.

        A duplicate whose earlier notification did not go out is RETRIED, not
        skipped: the persisted document carries the notification state, so a
        resubmission after a SendGrid failure is how the owed mail gets sent
        (#899 review, Codex P1 — a 202 on a lost notification made every retry
        a silent no-op).
        """
        doc_id, document = build_document(fields, source)
        with self._lock:
            outcome = self.store.create(doc_id, document)
        # WO-33 (#1003): the hook's outcome is REPORTED (``pipeline`` key:
        # ``sourced`` | ``failed`` | ``skipped``), never silently dropped. It
        # still never changes the request outcome — the document is persisted
        # and the notification path is unaffected either way.
        pipeline = "skipped"
        if outcome == "created" and self.on_sourced is not None:
            try:
                self.on_sourced(dict(document))
                pipeline = "sourced"
            except Exception:  # noqa: BLE001 — best-effort side channel, never a 503
                pipeline = "failed"
        if outcome == "duplicate":
            existing = self.store.get(doc_id) or document
            if existing.get("notify") == "sent":
                return {"request_id": doc_id, "store": outcome, "notify": "already_sent", "pipeline": pipeline}
            document = existing
        notify = self.notifier.notify(document)
        self.store.set_notify(doc_id, "sent" if notify == "sent" else "failed")
        return {"request_id": doc_id, "store": outcome, "notify": notify, "pipeline": pipeline}
