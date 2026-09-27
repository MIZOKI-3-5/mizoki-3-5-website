"""AEO/GEO authority pages — loader, front-matter parser, expiry check, renderer.

Lane 5 S4 (PROJECT COMPLETION v1.0, 2026-09-02). Serves the pages under the
repository's ``docs/marketing/aeo/*.md`` at ``/learn/<slug>`` behind the
``LEARN_PAGES`` flag (``site_flags.learn_pages_enabled``; default OFF → 404).

Design constraints, each pinned by ``tests/test_learn_pages.py``:

* **No new runtime dependency.** The site's ``markdown`` library is a
  BUILD-TIME dependency of ``scripts/build_site_docs.py`` (``requirements-docs.lock``)
  and is not in the runtime image (``requirements.txt``). This module renders a
  bounded markdown SUBSET (headings, paragraphs, lists, fenced code, bold /
  emphasis / inline code / http(s)-or-site-relative links). Raw HTML is never
  passed through — every character is escaped first — so a page cannot inject
  a script, and the pages are tested to use only the supported subset.
* **Fail closed, honestly.** The pages directory is resolved from
  ``LEARN_PAGES_DIR`` or the two default locations; when none exists and the
  flag is ON, the route answers ``503 not_configured`` — never a healthy stub.
  A page whose ``expires`` date has passed is WITHHELD (404), never served
  stale; the index lists only current pages.
* **Front matter is the contract.** ``title``, ``last_reviewed``, ``owner``
  (a role, never a person or an address), ``expires`` (≤ 90 days after
  ``last_reviewed``), ``status_label`` (LIVE / PARTIAL / IN BUILD / PROPOSED /
  ROADMAP — the capability label the page describes; nothing on the page may
  claim above it). A malformed page is a load error, not a silently skipped
  file.
* **FAQ JSON-LD** is the one fenced ```` ```json ```` block whose ``@type`` is
  ``FAQPage``; it is emitted as ``<script type="application/ld+json">`` in the
  head and removed from the rendered body.

Nothing here reads the network or the environment beyond ``LEARN_PAGES_DIR``.
"""
from __future__ import annotations

import html
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

SITE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SITE_DIR.parent
PAGES_DIR_ENV = "LEARN_PAGES_DIR"
# Dev/test checkout first (the repository's docs tree); then a deploy-time copy
# inside the site image (the image is built from "# MIZ OKI 3.5" only, so the
# repository docs/ tree is NOT present in production without that copy step).
DEFAULT_PAGES_DIRS = (REPO_ROOT / "docs" / "marketing" / "aeo", SITE_DIR / "learn_pages")

STATUS_LABELS = ("LIVE", "PARTIAL", "IN BUILD", "PROPOSED", "ROADMAP")
REQUIRED_FRONT_MATTER = ("title", "last_reviewed", "owner", "expires", "status_label")
MAX_REVIEW_DAYS = 90
MAX_DIRECT_ANSWER_WORDS = 60
MIN_SOURCED_STATS = 5
MIN_FAQ_ITEMS = 3

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# An inline-sourced statistic: "(NRF / Happy Returns, Oct 2025)". The source
# must start with a capital and the month/year must sit in the same
# parenthesis — the same shape scripts/mizoki_canon.py rule V13 accepts.
STAT_CITATION = re.compile(
    r"\(([A-Z][^()]*?),\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+((?:19|20)\d{2})\)"
)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_FENCE = re.compile(r"^```([\w-]*)\s*$")
_LINK_TARGET = re.compile(r"^(?:https://[^\s\"'<>]+|/[^\s\"'<>]*)$")


class PageError(ValueError):
    """A page that does not satisfy the front-matter contract."""


@dataclass(frozen=True)
class Page:
    slug: str
    title: str
    description: str
    last_reviewed: date
    owner: str
    expires: date
    status_label: str
    body_md: str            # markdown after the front matter, JSON-LD block removed
    faq_jsonld: dict | None
    direct_answer: str
    path: str


# ----------------------------------------------------------------- location

def pages_dir() -> Path | None:
    """The pages directory, or None when nothing is configured (fail closed)."""
    override = os.environ.get(PAGES_DIR_ENV, "").strip()
    candidates = (Path(override),) if override else DEFAULT_PAGES_DIRS
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


# ------------------------------------------------------------- front matter

def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Return (fields, body). Scalars only — ``key: value`` per line; a quoted
    value has its quotes stripped. No YAML library is needed or used."""
    match = _FRONT_MATTER.match(text)
    if not match:
        raise PageError("missing YAML front matter (--- ... ---)")
    fields: dict[str, str] = {}
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise PageError(f"front matter line is not key: value — {line!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key in fields:
            raise PageError(f"duplicate front-matter key {key!r}")
        fields[key] = value
    return fields, text[match.end():]


def _parse_date(value: str, key: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PageError(f"{key} must be an ISO date (YYYY-MM-DD), got {value!r}") from exc


def load_page(path: Path) -> Page:
    text = path.read_text(encoding="utf-8")
    fields, body = parse_front_matter(text)
    missing = [k for k in REQUIRED_FRONT_MATTER if not fields.get(k)]
    if missing:
        raise PageError(f"{path.name}: missing front matter {missing}")
    slug = path.stem
    if not SLUG.match(slug):
        raise PageError(f"{path.name}: file name is not a slug ([a-z0-9-])")
    last_reviewed = _parse_date(fields["last_reviewed"], "last_reviewed")
    expires = _parse_date(fields["expires"], "expires")
    if expires <= last_reviewed:
        raise PageError(f"{path.name}: expires must be after last_reviewed")
    if (expires - last_reviewed).days > MAX_REVIEW_DAYS:
        raise PageError(f"{path.name}: expires is more than {MAX_REVIEW_DAYS} days after last_reviewed")
    status_label = fields["status_label"].strip("[]")
    if status_label not in STATUS_LABELS:
        raise PageError(f"{path.name}: status_label {status_label!r} not in {STATUS_LABELS}")
    if EMAIL.search(fields["owner"]):
        raise PageError(f"{path.name}: owner must be a role, never an address")
    faq_jsonld, body_wo_jsonld = extract_jsonld(body)
    return Page(
        slug=slug,
        title=fields["title"],
        description=fields.get("description", ""),
        last_reviewed=last_reviewed,
        owner=fields["owner"],
        expires=expires,
        status_label=status_label,
        body_md=body_wo_jsonld,
        faq_jsonld=faq_jsonld,
        direct_answer=direct_answer(body_wo_jsonld),
        path=str(path),
    )


def load_pages(directory: Path) -> list[Page]:
    """Every ``*.md`` page in the directory, by slug. ``README.md`` is the
    directory's own documentation (the citation-KPI note), not a page."""
    pages = []
    for path in sorted(directory.glob("*.md")):
        if path.name.upper() == "README.MD":
            continue
        pages.append(load_page(path))
    return pages


def is_overdue(page: Page, today: date | None = None) -> bool:
    """True once ``expires`` has passed — the page is withheld, not served stale."""
    return (today or date.today()) > page.expires


# ------------------------------------------------------------ page sections

def _section(body_md: str, heading: str) -> str:
    """Text under ``## <heading>`` up to the next ``## `` heading (case-insensitive)."""
    lines = body_md.splitlines()
    out: list[str] = []
    active = False
    for line in lines:
        if line.startswith("## "):
            if active:
                break
            active = line[3:].strip().lower() == heading.lower()
            continue
        if active:
            out.append(line)
    return "\n".join(out).strip()


def direct_answer(body_md: str) -> str:
    return " ".join(_section(body_md, "Direct answer").split())


def word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def sourced_stat_citations(text: str) -> list[tuple[str, str, str]]:
    """Every ``(<Source>, <Mon YYYY>)`` citation in the text."""
    return [(m.group(1).strip(), m.group(2), m.group(3)) for m in STAT_CITATION.finditer(text)]


def extract_faq(body_md: str) -> list[tuple[str, str]]:
    """``### <question>`` items under ``## FAQ`` with their answer paragraphs."""
    section = _section(body_md, "FAQ")
    items: list[tuple[str, list[str]]] = []
    for line in section.splitlines():
        if line.startswith("### "):
            items.append((line[4:].strip(), []))
        elif items and line.strip():
            items[-1][1].append(line.strip())
    return [(q, " ".join(a)) for q, a in items]


def extract_jsonld(body_md: str) -> tuple[dict | None, str]:
    """The one fenced ``json`` block carrying a schema.org FAQPage, and the body
    with that block removed. Any other fenced block is left in place."""
    lines = body_md.splitlines()
    out: list[str] = []
    found: dict | None = None
    i = 0
    while i < len(lines):
        fence = _FENCE.match(lines[i])
        if fence and fence.group(1).lower() == "json" and found is None:
            j = i + 1
            block: list[str] = []
            while j < len(lines) and not _FENCE.match(lines[j]):
                block.append(lines[j])
                j += 1
            try:
                data = json.loads("\n".join(block))
            except json.JSONDecodeError as exc:
                raise PageError(f"json block is not valid JSON: {exc}") from exc
            if isinstance(data, dict) and data.get("@type") == "FAQPage":
                found = data
                i = j + 1
                # drop a blank line that immediately followed the block
                if i < len(lines) and not lines[i].strip():
                    i += 1
                continue
        out.append(lines[i])
        i += 1
    return found, "\n".join(out)


# ------------------------------------------------------------- the renderer

def _inline(text: str) -> str:
    """Escape first, then apply the four inline forms. Links are only ever
    https:// or site-relative — anything else stays literal text."""
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", lambda m: f"<strong>{m.group(1)}</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*\s][^*]*?)\*(?!\*)", lambda m: f"<em>{m.group(1)}</em>", escaped)

    def link(m: re.Match) -> str:
        label, target = m.group(1), html.unescape(m.group(2))
        if not _LINK_TARGET.match(target):
            return m.group(0)
        return f'<a href="{html.escape(target, quote=True)}">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, escaped)


def render_markdown(md: str) -> str:
    """Bounded markdown subset → HTML. See the module docstring for the subset."""
    out: list[str] = []
    para: list[str] = []
    list_tag: str | None = None
    lines = md.splitlines()
    i = 0

    def flush_para() -> None:
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None

    while i < len(lines):
        line = lines[i]
        fence = _FENCE.match(line)
        if fence:
            flush_para()
            close_list()
            j = i + 1
            block: list[str] = []
            while j < len(lines) and not _FENCE.match(lines[j]):
                block.append(lines[j])
                j += 1
            lang = html.escape(fence.group(1), quote=True)
            cls = f' class="language-{lang}"' if lang else ""
            out.append(f"<pre><code{cls}>{html.escape(chr(10).join(block), quote=False)}</code></pre>")
            i = j + 1
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            flush_para()
            close_list()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            anchor = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
            out.append(f'<h{level} id="{html.escape(anchor, quote=True)}">{_inline(text)}</h{level}>')
            i += 1
            continue
        item = re.match(r"^(?:[-*]|\d+\.)\s+(.*)$", line)
        if item:
            flush_para()
            tag = "ol" if line[0].isdigit() else "ul"
            if list_tag != tag:
                close_list()
                out.append(f"<{tag}>")
                list_tag = tag
            out.append(f"<li>{_inline(item.group(1))}</li>")
            i += 1
            continue
        if line.startswith("> "):
            flush_para()
            close_list()
            out.append(f"<blockquote><p>{_inline(line[2:])}</p></blockquote>")
            i += 1
            continue
        if not line.strip():
            flush_para()
            close_list()
            i += 1
            continue
        if list_tag:
            close_list()
        para.append(line.strip())
        i += 1
    flush_para()
    close_list()
    return "\n".join(out)


# Self-contained: no web font, no stylesheet, no script host — the no-egress
# sweep (tests/test_no_egress.py) is extended to these routes by
# tests/test_learn_pages.py.
_CSS = (
    "body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;"
    "color:#1b1f24;background:#fff;line-height:1.55}"
    "main{max-width:44rem;margin:0 auto;padding:2rem 1.25rem 4rem}"
    "header.site{border-bottom:1px solid #e3e6ea;padding:.75rem 1.25rem;font-size:.9rem}"
    "header.site a{color:#1b1f24;text-decoration:none;margin-right:1rem}"
    ".meta{font-size:.85rem;color:#4b5563;margin:0 0 1.5rem}"
    ".label{display:inline-block;border:1px solid #4b5563;border-radius:.25rem;padding:0 .4rem;"
    "font-size:.75rem;letter-spacing:.04em;margin-right:.5rem}"
    ".direct{border-left:4px solid #1b1f24;padding:.25rem 1rem;margin:1rem 0 1.5rem;background:#f6f7f9}"
    "pre{overflow-x:auto;background:#f6f7f9;padding:.75rem;border-radius:.25rem;font-size:.85rem}"
    "code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}"
    "footer{font-size:.8rem;color:#4b5563;border-top:1px solid #e3e6ea;margin-top:3rem;padding-top:1rem}"
    "h1{font-size:1.75rem;line-height:1.2}h2{font-size:1.25rem;margin-top:2rem}h3{font-size:1.05rem}"
)


def _jsonld_script(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def _shell(title: str, description: str, canonical: str, head_extra: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{html.escape(title)} · MIZ OKI Learn</title>\n"
        f"<meta name=\"description\" content=\"{html.escape(description, quote=True)}\">\n"
        f"<link rel=\"canonical\" href=\"{html.escape(canonical, quote=True)}\">\n"
        "<meta name=\"robots\" content=\"index,follow\">\n"
        f"<style>{_CSS}</style>\n{head_extra}"
        "</head>\n<body>\n"
        "<header class=\"site\"><a href=\"/\">MIZ OKI</a><a href=\"/learn/\">Learn</a>"
        "<a href=\"/docs\">Docs</a><a href=\"/shopify\">Shopify</a></header>\n"
        f"<main>\n{body}\n"
        "<footer>Capability labels (LIVE · PARTIAL · IN BUILD · PROPOSED · ROADMAP) and figure labels "
        "follow the platform's published truth discipline; every third-party statistic names its source "
        "and month inline. Pages are withheld automatically once their review date passes.</footer>\n"
        "</main>\n</body>\n</html>\n"
    )


def render_page(page: Page, base_url: str) -> str:
    body_html = render_markdown(page.body_md)
    # Give the direct-answer block its own visual weight: wrap the section that
    # follows the "Direct answer" heading. The renderer emitted it as h2 + p.
    body_html = re.sub(
        r'(<h2 id="direct-answer">.*?</h2>)\n(<p>.*?</p>)',
        r'\1\n<div class="direct">\2</div>',
        body_html, count=1, flags=re.S,
    )
    meta = (
        f'<p class="meta"><span class="label">{html.escape(page.status_label)}</span>'
        f"Last reviewed {page.last_reviewed.isoformat()} · Review due {page.expires.isoformat()} · "
        f"Owner: {html.escape(page.owner)}</p>"
    )
    head_extra = _jsonld_script(page.faq_jsonld) + "\n" if page.faq_jsonld else ""
    body = f"<h1>{html.escape(page.title)}</h1>\n{meta}\n{body_html}"
    return _shell(page.title, page.description or page.direct_answer, f"{base_url}/learn/{page.slug}", head_extra, body)


def render_index(pages: Iterable[Page], base_url: str) -> str:
    items = "".join(
        f'<li><a href="/learn/{html.escape(p.slug, quote=True)}">{html.escape(p.title)}</a>'
        f' <span class="label">{html.escape(p.status_label)}</span>'
        f"<br><small>{html.escape(p.description or p.direct_answer)}</small></li>\n"
        for p in pages
    )
    body = (
        "<h1>Learn</h1>\n"
        "<p class=\"meta\">Direct answers on governed ad autonomy, incrementality and the decision "
        "objects behind them. Each page states the capability label it describes.</p>\n"
        f"<ul>\n{items}</ul>"
    )
    return _shell("Learn", "MIZ OKI authority pages: governed ad autonomy, incrementality, decision governance.",
                  f"{base_url}/learn/", "", body)


# ---------------------------------------------------------------- llms.txt

def render_llms_txt(static_text: str, pages: Iterable[Page], base_url: str) -> str:
    """The static llms.txt plus a ``## Learn`` section derived from the loader —
    the /learn/ links are never hand-listed in the static file."""
    lines = [static_text.rstrip("\n")]
    current = list(pages)
    if current:
        lines.append("")
        lines.append("## Learn")
        lines.append("")
        for p in current:
            summary = p.description or p.direct_answer
            lines.append(f"- [{p.title}]({base_url}/learn/{p.slug}): {summary}")
    return "\n".join(lines) + "\n"


def llms_txt_paths(text: str, base_url: str) -> list[str]:
    """Every site path the file links to (absolute URLs on the canonical host)."""
    prefix = re.escape(base_url)
    return sorted({m.group(1) for m in re.finditer(prefix + r"(/[^\s)>\"']*)", text)})
