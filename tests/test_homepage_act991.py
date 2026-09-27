"""Homepage §04 DECISION GATES — ACT-991 told as one story (owner prompt
"ACT-991 homepage reconcile r1.0", 2026-09-25).

Canon: ACT-991 is an ILLUSTRATIVE scenario (TRUTH.md 2.5,
`PLATFORM_CLAIMS.act_991`) — a $5.0M capital distribution, DEL score 41
against the threshold of 80, blocked, then re-routed to the $3.2M Option B
(docs/MIZOKI3_SIX_DOMAIN_BLUEPRINT.md, worked Decision Proof). The homepage
v2 lane left the numeric reconciliation as an open owner call; this pins the
owner's ruling on the served `/`:

  1. the four-gate scorecard survives, the fiduciary-floor BREACH row stays as
     the cause, and the header verdict is unchanged;
  2. the scorecard gains the DEL line and the outcome line, verbatim, each
     carrying its own ILLUSTRATIVE label and no other claim class;
  3. verdicts stay text-labeled, and every colour the new lines use meets WCAG
     AA (4.5:1) against the line's own background, computed from the page's
     own tokens rather than assumed;
  4. the sandbox's ACT-991 preset reads the re-route and still drives a veto
     under the sandbox's own gate thresholds;
  5. no figure beyond canon enters §04 — the new lines carry only 41, 80 and
     $3.2M — and "Option B" appears nowhere outside §04.
"""
import html
import re
import tempfile
import unittest
from pathlib import Path

from app import create_app
from mizoki_runtime import create_runtime

REPO_ROOT = Path(__file__).resolve().parents[1]

DEL_LINE = "DEL score 41 · threshold 80 → VETOED"
OUTCOME_LINE = "Re-routed: Option B — $3.2M distribution, floor preserved. Written to the ledger."
PRESET = "ACT-991 · liquidity floor breach → VETOED → re-routed to Option B ($3.2M)"
# The closed claim vocabularies a reader could mistake for a class other than
# ILLUSTRATIVE (TRUTH.md Article 2 labels + the §B.6 capability labels).
OTHER_CLAIM_CLASSES = ("verified result", "benchmark result", "pilot result", "design target",
                       "live", "partial", "in build", "proposed", "composite")


def visible(markup: str) -> str:
    text = re.sub(r"<[^>]+>", " ", markup)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def inline_text(markup: str) -> str:
    """Text as an inline run reads it: tags vanish WITHOUT becoming spaces, so a
    space lost (or doubled) next to an inline element fails the exact match."""
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def phrase(line: str) -> str:
    """A ledger line's statement — everything before its ILLUSTRATIVE label."""
    return inline_text(line.split('<span class="sc-il">')[0])


def _luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(fg: str, bg: str) -> float:
    hi, lo = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class HomepageAct991TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        runtime = create_runtime(base_dir=REPO_ROOT, data_dir=Path(cls.temp_dir.name))
        cls.app = create_app(runtime=runtime)
        cls.app.config.update(TESTING=True)
        client = cls.app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        cls.home = response.get_data(as_text=True)
        response.close()
        cls.section = cls.home.split('<section id="control"')[1].split("</section>")[0]
        cls.scorecard = cls.section.split('<div class="scorecard reveal">')[1].split('<div class="sandbox')[0]
        # Absent lines read as "" so a regression fails as an assertion, not a setUp error.
        found = {kind: re.search(rf'<div class="sc-line sc-{kind}">(.*?)</div>', cls.scorecard, re.S)
                 for kind in ("del", "out")}
        cls.del_line = found["del"].group(1) if found["del"] else ""
        cls.outcome_line = found["out"].group(1) if found["out"] else ""

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    # -- 1. the four-gate scorecard and its cause survive ----------------------
    def test_four_gate_scorecard_and_breach_row_survive(self) -> None:
        self.assertEqual(4, self.scorecard.count('<div class="sc-item">'))
        self.assertIn('<span class="sc-verdict">FIDUCIARY GATE FAILED · VETOED</span>', self.scorecard)
        self.assertIn('<span class="sc-k">Fiduciary liquidity floor</span><span class="sc-v veto">BREACH</span>',
                      self.scorecard)
        # The breach row is still the grid's last cell (it owns the red dot),
        # and the new lines sit outside the grid, so they read as results, not
        # as a fifth gate.
        grid = self.scorecard.split('<div class="sc-grid">')[1].split('<div class="sc-f">')[0]
        self.assertNotIn("sc-line", grid)
        last_cell = grid.rsplit('<div class="sc-item">', 1)[1]
        self.assertIn("Fiduciary liquidity floor", last_cell)
        self.assertIn("BREACH", last_cell)
        markers = ('<div class="sc-h">', '<div class="sc-grid">', '<div class="sc-f">',
                   '<div class="sc-line sc-del">', '<div class="sc-line sc-out">')
        for marker in markers:
            self.assertIn(marker, self.scorecard, marker)
        order = [self.scorecard.index(marker) for marker in markers]
        self.assertEqual(order, sorted(order))

    # -- 2. the two lines, verbatim, each ILLUSTRATIVE and nothing else --------
    def test_del_and_outcome_lines_are_verbatim_and_labeled(self) -> None:
        # Exact wording, character for character — including the spaces that
        # sit next to inline elements (the VETOED chip, the bold lead).
        self.assertEqual(DEL_LINE, phrase(self.del_line))
        self.assertEqual(OUTCOME_LINE, phrase(self.outcome_line))
        self.assertEqual(f"{DEL_LINE} ILLUSTRATIVE", visible(self.del_line))
        self.assertEqual(f"{OUTCOME_LINE} ILLUSTRATIVE", visible(self.outcome_line))
        for line in (self.del_line, self.outcome_line):
            with self.subTest(line=visible(line)):
                self.assertEqual(1, line.count('<span class="sc-il">ILLUSTRATIVE</span>'))
                text = visible(line).lower()
                for label in OTHER_CLAIM_CLASSES:
                    self.assertIsNone(re.search(rf"\b{re.escape(label)}\b", text), label)
        # The post-deploy probe strings are contiguous in the served bytes.
        for probe in ("threshold 80", "Option B"):
            self.assertIn(probe, self.home, probe)

    # -- 3. verdicts are text, and the new label text meets AA -----------------
    def test_verdict_is_text_labeled_and_new_text_meets_aa_contrast(self) -> None:
        self.assertIn('<span class="sc-v veto">VETOED</span>', self.del_line)
        tokens = dict(re.findall(r"--([a-z0-9]+):(#[0-9A-Fa-f]{6})", self.home.split("</style>")[0]))

        def rule(selector: str) -> str:
            match = re.search(re.escape(selector) + r"\{([^}]*)\}", self.home)
            self.assertIsNotNone(match, f"no CSS rule for {selector}")
            return match.group(1)

        def token(body: str, prop: str) -> str:
            match = re.search(rf"(?<![-\w]){prop}:var\(--([a-z0-9]+)\)", body)
            self.assertIsNotNone(match, f"{prop} is not a design token in {{{body}}}")
            return tokens[match.group(1)]

        background = token(rule(".sc-line"), "background")
        pairs = {
            "line text": token(rule(".sc-line"), "color"),
            "bold lead": token(rule(".sc-line b"), "color"),
            "ILLUSTRATIVE label": token(rule(".sc-il"), "color"),
            "VETOED chip": token(rule(".sc-v.veto"), "color"),
        }
        for name, foreground in pairs.items():
            with self.subTest(name=name, fg=foreground, bg=background):
                self.assertGreaterEqual(contrast(foreground, background), 4.5)

    # -- 4. the sandbox preset reads the re-route and still vetoes -------------
    def test_act991_preset_reads_the_reroute_and_still_vetoes(self) -> None:
        button = re.search(r'<button class="preset" type="button" data-c="(\d+)" data-p="(\d+)" data-r="(\d+)">'
                           r"(ACT-991.*?)</button>", self.section, re.S)
        self.assertIsNotNone(button)
        self.assertEqual(PRESET, inline_text(button.group(4)))
        c, p, r = (int(button.group(i)) for i in (1, 2, 3))
        c_min, p_min, r_max = (int(x) for x in re.search(
            r"var gc=c>=(\d+),gp=p>=(\d+),gr=r<=(\d+);", self.home).groups())
        self.assertTrue(c < c_min or p < p_min or r > r_max,
                        "the ACT-991 preset must fail a gate in the sandbox it labels VETOED")

    # -- 5. no figure beyond canon; Option B lives only in §04 -----------------
    def test_no_figure_beyond_canon_and_option_b_scoped_to_s04(self) -> None:
        figures = re.findall(r"\$?\d+(?:\.\d+)?M?", visible(self.del_line) + " " + visible(self.outcome_line))
        self.assertEqual(["41", "80", "$3.2M"], figures)
        self.assertEqual(2, self.section.count("Option B"))
        self.assertEqual(self.section.count("Option B"), self.home.count("Option B"))
        # The gauge still tells the same number the DEL line states.
        self.assertIn('<div class="gnum" id="gscore" style="color:var(--veto)">41</div>', self.section)
        self.assertIn("439.8*(1-0.41)", self.home)

    # -- Guardian: the no-IntersectionObserver fallback tells the same story --
    def test_gauge_fallback_draws_the_same_41_veto_arc(self) -> None:
        # Browsers without IntersectionObserver used to get an 87% teal arc
        # under a red "41 … VETOED" — the design canon's banned gauge-87 drift
        # marker (docs/DESIGN_CANON.md §2). Both branches now draw 41% in veto.
        observers = self.home.split("/* ---------- observers: enhancement only ---------- */")[1]
        fallback = observers.split("}else{")[1].split("})();")[0]
        self.assertIn("each(document.querySelectorAll('.reveal')", fallback)
        self.assertIn("strokeDashoffset=439.8*(1-0.41)", fallback)
        self.assertIn("style.stroke='var(--veto)'", fallback)
        self.assertEqual(2, self.home.count("439.8*(1-0.41)"))
        self.assertNotIn("1-0.87", self.home)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
