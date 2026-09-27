"""Lane 3 form submission → ``SOURCED`` partner (idempotent).

Reads the Lane 3 pilot-request document shape written by
``# MIZ OKI 3.5/mizoki_runtime/pilot_requests.build_document``::

    {"email", "store", "source", "received_utc", "stage": "SOURCED",
     "request_id": sha256(email|store), "notify"}

and produces a ``PartnerRecord`` whose ``partner_id`` IS that request id, so
resubmissions (already de-duplicated on the Firestore side) map to the same
partner and ``store.put_once`` refuses the duplicate. The e-mail NEVER enters
the partner record: ``display_name`` is the store host (a business identifier
already public on the storefront), and the BigQuery row carries only the hash.

Consent: an inbound pilot request is a request to be contacted about that
pilot, so the basis is ``inbound_request`` recorded at ``received_utc``. It
authorises a reply about the request — nothing wider — and an opt-out flips
``opted_out`` and closes the gate again.

Call site (flag-OFF): ``PilotRequestService(on_sourced=...)`` in
``pilot_requests.py`` accepts an optional callback invoked ONLY for a newly
created request; wiring it to ``source_from_pilot_request`` happens at
``app.py::_pilot_service()`` behind ``DESIGN_PARTNER_PIPELINE`` and is NOT
done in this wave (the site runtime does not import ``src/shared``).
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from .models import Consent, ConsentBasis, PartnerRecord, Segment, SizeBand, Source
from .store import PartnerStore

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def request_id(email: str, store: str) -> str:
    """Byte-identical to ``pilot_requests.request_id`` — the shared idempotency key."""
    return hashlib.sha256(f"{email}|{store}".encode()).hexdigest()


def partner_from_pilot_request(request: Mapping[str, Any]) -> PartnerRecord | None:
    """Pure: build the record, or ``None`` when the document is not a valid
    Lane 3 request (missing/blank email or store, malformed id)."""
    email = request.get("email")
    store_host = request.get("store")
    if not isinstance(email, str) or not email.strip() or not isinstance(store_host, str) or not store_host.strip():
        return None
    email, store_host = email.strip().lower(), store_host.strip().lower()
    rid = request.get("request_id") or request_id(email, store_host)
    if not isinstance(rid, str) or not _HEX64.match(rid) or rid != request_id(email, store_host):
        return None  # a document whose id does not match its own fields is not trusted
    received = request.get("received_utc")
    if not isinstance(received, str) or not _ISO_RE.match(received):
        return None
    return PartnerRecord(
        partner_id=rid,
        segment=Segment.BRAND,
        source=Source.FORM,
        band=SizeBand.UNKNOWN,
        consent=Consent(basis=ConsentBasis.INBOUND_REQUEST, recorded_at=received),
        display_name=store_host,          # Firestore only; never the e-mail
        created_at=received,
        updated_at=received,
    )


def source_from_pilot_request(request: Mapping[str, Any], store: PartnerStore) -> PartnerRecord | None:
    """Idempotent on ``sha256(email|store)``: the first call creates the
    SOURCED partner, every later call returns the EXISTING record unchanged
    (stage included — a resubmission never resets a partner to SOURCED).
    ``None`` when the request is invalid."""
    candidate = partner_from_pilot_request(request)
    if candidate is None:
        return None
    if store.put_once(candidate):
        return candidate
    return store.get(candidate.partner_id)
