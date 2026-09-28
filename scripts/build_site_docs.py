#!/usr/bin/env python3
"""Build the mizoki3.com/docs static portal from the repository's docs/ tree.

Renders every ``docs/**/*.md`` to a styled, theme-aware HTML page, builds a
searchable grouped index, and copies non-markdown files (as syntax-shell text or
downloads). A doc merged to ``docs/`` is on the site at the next deploy — no
per-doc wiring (owner directive 2026-08-20: mizoki3.com/docs is public and
carries all of ``docs/``).

SECURITY GATE (non-negotiable). Any file whose contents match a live-credential
pattern is EXCLUDED from the site and listed in ``EXCLUSIONS.json``. Publishing a
real secret to the public web is never done, even under "publish everything" —
the operator sees exactly what was withheld and can act on it. A tabular data
file (.csv/.tsv/.xlsx/.parquet) is withheld from every portal unless its path is
on ``docs/_inventory/tabular_allowlist.txt`` (WS-0, 2026-09-01). Everything else
is published as written.

Usage (from the repo root, so ``docs/`` is visible):
    python3 "# MIZ OKI 3.5/scripts/build_site_docs.py" [--repo-root .] [--out "# MIZ OKI 3.5/site_docs"]

Invoked by ``.github/workflows/deploy-homepage.yml`` AFTER the marketing content
gates and BEFORE the image build, so the raw docs never enter the truth-discipline
gate's scope (they are internal engineering docs, not gated marketing copy).
"""
from __future__ import annotations

import argparse
import html
import json
import os
import posixpath
import re
import shutil
import sys
from pathlib import Path

import markdown  # build-time only; not a runtime image dependency

REPO_SLUG = "mediaintelligence/MIZOKICloudRun"
GH_BLOB = f"https://github.com/{REPO_SLUG}/blob/main"
GH_RAW = f"https://raw.githubusercontent.com/{REPO_SLUG}/main"

# Files rendered as monospaced source (inside the page shell) rather than markdown.
TEXT_EXT = {".txt", ".py", ".js", ".jsx", ".ts", ".tsx", ".sql", ".json",
            ".yaml", ".yml", ".csv", ".sh", ".toml", ".ini", ".cfg"}
# Binaries copied verbatim and offered as a download link.
BINARY_EXT = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

# --- The secret gate. A hit EXCLUDES the file. Tuned for VALUES, not mentions. --
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA|PGP|PRIVATE) [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                       # AWS access key id
    re.compile(r"\bASIA[0-9A-Z]{16}\b"),                       # AWS temp key id
    re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),                 # Google API key
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),                    # GitHub PAT
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),           # Slack token
    re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),                    # OpenAI-style key
    re.compile(r'"private_key"\s*:\s*"-----BEGIN'),            # GCP SA key json
    re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*"
               r"['\"][A-Za-z0-9/+_\-]{16,}['\"]"),
]
# Phrases that mark a match as illustrative, not a live secret.
SECRET_ALLOW = re.compile(
    r"(?i)example|placeholder|redacted|dummy|fake|your-|<[a-z0-9_\- ]+>|"
    r"xxxx|change[_-]?me|todo|\bfoo\b|\bbar\b|: string|\.\.\.")


def find_secrets(text: str) -> list[str]:
    hits = []
    for pat in SECRET_PATTERNS:
        for m in pat.finditer(text):
            line = text[max(0, m.start() - 20): m.end() + 20]
            if SECRET_ALLOW.search(line):
                continue
            hits.append(pat.pattern[:48])
    return sorted(set(hits))


# --- The internal-disclosure gate (MIZ-SEC 2026-08-21). ----------------------
# The secret gate above stops CREDENTIALS reaching the public web. It does not
# stop INFRASTRUCTURE IDENTIFIERS, and this repository is private: until this
# gate existed, mizoki3.com/docs was the only path from private source to the
# open internet, and it published the production GCP project id on 132 pages and
# the Cloud Run service-URL hash on 83 (measured 2026-08-21, before the fix).
#
# Those are not credentials, so nothing here is "a leaked password". They are
# reconnaissance material: the project id yields bucket names, Artifact Registry
# paths, and service-account principals (`*@<project>.iam.gserviceaccount.com`);
# the URL hash lets anyone construct and probe every Cloud Run service URL in
# the fleet. Publishing them narrows an attacker's search space against real
# infrastructure for no reader benefit — a docs reader never needs the project id.
#
# Scope is deliberately narrow, and the exclusions are stated rather than tuned
# away (.claude/rules/01-verification-discipline.md — never narrow a rule to
# admit a false positive; bound the exemption and say why):
#   * Human-approval ceremony strings (`APPROVED: MERGE` / `APPROVED: DEPLOY`)
#     are NOT gated. They are typed into a workflow_dispatch input that already
#     requires repository write access, so knowing the string grants nothing.
#     Gating them would withhold docs/OFFERING_MAP.md — the architecture canon —
#     to defend a non-secret.
#   * AI branch names (`claude/…`, `cursor/…`) are NOT gated: process noise, not
#     an attack primitive, and the pattern matched 110 files of ordinary prose.
#
# There is deliberately NO per-document publish override. A false positive is
# fixed by removing the identifier from the document (build-to-claim), never by
# a bypass parameter that a later change could reuse to publish real disclosure
# (CONSTITUTION II.1 — no bypass parameter exists in any gate).
INTERNAL_IDENTIFIERS = (
    # (regex, human-readable reason shown on the index and in EXCLUSIONS.json)
    (re.compile(r"spry-bus-425315-p6"), "GCP production project id"),
    (re.compile(r"ehqxake3ia"), "Cloud Run service-URL hash (fleet-wide)"),
)

# An author's explicit, deterministic opt-out. Put this marker anywhere in a
# document and the portal will never publish it, whatever its content.
INTERNAL_MARKER = re.compile(r"<!--\s*mizoki:internal\s*-->", re.I)

# Trees that are internal BY PURPOSE rather than by content. `docs/prompts/`
# holds versioned production build prompts — branch names, gate strings, and
# deploy procedure are their subject matter, so they are operator instructions
# that happen to be written in markdown, not documentation for site readers.
# `marketing/aeo/` (Lane 5 S4, 2026-09-02): the AEO authority pages are served ONLY
# through /learn behind LEARN_PAGES (default OFF); rendering them into the public
# /docs portal before the owner confirms S4-1/S4-2 would make them site-visible
# through a side door, so the tree is withheld here until that ruling (OPEN_ITEMS S4-2).
# S4-2 RULED NO 2026-09-15 (owner ruling 2026-09-15,
# docs/reports/OWNER_RULINGS_2026-09-15_REGISTER_CLOSEOUT.md): the docs-portal copy is not
# wanted; /learn is the served surface and two renderers of the same claims are a drift
# hazard. `marketing/aeo/` stays withheld here permanently. No behaviour change.
# `skills/xprovider-v1/` (2026-09-25): the cross-provider skill pack exports are
# operator install material — assistant instructions, the owner's personal inbox
# and writing workflows, and the full platform skill — not documentation for site
# readers. The rest of `docs/skills/` (registration and rollout reports) stays public.
INTERNAL_PATH_PREFIXES = ("prompts/", "marketing/aeo/", "skills/xprovider-v1/")

# --- The tabular-data gate (WS-0, 2026-09-01). ---------------------------------
# The two gates above look for credential VALUES and infrastructure IDENTIFIERS.
# Neither notices a customer export: a Shopify customer CSV under docs/misc/
# (16,425 rows — names, e-mails, phones, postal addresses) carried no secret and
# no project id, so the builder rendered it to the PUBLIC portal as a code page.
# Tabular files are data, not documentation, and person data is the thing the
# privacy thesis exists to protect — so this rule is an ALLOW-list, not a
# deny-list: a tabular file under docs/ is withheld from EVERY portal (public and
# signed-in) unless its repo-relative path is listed, one per line, in
# docs/_inventory/tabular_allowlist.txt. The allowlist is the bounded opt-out
# rule 01 asks for: a row names one path, so it cannot be reused to publish a
# different file, and adding a row is a reviewed change to a tracked file.
# Allowlisting a binary table (.xlsx/.parquet) does not add a renderer — it is
# still withheld as an unsupported type; the list only lifts the data gate.
TABULAR_EXT = {".csv", ".tsv", ".xlsx", ".parquet"}
TABULAR_ALLOWLIST = "docs/_inventory/tabular_allowlist.txt"
# Person-like column vocabulary. A HEURISTIC WARNING, never a gate: a header row
# carrying one of these words (as a whole word — `display_name` hits, `filename`
# does not) is printed as a `::warning::` so a reviewer looks at the file. It
# neither publishes nor withholds on its own; the allowlist decides that.
PERSON_TOKENS = frozenset({"name", "email", "e-mail", "phone", "address"})
_CELL_SPLIT = re.compile(r"[,\t;|]")
_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")
# A header cell: one to five word-like tokens, no sentence punctuation.
_HEADER_CELL = re.compile(r"[A-Za-z0-9_\-#()/]{1,32}(?: [A-Za-z0-9_\-#()/]{1,32}){0,4}")
# Files whose first line can be a header row. Markdown, HTML and JSON have their
# own first lines; scanning them produced only false positives (measured 2026-09-01).
HEADER_SCAN_EXT = TABULAR_EXT | {".txt"}


def load_tabular_allowlist(root: Path) -> set[str]:
    """Repo-relative paths permitted to publish. Missing file ⇒ empty ⇒ fail closed."""
    path = root / TABULAR_ALLOWLIST
    if not path.is_file():
        return set()
    rows = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            rows.add(line)
    return rows


def tabular_gate(rel: str, allowlist: set[str]) -> str | None:
    """Reason a tabular file is withheld from every portal (None ⇒ may publish).

    `rel` is the repo-relative path (``docs/misc/x.csv``) — the same string a
    reviewer writes into the allowlist, so there is exactly one spelling.
    """
    if posixpath.splitext(rel)[1].lower() not in TABULAR_EXT:
        return None
    if rel in allowlist:
        return None
    return f"tabular data not listed in {TABULAR_ALLOWLIST}"


def person_like_columns(header_line: str) -> list[str]:
    """Header cells that look like person data (name / e-mail / phone / address).

    Only a line with three or more delimited cells is treated as a header row,
    so a prose sentence that happens to contain "name" is not flagged.
    """
    cells = [c.strip().strip("\"'") for c in _CELL_SPLIT.split(header_line)]
    # A header row is three or more short, word-like cells. Markup, JSON, and
    # prose fail that shape and are never flagged.
    if len(cells) < 3 or not all(_HEADER_CELL.fullmatch(c) for c in cells):
        return []
    hits = []
    for cell in cells:
        tokens = set(_TOKEN_SPLIT.split(cell.lower()))
        if tokens & PERSON_TOKENS or "e-mail" in cell.lower():
            hits.append(cell)
    return hits


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line
    return ""


def find_internal(text: str, docrel: str = "") -> list[str]:
    """Reasons this document must not reach the public portal (empty ⇒ publish)."""
    reasons = []
    if INTERNAL_MARKER.search(text):
        reasons.append("marked <!-- mizoki:internal -->")
    for prefix in INTERNAL_PATH_PREFIXES:
        if docrel.startswith(prefix):
            reasons.append(f"internal tree docs/{prefix}")
            break
    for pat, why in INTERNAL_IDENTIFIERS:
        if pat.search(text):
            reasons.append(why)
    return sorted(set(reasons))


def find_internal_bytes(raw: bytes) -> list[str]:
    """Same gate for files copied verbatim (PDFs, images) — they are published too."""
    reasons = []
    for pat, why in INTERNAL_IDENTIFIERS:
        if pat.search(raw.decode("utf-8", "ignore")):
            reasons.append(why)
    return sorted(set(reasons))


def md_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
        if s and not s.startswith(("<!--", "---", "```")):
            break
    return fallback


def strip_scripts(html_text: str) -> str:
    # Docs are trusted internal content; still, never emit <script>/on*=/js: hrefs.
    html_text = re.sub(r"(?is)<script.*?</script>", "", html_text)
    html_text = re.sub(r'(?i)\son\w+\s*=\s*"[^"]*"', "", html_text)
    html_text = re.sub(r"(?i)href\s*=\s*\"javascript:[^\"]*\"", 'href="#"', html_text)
    return html_text


def rewrite_href(href: str, doc_rel: str, internal: set[str]) -> str:
    """Rewrite one link found in the doc at repo-relative ``doc_rel`` (under docs/).

    ``internal`` holds the doc-relative paths that render into the sign-in-only
    portal. A link to one of those must resolve to ``/docs/internal/...``: the
    public path 404s, because the document is not there. Measured 2026-08-22:
    248 cross-links pointed at the public path for a gated target.
    """
    if not href or href.startswith(("http://", "https://", "mailto:", "#", "//")):
        return href
    anchor = ""
    if "#" in href:
        href, anchor = href.split("#", 1)
        anchor = "#" + anchor
    if not href:
        return anchor or "#"
    if href.startswith("/"):
        return href + anchor
    # Resolve relative to the doc's directory, as a repo-relative posix path.
    base = posixpath.dirname(doc_rel)
    target = posixpath.normpath(posixpath.join(base, href))
    if target.startswith("docs/"):
        rel = target[len("docs/"):]
        ext = posixpath.splitext(rel)[1].lower()
        prefix = "/docs/internal/" if rel in internal else "/docs/"
        if ext == ".md":
            return prefix + posixpath.splitext(rel)[0] + ".html" + anchor
        if ext in TEXT_EXT:
            return prefix + rel + ".html" + anchor
        return prefix + rel + anchor  # binary copied verbatim
    # Anything outside docs/ points at the repo — send readers to GitHub.
    return f"{GH_BLOB}/{target}{anchor}"


HREF_RE = re.compile(r'href\s*=\s*"([^"]*)"')
IMG_RE = re.compile(r'src\s*=\s*"([^"]*)"')


def rewrite_links(body: str, doc_rel: str, internal: set[str]) -> str:
    body = HREF_RE.sub(
        lambda m: f'href="{html.escape(rewrite_href(m.group(1), doc_rel, internal), quote=True)}"',
        body)

    def _img(m: re.Match) -> str:
        src = m.group(1)
        if src.startswith(("http://", "https://", "data:", "/")):
            return m.group(0)
        base = posixpath.dirname(doc_rel)
        target = posixpath.normpath(posixpath.join(base, src))
        return f'src="{GH_RAW}/{target}"'
    return IMG_RE.sub(_img, body)


# --------------------------------------------------------------------------- CSS
PAGE_CSS = """
:root{--bg:#f2f6f5;--card:#fff;--card-2:#f7faf9;--ink:#14211f;--muted:#576966;--faint:#7f908d;
--line:#e0e8e7;--accent:#0d7a71;--accent-ink:#0a5c55;--accent-weak:#e2f0ee;--code:#0e3b37;
--ok:#1c8a5a;--ok-weak:#e3f2ea;--warn:#a56b12;--warn-weak:#f6ecd7;--off:#67716f;--off-weak:#eceeed;
--shadow:0 1px 2px rgba(16,36,34,.05),0 8px 24px rgba(16,36,34,.06);
--shadow-lift:0 2px 4px rgba(16,36,34,.06),0 14px 34px rgba(16,36,34,.11);--radius:14px}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0a1211;
--card:#111b19;--card-2:#0e1817;--ink:#e6efec;--muted:#93a6a2;--faint:#728480;--line:#22302d;
--accent:#38c3b3;--accent-ink:#63d8ca;--accent-weak:#123430;--code:#bfe9e2;
--ok:#3bb87c;--ok-weak:#12281e;--warn:#d99f43;--warn-weak:#2a2111;--off:#7d8987;--off-weak:#18211f;
--shadow:0 1px 2px rgba(0,0,0,.34),0 8px 24px rgba(0,0,0,.4);
--shadow-lift:0 2px 6px rgba(0,0,0,.4),0 16px 40px rgba(0,0,0,.5)}}
:root[data-theme="dark"]{--bg:#0a1211;--card:#111b19;--card-2:#0e1817;--ink:#e6efec;--muted:#93a6a2;
--faint:#728480;--line:#22302d;--accent:#38c3b3;--accent-ink:#63d8ca;--accent-weak:#123430;--code:#bfe9e2;
--ok:#3bb87c;--ok-weak:#12281e;--warn:#d99f43;--warn-weak:#2a2111;--off:#7d8987;--off-weak:#18211f;
--shadow:0 1px 2px rgba(0,0,0,.34),0 8px 24px rgba(0,0,0,.4);
--shadow-lift:0 2px 6px rgba(0,0,0,.4),0 16px 40px rgba(0,0,0,.5)}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);line-height:1.62;
font-family:"IBM Plex Sans",system-ui,-apple-system,Segoe UI,sans-serif;font-weight:450;
-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:var(--accent-ink);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1120px;margin:0 auto;padding:clamp(24px,4vw,56px) clamp(18px,4vw,40px) 80px}
.wrap.doc{max-width:900px}
.topbar{display:flex;align-items:center;gap:10px;font-family:"IBM Plex Mono",monospace;
font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);
margin-bottom:24px;flex-wrap:wrap}
.topbar a{color:var(--accent-ink)}.topbar .sep{opacity:.5}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.14em;
text-transform:uppercase;color:var(--accent-ink);margin:0 0 16px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.eyebrow::before{content:"";width:26px;height:2px;background:var(--accent);display:inline-block}
h1{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:clamp(30px,5vw,50px);
line-height:1.04;letter-spacing:-.015em;margin:.1em 0 .35em;text-wrap:balance}
h2{font-family:"Fraunces",serif;font-weight:600;font-size:1.5em;margin:1.8em 0 .5em;
padding-bottom:.28em;border-bottom:1px solid var(--line);letter-spacing:-.01em}
h3{font-family:"Fraunces",serif;font-weight:600;font-size:1.2em;margin:1.5em 0 .4em}
h4,h5,h6{font-weight:600;margin:1.3em 0 .4em}
p,li{font-size:15.5px}
.prose>*:first-child{margin-top:0}
.lede{font-size:clamp(15px,1.9vw,17px);color:var(--muted);max-width:66ch;margin:14px 0 0}
code{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.88em;color:var(--code);
background:color-mix(in srgb,var(--ink) 8%,transparent);padding:.06em .36em;border-radius:5px}
pre{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;
overflow-x:auto;font-size:13px;line-height:1.55;box-shadow:var(--shadow)}
pre code{background:none;padding:0;color:var(--ink);font-size:13px}
blockquote{margin:1.2em 0;padding:.4em 1.1em;border-left:3px solid var(--accent);
background:var(--accent-weak);border-radius:0 10px 10px 0;color:var(--ink)}
blockquote p{margin:.4em 0}
table{border-collapse:collapse;width:100%;margin:1.3em 0;font-size:14px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:8px 12px;text-align:left;vertical-align:top}
th{background:var(--accent-weak);font-weight:600}
hr{border:none;border-top:1px solid var(--line);margin:2em 0}
img{max-width:100%;height:auto;border-radius:8px}
ul,ol{padding-left:1.3em}
.docfoot{margin-top:48px;padding-top:20px;border-top:1px solid var(--line);
display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--muted);
font-family:"IBM Plex Mono",monospace}
/* index hero + status pills */
.status{display:flex;flex-wrap:wrap;gap:10px;margin:24px 0 0}
.pill{display:inline-flex;align-items:baseline;gap:8px;padding:8px 13px;border:1px solid var(--line);
border-radius:999px;background:var(--card);font-size:13px;box-shadow:var(--shadow)}
.pill .k{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--faint)}
.pill .v{font-weight:600}
.dot{width:8px;height:8px;border-radius:50%;align-self:center;flex:0 0 auto}
.dot.ok{background:var(--ok)}.dot.warn{background:var(--warn)}.dot.off{background:var(--off)}
.search{width:100%;padding:13px 15px;margin:26px 0 6px;border:1px solid var(--line);
border-radius:12px;background:var(--card);color:var(--ink);font-size:15px;
font-family:inherit;box-shadow:var(--shadow)}
.search:focus{outline:2px solid var(--accent);outline-offset:1px}
.metaline{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--faint);margin:6px 2px 8px}
/* sections + card grid */
section.group{margin:32px 0 0}
.sec-head{display:flex;align-items:baseline;gap:12px;margin:0 0 14px;padding-bottom:10px;border-bottom:1px solid var(--line)}
.sec-head h2{font-family:"Fraunces",serif;font-weight:600;font-size:20px;letter-spacing:-.01em;margin:0;padding:0;border:0}
.sec-head .count{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--faint)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(288px,1fr));gap:14px}
a.card{display:flex;flex-direction:column;gap:8px;text-decoration:none;color:inherit;
background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px 16px 14px;
box-shadow:var(--shadow);transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease;
position:relative;overflow:hidden}
a.card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--accent);opacity:0;transition:opacity .16s ease}
a.card:hover{transform:translateY(-3px);box-shadow:var(--shadow-lift);border-color:color-mix(in srgb,var(--accent) 40%,var(--line));text-decoration:none}
a.card:hover::before{opacity:1}
a.card:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.kick{display:flex;align-items:center;justify-content:space-between;gap:10px}
.kick .type{font-family:"IBM Plex Mono",monospace;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint)}
.tag{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.04em;padding:3px 8px;border-radius:6px;white-space:nowrap;font-weight:500}
.tag.doc{background:var(--accent-weak);color:var(--accent-ink)}
.tag.page{background:var(--ok-weak);color:var(--ok)}
.tag.download{background:var(--off-weak);color:var(--off)}
a.card h3{font-family:"Fraunces",serif;font-weight:600;font-size:16.5px;line-height:1.18;margin:2px 0 0;
letter-spacing:-.005em;text-wrap:balance;padding:0;border:0}
.path{margin-top:auto;padding-top:10px;font-family:"IBM Plex Mono",monospace;font-size:11px;
color:var(--accent-ink);word-break:break-all;display:flex;align-items:center;gap:7px}
.path::before{content:"↳";color:var(--faint);flex:0 0 auto}
footer.law{margin-top:56px;padding-top:22px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}
footer.law .lead{color:var(--ink);font-size:13.5px;margin:0 0 12px;max-width:80ch}
footer.law .lead b{color:var(--accent-ink)}
footer.law .meta{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--faint);display:flex;flex-wrap:wrap;gap:6px 18px}
.excluded{margin-top:30px;padding:16px 18px;border-radius:12px;
border:1px solid color-mix(in srgb,var(--warn) 34%,transparent);
background:var(--warn-weak);font-size:13.5px;color:var(--ink)}
.excluded b{color:var(--warn)}.excluded a{color:var(--accent-ink)}.excluded ul{margin:.5em 0 0}
@media(max-width:560px){.sec-head{flex-wrap:wrap}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}a.card{transition:none}a.card:hover{transform:none}}
"""

HEAD = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&'
        'family=IBM+Plex+Mono:wght@400;500&'
        'family=IBM+Plex+Sans:wght@400;450;500;600&display=swap">'
        f"<style>{PAGE_CSS}</style>")


def page(title: str, body: str, source_rel: str | None, internal: bool = False) -> str:
    src = ""
    if source_rel:
        src = (f'<a href="{GH_BLOB}/{html.escape(source_rel)}" '
               f'rel="noopener">View source on GitHub →</a>')
    root_href = "/docs/internal" if internal else "/docs"
    crumb = "MIZ OKI · Internal docs" if internal else "MIZ OKI · Docs"
    banner = ("<div class=\"excluded\"><b>Internal — signed in.</b> This page is "
              "served only to an authenticated session and is not part of the "
              "public documentation site.</div>") if internal else ""
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<meta name=\"robots\" content=\"noindex,nofollow\">"
        f"<title>{html.escape(title)} · MIZ OKI docs</title>{HEAD}</head><body>"
        "<div class=\"wrap doc\">"
        f"<nav class=\"topbar\"><a href=\"{root_href}\">{crumb}</a>"
        f"<span class=\"sep\">/</span><span>{html.escape(title)}</span></nav>"
        f"{banner}"
        f"<article class=\"prose\">{body}</article>"
        f"<div class=\"docfoot\"><a href=\"{root_href}\">← All docs</a>{src}</div>"
        "</div></body></html>")


def render_markdown(text: str) -> str:
    md = markdown.Markdown(extensions=[
        "fenced_code", "tables", "sane_lists", "toc", "attr_list", "footnotes",
        "md_in_html", "admonition"])
    return md.convert(text)


def run_self_test() -> bool:
    """Prove the internal gate fires BEFORE trusting a build, in both directions.

    A gate that cannot fail is not a gate (TRUTH.md 5.2). The legal cases matter
    as much as the violations: a rule that withheld ordinary product copy would
    quietly empty the portal, which is the opposite failure and just as bad.
    """
    violations = [
        ("project id", "The service runs in spry-bus-425315-p6 / us-central1.", ""),
        ("project id in a service account",
         "Grant run.invoker to mizoki-platform@spry-bus-425315-p6.iam.gserviceaccount.com.", ""),
        ("Cloud Run URL hash",
         "POST https://service-marketing-connectors-ehqxake3ia-uc.a.run.app/health", ""),
        ("explicit internal marker", "# Ordinary title\n<!-- mizoki:internal -->\nBody.", ""),
        ("internal tree by path", "# A build prompt with no identifiers at all.",
         "prompts/SOME_MASTER_PROMPT.md"),
    ]
    legal = [
        ("ordinary product copy",
         "MIZ OKI Signal prices every order at what it truly nets after returns.", ""),
        ("architecture canon naming the approval ceremony",
         "The site ships only when a human types APPROVED: DEPLOY on the dispatch.", ""),
        ("merge ceremony string", "Land it with APPROVED: MERGE in session.", ""),
        ("AI branch name in prose",
         "Landed via claude/oracle-preconversion-intent-v1.0 on main.", ""),
        ("generic cloud vocabulary",
         "Cloud Run, us-central1, BigQuery, and Firestore back the fleet.", ""),
        ("marketing doc under a normal tree",
         "# Shopify offering\nNet contribution, not top line.", "marketing/OFFER.md"),
    ]
    ok = True
    for name, text, docrel in violations:
        hits = find_internal(text, docrel)
        print(f"  self-test seeded disclosure [{name}]: {'CAUGHT' if hits else 'MISSED'}")
        ok &= bool(hits)
    for name, text, docrel in legal:
        hits = find_internal(text, docrel)
        print(f"  self-test legal content [{name}]: "
              f"{'STAYS PUBLISHED' if not hits else 'WRONGLY WITHHELD ' + str(hits)}")
        ok &= not hits
    # The binary path must enforce the same rule as the text path.
    bin_hit = bool(find_internal_bytes(b"%PDF-1.4 ... project spry-bus-425315-p6 ..."))
    print(f"  self-test binary path carries the gate: {'CAUGHT' if bin_hit else 'MISSED'}")
    ok &= bin_hit
    bin_clean = not find_internal_bytes(b"%PDF-1.4 ... ordinary pilot playbook ...")
    print(f"  self-test binary path passes clean files: "
          f"{'OK' if bin_clean else 'WRONGLY WITHHELD'}")
    ok &= bin_clean
    # The tabular-data gate, both directions (WS-0). Person data never reaches a
    # portal by omission; an allowlisted template is not withheld by accident.
    seed_allow = {"docs/onboarding/cogs_worksheet_template.csv"}
    tab_hit = bool(tabular_gate("docs/misc/customers_export.csv", seed_allow))
    print(f"  self-test unlisted tabular file is withheld: {'CAUGHT' if tab_hit else 'MISSED'}")
    ok &= tab_hit
    tab_clean = tabular_gate("docs/onboarding/cogs_worksheet_template.csv", seed_allow) is None
    print(f"  self-test allowlisted table stays published: "
          f"{'OK' if tab_clean else 'WRONGLY WITHHELD'}")
    ok &= tab_clean
    tab_md = tabular_gate("docs/onboarding/cogs_worksheet.md", set()) is None
    print(f"  self-test non-tabular file is not touched by the data gate: "
          f"{'OK' if tab_md else 'WRONGLY WITHHELD'}")
    ok &= tab_md
    warn_hit = bool(person_like_columns("Customer ID,First Name,Last Name,Email,Phone"))
    print(f"  self-test person-like header is flagged: {'CAUGHT' if warn_hit else 'MISSED'}")
    ok &= warn_hit
    warn_clean = not person_like_columns("section,variant_id,sku,landed_unit_cogs,notes")
    print(f"  self-test economics header is not flagged: "
          f"{'OK' if warn_clean else 'WRONGLY FLAGGED'}")
    ok &= warn_clean
    print("SELF-TEST PASS — the internal gate fires" if ok
          else "SELF-TEST FAIL — the internal gate is not trustworthy")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--out", default="# MIZ OKI 3.5/site_docs")
    ap.add_argument("--out-internal", default="# MIZ OKI 3.5/site_docs_internal",
                    help="portal for docs that require a signed-in session")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the internal-disclosure gate catches seeded cases")
    args = ap.parse_args()

    if args.self_test:
        return 0 if run_self_test() else 1

    root = Path(args.repo_root).resolve()
    docs = root / "docs"
    out = (root / args.out).resolve()
    out_internal = (root / args.out_internal).resolve()
    if not docs.is_dir():
        print(f"::error::docs/ not found under {root}", file=sys.stderr)
        return 1

    for d in (out, out_internal):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    tabular_allowlist = load_tabular_allowlist(root)
    person_warnings: list[str] = []

    # First pass: the set of repo-relative doc paths we will publish (for links).
    all_files = [p for p in docs.rglob("*") if p.is_file()]
    known = {str(p.relative_to(root).as_posix()) for p in all_files}

    # Classify BEFORE rendering. A link's correct target depends on which portal
    # the target lands in, and that is only knowable once every file has been
    # gated — so the classification cannot be a side effect of the render loop.
    internal_docrels: set[str] = set()
    for src in all_files:
        docrel = src.relative_to(docs).as_posix()
        reasons: list[str] = []
        if src.suffix.lower() in BINARY_EXT:
            reasons = find_internal_bytes(src.read_bytes())
            for prefix in INTERNAL_PATH_PREFIXES:
                if docrel.startswith(prefix):
                    reasons = sorted(set(reasons + [f"internal tree docs/{prefix}"]))
                    break
        else:
            try:
                reasons = find_internal(src.read_text(encoding="utf-8"), docrel)
            except (UnicodeDecodeError, OSError):
                continue          # unreadable files are excluded later anyway
        if reasons:
            internal_docrels.add(docrel)

    # One output path, one source. Two sources resolving to the same output
    # overwrite each other silently — that defect hid a hand-authored page for
    # five deploys (shared-memory hazard e3d81187). Fail the build instead.
    emitted: dict[Path, str] = {}
    collisions: list[str] = []

    def claim(dest: Path, rel: str) -> bool:
        prior = emitted.get(dest)
        if prior is not None:
            collisions.append(f"{dest.name}: '{prior}' and '{rel}' both render here")
            return False
        emitted[dest] = rel
        return True

    entries: list[dict] = []
    internal_entries: list[dict] = []
    excluded: list[dict] = []
    # A withheld file from a tree that is internal BY PURPOSE (INTERNAL_PATH_PREFIXES)
    # is not NAMED on the public portal either: its entry is listed behind sign-in,
    # beside the tree's rendered pages. Measured 2026-09-25: the xprovider pack's
    # Claude zips cannot be read as text, and the public withheld list would have
    # named all 14 — the owner's personal workflow skills among them — while every
    # other file of that tree stays sign-in-only.
    excluded_internal: list[dict] = []
    written = 0
    written_internal = 0

    def target(is_internal: bool):
        """Where a document renders, and which index lists it.

        Internal documents are NOT discarded — they are rendered into a second
        portal that app.py serves only behind the site's own login
        (`login_required`, the same session gate the front end uses). Owner
        directive 2026-08-21: "put the docs under the same code log in as the
        front end." Withholding kept infrastructure identifiers off the public
        web but also cost the team its own runbooks; signing in restores them
        without reopening the disclosure.
        """
        return (out_internal, internal_entries, "/docs/internal/") if is_internal \
            else (out, entries, "/docs/")

    for src in sorted(all_files):
        rel = src.relative_to(root).as_posix()          # e.g. docs/runbooks/x.md
        docrel = src.relative_to(docs).as_posix()       # e.g. runbooks/x.md
        ext = src.suffix.lower()
        withheld_into = excluded_internal if docrel.startswith(INTERNAL_PATH_PREFIXES) else excluded

        # Data gate first: a table is withheld from BOTH portals unless it is
        # allowlisted by path. This runs before the secret and identifier gates
        # because those look for the wrong thing in a customer export.
        withheld = tabular_gate(rel, tabular_allowlist)
        if withheld:
            withheld_into.append({"path": rel, "reason": withheld})
            continue

        if ext in BINARY_EXT:
            # Binaries are published verbatim, so they pass the same gate. A PDF
            # carrying the project id is the identical disclosure as a markdown
            # page carrying it.
            internal = find_internal_bytes(src.read_bytes())
            for prefix in INTERNAL_PATH_PREFIXES:
                if docrel.startswith(prefix):
                    internal = sorted(set(internal + [f"internal tree docs/{prefix}"]))
                    break
            dest_root, dest_entries, href_prefix = target(bool(internal))
            dest = dest_root / docrel
            if not claim(dest, rel):
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            dest_entries.append({"title": src.name, "path": docrel,
                                 "href": href_prefix + docrel,
                                 "group": docrel.split("/")[0] if "/" in docrel else "(root)",
                                 "kind": "download", "internal": internal})
            if internal:
                written_internal += 1
            else:
                written += 1
            continue

        try:
            raw = src.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            withheld_into.append({"path": rel, "reason": f"unreadable: {exc.__class__.__name__}"})
            continue

        # Heuristic, not a gate: a header row that looks like person data is
        # reported so a reviewer looks — on an allowlisted table or on any text
        # file that starts with such a row.
        person_cols = person_like_columns(first_line(raw)) if ext in HEADER_SCAN_EXT else []
        if person_cols:
            person_warnings.append(rel)
            print(f"::warning::person-like columns in {rel}: {', '.join(person_cols)}",
                  file=sys.stderr)

        secrets = find_secrets(raw)
        if secrets:
            withheld_into.append({"path": rel, "reason": "secret-scan", "matched": secrets})
            continue

        internal = find_internal(raw, docrel)
        dest_root, dest_entries, href_prefix = target(bool(internal))

        if ext in {".html", ".htm"}:
            # A complete, self-styled page (e.g. a published compendium) — served
            # verbatim, listed on the index, never re-wrapped.
            m = re.search(r"<title>(.*?)</title>", raw, re.I | re.S)
            title = html.unescape(m.group(1).strip()) if m else src.stem
            dest = dest_root / docrel
            if not claim(dest, rel):
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(raw, encoding="utf-8")
            dest_entries.append({"title": title, "path": docrel,
                                 "href": href_prefix + docrel,
                                 "group": docrel.split("/")[0] if "/" in docrel else "(root)",
                                 "kind": "page", "internal": internal})
            if internal:
                written_internal += 1
            else:
                written += 1
            continue

        if ext == ".md":
            title = md_title(raw, src.stem)
            body = strip_scripts(render_markdown(raw))
            body = rewrite_links(body, rel, internal_docrels)
            outrel = posixpath.splitext(docrel)[0] + ".html"
        elif ext in TEXT_EXT:
            title = src.name
            body = (f"<h1>{html.escape(src.name)}</h1>"
                    f"<pre><code>{html.escape(raw)}</code></pre>")
            outrel = docrel + ".html"
        else:
            withheld_into.append({"path": rel, "reason": f"unsupported type {ext or '(none)'}"})
            continue

        dest = dest_root / outrel
        if not claim(dest, rel):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page(title, body, rel, internal=bool(internal)), encoding="utf-8")
        dest_entries.append({"title": title, "path": docrel,
                             "href": href_prefix + outrel,
                             "group": docrel.split("/")[0] if "/" in docrel else "(root)",
                             "kind": "doc", "internal": internal})
        if internal:
            written_internal += 1
        else:
            written += 1

    if collisions:
        print("::error::output-path collision — two sources render to one page; "
              "rename one so each source owns a distinct output path",
              file=sys.stderr)
        for c in collisions:
            print(f"  collision: {c}", file=sys.stderr)
        return 1

    # ------------------------------------------------------------------- index
    def group_sort(k: str) -> tuple[int, str]:
        return (1 if k == "(root)" else 0, k.lower())

    kind_label = {"doc": "Doc", "page": "Page", "download": "File"}

    def render_index(items: list[dict], count: int, *, internal: bool,
                     extra_html: str = "", stats: dict | None = None) -> str:
        groups: dict[str, list[dict]] = {}
        for e in items:
            groups.setdefault(e["group"], []).append(e)
        blocks = []
        for g in sorted(groups, key=group_sort):
            rows_ = sorted(groups[g], key=lambda e: e["title"].lower())
            cards = "".join(
                f'<a class="card" data-s="{html.escape((e["title"]+" "+e["path"]).lower())}" '
                f'href="{html.escape(e["href"])}">'
                f'<div class="kick"><span class="type">'
                f'{html.escape((posixpath.splitext(e["path"])[1][1:] or "doc").upper())}'
                f'</span><span class="tag {html.escape(e.get("kind","doc"))}">'
                f'{html.escape(kind_label.get(e.get("kind","doc"),"Doc"))}</span></div>'
                f'<h3>{html.escape(e["title"])}</h3>'
                f'<span class="path">{html.escape(e["path"])}</span></a>'
                for e in rows_)
            blocks.append(
                f'<section class="group"><div class="sec-head">'
                f'<h2>{html.escape(g)}</h2><span class="count">{len(rows_)}</span></div>'
                f'<div class="grid">{cards}</div></section>')
        search_js = (
            "<script>const q=document.getElementById('q'),"
            "cs=[...document.querySelectorAll('.card')];"
            "q.addEventListener('input',()=>{const v=q.value.trim().toLowerCase();let n=0;"
            "cs.forEach(c=>{const m=!v||c.dataset.s.includes(v);"
            "c.style.display=m?'':'none';if(m)n++;});"
            "document.querySelectorAll('.group').forEach(g=>{"
            "const any=[...g.querySelectorAll('.card')]"
            ".some(c=>c.style.display!=='none');g.style.display=any?'':'none';});"
            "document.getElementById('c').textContent=n+' of " + str(count) +
            " shown';});</script>")
        title = "MIZ OKI Internal Documentation" if internal else "MIZ OKI Documentation"
        eyebrow = ("MIZ OKI · Internal · signed-in only" if internal
                   else "MIZ OKI · Platform Documentation")
        lede = ("Documents that carry production infrastructure identifiers or "
                "build instructions. Served only to a signed-in session — this "
                "page is never part of the public documentation site."
                if internal else
                "The platform's engineering, governance, and product docs — "
                "generated from the repository's <code>docs/</code> tree and "
                "rebuilt on every deploy.")
        crumb = "Internal docs" if internal else "Docs"

        def pill(dot: str, k: str, v) -> str:
            return (f'<span class="pill"><span class="dot {dot}"></span>'
                    f'<span class="k">{html.escape(k)}</span>'
                    f'<span class="v">{html.escape(str(v))}</span></span>')
        pills = ""
        if stats:
            if internal:
                inner = pill("off", "Sign-in only", stats.get("internal", count))
            else:
                inner = (pill("ok", "Public", stats.get("public", count))
                         + pill("off", "Sign-in", stats.get("internal", 0))
                         + pill("warn", "Withheld", stats.get("withheld", 0))
                         + pill("ok", "Source", "docs/ tree"))
            pills = f'<div class="status">{inner}</div>'

        footer = (
            '<footer class="law"><p class="lead">'
            '<b>Generated from the repository <code>docs/</code> tree</b> and rebuilt on '
            'every deploy — GitHub is the source of truth. A live-credential scan and an '
            'infrastructure-identifier gate run before publish: documents that carry a '
            'secret are withheld entirely, and documents that carry a production identifier '
            'are served only to a signed-in session.</p><div class="meta">'
            '<span>repo · mediaintelligence/MIZOKICloudRun</span>'
            '<span>portal · mizoki3.com/docs</span>'
            '<span>links → blob/main</span></div></footer>')
        return (
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta name=\"robots\" content=\"noindex,nofollow\">"
            f"<title>{title}</title>{HEAD}</head><body><div class=\"wrap\">"
            "<nav class=\"topbar\"><a href=\"/\">MIZ OKI 3.5</a>"
            f"<span class=\"sep\">/</span><span>{crumb}</span></nav>"
            f"<p class=\"eyebrow\">{html.escape(eyebrow)}</p>"
            f"<h1>{title}</h1>"
            f"<p class=\"lede\">{lede}</p>"
            f"{pills}"
            "<input id=\"q\" class=\"search\" type=\"search\" "
            "placeholder=\"Filter docs by title or path…\" "
            "autocomplete=\"off\" aria-label=\"Filter docs\">"
            f"<div class=\"metaline\" id=\"c\">{count} docs</div>"
            f"{''.join(blocks)}{extra_html}{footer}{search_js}</div></body></html>")

    def withheld_rows(items: list[dict]) -> str:
        return "".join(
            f"<li><code>{html.escape(x['path'])}</code> — {html.escape(x['reason'])}"
            f"{(' (' + ', '.join(map(html.escape, x['matched'])) + ')') if x.get('matched') else ''}</li>"
            for x in items)

    excl_html = ""
    if excluded:
        excl_html = (
            f'<div class="excluded"><b>{len(excluded)} file(s) withheld</b> from every '
            f'portal (live-credential scan or unsupported type). They remain in the repo.'
            f'<ul>{withheld_rows(excluded)}</ul></div>')
    excl_internal_html = ""
    if excluded_internal:
        excl_internal_html = (
            f'<div class="excluded"><b>{len(excluded_internal)} file(s) withheld</b> from '
            f'both portals. They sit in a tree that is internal by purpose, so they are '
            f'listed only here. They remain in the repo.'
            f'<ul>{withheld_rows(excluded_internal)}</ul></div>')

    # The public index says the internal set exists and how to reach it. Saying so
    # is not a disclosure — the count and the sign-in link carry no identifiers —
    # and hiding it would leave readers hunting for docs that simply moved.
    if written_internal:
        excl_html += (
            f'<div class="excluded"><b>{written_internal} document(s) require '
            f'sign-in.</b> They carry production infrastructure identifiers or build '
            f'instructions, so they are served only to an authenticated session: '
            f'<a href="/docs/internal">MIZ OKI internal docs →</a></div>')

    portal_stats = {"public": written, "internal": written_internal,
                    "withheld": len(excluded)}
    (out / "index.html").write_text(
        render_index(entries, written, internal=False, extra_html=excl_html,
                     stats=portal_stats),
        encoding="utf-8")
    (out_internal / "index.html").write_text(
        render_index(internal_entries, written_internal, internal=True,
                     extra_html=excl_internal_html,
                     stats={**portal_stats, "withheld": len(excluded_internal)}),
        encoding="utf-8")

    (out / "EXCLUSIONS.json").write_text(json.dumps(excluded, indent=2), encoding="utf-8")
    (out_internal / "EXCLUSIONS.json").write_text(
        json.dumps(excluded_internal, indent=2), encoding="utf-8")
    (out / "manifest.json").write_text(
        json.dumps({"written": written, "excluded": len(excluded),
                    "internal": written_internal, "entries": entries}, indent=2),
        encoding="utf-8")
    (out_internal / "manifest.json").write_text(
        json.dumps({"written": written_internal, "entries": internal_entries},
                   indent=2), encoding="utf-8")

    by_reason: dict[str, int] = {}
    for x in excluded:
        by_reason[x["reason"]] = by_reason.get(x["reason"], 0) + 1
    summary = ", ".join(f"{n} {r}" for r, n in sorted(by_reason.items())) or "none"
    print(f"site_docs: {written} public pages → {out}")
    print(f"site_docs: {written_internal} sign-in-only pages → {out_internal}")
    print(f"site_docs: {len(excluded)} withheld entirely ({summary})")
    for x in excluded:
        print(f"  withheld: {x['path']} ({x['reason']})")
    print(f"site_docs: {len(excluded_internal)} withheld from an internal tree "
          f"(listed only behind sign-in)")
    for x in excluded_internal:
        print(f"  withheld (internal tree): {x['path']} ({x['reason']})")
    if person_warnings:
        print(f"site_docs: {len(person_warnings)} published file(s) start with a "
              f"person-like header — review them: {', '.join(person_warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
