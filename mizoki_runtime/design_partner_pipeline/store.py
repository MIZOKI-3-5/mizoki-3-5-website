"""Partner stores (Strategy S1, Lane 6).

  PartnerStore           the interface every caller programs against.
  InMemoryPartnerStore   the test / offline implementation.
  FirestorePartnerStore  ``partners/{id}`` — current record incl. display name.
  BigQueryPipelineSink   append-only stage events → ``unified.design_partner_pipeline``
                         (pseudonymous id + categorical facts only), streaming
                         insert with ``insert_id`` as the idempotency key,
                         behind a circuit breaker. BUILT AND UNWIRED (IN BUILD,
                         verifier F-05): nothing calls ``append`` today and
                         ``transition()`` emits no row — wiring is a separate,
                         gated change.

The real clients are constructed ONLY by ``resolve_store()`` and ONLY when
``DESIGN_PARTNER_PIPELINE`` is on; every ``google.cloud`` import is inside a
method (``tests/gtm/test_store.py`` asserts the module has no top-level
client import). Flag OFF → ``resolve_store()`` returns ``None`` and the
caller reports ``not_configured``. Flag ON with no client library or no
credentials → ``NotConfigured`` is raised, never a healthy stub.

Circuit breaker: mirrors ``# MIZ OKI 3.5/mizoki_runtime/site_events.CircuitBreaker``
(threshold / cooldown / half-open probe). There is no shared breaker under
``src/shared`` today — a candidate BUILD_DEBT row, named in the packet.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Iterable, Mapping, Protocol

from .flags import DESIGN_PARTNER_PIPELINE_ENV, pipeline_enabled
from .models import PartnerRecord, now_iso
from .stages import Stage

FIRESTORE_COLLECTION = "partners"
MILESTONE_COLLECTION = "partner_milestones"
DEFAULT_BQ_TABLE = "unified.design_partner_pipeline"
BQ_TABLE_ENV = "DESIGN_PARTNER_PIPELINE_BQ_TABLE"
PROJECT_ENV = "GOOGLE_CLOUD_PROJECT"


class NotConfigured(RuntimeError):
    """The flag is on but the sink cannot be built — health says not_configured."""


class StaleUpdate(RuntimeError):
    """``update(expected_stage=…)`` found a different stage on the stored
    record: a concurrent transition already moved it (verifier F-08). The
    caller re-reads and re-decides; nothing was written."""


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
            return time.monotonic() - self._opened_at >= self.cooldown_s  # half-open probe

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


class PartnerStore(Protocol):
    def get(self, partner_id: str) -> PartnerRecord | None: ...
    def put_once(self, record: PartnerRecord) -> bool:
        """Create; False (and no write) when the id already exists — idempotent."""
        ...
    def update(self, record: PartnerRecord, expected_stage: Stage | None = None) -> None:
        """Replace the stored record. With ``expected_stage`` the write is
        REFUSED (``StaleUpdate``) unless the stored record is still at that
        stage — the precondition every transition write must carry."""
        ...
    def list_all(self) -> list[PartnerRecord]: ...
    def record_milestone(self, key: str) -> bool:
        """True when ``key`` was newly recorded; False when it already was."""
        ...
    def milestones(self) -> list[str]: ...


def apply_transition(store: "PartnerStore", record: PartnerRecord, target: Stage,
                     at: str | None = None) -> PartnerRecord:
    """``transition()`` + ``update(expected_stage=<the stage before the move>)``
    — the one write shape a caller should use, so a concurrent move is
    refused (``StaleUpdate``) rather than overwritten."""
    from .models import transition  # local: models must not import store

    before = record.stage
    transition(record, target, at)
    store.update(record, expected_stage=before)
    return record


def counts_by_stage(records: Iterable[PartnerRecord]) -> dict[str, int]:
    """Every stage present with its count (zeros included) — never a name."""
    counts = {s.value: 0 for s in Stage}
    for r in records:
        counts[r.stage.value] += 1
    return counts


class InMemoryPartnerStore:
    def __init__(self) -> None:
        self._docs: dict[str, dict[str, Any]] = {}
        self._milestones: list[str] = []
        self._events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def get(self, partner_id: str) -> PartnerRecord | None:
        with self._lock:
            doc = self._docs.get(partner_id)
        return PartnerRecord.from_document(doc) if doc else None

    def put_once(self, record: PartnerRecord) -> bool:
        with self._lock:
            if record.partner_id in self._docs:
                return False
            self._docs[record.partner_id] = record.to_document()
        self._events.append(record.to_bigquery_row(None, record.stage, record.created_at))
        return True

    def update(self, record: PartnerRecord, expected_stage: Stage | None = None) -> None:
        with self._lock:
            stored = self._docs.get(record.partner_id)
            if stored is None:
                raise KeyError(record.partner_id)
            if expected_stage is not None and stored["stage"] != Stage(expected_stage).value:
                raise StaleUpdate(f"{record.partner_id[:12]}…: stored stage {stored['stage']} "
                                  f"!= expected {Stage(expected_stage).value}")
            self._docs[record.partner_id] = record.to_document()

    def list_all(self) -> list[PartnerRecord]:
        with self._lock:
            docs = list(self._docs.values())
        return [PartnerRecord.from_document(d) for d in docs]

    def record_milestone(self, key: str) -> bool:
        with self._lock:
            if key in self._milestones:
                return False
            self._milestones.append(key)
            return True

    def milestones(self) -> list[str]:
        with self._lock:
            return list(self._milestones)

    # test helper: the rows a BigQuery sink would have received
    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)


class FirestorePartnerStore:
    """``partners/{id}`` (current record, display name included) and
    ``partner_milestones/{key}`` (emitted-once ledger). ``create`` — never
    ``set`` — so a duplicate is a no-op (the Lane 3 ``FirestorePilotStore``
    precedent). ``client`` may be injected for tests."""

    def __init__(self, client: Any = None, project: str | None = None,
                 collection: str = FIRESTORE_COLLECTION,
                 milestone_collection: str = MILESTONE_COLLECTION) -> None:
        self._client = client
        self._project = project
        self.collection = collection
        self.milestone_collection = milestone_collection

    def _resolve(self) -> Any:
        if self._client is None:
            try:
                from google.cloud import firestore  # lazy — never at module level
            except Exception as exc:  # noqa: BLE001
                raise NotConfigured(f"google-cloud-firestore unavailable: {exc!r}") from exc
            try:
                self._client = firestore.Client(project=self._project) if self._project else firestore.Client()
            except Exception as exc:  # noqa: BLE001
                raise NotConfigured(f"firestore credentials unavailable: {exc!r}") from exc
        return self._client

    def get(self, partner_id: str) -> PartnerRecord | None:
        snap = self._resolve().collection(self.collection).document(partner_id).get()
        if not getattr(snap, "exists", False):
            return None
        return PartnerRecord.from_document(snap.to_dict() or {})

    def put_once(self, record: PartnerRecord) -> bool:
        ref = self._resolve().collection(self.collection).document(record.partner_id)
        try:
            ref.create(record.to_document())
        except Exception as exc:  # noqa: BLE001 — AlreadyExists is the idempotent no-op
            if exc.__class__.__name__ in ("AlreadyExists", "Conflict"):
                return False
            raise
        return True

    def update(self, record: PartnerRecord, expected_stage: Stage | None = None) -> None:
        """Read → check the expected stage → write with a ``last_update_time``
        precondition on the snapshot just read, so a transition that raced in
        between fails the precondition instead of being overwritten
        (verifier F-08). Write path fails loudly: nothing is swallowed."""
        client = self._resolve()
        ref = client.collection(self.collection).document(record.partner_id)
        snap = ref.get()
        if not getattr(snap, "exists", False):
            raise KeyError(record.partner_id)
        stored = snap.to_dict() or {}
        if expected_stage is not None and stored.get("stage") != Stage(expected_stage).value:
            raise StaleUpdate(f"{record.partner_id[:12]}…: stored stage {stored.get('stage')} "
                              f"!= expected {Stage(expected_stage).value}")
        option = client.write_option(last_update_time=snap.update_time)
        ref.update(record.to_document(), option=option)

    def list_all(self) -> list[PartnerRecord]:
        out = []
        for snap in self._resolve().collection(self.collection).stream():
            out.append(PartnerRecord.from_document(snap.to_dict() or {}))
        return out

    def record_milestone(self, key: str) -> bool:
        ref = self._resolve().collection(self.milestone_collection).document(key)
        try:
            ref.create({"key": key, "emitted_at": now_iso()})
        except Exception as exc:  # noqa: BLE001
            if exc.__class__.__name__ in ("AlreadyExists", "Conflict"):
                return False
            raise
        return True

    def milestones(self) -> list[str]:
        return [snap.id for snap in self._resolve().collection(self.milestone_collection).stream()]


class BigQueryPipelineSink:
    """Streaming insert of stage-event rows. ``insert_id`` is the idempotency
    key BigQuery de-duplicates on. ``client`` may be injected for tests."""

    def __init__(self, table: str = DEFAULT_BQ_TABLE, client: Any = None,
                 project: str | None = None, breaker: CircuitBreaker | None = None) -> None:
        self.table = table
        self._client = client
        self._project = project
        self.breaker = breaker or CircuitBreaker()

    def _resolve(self) -> Any:
        if self._client is None:
            try:
                from google.cloud import bigquery  # lazy — never at module level
            except Exception as exc:  # noqa: BLE001
                raise NotConfigured(f"google-cloud-bigquery unavailable: {exc!r}") from exc
            try:
                self._client = bigquery.Client(project=self._project) if self._project else bigquery.Client()
            except Exception as exc:  # noqa: BLE001
                raise NotConfigured(f"bigquery credentials unavailable: {exc!r}") from exc
        return self._client

    def append(self, rows: list[dict[str, Any]]) -> str:
        """``inserted`` | ``circuit_open`` | raises on a hard error (write paths fail loudly)."""
        if not rows:
            return "inserted"
        if not self.breaker.allow():
            return "circuit_open"
        try:
            errors = self._resolve().insert_rows_json(
                self.table, rows, row_ids=[r["insert_id"] for r in rows])
        except Exception:
            self.breaker.record(False)
            raise
        ok = not errors
        self.breaker.record(ok)
        if not ok:
            raise RuntimeError(f"bigquery insert errors: {errors!r}")
        return "inserted"


def resolve_store(env: Mapping[str, str] | None = None) -> FirestorePartnerStore | None:
    """The ONLY constructor of a real store. Flag OFF → ``None`` (caller says
    ``not_configured``). Flag ON → a Firestore store built from the
    environment; its first use raises ``NotConfigured`` if the client or the
    credentials are missing."""
    env = os.environ if env is None else env
    if not pipeline_enabled(env):
        return None
    return FirestorePartnerStore(project=env.get(PROJECT_ENV) or None)


def resolve_sink(env: Mapping[str, str] | None = None) -> BigQueryPipelineSink | None:
    env = os.environ if env is None else env
    if not pipeline_enabled(env):
        return None
    return BigQueryPipelineSink(table=env.get(BQ_TABLE_ENV, DEFAULT_BQ_TABLE),
                                project=env.get(PROJECT_ENV) or None)


def status(env: Mapping[str, str] | None = None, store: FirestorePartnerStore | None = None) -> dict[str, Any]:
    """Health line — ``configured`` ONLY when the store actually resolves
    (verifier F-04): flag OFF, missing client library, or missing credentials
    all report ``not_configured`` with the reason. Never a secret value.
    ``store`` may be injected (tests / a caller that already built one)."""
    env = os.environ if env is None else env
    line: dict[str, Any] = {"bq_table": env.get(BQ_TABLE_ENV, DEFAULT_BQ_TABLE)}
    if not pipeline_enabled(env):
        line["design_partner_pipeline"] = "not_configured"
        line["reason"] = f"{DESIGN_PARTNER_PIPELINE_ENV} is off"
        return line
    try:
        (store or resolve_store(env))._resolve()  # type: ignore[union-attr]
    except Exception as exc:  # noqa: BLE001 — any failure to resolve is not_configured
        line["design_partner_pipeline"] = "not_configured"
        line["reason"] = str(exc)[:200]
        return line
    line["design_partner_pipeline"] = "configured"
    return line
