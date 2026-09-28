import json
import os
import re
import tempfile
import unittest
from pathlib import Path

import app as app_module
from app import create_app
from mizoki_runtime import create_runtime


REPO_ROOT = Path(__file__).resolve().parents[1]


class FlaskAppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(self.temp_dir.name))
        app = create_app(runtime=runtime)
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_root_static_assets_are_served(self) -> None:
        response = self.client.get("/app.js")
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Application JavaScript", response.data)
        response.close()

    def test_mcp_tools_endpoint_returns_registered_tools(self) -> None:
        response = self.client.get("/api/mcp/tools")
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertIn("tools", payload)
        self.assertTrue(any(tool["name"] == "graphrag.query" for tool in payload["tools"]))

    def test_boss_execute_endpoint_selects_tool_and_returns_context(self) -> None:
        response = self.client.post(
            "/api/boss/execute",
            json={"intent": "Explain the Decision Control Plane."},
        )
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertIn("selection", payload)
        self.assertIn("context", payload)
        self.assertIn("candidates", payload)
        self.assertTrue(payload["context"]["matched_entities"])

    def test_learn_skill_endpoint_validates_required_fields(self) -> None:
        response = self.client.post("/api/boss/skills/learn", json={"name": "bad"})
        self.assertEqual(400, response.status_code)
        self.assertIn("Missing required field", response.get_json()["error"])

    def test_mcp_call_returns_400_for_unknown_tools(self) -> None:
        response = self.client.post("/api/mcp/call", json={"name": "nope", "arguments": {}})
        self.assertEqual(400, response.status_code)
        self.assertIn("unknown tool", response.get_json()["error"])

    def test_duplicate_skill_returns_400_instead_of_server_error(self) -> None:
        first_response = self.client.post(
            "/api/boss/skills/learn",
            json={"name": "dcp", "description": "desc", "trigger_phrases": ["decision control plane"]},
        )
        self.assertEqual(200, first_response.status_code)

        second_response = self.client.post(
            "/api/boss/skills/learn",
            json={"name": "dcp", "description": "desc", "trigger_phrases": ["decision control plane"]},
        )
        self.assertEqual(400, second_response.status_code)
        self.assertIn("skill already exists", second_response.get_json()["error"])

    def test_boss_can_learn_skill_via_natural_language_execute_request(self) -> None:
        response = self.client.post(
            "/api/boss/execute",
            json={"intent": "Learn a new skill for decision control plane questions."},
        )
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertEqual("skills.learn", payload["selection"]["tool_name"])
        self.assertIn("decision.explain_pipeline", payload["execution"]["result"]["skill"]["preferred_tools"])

    def test_graph_native_context_and_loop_endpoints_work(self) -> None:
        context_response = self.client.post(
            "/api/boss/graph/context",
            json={"intent": "Map the graph-native context for the decision control plane."},
        )
        self.assertEqual(200, context_response.status_code)
        context_payload = context_response.get_json()
        self.assertIn("context", context_payload)
        self.assertTrue(context_payload["context"]["recommended_subagents"])

        loop_response = self.client.post(
            "/api/boss/graph/loop",
            json={
                "intent": "Run the graph-native decision loop for platform governance.",
                "goal": "Produce an audit-ready decision path.",
            },
        )
        self.assertEqual(200, loop_response.status_code)
        loop_payload = loop_response.get_json()
        self.assertIn("trace_id", loop_payload)
        self.assertIn("act", loop_payload)
        self.assertTrue(loop_payload["act"]["assigned_subagents"])

        simulation_response = self.client.post(
            "/api/boss/graph/simulate",
            json={
                "intent": "Simulate a counterfactual for the decision control plane.",
                "proposed_action": "Tighten validation before action.",
            },
        )
        self.assertEqual(200, simulation_response.status_code)
        simulation_payload = simulation_response.get_json()
        self.assertIn("counterfactual_delta", simulation_payload)

    def test_graph_native_subagent_endpoint_lists_cells(self) -> None:
        response = self.client.get("/api/boss/graph/subagents")
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertIn("subagents", payload)
        self.assertTrue(any(item["stage"] == "sense" for item in payload["subagents"]))

    def test_learn_skill_from_loop_endpoint_promotes_recent_loop(self) -> None:
        loop_response = self.client.post(
            "/api/boss/graph/loop",
            json={"intent": "Run the graph-native decision loop for platform governance."},
        )
        self.assertEqual(200, loop_response.status_code)
        trace_id = loop_response.get_json()["trace_id"]

        learn_response = self.client.post(
            "/api/boss/skills/learn-from-loop",
            json={"trace_id": trace_id},
        )
        self.assertEqual(200, learn_response.status_code)
        payload = learn_response.get_json()
        self.assertIn("skill", payload)
        self.assertTrue(payload["skill"]["preferred_tools"])

    def test_graph_context_endpoint_rejects_invalid_top_k(self) -> None:
        response = self.client.post(
            "/api/boss/graph/context",
            json={"intent": "Explain the platform.", "top_k": 0},
        )
        self.assertEqual(400, response.status_code)
        self.assertIn("at least 1", response.get_json()["error"])


class AdminAuthAndAPIGateTestCase(unittest.TestCase):
    """Cover the new /admin login flow and the opt-in API auth gate."""

    DEMO_USERS = {"admin@mizoki3.com": "test-pw"}

    def _make_app(self, *, require_api_auth: bool = False, demo_users: dict | None = None):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        old_users = os.environ.get("MIZOKI_DEMO_USERS_JSON")
        old_gate = os.environ.get("MIZOKI_REQUIRE_AUTH_FOR_APIS")
        users = self.DEMO_USERS if demo_users is None else demo_users
        os.environ["MIZOKI_DEMO_USERS_JSON"] = json.dumps(users) if users else ""
        os.environ["MIZOKI_REQUIRE_AUTH_FOR_APIS"] = "true" if require_api_auth else "false"

        def _restore():
            if old_users is None:
                os.environ.pop("MIZOKI_DEMO_USERS_JSON", None)
            else:
                os.environ["MIZOKI_DEMO_USERS_JSON"] = old_users
            if old_gate is None:
                os.environ.pop("MIZOKI_REQUIRE_AUTH_FOR_APIS", None)
            else:
                os.environ["MIZOKI_REQUIRE_AUTH_FOR_APIS"] = old_gate

        self.addCleanup(_restore)
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(temp_dir.name))
        app = create_app(runtime=runtime)
        app.config.update(TESTING=True)
        return app.test_client()

    def test_admin_unauth_redirects_to_login(self) -> None:
        client = self._make_app()
        r = client.get("/admin")
        self.assertEqual(302, r.status_code)
        self.assertIn("/admin/login", r.headers["Location"])

    def test_admin_login_form_renders(self) -> None:
        client = self._make_app()
        r = client.get("/admin/login")
        self.assertEqual(200, r.status_code)
        self.assertIn(b"Admin sign-in", r.data)

    def test_admin_login_with_bad_password_redirects_back(self) -> None:
        client = self._make_app()
        r = client.post(
            "/admin/login",
            data={"email": "admin@mizoki3.com", "password": "wrong"},
        )
        self.assertEqual(302, r.status_code)
        self.assertIn("/admin/login", r.headers["Location"])

    def test_admin_login_with_good_password_grants_session(self) -> None:
        client = self._make_app()
        r = client.post(
            "/admin/login",
            data={"email": "admin@mizoki3.com", "password": "test-pw"},
        )
        self.assertEqual(302, r.status_code)
        self.assertIn("/admin/", r.headers["Location"])
        # Follow redirect — dashboard should render
        r2 = client.get("/admin")
        self.assertEqual(200, r2.status_code)
        self.assertIn(b"Backend dashboard", r2.data)

    def test_admin_logout_clears_session(self) -> None:
        client = self._make_app()
        client.post(
            "/admin/login",
            data={"email": "admin@mizoki3.com", "password": "test-pw"},
        )
        client.get("/admin/logout")
        r = client.get("/admin")
        self.assertEqual(302, r.status_code)
        self.assertIn("/admin/login", r.headers["Location"])

    # ----- Opt-in API auth gate -------------------------------------------

    def test_api_gate_off_by_default_apis_are_public(self) -> None:
        client = self._make_app(require_api_auth=False)
        r = client.get("/api/mcp/tools")
        self.assertEqual(200, r.status_code)
        r2 = client.get("/api/boss/discover")
        self.assertEqual(200, r2.status_code)

    def test_api_gate_on_blocks_unauthenticated_callers(self) -> None:
        client = self._make_app(require_api_auth=True)
        r = client.get("/api/mcp/tools")
        self.assertEqual(401, r.status_code)
        self.assertIn("Authentication required", r.get_json()["error"])

    def test_api_gate_on_allows_signed_in_callers(self) -> None:
        client = self._make_app(require_api_auth=True)
        client.post(
            "/admin/login",
            data={"email": "admin@mizoki3.com", "password": "test-pw"},
        )
        r = client.get("/api/mcp/tools")
        self.assertEqual(200, r.status_code)

    def test_api_gate_always_lets_health_through(self) -> None:
        client = self._make_app(require_api_auth=True)
        r = client.get("/api/health")
        self.assertEqual(200, r.status_code)

    # ----- Admin-login state surfaced on /api/health ----------------------

    def test_health_reports_admin_login_enabled(self) -> None:
        client = self._make_app()
        r = client.get("/api/health")
        self.assertEqual(200, r.status_code)
        self.assertTrue(r.get_json()["admin_login_enabled"])

    def test_health_reports_admin_login_disabled_when_no_users(self) -> None:
        client = self._make_app(demo_users={})
        r = client.get("/api/health")
        self.assertEqual(200, r.status_code)
        self.assertFalse(r.get_json()["admin_login_enabled"])

    def test_login_with_no_users_configured_flashes_disabled(self) -> None:
        client = self._make_app(demo_users={})
        r = client.post(
            "/admin/login",
            data={"email": "admin@mizoki3.com", "password": "anything"},
            follow_redirects=True,
        )
        self.assertEqual(200, r.status_code)
        self.assertIn(b"Local admin login is disabled", r.data)


class LoginGateHardeningTestCase(unittest.TestCase):
    """CSRF + attempt-throttling + constant-time compare on the sign-in form.

    MIZ-SEC 2026-08-22. `/admin/login` is public, unauthenticated, and since
    the 2026-08-21 internal-docs directive it is the only gate in front of
    `/docs/internal` (production infrastructure identifiers and build
    instructions). It previously accepted unlimited attempts at full speed,
    carried no CSRF token, and compared passwords with `==`.

    Pinned in BOTH directions per `.claude/rules/01-verification-discipline.md`:
    every case that must be REFUSED has a sibling proving the legitimate flow
    still succeeds — a gate that also blocks the operator is the opposite
    failure, and just as bad.
    """

    DEMO_USERS = {"admin@mizoki3.com": "test-pw"}

    def _make_app(self, *, enforce_csrf: bool = True, enforce_rate: bool = False,
                  login_per_min: int = 5):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        old_users = os.environ.get("MIZOKI_DEMO_USERS_JSON")
        os.environ["MIZOKI_DEMO_USERS_JSON"] = json.dumps(self.DEMO_USERS)

        def _restore():
            if old_users is None:
                os.environ.pop("MIZOKI_DEMO_USERS_JSON", None)
            else:
                os.environ["MIZOKI_DEMO_USERS_JSON"] = old_users

        self.addCleanup(_restore)
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(temp_dir.name))
        app = create_app(runtime=runtime)
        app.config.update(
            TESTING=True,
            LOGIN_CSRF_ENFORCE_IN_TESTS=enforce_csrf,
            LOGIN_RATE_LIMIT_ENFORCE_IN_TESTS=enforce_rate,
        )
        if enforce_rate:
            # Rebuild the limiter so the tightened budget actually applies.
            app.extensions["demo_rate_limiter"] = app_module.DemoRateLimiter(
                per_min=app.config["DEMO_RATE_PER_MIN"],
                burst=app.config["DEMO_RATE_BURST"],
                telemetry_per_min=app.config["DEMO_TELEMETRY_RATE_PER_MIN"],
                login_per_min=login_per_min,
            )
        return app.test_client()

    @staticmethod
    def _token(client) -> str:
        """Fetch the sign-in page and read the token out of the rendered form."""
        html = client.get("/admin/login").data.decode()
        match = re.search(r'name="csrf_token" value="([^"]+)"', html)
        assert match, "sign-in form rendered no csrf_token field"
        return match.group(1)

    # ----- CSRF: the form must carry a token ------------------------------
    def test_login_form_renders_a_csrf_token(self) -> None:
        client = self._make_app()
        self.assertTrue(self._token(client))

    def test_login_with_valid_csrf_token_succeeds(self) -> None:
        """The direction that matters most: the gate must not lock the operator out."""
        client = self._make_app()
        token = self._token(client)
        r = client.post("/admin/login", data={
            "email": "admin@mizoki3.com", "password": "test-pw", "csrf_token": token,
        })
        self.assertEqual(302, r.status_code)
        self.assertIn("/admin/", r.headers["Location"])
        self.assertEqual(200, client.get("/admin").status_code)

    def test_login_without_csrf_token_is_refused(self) -> None:
        client = self._make_app()
        self._token(client)  # establish a session, then omit the field
        r = client.post("/admin/login", data={
            "email": "admin@mizoki3.com", "password": "test-pw",
        })
        self.assertEqual(302, r.status_code)
        self.assertIn("/admin/login", r.headers["Location"])
        # Refused means NO session was granted — not merely a redirect.
        self.assertEqual(302, client.get("/admin").status_code)

    def test_login_with_wrong_csrf_token_is_refused(self) -> None:
        client = self._make_app()
        self._token(client)
        r = client.post("/admin/login", data={
            "email": "admin@mizoki3.com", "password": "test-pw",
            "csrf_token": "not-the-right-token",
        })
        self.assertEqual(302, r.status_code)
        self.assertEqual(302, client.get("/admin").status_code)

    def test_csrf_token_is_rotated_after_sign_in(self) -> None:
        """Session fixation: a token planted before sign-in must not survive it."""
        client = self._make_app()
        before = self._token(client)
        client.post("/admin/login", data={
            "email": "admin@mizoki3.com", "password": "test-pw", "csrf_token": before,
        })
        with client.session_transaction() as sess:
            self.assertIsNone(sess.get("_csrf_token"))

    # ----- Attempt throttling ---------------------------------------------
    def test_sign_in_attempts_are_throttled(self) -> None:
        client = self._make_app(enforce_csrf=False, enforce_rate=True, login_per_min=3)
        for i in range(3):
            r = client.post("/admin/login", data={
                "email": "admin@mizoki3.com", "password": "wrong",
            })
            self.assertEqual(302, r.status_code, f"attempt {i + 1} should be allowed")
        blocked = client.post("/admin/login", data={
            "email": "admin@mizoki3.com", "password": "wrong",
        })
        self.assertEqual(429, blocked.status_code)
        self.assertIn("Retry-After", blocked.headers)
        self.assertIn(b"Too many sign-in attempts", blocked.data)

    def test_throttle_also_covers_the_second_login_post_path(self) -> None:
        """/login has no form but checks the same passwords — one door is not a gate."""
        client = self._make_app(enforce_csrf=False, enforce_rate=True, login_per_min=2)
        for _ in range(2):
            client.post("/login", data={"email": "x@y.z", "password": "wrong"})
        blocked = client.post("/login", data={"email": "x@y.z", "password": "wrong"})
        self.assertEqual(429, blocked.status_code)

    def test_throttle_does_not_touch_the_form_get(self) -> None:
        """Reloading the sign-in page is not an attempt and must never 429."""
        client = self._make_app(enforce_csrf=False, enforce_rate=True, login_per_min=2)
        for _ in range(8):
            self.assertEqual(200, client.get("/admin/login").status_code)

    def test_throttle_does_not_touch_unrelated_posts(self) -> None:
        client = self._make_app(enforce_csrf=False, enforce_rate=True, login_per_min=1)
        client.post("/admin/login", data={"email": "a@b.c", "password": "x"})
        # A different POST path must not be drawing down the login bucket.
        r = client.post("/api/demo/telemetry", json={"event": "ping"})
        self.assertNotEqual(429, r.status_code)

    # ----- Constant-time, hashed credential comparison ---------------------
    #
    # `_check_demo_credentials` operates on werkzeug hashes, never plaintext
    # (MIZ-SEC 2026-08-26: MIZOKI_DEMO_USERS_JSON values are now hashed at
    # rest in process memory too, not just compared in constant time). Run
    # DEMO_USERS through the same normalizer `_load_demo_users` uses so these
    # tests exercise the real hash-verification path.
    HASHED_DEMO_USERS = app_module._normalize_demo_users(DEMO_USERS)

    def test_credential_check_accepts_the_real_password(self) -> None:
        self.assertTrue(app_module._check_demo_credentials(
            self.HASHED_DEMO_USERS, "admin@mizoki3.com", "test-pw"))

    def test_credential_check_rejects_a_wrong_password(self) -> None:
        self.assertFalse(app_module._check_demo_credentials(
            self.HASHED_DEMO_USERS, "admin@mizoki3.com", "test-pX"))

    def test_credential_check_rejects_an_unknown_email(self) -> None:
        self.assertFalse(app_module._check_demo_credentials(
            self.HASHED_DEMO_USERS, "nobody@example.com", "test-pw"))

    def test_credential_check_rejects_the_placeholder_itself(self) -> None:
        """The unknown-email dummy must never be usable as a password."""
        self.assertFalse(app_module._check_demo_credentials(
            self.HASHED_DEMO_USERS, "nobody@example.com", app_module._ABSENT_USER_PLACEHOLDER))

    def test_credential_check_survives_a_non_ascii_password(self) -> None:
        """A form field is arbitrary input — a non-ASCII password must never
        turn into a 500, hashed comparison or not."""
        self.assertFalse(app_module._check_demo_credentials(
            self.HASHED_DEMO_USERS, "admin@mizoki3.com", "pass\u00e9\u00e9word"))
        self.assertFalse(app_module._check_demo_credentials(
            self.HASHED_DEMO_USERS, "\u00fcser@example.com", "\u00e9"))

    def test_demo_users_are_never_stored_as_plaintext(self) -> None:
        """The actual security property: no configured password survives
        `_load_demo_users`/`_normalize_demo_users` as a raw comparable string."""
        for stored in self.HASHED_DEMO_USERS.values():
            self.assertTrue(stored.startswith(app_module._HASH_PREFIXES))
            self.assertNotIn("test-pw", stored)

    def test_normalize_demo_users_passes_through_an_already_hashed_value(self) -> None:
        """A secret rotated to a real werkzeug hash must not be re-hashed
        (that would hash a hash, not verify the intended password)."""
        pre_hashed = app_module.generate_password_hash(
            "test-pw", method=app_module._DEMO_PASSWORD_HASH_METHOD)
        normalized = app_module._normalize_demo_users({"admin@mizoki3.com": pre_hashed})
        self.assertEqual(pre_hashed, normalized["admin@mizoki3.com"])
        self.assertTrue(app_module._check_demo_credentials(
            normalized, "admin@mizoki3.com", "test-pw"))


class BlogFeedTestCase(unittest.TestCase):
    """Cover the new RSS / JSON Feed routes."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(self.temp_dir.name))
        app = create_app(runtime=runtime)
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_rss_feed_returns_xml_with_all_posts(self) -> None:
        r = self.client.get("/blog/feed.xml")
        self.assertEqual(200, r.status_code)
        self.assertTrue(r.content_type.startswith("application/rss+xml"))
        self.assertEqual(12, r.data.count(b"<item>"))

    def test_json_feed_returns_jsonfeed_envelope(self) -> None:
        r = self.client.get("/blog/feed.json")
        self.assertEqual(200, r.status_code)
        body = r.get_json()
        self.assertEqual(
            "https://jsonfeed.org/version/1.1", body["version"]
        )
        self.assertEqual(12, len(body["items"]))

    def test_posts_manifest_passthrough(self) -> None:
        r = self.client.get("/blog/posts.json")
        self.assertEqual(200, r.status_code)
        self.assertEqual(12, len(r.get_json()["posts"]))


class GoogleAdsApiTestCase(unittest.TestCase):
    """Cover the /api/boss/google-ads/* GAQL pre-flight endpoints."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(self.temp_dir.name))
        app = create_app(runtime=runtime)
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_google_ads_validate_endpoint_flags_sunset_version(self) -> None:
        response = self.client.post(
            "/api/boss/google-ads/validate",
            json={
                "query": "SELECT campaign.id FROM campaign",
                "api_version": "v19",
                "as_of": "2026-06-30",
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertFalse(payload["valid"])
        self.assertTrue(any(e["code"] == "api_version_sunset" for e in payload["errors"]))

    def test_google_ads_validate_endpoint_requires_query(self) -> None:
        response = self.client.post("/api/boss/google-ads/validate", json={"query": ""})
        self.assertEqual(400, response.status_code)

    def test_google_ads_validate_batch_endpoint(self) -> None:
        response = self.client.post(
            "/api/boss/google-ads/validate-batch",
            json={
                "queries": [
                    "SELECT campaign.id FROM campaign",
                    "SELECT campaign.bogus FROM campaign",
                ],
                "api_version": "v21",
                "as_of": "2026-06-30",
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertEqual(2, payload["received"])
        self.assertEqual(1, payload["valid"])

    def test_google_ads_versions_endpoint_returns_schedule(self) -> None:
        response = self.client.get("/api/boss/google-ads/versions?as_of=2026-06-30")
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertIn("schedule", payload)
        self.assertTrue(any(v["status"] == "sunset" for v in payload["schedule"]))

    def test_google_ads_fields_endpoint_returns_metadata(self) -> None:
        response = self.client.get("/api/boss/google-ads/fields?resource=campaign")
        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertTrue(payload["known_resource"])
        self.assertIn("campaign", payload["resource"])

    def test_discover_exposes_google_ads_block(self) -> None:
        response = self.client.get("/api/boss/discover")
        self.assertEqual(200, response.status_code)
        block = response.get_json()["google_ads"]
        self.assertIn("google_ads.validate_gaql", block["tools"])
        self.assertIn("default_version", block)


if __name__ == "__main__":
    unittest.main()
