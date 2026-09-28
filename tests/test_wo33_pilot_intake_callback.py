"""WO-33 (#1003) — the site pilot request is wired to the design-partner
pipeline intake behind ``DESIGN_PARTNER_PIPELINE`` (default ``"false"``).

Ruled packaging path (2026-09-15): the pipeline package is VENDORED into
``mizoki_runtime/design_partner_pipeline/`` (the site runtime does not import
``src/shared``), byte-identical to ``src/shared/design_partner_pipeline/``
(parity test in ``tests/gtm/test_design_partner_vendor_parity.py`` and below).

Acceptance: flag ON → a submitted request creates a SOURCED partner in the
intake store (``partner_id == sha256(email|store)``); a hook failure is
surfaced in the response (``pipeline: "failed"``), never silently dropped;
flag ON with no resolvable store → 503 ``not_configured`` naming the flag;
flag OFF → the response is byte-identical to the pre-WO-33 shape.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402
from mizoki_runtime import create_runtime, pilot_requests  # noqa: E402

SITE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SITE_ROOT.parent
VENDORED = SITE_ROOT / "mizoki_runtime" / "design_partner_pipeline"
CANONICAL = REPO_ROOT / "src" / "shared" / "design_partner_pipeline"

ENV_OK = {"SENDGRID_API_KEY": "SG.test", "PILOT_NOTIFY_TO": "owner@example.test",
          "PILOT_NOTIFY_FROM": "noreply@example.test", "PILOT_FORM": "true"}
BODY = {"email": "merchant@example.com", "store": "example.myshopify.com"}


class _Store:
    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}

    def configured(self) -> bool:
        return True

    def create(self, doc_id, document):
        if doc_id in self.docs:
            return "duplicate"
        self.docs[doc_id] = dict(document)
        return "created"

    def get(self, doc_id):
        return dict(self.docs[doc_id]) if doc_id in self.docs else None

    def set_notify(self, doc_id, state):
        self.docs[doc_id]["notify"] = state


class _Resp:
    status = 202

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FailingPartnerStore:
    def get(self, partner_id):
        return None

    def put_once(self, record):
        raise RuntimeError("partner store down")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class VendorParity(unittest.TestCase):
    def test_wo33_vendored_pipeline_is_byte_identical_to_src_shared(self) -> None:
        self.assertTrue(VENDORED.is_dir(), "mizoki_runtime/design_partner_pipeline is not vendored")
        canonical = sorted(p.name for p in CANONICAL.glob("*.py"))
        vendored = sorted(p.name for p in VENDORED.glob("*.py"))
        self.assertEqual(canonical, vendored)
        for name in canonical:
            self.assertEqual(_sha(CANONICAL / name), _sha(VENDORED / name), f"drift: {name}")

    def test_wo33_flag_default_is_the_literal_false(self) -> None:
        from mizoki_runtime.design_partner_pipeline import flags
        import inspect
        self.assertIn('env.get(DESIGN_PARTNER_PIPELINE_ENV, "false")', inspect.getsource(flags))
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(flags.pipeline_enabled())


class PilotCallback(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(create_runtime())
        self.app.testing = True
        self.client = self.app.test_client()
        self.sent: list[dict] = []

        def opener(req, timeout=0):
            self.sent.append(json.loads(req.data))
            return _Resp()

        self.app.extensions["pilot_request_store"] = _Store()
        self.app.extensions["pilot_request_notifier"] = pilot_requests.SendGridNotifier(opener=opener)

    def _partner_store(self):
        from mizoki_runtime.design_partner_pipeline.store import InMemoryPartnerStore
        store = InMemoryPartnerStore()
        self.app.extensions["design_partner_store"] = store
        return store

    def test_wo33_flag_on_submit_creates_a_sourced_partner_in_the_intake_store(self) -> None:
        store = self._partner_store()
        with mock.patch.dict(os.environ, {**ENV_OK, "DESIGN_PARTNER_PIPELINE": "true"}):
            res = self.client.post("/shopify/pilot-request", json=BODY)
            self.assertEqual(202, res.status_code, res.get_json())
            data = res.get_json()
            self.assertEqual("sourced", data["pipeline"])
            rid = pilot_requests.request_id(BODY["email"], BODY["store"])
            self.assertEqual(rid, data["request_id"])
            partner = store.get(rid)
            self.assertIsNotNone(partner, "intake record missing")
            self.assertEqual("SOURCED", partner.stage.value)
            self.assertEqual(BODY["store"], partner.display_name)      # never the e-mail
            self.assertNotIn(BODY["email"], json.dumps(partner.to_document()))
            # duplicate: the pipeline is NOT re-sourced and says so
            again = self.client.post("/shopify/pilot-request", json=BODY)
            self.assertEqual(202, again.status_code)
            self.assertEqual("skipped", again.get_json()["pipeline"])
            self.assertEqual(1, len(store.list_all()))
            self.assertEqual("configured", self.client.get("/api/health").get_json()["design_partner_pipeline"])

    def test_wo33_hook_failure_is_surfaced_not_silently_dropped(self) -> None:
        self.app.extensions["design_partner_store"] = _FailingPartnerStore()
        with mock.patch.dict(os.environ, {**ENV_OK, "DESIGN_PARTNER_PIPELINE": "true"}):
            res = self.client.post("/shopify/pilot-request", json=BODY)
        # persisted + notified, so 202 — but the pipeline leg is reported failed
        self.assertEqual(202, res.status_code, res.get_json())
        self.assertEqual("failed", res.get_json()["pipeline"])
        self.assertEqual(1, len(self.sent))

    def test_wo33_flag_on_without_a_store_is_503_not_configured(self) -> None:
        # No injected store, no credentials/client library in the sandbox.
        with mock.patch.dict(os.environ, {**ENV_OK, "DESIGN_PARTNER_PIPELINE": "true"}):
            res = self.client.post("/shopify/pilot-request", json=BODY)
            self.assertEqual(503, res.status_code)
            self.assertEqual({"status": "not_configured", "flag": "DESIGN_PARTNER_PIPELINE"}, res.get_json())
            self.assertEqual({}, self.app.extensions["pilot_request_store"].docs)   # nothing persisted
            self.assertEqual("not_configured", self.client.get("/api/health").get_json()["design_partner_pipeline"])
            self.assertEqual(503, self.client.get("/health").status_code)

    def test_wo33_flag_off_response_is_byte_identical_and_no_partner_is_created(self) -> None:
        store = self._partner_store()
        with mock.patch.dict(os.environ, {**ENV_OK, "DESIGN_PARTNER_PIPELINE": "false"}):
            res = self.client.post("/shopify/pilot-request", json=BODY)
            self.assertEqual(202, res.status_code)
            self.assertEqual({"status": "received", "duplicate": False,
                              "request_id": pilot_requests.request_id(BODY["email"], BODY["store"])},
                             res.get_json())
            self.assertEqual("off", self.client.get("/api/health").get_json()["design_partner_pipeline"])
        self.assertEqual([], store.list_all())


if __name__ == "__main__":
    unittest.main()
