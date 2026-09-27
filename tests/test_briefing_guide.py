"""Decision Concierge (Executive Briefing guide agent) — behavior + claims lint."""
from __future__ import annotations

import importlib.util
import pathlib
import re
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
GUIDE_JS = REPO_ROOT / "executive-briefing" / "js" / "guide.js"

_cq_spec = importlib.util.spec_from_file_location(
    "content_qa_briefing", REPO_ROOT / "scripts" / "content_qa.py")
content_qa = importlib.util.module_from_spec(_cq_spec)
_cq_spec.loader.exec_module(content_qa)

from app import create_app  # noqa: E402
from mizoki_runtime import briefing_guide, create_runtime  # noqa: E402


class _AppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = pathlib.Path(self.temp_dir.name)
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=self.data_dir)
        self.app = create_app(runtime=runtime)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()


class GuideWiringTestCase(_AppTestCase):
    def test_briefing_page_loads_the_guide(self) -> None:
        body = self.client.get("/executive-briefing/").get_data(as_text=True)
        self.assertIn('src="js/guide.js', body)

    def test_guide_asset_served(self) -> None:
        self.assertTrue(GUIDE_JS.is_file())
        response = self.client.get("/executive-briefing/js/guide.js")
        self.assertEqual(200, response.status_code)

    def test_guide_tools_registered_under_boss(self) -> None:
        body = self.client.get("/api/mcp/tools").get_data(as_text=True)
        self.assertIn("guide.answer", body)
        self.assertIn("guide.memory_summary", body)


class GuideEndpointsTestCase(_AppTestCase):
    def test_event_roundtrip_and_summary(self) -> None:
        for event, payload in (
            ("guide_opened", {"mode": "guided"}),
            ("stage_changed", {"stage": "exposure"}),
            ("suggestion_accepted", {"suggestion": "x"}),
            ("decision_confirmed", {"intent": "pilot"}),
        ):
            response = self.client.post(
                "/api/briefing/guide/event",
                json={"session": "gs_test", "event": event, "stage": "exposure",
                      "domain": "signal", "role": "cfo", "payload": payload},
            )
            self.assertEqual(200, response.status_code, event)
        summary = self.client.get("/api/briefing/guide/summary").get_json()
        self.assertEqual(1, summary["sessions"])
        self.assertEqual(4, summary["events_total"])
        self.assertEqual(1.0, summary["suggestion_acceptance"])
        self.assertIn("decision_confirmed:pilot", summary["decision_intents"])

    def test_unknown_event_rejected(self) -> None:
        response = self.client.post(
            "/api/briefing/guide/event",
            json={"session": "gs_test", "event": "rm_rf_everything"},
        )
        self.assertEqual(400, response.status_code)

    def test_ask_matches_bi_objection_and_logs_it(self) -> None:
        response = self.client.post(
            "/api/briefing/guide/ask",
            json={"session": "gs_test", "question": "We already have BI dashboards in Looker — why this?",
                  "stage": "exposure", "domain": "signal", "role": "cfo"},
        )
        self.assertEqual(200, response.status_code)
        answer = response.get_json()
        self.assertEqual("objection", answer["kind"])
        self.assertEqual("existing_bi", answer["topic"])
        self.assertIn("Keep your BI", answer["answer"])
        summary = self.client.get("/api/briefing/guide/summary").get_json()
        self.assertEqual({"existing_bi": 1}, summary["objections_ranked"])

    def test_security_answer_makes_no_certification_claims(self) -> None:
        answer = self.client.post(
            "/api/briefing/guide/ask",
            json={"session": "gs_test", "question": "How do you handle security and compliance?"},
        ).get_json()
        self.assertEqual("security", answer["topic"])
        for banned in ("SOC", "ISO 27001", "certified", "guarantee"):
            self.assertNotIn(banned.lower(), answer["answer"].lower(), banned)

    def test_demo_surface_ask_roundtrip(self) -> None:
        """The demo docent asks through the same endpoint, tagged stage=demo
        + domain=<desk>, so ledger analytics can segment demo traffic."""
        response = self.client.post(
            "/api/briefing/guide/ask",
            json={"session": "ds_test", "question": "do you get the same numbers if I replay the seed?",
                  "stage": "demo", "domain": "hub"},
        )
        self.assertEqual(200, response.status_code)
        answer = response.get_json()
        self.assertEqual(("fact", "replay_seed"), (answer["kind"], answer["topic"]))
        summary = self.client.get("/api/briefing/guide/summary").get_json()
        self.assertEqual({"replay_seed": 1}, summary["question_topics"])
        self.assertEqual({"demo": 1}, summary["last_stage_by_session"])

    def test_unknown_question_gets_honest_fallback(self) -> None:
        answer = self.client.post(
            "/api/briefing/guide/ask",
            json={"session": "gs_test", "question": "zzz qqq xxyzzy?"},
        ).get_json()
        self.assertEqual("unknown", answer["kind"])
        self.assertIn("human follow-up", answer["answer"])


class GuideBankTestCase(unittest.TestCase):
    def test_every_cached_objection_resolves(self) -> None:
        probes = {
            "integration_risk": "how hard is the integration with our systems",
            "existing_bi": "we already have dashboards and a reporting team",
            "security": "is our data secure, what about privacy",
            "not_now": "maybe next quarter, timing is bad",
            "budget_owner": "who is the budget sponsor for procurement",
            "pricing": "how much does the subscription cost",
        }
        for expected, question in probes.items():
            kind, topic, _entry = briefing_guide.classify_question(question)
            self.assertEqual(("objection", expected), (kind, topic), question)

    def test_demo_facing_facts_resolve(self) -> None:
        """2026-08-02: 'the chat is very limited' — the fact pack now covers
        the demo surface (desks, ORACLE, seeds, pilot, the Boss, the voice)."""
        probes = {
            "desks": "which desk should I open next, capital or the nexus boardroom?",
            "oracle_intent": "can oracle predict purchase intent before they act?",
            "replay_seed": "if I rerun with the same seed do I get the same numbers?",
            "pilot_path": "what is the next step to get started with a pilot?",
            "boss_agent": "who are you exactly, some kind of agent narrating this?",
            "voice_output_only": "is the microphone listening to me while you talk?",
        }
        for expected, question in probes.items():
            kind, topic, _entry = briefing_guide.classify_question(question)
            self.assertEqual(("fact", expected), (kind, topic), question)

    def test_record_event_rejects_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                briefing_guide.record_event(pathlib.Path(tmp) / "g.jsonl", "s", "bogus_event")


class GuideClaimsDisciplineTestCase(unittest.TestCase):
    """The concierge may only say what written canon may say — both layers."""

    def setUp(self) -> None:
        js = GUIDE_JS.read_text(encoding="utf-8")
        literals = re.findall(r'"((?:[^"\\\n]|\\.)*)"', js)
        literals += re.findall(r"'((?:[^'\\\n]|\\.)*)'", js)
        py_answers = [f["answer"] for f in briefing_guide.PRODUCT_FACTS]
        py_answers += [o["answer"] for o in briefing_guide.OBJECTIONS]
        py_answers.append(briefing_guide.UNKNOWN_ANSWER)
        self.speakable = "\n".join(literals + py_answers)

    def test_banned_vocabulary_absent(self) -> None:
        banned = [
            r"guarantee", r"soc\s?2", r"iso\s?27001", r"will buy", r"act now",
            r"limited[\s-]?time", r"risk[\s-]?free", r"revolutionary",
            r"best[\s-]in[\s-]class", r"don'?t miss", r"mind[\s-]?reading",
            r"\$\s?\d",  # the concierge never invents dollar figures
        ]
        for pattern in banned:
            self.assertIsNone(
                re.search(pattern, self.speakable, re.IGNORECASE),
                f"banned phrase in concierge copy: {pattern}",
            )

    def test_required_stance_present(self) -> None:
        self.assertIn("I'll suggest; you commit", self.speakable)
        self.assertIn("how fast you start", self.speakable)


class BriefingStageClaimsTestCase(unittest.TestCase):
    """The briefing's own stages (app.js) carry no trust chip the tree cannot back.

    The concierge copy above was already held to this; the stage renderer was
    not, and Stage 05 shipped "SOC 2 Type II", "SSO / SCIM" and "Data residency
    options" chips until 2026-09-25. docs/product/SECURITY_PACKET_v1.md §9
    records no SOC 2 report (row 2) and no residency mechanism (row 7, D-14);
    SCIM has no implementation anywhere in the tree. content_qa reads HTML and
    Markdown, not the JavaScript that renders this page, so this test is the
    gate for it.
    """

    def test_stage_renderer_names_no_unbacked_attestation(self) -> None:
        # content_qa scans executive-briefing/js/data.js, not this renderer, so
        # this test is the renderer's only attestation gate. It applies the
        # shared rule (content_qa.attestation_hits) rather than a partial copy:
        # the #1156 copy listed SOC 2 / ISO 27001 / HIPAA and missed PCI DSS,
        # "GDPR compliant/certified" and ISO 42001 (review follow-up).
        js = (REPO_ROOT / "executive-briefing" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertEqual([], [m.group(0) for m in content_qa.attestation_hits(js)])
        # The same chip row also named SSO/SCIM and data-residency options,
        # which no shipped surface backs; they are not attestations, so they
        # stay pinned here by name.
        for pattern in (r"\bscim\b", r"data residency options"):
            self.assertIsNone(re.search(pattern, js, re.IGNORECASE), pattern)

    def test_the_renderer_gate_fires_on_every_attestation_family(self) -> None:
        # Both directions (rule 01): the shared rule must catch each family
        # the partial copy missed, so a green renderer test means something.
        for claim in ("PCI DSS compliant checkout", "GDPR Compliant",
                      "ISO 42001 certified", "SOC 2 Type II"):
            self.assertTrue(content_qa.attestation_hits(f"'<span>{claim}</span>'"), claim)

    def test_mobile_sheet_cannot_block_the_briefing(self) -> None:
        """2026-07-31 regression: on phones the open rail covered #mb-start —
        the executive could not commit anything."""
        source = GUIDE_JS.read_text(encoding="utf-8")
        # Compact peek sheet + reserved space + a shrunken app height box, so
        # the briefing's own controls lay out above the guide.
        self.assertIn("@media (max-width:1099px)", source)
        self.assertIn("html.mzg-docked body{padding-bottom:170px;}", source)
        self.assertIn(".mzg-panel{left:8px;right:8px;width:auto;max-height:152px;}", source)
        self.assertIn("html.mzg-docked #mizoki-briefing{min-height:calc(100dvh - 160px);}", source)
        # Expand/shrink affordance for the full sheet on small screens.
        self.assertIn("mzg-expanded", source)
        self.assertIn('el("button", "mzg-grow"', source)
        # Occluded controls are SCROLLED into view — never pressed.
        self.assertIn("function ensureVisible", source)
        self.assertIn("scrollIntoView", source)

    def test_guide_never_clicks_briefing_controls(self) -> None:
        # Suggest + highlight only: the executive commits every action.
        source = GUIDE_JS.read_text(encoding="utf-8")
        self.assertNotIn(".click(", source)

    def test_voice_replies_are_output_only(self) -> None:
        """2026-08-02: the concierge gained spoken replies — synthesis only.
        The bright line holds: it speaks; it never listens."""
        source = GUIDE_JS.read_text(encoding="utf-8")
        self.assertIn("speechSynthesis", source)
        self.assertIn("🔊 voice replies", source)
        self.assertIn('sessionStorage.getItem("mzg-voice")', source)
        self.assertIn("I speak — I never listen", source)
        for forbidden in ("SpeechRecognition", "webkitSpeechRecognition", "getUserMedia", "MediaRecorder"):
            self.assertNotIn(forbidden, source, forbidden)
        # cancel() clears the queue BEFORE the next utterance is queued — a
        # cancel landing on a just-queued utterance wedges Chrome's engine.
        self.assertLess(source.index("window.speechSynthesis.cancel(); // clear the queue BEFORE speaking"),
                        source.index("window.speechSynthesis.speak(u)"))


if __name__ == "__main__":
    unittest.main()
