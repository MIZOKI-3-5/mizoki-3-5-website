#!/usr/bin/env python3
"""Runtime-corpus attestation gate: no unattested compliance attestation in
the text the site runtime serves through /api/mcp/call.

Why a separate gate (CV-7, 2026-09-25; review on #1171). The site runtime's
SiteCorpus (mizoki_runtime/runtime.py DOCUMENT_SPECS) loads ten documents,
five of them pages app.py 301-redirects. graphrag.query returns their text
(snippet) plus each spec's title and summary through /api/mcp/call, which
production leaves unauthenticated. content_qa.py scopes by the route table,
so it never reads them, and the site test that holds them
(tests/test_runtime_corpus_attestations.py) runs only in PR CI. This script
is stdlib-only so the gates that land or publish content run it too:
.github/scripts/content_gates.sh (PR CI and the auto-merge lanes) and
deploy-homepage.yml (before any image is built).

One detector: content_qa.attestation_hits, loaded by path. The text checked
is the text served: the runtime's own _strip_markup, copied below because
runtime.py cannot be imported here (it pulls in sibling modules with
third-party dependencies). runtime.py is parsed, never imported: for
DOCUMENT_SPECS, and for its _strip_markup, which the self-test compares with
the copy statement for statement. tests/test_runtime_corpus_attestations.py
pins the copy too, but only in PR CI. A document is scanned only if its file
exists, because SiteCorpus drops a spec whose file is missing, title and
summary included (review on #1176).

Exit 0 when clean; 1 with one line per finding. --self-test proves the
detector fires on the copy removed on 2026-09-25, stays silent on the
denials that stayed, and reads the text the runtime serves.
"""
from __future__ import annotations

import argparse
import ast
import html
import importlib.util
import re
import sys
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = SITE_ROOT / "mizoki_runtime" / "runtime.py"
CONTENT_QA = SITE_ROOT / "scripts" / "content_qa.py"
GATE = Path(__file__).resolve()

# The copy removed on 2026-09-25 must fire; the denials that stayed must not.
SEEDED_FIRE = (
    "<span>SOC 2 Type II Certified • GDPR Compliant • HIPAA Ready</span>",
    "<p>MIZ OKI can be managed entirely via our SOC2 Type II compliant cloud.</p>",
    '<h4>Enterprise Compliance Standards</h4><div class="c-tag">ISO 27001</div>'
    '<div class="c-tag">HIPAA Compliant</div>',
)
SEEDED_LEGAL = (
    "<p>Audit trail retained (supports GDPR access requests; SOC 2 not attested).</p>",
    "<p>It does not establish SOC 2 or ISO certification.</p>",
)


def _strip_markup(raw_text: str) -> str:
    without_blocks = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_text)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_blocks)
    collapsed = re.sub(r"\s+", " ", html.unescape(without_tags)).strip()
    return collapsed


def load_content_qa():
    spec = importlib.util.spec_from_file_location("content_qa", CONTENT_QA)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def document_specs(runtime_path: Path = RUNTIME) -> list[dict]:
    """DOCUMENT_SPECS as runtime.py declares it, read without importing."""
    tree = ast.parse(runtime_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if any(isinstance(t, ast.Name) and t.id == "DOCUMENT_SPECS" for t in targets):
            return list(ast.literal_eval(node.value))
    raise SystemExit(f"DOCUMENT_SPECS not found in {runtime_path}")


def _statements(path: Path, name: str) -> list[str] | None:
    """A top-level function's statements as ast dumps, docstring dropped."""
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return [ast.dump(s) for s in node.body
                    if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
    return None


def stripper_parity(runtime_path: Path = RUNTIME, gate_path: Path = GATE) -> bool:
    """Whether this script's _strip_markup is still runtime.py's, statement for
    statement. If the copy drifts, the scan reads text the runtime never serves."""
    ours = _statements(gate_path, "_strip_markup")
    return ours is not None and ours == _statements(runtime_path, "_strip_markup")


def findings(content_qa, specs: list[dict], site_root: Path = SITE_ROOT) -> list[str]:
    """One line per attestation in any text graphrag.query can return."""
    found = []
    for spec in specs:
        path = site_root / spec["path"]
        if not path.exists():
            # SiteCorpus._load_documents skips the whole spec, so graphrag.query
            # returns none of it: not its text, title or summary.
            continue
        fields = {"title": spec.get("title", ""), "summary": spec.get("summary", ""),
                  "text": _strip_markup(path.read_text(encoding="utf-8"))}
        for field, text in fields.items():
            for m in content_qa.attestation_hits(text):
                context = " ".join(text[max(0, m.start() - 40): m.end() + 40].split())
                found.append(f"{spec['path']} [{field}] :: unattested compliance attestation "
                             f"served by graphrag.query: …{context}…")
    return found


def self_test(content_qa) -> bool:
    ok = True
    for i, seed in enumerate(SEEDED_FIRE, 1):
        caught = bool(content_qa.attestation_hits(_strip_markup(seed)))
        print(f"  self-test seeded violation [{i}]: {'CAUGHT' if caught else 'MISSED'}")
        ok = ok and caught
    for i, seed in enumerate(SEEDED_LEGAL, 1):
        silent = not content_qa.attestation_hits(_strip_markup(seed))
        print(f"  self-test legal wording [{i}]: {'STAYS LEGAL' if silent else 'FLAGGED'}")
        ok = ok and silent
    same = stripper_parity()
    print(f"  self-test markup stripper matches runtime.py: {'YES' if same else 'NO (re-copy _strip_markup)'}")
    specs = document_specs()
    print(f"  corpus documents declared in runtime.py: {len(specs)}")
    return ok and same and bool(specs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true",
                        help="prove the detector fires on seeded copy and stays silent on denials")
    args = parser.parse_args(argv)
    content_qa = load_content_qa()
    if args.self_test:
        if self_test(content_qa):
            print("SELF-TEST PASS — the runtime-corpus gate fires")
            return 0
        print("SELF-TEST FAIL — the runtime-corpus gate is not trustworthy")
        return 1
    specs = document_specs()
    found = findings(content_qa, specs)
    for line in found:
        print(line)
    if found:
        print(f"RUNTIME CORPUS FAIL — {len(found)} unattested attestation(s) in text "
              f"/api/mcp/call serves (docs/product/SECURITY_PACKET_v1.md §9)")
        return 1
    print(f"RUNTIME CORPUS OK — {len(specs)} documents (text, title, summary) carry no "
          f"unattested compliance attestation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
