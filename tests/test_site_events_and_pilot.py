"""Measurement without egress (Run 1 item 1.F, 2026-09-02) — both directions:

* flag OFF: /shopify bytes are IDENTICAL to the file; /event answers 204 and
  writes nothing; /shopify/pilot-request is 404; no client script rendered;
* flag ON: the stored row carries exactly ROW_FIELDS (no IP / UA / cookie /
  user id — asserted on the row AND the DDL); referrer host is never stored;
  an unconfigured sink answers 503 not_configured (never a healthy stub);
  writes carry an idempotency key; the circuit breaker opens; the pilot
  request is idempotent on sha256(email|store) and the response never echoes
  the email or store.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import SITE_EVENTS_SCRIPT, create_app
from mizoki_runtime import create_runtime, pilot_requests, site_events

REPO_ROOT = Path(__file__).resolve().parents[1]
EVENT = {"event_name": "page_view", "path": "/shopify", "variant": "none", "ts": "2026-09-02T02:17:45Z"}
IDENTITY_TOKENS = ("ip", "user_agent", "ua", "cookie", "user_id", "visitor", "session", "email", "referrer_host", "referer")


class _RecordingClient:
    def __init__(self, fail: bool = False) -> None:
        self.rows: list[dict] = []
        self.ids: list[str] = []
        self.fail = fail

    def insert_rows_json(self, table, rows, row_ids=None):
        if self.fail:
            raise RuntimeError("bq down")
        self.rows.extend(rows)
        self.ids.extend(row_ids or [])
        return []


class _RecordingFirestore:
    class _Ref:
        def __init__(self, store, doc_id):
            self.store, self.doc_id = store, doc_id

        def create(self, document):
            if self.doc_id in self.store:
                exc = type("AlreadyExists", (Exception,), {})()
                raise exc
            self.store[self.doc_id] = document

        def get(self):
            doc = self.store.get(self.doc_id)
            return type("Snap", (), {"exists": doc is not None, "to_dict": (lambda _s, d=doc: dict(d) if d else None)})()

        def update(self, fields):
            self.store[self.doc_id].update(fields)

    class _Coll:
        def __init__(self, store):
            self.store = store

        def document(self, doc_id):
            return _RecordingFirestore._Ref(self.store, doc_id)

    def __init__(self):
        self.store: dict[str, dict] = {}

    def collection(self, name):
        return _RecordingFirestore._Coll(self.store)


class _AppCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(self.temp_dir.name))
        self.app = create_app(runtime=runtime)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()
        self._env = mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        os.environ.pop("SITE_EVENTS", None)
        os.environ.pop("PILOT_FORM", None)

    def tearDown(self) -> None:
        self._env.stop()
        self.temp_dir.cleanup()


class FlagOffByteIdentical(_AppCase):
    def test_shopify_bytes_identical_to_file_with_flags_off(self) -> None:
        raw = (REPO_ROOT / "shopify.html").read_bytes()
        for path in ("/shopify", "/shopify.html"):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code)
            self.assertEqual(raw, response.data, f"{path}: flag-OFF serving must be byte-identical")
            self.assertNotIn(b'data-mizoki="site-events"', response.data)
            self.assertNotIn(b'data-mizoki="pilot-form"', response.data)
            response.close()

    def test_event_endpoints_answer_204_and_write_nothing(self) -> None:
        client = _RecordingClient()
        self.app.extensions["site_events_sink"] = site_events.BigQuerySiteEventsSink(client=client)
        for path in ("/event", "/shopify/event"):
            self.assertEqual(204, self.client.post(path, json=EVENT).status_code)
        self.assertEqual([], client.rows)

    def test_pilot_request_is_404_when_off(self) -> None:
        self.assertEqual(404, self.client.post("/shopify/pilot-request",
                                               json={"email": "a@b.co", "store": "x.myshopify.com"}).status_code)

    def test_health_reports_off(self) -> None:
        snap = self.client.get("/api/health").get_json()
        self.assertEqual("off", snap["site_events"])
        self.assertEqual("off", snap["pilot_form"])

    def test_operational_health_is_healthy_with_flags_off(self) -> None:
        response = self.client.get("/health")
        self.assertEqual((200, b"healthy"), (response.status_code, response.data))


class _Unconfigured:
    """A sink/service whose only fact is that it is not configured."""

    def configured(self) -> bool:
        return False


class FlagOnWithoutSink(_AppCase):
    """A flag ON without its sink is NOT a healthy revision — both health
    surfaces say so (#899 review, Codex P1: /health answered "healthy" while
    /api/health answered not_configured)."""

    def test_operational_health_fails_closed_per_flag(self) -> None:
        os.environ["SITE_EVENTS"] = "true"
        self.app.extensions["site_events_sink"] = _Unconfigured()
        response = self.client.get("/health")
        self.assertEqual(503, response.status_code)
        self.assertEqual(b"not_configured: SITE_EVENTS", response.data)
        self.assertEqual("not_configured", self.client.get("/api/health").get_json()["site_events"])

        os.environ["PILOT_FORM"] = "true"
        self.app.extensions["pilot_request_service"] = _Unconfigured()
        response = self.client.get("/health")
        self.assertEqual(503, response.status_code)
        self.assertEqual(b"not_configured: SITE_EVENTS,PILOT_FORM", response.data)

        os.environ["SITE_EVENTS"] = "false"
        self.assertEqual(b"not_configured: PILOT_FORM", self.client.get("/health").data)
        os.environ["PILOT_FORM"] = "false"
        self.assertEqual((200, b"healthy"), (lambda r: (r.status_code, r.data))(self.client.get("/health")))


class FlagOnSiteEvents(_AppCase):
    def setUp(self) -> None:
        super().setUp()
        os.environ["SITE_EVENTS"] = "true"
        self.bq = _RecordingClient()
        self.app.extensions["site_events_sink"] = site_events.BigQuerySiteEventsSink(client=self.bq)

    def test_operational_health_is_healthy_when_the_enabled_sink_is_configured(self) -> None:
        self.assertEqual((200, b"healthy"), (lambda r: (r.status_code, r.data))(self.client.get("/health")))

    def test_stored_row_is_exactly_the_closed_schema_and_identity_free(self) -> None:
        response = self.client.post("/event", json=EVENT, headers={
            "Referer": "https://chatgpt.com/c/abc123?q=secret", "User-Agent": "Mozilla/5.0 probe",
            "X-Forwarded-For": "203.0.113.9", "Cookie": "mv=a.0123456789abcdef"})
        self.assertEqual(204, response.status_code)
        self.assertEqual(1, len(self.bq.rows))
        row = self.bq.rows[0]
        self.assertEqual(set(site_events.ROW_FIELDS) | {"insert_id"}, set(row))
        for key in row:
            for token in IDENTITY_TOKENS:
                self.assertNotEqual(key.lower(), token, key)
        serialized = json.dumps(row)
        self.assertNotIn("203.0.113.9", serialized)
        self.assertNotIn("Mozilla", serialized)
        self.assertNotIn("0123456789abcdef", serialized)
        self.assertNotIn("chatgpt.com", serialized)   # host never stored
        self.assertNotIn("secret", serialized)
        self.assertEqual("ai_answer_engine", row["referrer_class"])
        self.assertEqual("2026-09-02T02:00:00Z", row["ts_bucket_1h"])   # hour bucket, not the raw ts
        self.assertEqual(self.bq.ids, [row["insert_id"]])              # idempotency key sent

    def test_ddl_has_no_identity_column(self) -> None:
        cols = re.findall(r"^\s{2}(\w+)\s+(STRING|TIMESTAMP)", site_events.DDL, re.M)
        names = [c[0] for c in cols]
        self.assertEqual(list(site_events.ROW_FIELDS) + ["insert_id"], names)
        for name in names:
            self.assertNotIn(name.lower(), IDENTITY_TOKENS)
        self.assertIn("CREATE TABLE IF NOT EXISTS", site_events.DDL)   # additive only
        self.assertNotIn("ALTER TABLE", site_events.DDL)

    def test_referrer_classes_are_the_closed_set(self) -> None:
        cases = {None: "direct", "https://mizoki3.com/signal": "direct",
                 "https://www.google.com/search?q=x": "search",
                 "https://www.perplexity.ai/search/x": "ai_answer_engine",
                 "https://www.linkedin.com/feed/": "social",
                 "https://example.org/page": "other"}
        for ref, want in cases.items():
            self.assertEqual(want, site_events.classify_referrer(ref), ref)
            self.assertIn(want, site_events.REFERRER_CLASSES)

    def test_closed_vocabulary_rejects_unknown_events_paths_and_fields(self) -> None:
        bad = [dict(EVENT, event_name="login"), dict(EVENT, path="/admin"), dict(EVENT, variant="z"),
               dict(EVENT, ts="yesterday"), dict(EVENT, user_id="u1"), "not-an-object"]
        for payload in bad:
            response = self.client.post("/event", data=json.dumps(payload), content_type="application/json")
            self.assertEqual(400, response.status_code, payload)
        self.assertEqual([], self.bq.rows)

    def test_oversized_body_is_rejected(self) -> None:
        big = dict(EVENT, path="/shopify" + "?" + "x" * 600)
        self.assertEqual(400, self.client.post("/event", json=big).status_code)

    def test_unconfigured_sink_is_503_not_configured_and_health_says_so(self) -> None:
        self.app.extensions["site_events_sink"] = site_events.NullSink()
        response = self.client.post("/event", json=EVENT)
        self.assertEqual(503, response.status_code)
        self.assertEqual("not_configured", response.get_json()["status"])
        self.assertEqual("not_configured", self.client.get("/api/health").get_json()["site_events"])

    def test_configured_sink_reports_configured(self) -> None:
        self.assertEqual("configured", self.client.get("/api/health").get_json()["site_events"])

    def test_circuit_breaker_opens_after_failures(self) -> None:
        sink = site_events.BigQuerySiteEventsSink(client=_RecordingClient(fail=True),
                                                  breaker=site_events.CircuitBreaker(threshold=2, cooldown_s=999))
        self.app.extensions["site_events_sink"] = sink
        self.assertEqual(503, self.client.post("/event", json=EVENT).status_code)
        self.assertEqual(503, self.client.post("/event", json=EVENT).status_code)
        self.assertEqual("open", sink.breaker.state)
        self.assertEqual("circuit_open", sink.write(site_events.build_row(site_events.validate(EVENT)[0], None)))

    def test_client_script_is_rendered_only_on_and_is_same_origin(self) -> None:
        html = self.client.get("/shopify").data.decode("utf-8")
        self.assertIn('data-mizoki="site-events"', html)
        self.assertLessEqual(len(SITE_EVENTS_SCRIPT.encode("utf-8")), 1024)
        self.assertIn('fetch("/event"', SITE_EVENTS_SCRIPT)
        self.assertNotRegex(SITE_EVENTS_SCRIPT, r"https?://")           # no third-party endpoint
        self.assertNotIn("<script src", html.split('data-mizoki="site-events"')[1])
        for name in ("calculator_complete", "outbound_click", "page_view"):
            self.assertIn(name, SITE_EVENTS_SCRIPT)
        # pilot_cta_click rides the form button's data-event attribute (the
        # script forwards any data-event it finds); pinned on the form fragment.
        from app import PILOT_FORM_HTML
        self.assertIn('data-event="pilot_cta_click"', PILOT_FORM_HTML)
        self.assertIn("a.dataset.event", SITE_EVENTS_SCRIPT)
        for name in site_events.EVENT_ALLOWLIST:
            self.assertTrue(name in SITE_EVENTS_SCRIPT or name in PILOT_FORM_HTML, name)
        os.environ["SITE_EVENTS"] = "false"
        self.assertNotIn('data-mizoki="site-events"', self.client.get("/shopify").data.decode("utf-8"))


class FlagOnPilotForm(_AppCase):
    def setUp(self) -> None:
        super().setUp()
        os.environ["PILOT_FORM"] = "true"
        self.fs = _RecordingFirestore()
        self.sent: list[dict] = []

        class _Resp:
            status = 202

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(req, timeout=0):
            self.sent.append(json.loads(req.data))
            return _Resp()

        with mock.patch.dict(os.environ, {"SENDGRID_API_KEY": "SG.test", "PILOT_NOTIFY_TO": "owner@example.test",
                                          "PILOT_NOTIFY_FROM": "noreply@example.test"}):
            self.notifier = pilot_requests.SendGridNotifier(opener=opener)
        self.env_ok = {"SENDGRID_API_KEY": "SG.test", "PILOT_NOTIFY_TO": "owner@example.test",
                       "PILOT_NOTIFY_FROM": "noreply@example.test"}
        self.app.extensions["pilot_request_service"] = pilot_requests.PilotRequestService(
            store=pilot_requests.FirestorePilotStore(client=self.fs), notifier=self.notifier)

    def test_form_is_injected_only_on_and_links_the_privacy_statement(self) -> None:
        html = self.client.get("/shopify").data.decode("utf-8")
        self.assertIn('data-mizoki="pilot-form"', html)
        self.assertIn('action="/shopify/pilot-request"', html)
        self.assertIn("privacy_statement_pilot", html)
        self.assertTrue((REPO_ROOT.parent / "docs" / "marketing" / "privacy_statement_pilot.md").is_file())
        os.environ["PILOT_FORM"] = "false"
        self.assertEqual((REPO_ROOT / "shopify.html").read_bytes(), self.client.get("/shopify").data)

    def test_submit_is_idempotent_on_sha256_email_store_and_never_echoes(self) -> None:
        with mock.patch.dict(os.environ, self.env_ok):
            body = {"email": "Merchant@Example.com ", "store": "https://Example.myshopify.com/admin"}
            first = self.client.post("/shopify/pilot-request", json=body)
            self.assertEqual(202, first.status_code)
            data = first.get_json()
            self.assertEqual(pilot_requests.request_id("merchant@example.com", "example.myshopify.com"), data["request_id"])
            self.assertFalse(data["duplicate"])
            self.assertNotIn("example", json.dumps(data).lower().replace(data["request_id"], ""))
            second = self.client.post("/shopify/pilot-request", json=body)
            self.assertEqual(202, second.status_code)
            self.assertTrue(second.get_json()["duplicate"])
        self.assertEqual(1, len(self.fs.store))
        self.assertEqual(1, len(self.sent))                    # one notification, not two
        self.assertEqual("SOURCED", next(iter(self.fs.store.values()))["stage"])
        self.assertNotIn("SG.test", json.dumps(self.sent))     # key never in the mail body
        self.assertEqual("sent", next(iter(self.fs.store.values()))["notify"])

    def test_lost_notification_is_not_acknowledged_and_the_retry_resends_it(self) -> None:
        """#899 review (Codex P1): Firestore ok + SendGrid down must not answer 202,
        and the duplicate resubmission must re-send the owed mail, once."""
        body = {"email": "merchant@example.com", "store": "example.myshopify.com"}
        down = pilot_requests.SendGridNotifier(opener=mock.Mock(side_effect=OSError("sendgrid down")))
        svc = self.app.extensions["pilot_request_service"]
        svc.notifier = down
        with mock.patch.dict(os.environ, self.env_ok):
            first = self.client.post("/shopify/pilot-request", json=body)
            self.assertEqual(503, first.status_code)
            self.assertEqual({"status": "notify_failed", "retry": True,
                              "request_id": pilot_requests.request_id(body["email"], body["store"])},
                             first.get_json())
            self.assertEqual(1, len(self.fs.store))                      # persisted
            self.assertEqual("failed", next(iter(self.fs.store.values()))["notify"])
            svc.notifier = self.notifier                                  # SendGrid back
            second = self.client.post("/shopify/pilot-request", json=body)
            self.assertEqual(202, second.status_code)
            self.assertTrue(second.get_json()["duplicate"])
            third = self.client.post("/shopify/pilot-request", json=body)
            self.assertEqual(202, third.status_code)
        self.assertEqual(1, len(self.sent))                               # sent once, on the retry
        self.assertEqual("sent", next(iter(self.fs.store.values()))["notify"])

    def test_invalid_inputs_are_400(self) -> None:
        with mock.patch.dict(os.environ, self.env_ok):
            for payload in ({"email": "nope", "store": "x.myshopify.com"}, {"email": "a@b.co", "store": ""},
                            {"email": "a@b.co", "store": "x.myshopify.com", "phone": "1"}):
                self.assertEqual(400, self.client.post("/shopify/pilot-request", json=payload).status_code, payload)
        self.assertEqual({}, self.fs.store)

    def test_missing_secrets_fail_closed(self) -> None:
        for key in ("SENDGRID_API_KEY", "PILOT_NOTIFY_TO", "PILOT_NOTIFY_FROM"):
            os.environ.pop(key, None)
        response = self.client.post("/shopify/pilot-request", json={"email": "a@b.co", "store": "x.myshopify.com"})
        self.assertEqual(503, response.status_code)
        self.assertEqual("not_configured", response.get_json()["status"])
        self.assertEqual("not_configured", self.client.get("/api/health").get_json()["pilot_form"])
        self.assertEqual({}, self.fs.store)


if __name__ == "__main__":
    unittest.main()
