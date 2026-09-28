"""``PilotRequestService(on_sourced=...)`` — the flag-OFF extension point for
the design-partner pipeline (Strategy S1, Lane 6). Both directions: the hook
fires once for a newly created document and never for a duplicate; the
default is inert; a failing hook never changes the request outcome."""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mizoki_runtime import pilot_requests  # noqa: E402


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


ENV = {"SENDGRID_API_KEY": "SG.test", "PILOT_NOTIFY_TO": "owner@example.test", "PILOT_NOTIFY_FROM": "noreply@example.test"}
FIELDS = {"email": "merchant@example.test", "store": "example.myshopify.com"}


def _service(hook=None):
    notifier = pilot_requests.SendGridNotifier(opener=lambda req, timeout=0: _Resp())
    return pilot_requests.PilotRequestService(store=_Store(), notifier=notifier, on_sourced=hook)


class SourcedHook(unittest.TestCase):
    def test_default_is_inert(self) -> None:
        svc = _service()
        self.assertIsNone(svc.on_sourced)
        with mock.patch.dict(os.environ, ENV):
            self.assertEqual("created", svc.submit(FIELDS)["store"])

    def test_hook_fires_once_for_created_never_for_duplicate(self) -> None:
        seen: list[dict] = []
        svc = _service(seen.append)
        with mock.patch.dict(os.environ, ENV):
            first = svc.submit(FIELDS)
            second = svc.submit(FIELDS)
        self.assertEqual(("created", "duplicate"), (first["store"], second["store"]))
        self.assertEqual(1, len(seen))
        doc = seen[0]
        self.assertEqual(doc["request_id"], pilot_requests.request_id(FIELDS["email"], FIELDS["store"]))
        self.assertEqual("SOURCED", doc["stage"])
        # the hook receives a COPY: mutating it cannot reach the persisted document
        doc["stage"] = "TAMPERED"
        self.assertEqual("SOURCED", svc.store.docs[doc["request_id"]]["stage"])

    def test_failing_hook_never_changes_the_outcome(self) -> None:
        def boom(_doc):
            raise RuntimeError("pipeline down")
        svc = _service(boom)
        with mock.patch.dict(os.environ, ENV):
            result = svc.submit(FIELDS)
        self.assertEqual({"store": "created", "notify": "sent"}, {k: result[k] for k in ("store", "notify")})
        self.assertEqual("sent", svc.store.docs[result["request_id"]]["notify"])


if __name__ == "__main__":
    unittest.main()
