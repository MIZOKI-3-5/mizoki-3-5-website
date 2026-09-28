import hashlib
import json
import math
import os
import re
import secrets
import threading
import time
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

from mizoki_runtime import BossRuntime, create_runtime
from mizoki_runtime import abtest
from mizoki_runtime import learn_pages, pilot_requests, site_events, site_flags
# WO-33 (#1003): vendored design-partner pipeline (byte-identical to
# src/shared/design_partner_pipeline — the site runtime never imports src/shared);
# only `flags`, `intake` and `store` are used, all behind DESIGN_PARTNER_PIPELINE.
from mizoki_runtime.design_partner_pipeline import flags as dpp_flags
from mizoki_runtime.design_partner_pipeline import intake as dpp_intake
from mizoki_runtime.design_partner_pipeline import store as dpp_store
from mizoki_runtime import connections
from mizoki_runtime import (
    demo_capital,
    demo_counsel,
    demo_estate,
    demo_narrator,
    demo_nexus,
    demo_risk,
    demo_signal,
    demo_telemetry,
)
from mizoki_runtime import briefing_guide


BASE_DIR = Path(__file__).resolve().parent
INTENT_DIST_DIR = BASE_DIR / "intent-dist"
CANONICAL_HOST = "mizoki3.com"
CANONICAL_BASE_URL = f"https://{CANONICAL_HOST}"
# D3 fix: both URLs are env-tunable and default to on-site destinations —
# the old mizoki.mizoki3.com subdomain redirect-looped.
EXTERNAL_DASHBOARD_URL = os.environ.get("MIZOKI_EXTERNAL_DASHBOARD_URL", "/console")
EXTERNAL_LOGIN_URL = os.environ.get("MIZOKI_EXTERNAL_LOGIN_URL", "/admin/login")
TOP_LEVEL_STATIC_EXTENSIONS = {
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".map",
    ".md",
    ".pdf",
    ".png",
    ".svg",
    ".txt",
    ".xml",
    ".zip",
}
ALLOWED_TEMPLATES = {
    "contact.html",
    "index.html",
    "intelligence.html",
    "vision.html",
}


_BLOG_MANIFEST_PATH = BASE_DIR / "blog" / "posts.json"


def _load_blog_manifest() -> list[dict]:
    """Read blog/posts.json and return the list of post dicts (sorted newest first)."""
    if not _BLOG_MANIFEST_PATH.exists():
        return []
    try:
        with _BLOG_MANIFEST_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        posts = data.get("posts", []) if isinstance(data, dict) else []
        posts.sort(key=lambda p: p.get("published", ""), reverse=True)
        return posts
    except (json.JSONDecodeError, OSError):
        return []


def _xml_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_rss(posts: list[dict], base_url: str) -> str:
    """Render an RSS 2.0 feed from the manifest."""
    from datetime import datetime, timezone

    def to_rfc822(date_str: str) -> str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
        except (ValueError, TypeError):
            return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    items_xml: list[str] = []
    for p in posts:
        url = f"{base_url}/blog/{p['slug']}"
        items_xml.append(
            "    <item>\n"
            f"      <title>{_xml_escape(p['title'])}</title>\n"
            f"      <link>{_xml_escape(url)}</link>\n"
            f"      <guid isPermaLink=\"true\">{_xml_escape(url)}</guid>\n"
            f"      <description>{_xml_escape(p.get('summary', ''))}</description>\n"
            f"      <pubDate>{to_rfc822(p.get('published', ''))}</pubDate>\n"
            f"      <author>research@mizoki3.com ({_xml_escape(p.get('author', 'MIZ OKI'))})</author>\n"
            + "".join(f"      <category>{_xml_escape(t)}</category>\n" for t in p.get("tags", []))
            + "    </item>"
        )
    body = "\n".join(items_xml)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        "    <title>MIZ OKI 3.5 Journal</title>\n"
        f"    <link>{_xml_escape(base_url)}/blog</link>\n"
        f"    <atom:link href=\"{_xml_escape(base_url)}/blog/feed.xml\" rel=\"self\" type=\"application/rss+xml\" />\n"
        "    <description>Research and field notes on threshold-aware media buying, decision intelligence, and causal autonomous systems.</description>\n"
        "    <language>en-us</language>\n"
        f"    <lastBuildDate>{to_rfc822(posts[0].get('published', '')) if posts else ''}</lastBuildDate>\n"
        f"{body}\n"
        "  </channel>\n"
        "</rss>\n"
    )


# werkzeug hashes are always `<method>:<params...>$<salt>$<hash>` — a bare
# operator-typed demo password practically never takes that shape, which is
# what lets `_normalize_demo_users` tell "already hashed" apart from "still
# plaintext, needs upgrading" without a separate marker field.
_HASH_PREFIXES = ("pbkdf2:", "scrypt:")

# PBKDF2 rather than werkzeug's scrypt default: scrypt needs `hashlib.scrypt`,
# which some OpenSSL/LibreSSL builds (observed on this machine's Python) lack
# entirely, and a hashing method that only sometimes exists is not a
# reproducible dependency (`.claude/rules/03-dependency-reproducibility.md`).
# PBKDF2-HMAC-SHA256 has no such gap, and 600,000 iterations is the current
# OWASP-recommended floor for it.
_DEMO_PASSWORD_HASH_METHOD = "pbkdf2:sha256:600000"


def _normalize_demo_users(raw: dict[str, str]) -> dict[str, str]:
    """Return `raw` with every value guaranteed to be a werkzeug hash.

    `MIZOKI_DEMO_USERS_JSON` is meant to carry pre-hashed values (see
    `docs/PRODUCTION_SECRETS_SETUP.md`), but a value that is not already in
    werkzeug's hash format is hashed here, once, at load time — so no plain
    password ever sits in process memory past this point, and every stored
    credential is verified through the same `check_password_hash` path
    regardless of how the secret was populated.
    """
    return {
        email: value if value.startswith(_HASH_PREFIXES)
        else generate_password_hash(value, method=_DEMO_PASSWORD_HASH_METHOD)
        for email, value in raw.items()
    }


def _load_demo_users() -> dict[str, str]:
    raw_payload = os.environ.get("MIZOKI_DEMO_USERS_JSON", "").strip()
    if not raw_payload:
        return {}

    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("MIZOKI_DEMO_USERS_JSON must be valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("MIZOKI_DEMO_USERS_JSON must be an object of {email: password}.")

    users: dict[str, str] = {}
    for email, password in parsed.items():
        if not isinstance(email, str) or not isinstance(password, str):
            raise RuntimeError("All MIZOKI_DEMO_USERS_JSON keys and values must be strings.")
        users[email.strip().lower()] = password
    return _normalize_demo_users(users)


# A password-shaped constant hashed and compared against when the submitted
# email is not registered. Its only job is to make the unknown-email path do
# the same work as the known-email path, so response time never answers "does
# this address exist?". It is never a valid credential: `_check_demo_credentials`
# returns False on the unknown-email branch regardless of what the hash check
# said. Hashed once at import time — the whole point is that both branches
# pay the same, real hashing cost, not the cheaper cost of a raw comparison.
_ABSENT_USER_PLACEHOLDER = "x" * 32
_ABSENT_USER_PLACEHOLDER_HASH = generate_password_hash(
    _ABSENT_USER_PLACEHOLDER, method=_DEMO_PASSWORD_HASH_METHOD
)


def _check_demo_credentials(demo_users: dict[str, str], email: str, password: str) -> bool:
    """Constant-time, hash-based credential check that does not leak which emails exist.

    `demo_users` values are always werkzeug hashes (`_normalize_demo_users`
    guarantees it), so passwords are never compared or stored in the clear.
    Two separate leaks are closed here, same as before hashing replaced the
    raw comparison:

    * `check_password_hash` verifies via `hmac.compare_digest` against the
      derived hash, not the plaintext, so it takes the same time regardless
      of how much of the password was correct.
    * `email in demo_users and ...` would skip the (expensive) hash check
      entirely for an unknown address, so a wrong email would answer
      measurably faster than a wrong password for a real one — an oracle for
      enumerating valid operator addresses. Every branch now runs one real
      `check_password_hash` call, known account or not.
    """
    stored_hash = demo_users.get(email)
    expected_hash = _ABSENT_USER_PLACEHOLDER_HASH if stored_hash is None else stored_hash
    matched = check_password_hash(expected_hash, password)
    return matched and stored_hash is not None


# ----- CSRF for the sign-in form -------------------------------------------
# The session cookie is SameSite=Lax, which stops a cross-site POST from
# CARRYING an existing session — but login CSRF does not need the victim's
# cookie, it plants one: a forged cross-site POST signs the victim's browser
# into an account the attacker controls, and everything the victim then reads
# through /admin or /docs/internal is attacker-framed. A per-session token in
# the form closes it, with no new dependency.
_CSRF_SESSION_KEY = "_csrf_token"
_CSRF_FORM_FIELD = "csrf_token"


def _issue_csrf_token() -> str:
    """Return this session's CSRF token, minting one on first use."""
    token = session.get(_CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[_CSRF_SESSION_KEY] = token
    return token


def _csrf_token_valid(submitted: str | None) -> bool:
    """Constant-time check of a submitted token against the session's."""
    expected = session.get(_CSRF_SESSION_KEY)
    if not expected or not submitted:
        return False
    return secrets.compare_digest(expected, submitted)


class DemoRateLimiter:
    """Stdlib in-memory token bucket keyed by client IP (first XFF hop).

    Buckets start with ``per_min`` tokens and refill at ``per_min``/minute;
    ``burst`` extra capacity accumulates only while a client is idle. Telemetry
    and ``login`` each have their own, separate bucket. All knobs are
    env-tunable so launch tuning needs no deploy.

    THE BUDGET IS PER WORKER PROCESS, NOT PER SERVICE — measured, not assumed.
    ``_buckets`` is plain process memory and the image runs
    ``gunicorn --workers 2``, so each worker keeps its own counts and the
    effective per-IP ceiling is ``workers x per_min``. Measured against
    production 2026-08-22 on rev 00171-n6l, ``login_per_min=5``: 16 rapid POSTs
    from one IP to /admin/login returned exactly 10x302 then 6x429, the two
    workers exhausting in round-robin. An earlier 7-request probe saw no 429
    and was misread as "the limiter does not fire" — it was simply under the
    10-request effective threshold. Size the knob against ``workers x per_min``
    and re-measure if the worker count changes; a docstring that quotes a
    single-process number invites exactly that misreading.

    The ``login`` bucket is deliberately the tightest and takes NO burst
    credit: a human signing in needs two or three attempts, and every
    additional one is a guess. See ``_login_rate_limit`` for why the gate
    exists at all.

    SCOPE OF THE IP KEY — what is known, and what is NOT. ``client_key``
    reads the FIRST X-Forwarded-For hop. Measured 2026-08-22: for ordinary
    traffic through the load balancer that hop is STABLE — the probe above
    accumulated into one bucket per worker, which it could not have done had
    the key varied, and the LB logged a single remoteIp for all of it. What is
    still NOT measured is whether a caller who SETS the header can displace
    that hop and mint themselves a fresh bucket:

    * this service has two live ingress paths — the external HTTPS load
      balancer (mizoki3.com) and the direct *.run.app URL — and they do not
      necessarily present the same X-Forwarded-For shape;
    * if either path APPENDS the true client address instead of replacing the
      header, then the first hop is client-supplied and a caller who rotates a
      forged value gets a fresh bucket every time.

    So claim only this much: the gate ends unlimited full-speed guessing from
    an ordinary client, which is the state it was written to fix. Do not cite
    it as a defense against an attacker who sets the header. Measuring both
    ingress paths and keying on a trusted address is recorded as follow-up —
    deliberately not guessed at here, because a limiter believed to be
    stronger than it is, is worse than one whose limits are written down.
    """

    def __init__(
        self,
        per_min: int,
        burst: int,
        telemetry_per_min: int,
        login_per_min: int = 5,
    ) -> None:
        self.per_min = max(1, per_min)
        self.burst = max(0, burst)
        self.telemetry_per_min = max(1, telemetry_per_min)
        self.login_per_min = max(1, login_per_min)
        self._lock = threading.Lock()
        self._buckets: dict[tuple[str, str], list[float]] = {}

    @staticmethod
    def client_key() -> str:
        forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        return forwarded or (request.remote_addr or "unknown")

    def check(self, key: str, weight: float, bucket: str = "demo") -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        if bucket == "telemetry":
            start = capacity = float(self.telemetry_per_min)
            refill = self.telemetry_per_min / 60.0
        elif bucket == "login":
            # No burst credit: capacity == the per-minute allowance.
            start = capacity = float(self.login_per_min)
            refill = self.login_per_min / 60.0
        else:
            start = float(self.per_min)
            capacity = float(self.per_min + self.burst)
            refill = self.per_min / 60.0
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.get((bucket, key), (start, now))
            tokens = min(capacity, tokens + (now - last) * refill)
            if tokens >= weight:
                self._buckets[(bucket, key)] = (tokens - weight, now)
                return True, 0
            self._buckets[(bucket, key)] = (tokens, now)
            return False, max(1, math.ceil((weight - tokens) / refill))


def _demo_rate_weight(path: str) -> tuple[float, str]:
    """Weight + bucket for a /api/demo/* request (closed decision #3)."""
    if path == "/api/demo/telemetry":
        return 1.0, "telemetry"
    if path.startswith("/api/abtest/"):
        # A/B/C outcome beacons ride the telemetry bucket — same public-write
        # abuse posture as the demo telemetry endpoint.
        return 1.0, "telemetry"
    if path.endswith("/stream"):
        return 3.0, "demo"
    if path.endswith("/export"):
        return 2.0, "demo"
    return 1.0, "demo"


# --- Deterministic demo-run registry (shared by run/export/narrate) --------
# Engine cores are lru_cached on their pure (scenario, seed) inputs; the
# Signal + Counsel engines predate the cache rule, so their caching wrapper
# lives here (§6.4) — SSE still paces frames, compute happens once.

_signal_pipeline = demo_signal.SignalFactoryPipeline()
_counsel_synthesizer = demo_counsel.LegalSynthesizer()
_capital_pipeline = demo_capital.CapitalDeskPipeline()
_estate_engine = demo_estate.EstateRoomEngine()
_risk_engine = demo_risk.RiskSentinelEngine()
_nexus_engine = demo_nexus.NexusRunEngine()


@lru_cache(maxsize=64)
def _cached_signal_run_json(scenario: str, seed: int) -> str:
    return json.dumps(_signal_pipeline.run(scenario, seed=seed))


def _signal_run(scenario: str, seed: int) -> dict:
    return json.loads(_cached_signal_run_json(scenario, seed))


@lru_cache(maxsize=64)
def _cached_counsel_scenario_json(scenario_id: str) -> str:
    return json.dumps(_counsel_synthesizer.synthesize(scenario_id=scenario_id))


def _counsel_scenario_run(scenario_id: str) -> dict:
    return json.loads(_cached_counsel_scenario_json(scenario_id))


# demo key -> (scenario ids, runner(scenario, seed) -> trace dict)
DEMO_RUN_REGISTRY: dict[str, dict] = {
    "signal": {
        "scenarios": lambda: set(demo_signal.SCENARIOS),
        "run": lambda scenario, seed: _signal_run(scenario, seed),
        "default_scenario": "ecommerce_roas",
    },
    "counsel": {
        "scenarios": lambda: {s["id"] for s in demo_counsel.list_scenarios()},
        "run": lambda scenario, seed: _counsel_scenario_run(scenario),
        "default_scenario": "trust_modification_gst",
    },
    "estate": {
        "scenarios": lambda: set(demo_estate.SCENARIOS),
        "run": lambda scenario, seed: _estate_engine.run(scenario, seed=seed),
        "default_scenario": "ct_estate_settlement",
    },
    "capital": {
        "scenarios": lambda: set(demo_capital.SCENARIOS),
        "run": lambda scenario, seed: _capital_pipeline.run(scenario, seed=seed),
        "default_scenario": "growth_reallocation",
    },
    "risk": {
        "scenarios": lambda: set(demo_risk.SCENARIOS),
        "run": lambda scenario, seed: _risk_engine.run(scenario, seed=seed),
        "default_scenario": "quarterly_close",
    },
    "nexus": {
        "scenarios": lambda: set(demo_nexus.SCENARIOS),
        "run": lambda scenario, seed: _nexus_engine.run(scenario, seed=seed),
        "default_scenario": "cpm_shock",
    },
}

# Demo page filename per pretty route (share-embedding targets, §5.1).
DEMO_PAGE_FILES: dict[str, str] = {
    "signal": "demo-signal.html",
    "counsel": "demo-counsel.html",
    "estate": "demo-estate.html",
    "capital": "demo-capital.html",
    "risk": "demo-risk.html",
    "nexus": "demo-nexus.html",
}


# --- Run 1 item 1.F: flag-ON-only injected fragments ------------------------
# Rendered ONLY when the flag is on (tests pin flag-OFF byte parity). The
# script is same-origin fetch only, sends the closed event vocabulary, and
# carries no identifier; keepalive lets pagehide deliver the last beacon.
SITE_EVENTS_SCRIPT = (
    '<script data-mizoki="site-events">(function(){var P=location.pathname,'
    'V=(document.cookie.match(/(?:^|; )mv=([abc])\\./)||[])[1]||"none";'
    'function s(n){try{fetch("/event",{method:"POST",keepalive:true,credentials:"same-origin",'
    'headers:{"Content-Type":"application/json"},body:JSON.stringify({event_name:n,path:P,'
    'variant:V,ts:new Date().toISOString()})})}catch(e){}}'
    's("page_view");document.addEventListener("click",function(e){var a=e.target&&e.target.closest'
    '&&e.target.closest("a,button");if(!a)return;if(a.dataset&&a.dataset.event){s(a.dataset.event);return}'
    'var h=a.getAttribute&&a.getAttribute("href")||"";if(/^https?:\\/\\//.test(h)&&h.indexOf(location.host)<0)'
    's("outbound_click")},true);window.mizokiCalculatorComplete=function(){s("calculator_complete")}})();'
    '</script>\n'
)
assert len(SITE_EVENTS_SCRIPT.encode("utf-8")) <= 1024, "site-events client script must stay <= 1 KB"

PILOT_FORM_HTML = (
    '<section id="pilot-request"><div class="wrap">'
    '<p class="mark sec-mark">§07 · Request a pilot conversation</p>'
    '<h2>Two fields. No forms first, no follow-up sequence.</h2>'
    '<form method="post" action="/shopify/pilot-request" class="cta-row" data-mizoki="pilot-form">'
    '<label>Work email <input type="email" name="email" required maxlength="254" autocomplete="email"></label>'
    '<label>Store URL <input type="text" name="store" required maxlength="253" placeholder="yourstore.myshopify.com"></label>'
    '<button class="btn" type="submit" data-event="pilot_cta_click">Request a pilot conversation</button>'
    '</form>'
    '<p class="note">We store your email and store URL once, to reply. Nothing else — no cookies, no tracking pixel, '
    'no third-party analytics. See the <a href="/docs/marketing/privacy_statement_pilot.html">pilot privacy statement</a>.</p>'
    '</div></section>\n'
)


def create_app(runtime: BossRuntime | None = None) -> Flask:
    app = Flask(__name__, static_folder="assets", static_url_path="/assets")
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("ENVIRONMENT", "").lower() == "production",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        JSON_SORT_KEYS=False,
    )

    app.config["MIZOKI_DEMO_USERS"] = _load_demo_users()
    if app.config["MIZOKI_DEMO_USERS"]:
        app.logger.info(
            "Admin login enabled with %d user(s).", len(app.config["MIZOKI_DEMO_USERS"])
        )
    else:
        app.logger.warning(
            "Admin login DISABLED: MIZOKI_DEMO_USERS_JSON is empty or unset. "
            "If this is production, the mizoki-website-demo-users secret has no "
            "usable value — see docs/PRODUCTION_SECRETS_SETUP.md."
        )
    app.config["REQUIRE_API_AUTH"] = os.environ.get(
        "MIZOKI_REQUIRE_AUTH_FOR_APIS", ""
    ).strip().lower() in ("1", "true", "yes", "on")
    # Canonical host = apex (closed decision #1); kill-switch honored.
    app.config["CANONICAL_REDIRECT_ENABLED"] = (
        os.environ.get("MIZOKI_CANONICAL_REDIRECT", "").strip().lower() != "off"
    )
    # Public demo-API rate limits (closed decision #3) — env-tunable.
    app.config.setdefault(
        "DEMO_RATE_PER_MIN", int(os.environ.get("MIZOKI_DEMO_RATE_PER_MIN", "30"))
    )
    app.config.setdefault(
        "DEMO_RATE_BURST", int(os.environ.get("MIZOKI_DEMO_RATE_BURST", "10"))
    )
    app.config.setdefault(
        "DEMO_TELEMETRY_RATE_PER_MIN",
        int(os.environ.get("MIZOKI_DEMO_TELEMETRY_RATE_PER_MIN", "10")),
    )
    # Sign-in attempt budget per IP per minute (MIZ-SEC 2026-08-22). Tunable
    # without a deploy because the right number is an operations question: too
    # tight locks out a fat-fingered operator, too loose is not a gate.
    app.config.setdefault(
        "LOGIN_RATE_PER_MIN", int(os.environ.get("MIZOKI_LOGIN_RATE_PER_MIN", "5"))
    )
    app.extensions["boss_runtime"] = runtime or create_runtime(BASE_DIR)
    app.extensions["demo_rate_limiter"] = DemoRateLimiter(
        per_min=app.config["DEMO_RATE_PER_MIN"],
        burst=app.config["DEMO_RATE_BURST"],
        telemetry_per_min=app.config["DEMO_TELEMETRY_RATE_PER_MIN"],
        login_per_min=app.config["LOGIN_RATE_PER_MIN"],
    )

    @app.before_request
    def _canonical_host_redirect():
        # www.* 308-redirects to the same path on the apex (§6.1), unless
        # MIZOKI_CANONICAL_REDIRECT=off.
        if not app.config.get("CANONICAL_REDIRECT_ENABLED"):
            return None
        host = (request.host or "").split(":")[0]
        if not host.startswith("www."):
            return None
        query = request.query_string.decode()
        target = CANONICAL_BASE_URL + request.path + (f"?{query}" if query else "")
        return redirect(target, code=308)

    # Every path that compares a password. `/login` keeps no form of its own
    # (its GET redirects away) but its POST still checks credentials, so it is
    # the same guessing surface and is limited identically — a gate that
    # covers one of two doors is not a gate.
    _LOGIN_POST_PATHS = frozenset({"/admin/login", "/login"})

    @app.before_request
    def _login_rate_limit():
        """Throttle sign-in attempts per IP.

        WHY. This form is unauthenticated, public, and — since the 2026-08-21
        internal-docs directive — the only thing standing in front of
        /docs/internal, which carries production infrastructure identifiers
        and build instructions. Before this hook it accepted unlimited
        attempts at full speed.

        Bypassed under TESTING unless a test opts in, matching the demo
        limiter directly below: the suite POSTs to /admin/login many times
        across unrelated cases, and a limiter that silently ate the 6th of
        them would make those tests flaky for a reason nobody would look for.
        """
        if request.method != "POST" or request.path not in _LOGIN_POST_PATHS:
            return None
        if app.config.get("TESTING") and not app.config.get("LOGIN_RATE_LIMIT_ENFORCE_IN_TESTS"):
            return None
        limiter: DemoRateLimiter = app.extensions["demo_rate_limiter"]
        allowed, retry_after = limiter.check(limiter.client_key(), 1.0, "login")
        if allowed:
            return None
        app.logger.warning(
            "Sign-in rate limit hit for %s on %s", limiter.client_key(), request.path
        )
        # 429 rather than a redirect: the status is the signal an operator or
        # an uptime check can actually see. The form is re-rendered so a human
        # who simply typed too fast gets a page instead of a bare error.
        response = render_template(
            "admin_login.html", csrf_token=_issue_csrf_token(),
            rate_limited=True, retry_after=retry_after,
        )
        return response, 429, {"Retry-After": str(retry_after)}

    @app.before_request
    def _demo_api_rate_limit():
        # One decorator's worth of limiting for the whole public demo API.
        # Bypassed under TESTING except when a test opts in explicitly.
        path = request.path
        if not (path.startswith("/api/demo/") or path.startswith("/api/abtest/")):
            return None
        if app.config.get("TESTING") and not app.config.get("DEMO_RATE_LIMIT_ENFORCE_IN_TESTS"):
            return None
        weight, bucket = _demo_rate_weight(path)
        limiter: DemoRateLimiter = app.extensions["demo_rate_limiter"]
        allowed, retry_after = limiter.check(limiter.client_key(), weight, bucket)
        if allowed:
            return None
        response = jsonify({
            "error": "Rate limit exceeded — the public demo API allows "
                     f"{app.config['DEMO_RATE_PER_MIN']} weighted requests per minute per IP.",
            "retry_after_seconds": retry_after,
        })
        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)
        return response

    # Opt-in: gate /api/mcp/* and /api/boss/* behind admin session.
    # Off by default so the public site's chat demo keeps working.
    # Turn on by setting MIZOKI_REQUIRE_AUTH_FOR_APIS=true in the env.
    _AUTH_GATED_API_PREFIXES = ("/api/mcp/", "/api/boss/")
    _PUBLIC_API_PATHS = {"/api/health"}

    @app.before_request
    def _maybe_require_api_auth():
        if not app.config.get("REQUIRE_API_AUTH"):
            return None
        path = request.path
        if path in _PUBLIC_API_PATHS:
            return None
        if not path.startswith(_AUTH_GATED_API_PREFIXES):
            return None
        if "user" in session:
            return None
        return jsonify({
            "error": "Authentication required",
            "hint": "Sign in at /admin/login to obtain a session cookie.",
        }), 401

    def get_runtime() -> BossRuntime:
        return app.extensions["boss_runtime"]

    def login_required(view_func):
        @wraps(view_func)
        def decorated_function(*args, **kwargs):
            if "user" not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login_page"))
            return view_func(*args, **kwargs)

        return decorated_function

    def json_error(message: str, status_code: int):
        if request.path.startswith("/api/"):
            return jsonify({"error": message}), status_code
        return message, status_code

    def require_json_payload() -> dict:
        if not request.is_json:
            abort(400, description="Request must use application/json.")
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            abort(400, description="JSON body must be an object.")
        return payload

    def run_runtime_call(operation):
        try:
            return operation()
        except ValueError as exc:
            abort(400, description=str(exc))

    def serve_page(filename: str):
        return send_from_directory(BASE_DIR, filename)

    # ===== Site A/B/C test (SITE A/B/C TEST — DESIGN FIX r1.0) ==========
    # /signal is the ONE canonical, indexable landing; /marketing and /media
    # stay directly reachable (the owner's side-by-side comparison directive
    # stands) but their files carry canonical→/signal + noindex,follow.
    # Randomized variant serving at /signal is DARK until MIZOKI_ABTEST_MODE=on
    # (a reviewed deploy-workflow env change + owner-dispatched deploy); dark
    # mode serves variant A to everyone with no cookie and no assignment
    # events, while the outcome instrumentation (/go/pilot + /api/abtest/goal)
    # collects the baseline rates the pre-registration's power arithmetic
    # needs. Pre-registration (declared BEFORE any data collection):
    # docs/marketing/abtest-preregistration-signal-landing.md

    def _abtest_client() -> tuple[str, str, bool]:
        user_agent = request.headers.get("User-Agent", "")
        ip = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip() \
            or (request.remote_addr or "unknown")
        return ip, user_agent, abtest.is_bot(user_agent)

    def _abtest_assigned() -> str | None:
        # A stale cookie from an earlier live window is not an assignment
        # while the test is dark — mode off means no arm is live.
        parsed = abtest.parse_cookie(request.cookies.get(abtest.COOKIE_NAME))
        return parsed[0] if (parsed and abtest.mode_on()) else None

    def _abtest_ref() -> str:
        return abtest.classify_referrer(request.referrer, CANONICAL_HOST)

    def _abtest_mode() -> str:
        return "on" if abtest.mode_on() else "off"

    def _abtest_offpath_exposure(page_variant: str, page_path: str) -> None:
        ip, user_agent, bot = _abtest_client()
        abtest.log_event(
            "exposure", page=page_path, variant=page_variant,
            assigned=_abtest_assigned(), visitor=abtest.visitor_key(ip, user_agent),
            bot=bot, ref=_abtest_ref(), mode=_abtest_mode())

    @app.route("/go/pilot")
    def go_pilot():
        # Tracked CTA redirect (spec §3.3): logs the click, then 302s to the
        # variant's own mailto destination with an "[ref X]" subject token so
        # arriving inquiries identify their arm. Destinations come ONLY from
        # the closed registry — the request cannot steer the redirect.
        cta_key = request.args.get("cta", "")
        entry = abtest.CTA_REGISTRY.get(cta_key)
        if entry is None:
            abort(404)
        ip, user_agent, bot = _abtest_client()
        assigned = _abtest_assigned()
        abtest.log_event(
            "cta_click", cta=cta_key, page=abtest.VARIANT_PATHS[entry["page"]],
            variant=entry["page"], assigned=assigned,
            visitor=abtest.visitor_key(ip, user_agent), bot=bot,
            ref=_abtest_ref(), mode=_abtest_mode())
        response = redirect(abtest.cta_location(cta_key, assigned), code=302)
        response.headers["Cache-Control"] = "private, no-store"
        return response

    @app.route("/api/abtest/goal", methods=["POST"])
    def abtest_goal():
        # Tier-3 outcome beacon (scroll past the pilot section). Tiny JSON
        # body, closed goal/page vocabulary, telemetry-rate-limited.
        if request.content_length and request.content_length > 512:
            abort(400, description="Beacon payload too large.")
        payload = request.get_json(silent=True, force=True)
        if not isinstance(payload, dict):
            abort(400, description="Beacon must be a JSON object.")
        page = abtest.normalize_goal_page(payload.get("page"))
        if payload.get("goal") != abtest.GOAL_NAME or page is None:
            abort(400, description="Unknown goal or page.")
        ip, user_agent, bot = _abtest_client()
        assigned = _abtest_assigned()
        if page == "/signal":
            # At the canonical URL the rendered content is the assigned arm
            # while the test is live, and variant A while it is dark.
            variant = assigned or "a"
        else:
            variant = {"/marketing": "b", "/media": "c"}[page]
        abtest.log_event(
            "goal", goal=abtest.GOAL_NAME, page=page, variant=variant,
            assigned=assigned, visitor=abtest.visitor_key(ip, user_agent),
            bot=bot, ref=_abtest_ref(), mode=_abtest_mode())
        return "", 204

    @app.route("/api/abtest/state")
    def abtest_state():
        counts = abtest.counters_snapshot()
        return jsonify({
            "mode": _abtest_mode(),
            "canonical": abtest.CANONICAL_PATH,
            "variants": abtest.VARIANT_FILES,
            "assignments_this_instance": counts,
            "srm": abtest.srm_check(counts),
            "caveat": (
                "per-instance counters since boot — authoritative arm counts "
                "come from the assignment log in Cloud Logging "
                "(scripts/abtest_stats.py srm)"),
        })

    @app.route("/")
    def home():
        return serve_page("index.html")

    @app.route("/index.html")
    def index():
        return serve_page("index.html")

    @app.route("/counsel")
    @app.route("/counsel.html")
    def counsel():
        return serve_page("counsel.html")

    @app.route("/estate")
    @app.route("/estate.html")
    def estate():
        return serve_page("estate.html")

    @app.route("/capital")
    @app.route("/capital.html")
    def capital():
        return serve_page("capital.html")

    @app.route("/signal")
    @app.route("/signal.html")
    def signal():
        # A/B/C canonical landing: serve the assigned variant's file with the
        # serving-truth head posture (canonical=/signal, index,follow) so a
        # variant file's own baked noindex can never leak onto the canonical
        # URL. Dark mode (default) pins variant A for everyone.
        ip, user_agent, bot = _abtest_client()
        res = abtest.resolve(request.cookies.get(abtest.COOKIE_NAME), ip,
                             user_agent, abtest.mode_on(), bot)
        html = (BASE_DIR / abtest.VARIANT_FILES[res.variant]).read_text(
            encoding="utf-8")
        html = abtest.apply_head_posture(html, abtest.CANONICAL_URL,
                                         "index,follow")
        response = app.response_class(html, mimetype="text/html")
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Vary"] = "Cookie"
        if res.set_cookie:
            response.set_cookie(
                abtest.COOKIE_NAME,
                abtest.cookie_value(res.variant, res.visitor),
                max_age=abtest.COOKIE_MAX_AGE, samesite="Lax", httponly=True,
                secure=app.config["SESSION_COOKIE_SECURE"], path="/")
        if res.first_exposure and not bot:
            abtest.count_assignment(res.variant)
        abtest.log_event(
            "assignment" if res.first_exposure else "exposure",
            page="/signal", variant=res.variant, assigned=res.assigned,
            visitor=res.visitor, bot=bot, ref=_abtest_ref(),
            mode=_abtest_mode())
        return response

    # Signal capability site (2026-08-02): /signal is the hub of a multi-page
    # surface. Each capability page follows the site's dual-route convention.
    @app.route("/signal/thresholds", strict_slashes=False)
    @app.route("/signal-thresholds.html")
    def signal_thresholds():
        return serve_page("signal-thresholds.html")

    @app.route("/signal/budget", strict_slashes=False)
    @app.route("/signal-budget.html")
    def signal_budget():
        return serve_page("signal-budget.html")

    @app.route("/signal/creative", strict_slashes=False)
    @app.route("/signal-creative.html")
    def signal_creative():
        return serve_page("signal-creative.html")

    @app.route("/signal/audiences", strict_slashes=False)
    @app.route("/signal-audiences.html")
    def signal_audiences():
        return serve_page("signal-audiences.html")

    @app.route("/signal/measurement", strict_slashes=False)
    @app.route("/signal-measurement.html")
    def signal_measurement():
        return serve_page("signal-measurement.html")

    # Shopify-merchant homepage (owner-directed, 2026-08-07): a standalone
    # landing surface — no other page links to or depends on it.
    @app.route("/shopify", strict_slashes=False)
    @app.route("/shopify.html")
    def shopify():
        # Run 1 item 1.F (2026-09-02): with BOTH flags OFF (the default) the
        # file bytes are served unchanged — pinned byte-identical by
        # tests/test_site_events_and_pilot.py. Injection happens only flag-ON, so no
        # static file is edited and no site-visible change ships dark.
        if not (site_flags.site_events_enabled() or site_flags.pilot_form_enabled()):
            return serve_page("shopify.html")
        html = (BASE_DIR / "shopify.html").read_text(encoding="utf-8")
        if site_flags.pilot_form_enabled():
            html = html.replace("</main>", PILOT_FORM_HTML + "</main>", 1)
        if site_flags.site_events_enabled():
            html = html.replace("</body>", SITE_EVENTS_SCRIPT + "</body>", 1)
        response = app.response_class(html, mimetype="text/html")
        response.headers["Cache-Control"] = "private, no-store"
        return response

    # ===== Measurement without egress (Run 1 item 1.F; flags default OFF) =====
    # /event and /shopify/event store {event_name, path, variant, ts_bucket_1h,
    # referrer_class} — nothing else — to BigQuery unified.site_events_agg.
    # SITE_EVENTS OFF → 204, nothing written. ON but sink unconfigured → 503
    # not_configured (never a healthy stub). Same-origin fetch only; the client
    # script is rendered only flag-ON.

    def _site_events_sink():
        sink = app.extensions.get("site_events_sink")
        if sink is None:
            sink = site_events.BigQuerySiteEventsSink(
                table=os.environ.get("SITE_EVENTS_TABLE", site_events.DEFAULT_TABLE))
            app.extensions["site_events_sink"] = sink
        return sink

    def _site_event():
        if not site_flags.site_events_enabled():
            return "", 204
        if request.content_length and request.content_length > site_events.MAX_BODY_BYTES:
            abort(400, description="Event payload too large.")
        fields, error = site_events.validate(request.get_json(silent=True, force=True))
        if error:
            abort(400, description=error)
        sink = _site_events_sink()
        if not sink.configured():
            return jsonify({"status": "not_configured", "flag": site_flags.SITE_EVENTS_ENV}), 503
        row = site_events.build_row(fields, request.headers.get("Referer"), CANONICAL_HOST)
        outcome = sink.write(row)
        if outcome == "written":
            return "", 204
        return jsonify({"status": outcome}), 503

    @app.route("/event", methods=["POST"])
    def site_event():
        return _site_event()

    @app.route("/shopify/event", methods=["POST"])
    def shopify_site_event():
        return _site_event()

    def _design_partner_store():
        """WO-33 (#1003): the design-partner intake store, resolved ONLY when
        ``DESIGN_PARTNER_PIPELINE`` is on (default ``"false"`` — flag OFF is
        byte-identical to the pre-WO-33 site). Tests inject
        ``app.extensions["design_partner_store"]``; otherwise the vendored
        package's ``resolve_store()`` builds the Firestore store from the
        environment. ``None`` means the pipeline is off."""
        if not dpp_flags.pipeline_enabled():
            return None
        store = app.extensions.get("design_partner_store")
        if store is None:
            store = dpp_store.resolve_store()
            app.extensions["design_partner_store"] = store
        return store

    def _design_partner_configured() -> bool:
        """Flag ON with no resolvable store is NOT a healthy stub (Part 0 rule
        6): the pilot endpoint answers 503 ``not_configured`` and health says so."""
        store = _design_partner_store()
        if store is None:
            return False
        try:
            if hasattr(store, "_resolve"):
                store._resolve()
        except Exception:  # noqa: BLE001 — missing client library / credentials
            return False
        return True

    def _design_partner_hook():
        """The ``on_sourced`` callback for ``PilotRequestService``: a newly
        created pilot request becomes a SOURCED partner, idempotent on
        ``sha256(email|store)`` (``intake.source_from_pilot_request``). Flag
        OFF → ``None`` (the service stays inert, exactly as before)."""
        store = _design_partner_store()
        if store is None:
            return None

        def _on_sourced(document):
            record = dpp_intake.source_from_pilot_request(document, store)
            if record is None:
                raise ValueError("pilot request document did not produce a partner record")
            return record

        return _on_sourced

    def _pilot_service():
        svc = app.extensions.get("pilot_request_service")
        if svc is None:
            # WO-33: the sourced hook is wired here, behind DESIGN_PARTNER_PIPELINE.
            svc = pilot_requests.PilotRequestService(
                store=app.extensions.get("pilot_request_store"),
                notifier=app.extensions.get("pilot_request_notifier"),
                on_sourced=_design_partner_hook(),
            )
            app.extensions["pilot_request_service"] = svc
        return svc

    @app.route("/shopify/pilot-request", methods=["POST"])
    def shopify_pilot_request():
        if not site_flags.pilot_form_enabled():
            abort(404)
        if request.content_length and request.content_length > pilot_requests.MAX_BODY_BYTES:
            abort(400, description="Payload too large.")
        payload = request.get_json(silent=True, force=True)
        if payload is None and request.form:
            payload = {"email": request.form.get("email", ""), "store": request.form.get("store", "")}
        fields, error = pilot_requests.validate(payload)
        if error:
            abort(400, description=error)
        svc = _pilot_service()
        if not svc.configured():
            return jsonify({"status": "not_configured", "flag": site_flags.PILOT_FORM_ENV}), 503
        # WO-33: pipeline flag ON without a resolvable intake store fails closed
        # BEFORE anything is persisted — never a request that silently skips
        # the intake it was promised.
        pipeline_on = dpp_flags.pipeline_enabled()
        if pipeline_on and not _design_partner_configured():
            return jsonify({"status": "not_configured", "flag": dpp_flags.DESIGN_PARTNER_PIPELINE_ENV}), 503
        result = svc.submit(fields, source="/shopify")
        if result["store"] not in ("created", "duplicate"):
            return jsonify({"status": "failed"}), 503
        # Confidential: the response never echoes the email or store.
        if result["notify"] not in ("sent", "already_sent"):
            # Persisted, but the owner was NOT notified: say so and invite the
            # retry that re-sends it (the document remembers notify=failed).
            return jsonify({"status": "notify_failed", "request_id": result["request_id"],
                            "retry": True}), 503
        payload = {"status": "received", "request_id": result["request_id"],
                   "duplicate": result["store"] == "duplicate"}
        if pipeline_on:
            # WO-33: the intake leg's outcome is surfaced (sourced | skipped |
            # failed) — a failed hook is never a silent drop. Flag OFF keeps the
            # response byte-identical to the pre-WO-33 shape.
            payload["pipeline"] = result.get("pipeline", "skipped")
            if payload["pipeline"] == "failed":
                app.logger.warning("design-partner intake failed for request_id=%s (persisted + notified)",
                                   result["request_id"])
        return jsonify(payload), 202

    @app.route("/risk")
    @app.route("/risk.html")
    def risk():
        return serve_page("risk.html")

    @app.route("/privacy")
    @app.route("/privacy.html")
    def privacy_page():
        return serve_page("privacy.html")

    @app.route("/terms")
    @app.route("/terms.html")
    def terms_page():
        return serve_page("terms.html")

    # Canonical path is /executive-briefing/ (trailing slash): the module's
    # asset links are relative, so serving the page at the bare path would make
    # css/ and js/ resolve against the site root and 404. No bare-path route —
    # Werkzeug's default strict_slashes redirects /executive-briefing here.
    @app.route("/executive-briefing/")
    def executive_briefing():
        return send_from_directory(BASE_DIR / "executive-briefing", "index.html")

    @app.route("/executive-briefing/<path:filename>")
    def executive_briefing_assets(filename: str):
        base = (BASE_DIR / "executive-briefing").resolve()
        target = (base / filename).resolve()
        allowed = {".html", ".css", ".js", ".svg", ".png", ".md"}
        if not str(target).startswith(str(base) + "/") or not target.is_file() or target.suffix.lower() not in allowed:
            abort(404)
        return send_from_directory(base, filename)

    # ===== Documentation portal (/docs) ==============================
    # Static pages generated from the repository's docs/ tree by
    # scripts/build_site_docs.py at deploy time (owner directive
    # 2026-08-20: mizoki3.com/docs is public and carries all of docs/).
    # The generator runs AFTER the marketing content gates, so raw
    # engineering docs never enter the truth-discipline scan's scope, and
    # its secret gate withholds any file carrying a live credential.
    _SITE_DOCS = BASE_DIR / "site_docs"

    @app.route("/docs", strict_slashes=False)
    def docs_index():
        if not (_SITE_DOCS / "index.html").is_file():
            abort(404)
        return send_from_directory(_SITE_DOCS, "index.html")

    # Documents carrying production infrastructure identifiers or build
    # instructions are rendered into a SEPARATE tree and served only to a
    # signed-in session — the same `login_required` gate the rest of the front
    # end uses (owner directive 2026-08-21). Two properties make this safe:
    #   * physical separation — the public handler resolves inside _SITE_DOCS and
    #     therefore CANNOT reach _SITE_DOCS_INTERNAL, whatever path is requested;
    #   * fail-closed — with MIZOKI_DEMO_USERS_JSON unset no session can ever be
    #     established, so the internal tree is unreachable rather than open.
    _SITE_DOCS_INTERNAL = BASE_DIR / "site_docs_internal"

    @app.route("/docs/internal", strict_slashes=False)
    @login_required
    def docs_internal_index():
        if not (_SITE_DOCS_INTERNAL / "index.html").is_file():
            abort(404)
        return send_from_directory(_SITE_DOCS_INTERNAL, "index.html")

    @app.route("/docs/internal/<path:filename>")
    @login_required
    def docs_internal_asset(filename: str):
        base = _SITE_DOCS_INTERNAL.resolve()
        target = (base / filename).resolve()
        if not str(target).startswith(str(base) + "/"):
            abort(404)
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            abort(404)
        return send_from_directory(base, str(target.relative_to(base)))

    @app.route("/docs/<path:filename>")
    def docs_asset(filename: str):
        base = _SITE_DOCS.resolve()
        target = (base / filename).resolve()
        if not str(target).startswith(str(base) + "/"):
            abort(404)
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            abort(404)
        return send_from_directory(base, str(target.relative_to(base)))

    # ===== AEO/GEO authority pages (/learn) + /llms.txt — LEARN_PAGES ======
    # Lane 5 S4 (2026-09-02). Content: the repository's docs/marketing/aeo/*.md,
    # loaded, expiry-checked and rendered by mizoki_runtime.learn_pages (a
    # dependency-free markdown subset — the build-time `markdown` library is
    # not in the runtime image). Flag OFF → 404 on every path here, so the
    # served route table answers exactly as it did before this block existed.
    # Flag ON with no pages directory → 503 not_configured, never a healthy
    # stub. A page past its `expires` date is WITHHELD (404), never served
    # stale, and the index lists only current pages. /llms.txt is an explicit
    # rule so the top-level static catch-all never serves the file while OFF.
    def _learn_pages_or_none() -> list | None:
        directory = learn_pages.pages_dir()
        if directory is None:
            return None
        return learn_pages.load_pages(directory)

    def _learn_not_configured():
        return jsonify({"status": "not_configured", "flag": site_flags.LEARN_PAGES_ENV}), 503

    @app.route("/learn", strict_slashes=False)
    def learn_index():
        if not site_flags.learn_pages_enabled():
            abort(404)
        pages = _learn_pages_or_none()
        if pages is None:
            return _learn_not_configured()
        current = [p for p in pages if not learn_pages.is_overdue(p)]
        return app.response_class(learn_pages.render_index(current, CANONICAL_BASE_URL), mimetype="text/html")

    @app.route("/learn/<slug>")
    def learn_page(slug: str):
        if not site_flags.learn_pages_enabled():
            abort(404)
        if not learn_pages.SLUG.match(slug):
            abort(404)
        pages = _learn_pages_or_none()
        if pages is None:
            return _learn_not_configured()
        page = next((p for p in pages if p.slug == slug), None)
        if page is None or learn_pages.is_overdue(page):
            abort(404)
        return app.response_class(learn_pages.render_page(page, CANONICAL_BASE_URL), mimetype="text/html")

    @app.route("/llms.txt")
    def llms_txt():
        if not site_flags.learn_pages_enabled():
            abort(404)
        static = BASE_DIR / "llms.txt"
        if not static.is_file():
            abort(404)
        pages = _learn_pages_or_none() or []
        current = [p for p in pages if not learn_pages.is_overdue(p)]
        body = learn_pages.render_llms_txt(static.read_text(encoding="utf-8"), current, CANONICAL_BASE_URL)
        return app.response_class(body, mimetype="text/plain")

    @app.route("/pricing")
    @app.route("/pricing.html")
    def pricing():
        return serve_page("pricing.html")

    # Media-buyer landing: plain-English platform story + the client-side
    # Decision Control Simulator (deterministic, no backend engine needed).
    @app.route("/mizuki3")
    @app.route("/mizuki3.html")
    def mizuki3():
        return serve_page("mizuki3.html")

    # ===== Marketing parallel site (/marketing/*) ====================
    # The proposed media-buyer experience runs as a complete parallel site so
    # the classic canon site (root) and the new direction can be compared
    # live, side by side, before anything is retired. Purely additive — no
    # root surface is replaced.

    @app.route("/marketing", strict_slashes=False)
    def marketing_home():
        # Variant B's own URL: byte passthrough of the file (its canonical →
        # /signal + noindex,follow posture is baked in), logged as an
        # off-protocol exposure for the A/B/C analysis.
        _abtest_offpath_exposure("b", "/marketing")
        response = send_from_directory(BASE_DIR / "marketing", "index.html")
        response.headers["Cache-Control"] = "private, no-store"
        return response

    @app.route("/marketing/simulator", strict_slashes=False)
    def marketing_simulator():
        return send_from_directory(BASE_DIR / "marketing", "simulator.html")

    @app.route("/marketing/walkthrough", strict_slashes=False)
    def marketing_walkthrough():
        return send_from_directory(BASE_DIR / "marketing", "walkthrough.html")

    @app.route("/marketing/engine", strict_slashes=False)
    def marketing_engine():
        return send_from_directory(BASE_DIR / "marketing", "engine.html")

    @app.route("/marketing/modules", strict_slashes=False)
    def marketing_modules():
        return send_from_directory(BASE_DIR / "marketing", "modules.html")

    @app.route("/marketing/governance", strict_slashes=False)
    def marketing_governance():
        return send_from_directory(BASE_DIR / "marketing", "governance.html")

    # The experience shipped briefly at /media-buying; /marketing is its home.
    @app.route("/media-buying")
    @app.route("/media-buying.html")
    def media_buying():
        return redirect(url_for("marketing_home"), code=301)

    # ===== MIZ OKI Media (/media) — additive product page ==============
    # Isolated single-page surface served from media/ (self-contained HTML
    # plus local video/poster/storyboard assets). Purely additive: no other
    # route, template, stylesheet, or nav references it, and /media-buying
    # above is an unrelated legacy redirect. strict_slashes=False serves both
    # /media and /media/ directly, matching the /marketing convention.

    @app.route("/media", strict_slashes=False)
    def media_home():
        # Variant C's own URL — same posture-in-file + exposure-log pattern
        # as /marketing above.
        _abtest_offpath_exposure("c", "/media")
        response = send_from_directory(BASE_DIR / "media", "index.html")
        response.headers["Cache-Control"] = "private, no-store"
        return response

    # The standalone /media product site's sub-pages (owner spec Part 3).
    # Same convention as the /marketing division routes: clean extensionless
    # URLs served from real files in media/. The any() converter keeps this
    # closed-world — unknown paths still fall through to the asset route's
    # 404, and the classic site remains untouched.
    @app.route(
        "/media/<any('platform', 'decision-graph', 'how-it-works',"
        " 'use-cases', 'pilot', 'trust', 'resources', 'contact',"
        # Executive Demo r1.1 (2026-09-13, owner placement ruling): the
        # single-file presenter surface lives in the /media namespace only —
        # media/demo.html at /media/demo (slug renamed 2026-09-14, owner call;
        # the former /media/executive-demo 308s here). No engine run,
        # no /api/ call, no telemetry; robots noindex; deliberately absent
        # from sitemap_xml(). Nothing outside /media links to it (owner ruling
        # 2026-09-13, second reading: the standing rule holds — the classic
        # site and the A/B/C arms never link into /media; the demo hub keeps
        # only the division demos). Reached from the /media hero CTA.
        " 'demo'):page>",
        strict_slashes=False)
    def media_subpage(page: str):
        return send_from_directory(BASE_DIR / "media", f"{page}.html")

    # Executive Demo slug rename (2026-09-14, owner call): /media/demo is the
    # canonical URL (served by media_subpage above); the r1.1 slug and its
    # filename form are permanent redirects into it so links already shared
    # keep resolving. Still inside the /media namespace (owner ruling
    # 2026-09-13), still noindex and unlisted; one canonical URL.
    @app.route("/media/executive-demo", strict_slashes=False)
    @app.route("/media/executive-demo.html")
    def media_executive_demo_legacy_slug():
        return redirect("/media/demo", code=308)

    @app.route("/media/<path:filename>")
    def media_assets(filename: str):
        # Same traversal-guarded, extension-allowlisted pattern as the
        # executive-briefing assets route. send_from_directory serves the MP4
        # as video/mp4 with Range support, so the film streams from this route
        # and can never fall through to an HTML handler.
        base = (BASE_DIR / "media").resolve()
        target = (base / filename).resolve()
        allowed = {".html", ".css", ".js", ".svg", ".png", ".jpg", ".webp", ".mp4", ".webm", ".vtt", ".mp3", ".wav"}
        if not str(target).startswith(str(base) + "/") or not target.is_file() or target.suffix.lower() not in allowed:
            abort(404)
        return send_from_directory(base, filename)

    # Standalone Ecosystem Animation interactive player (40s product loop)
    @app.route("/animation", strict_slashes=False)
    @app.route("/animation.html")
    @app.route("/ecosystem-animation", strict_slashes=False)
    @app.route("/media/ecosystem", strict_slashes=False)
    def ecosystem_animation():
        response = send_from_directory(BASE_DIR, "ecosystem-animation-standalone.html")
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response

    @app.route("/animation/audio", strict_slashes=False)
    @app.route("/animation/ecosystem-vo-v1.mp3")
    @app.route("/media/assets/ecosystem-vo-v1.mp3")
    def ecosystem_animation_audio():
        response = send_from_directory(BASE_DIR, "ecosystem-vo-v1.mp3", mimetype="audio/mpeg")
        response.headers["Cache-Control"] = "public, max-age=86400"
        response.headers["Accept-Ranges"] = "bytes"
        return response

    @app.route("/animation/ecosystem-vo-v1.wav")
    @app.route("/media/assets/ecosystem-vo-v1.wav")
    def ecosystem_animation_wav():
        response = send_from_directory(BASE_DIR, "ecosystem-vo-v1.wav", mimetype="audio/wav")
        response.headers["Cache-Control"] = "public, max-age=86400"
        response.headers["Accept-Ranges"] = "bytes"
        return response

    # --- Full-site mirror under /marketing ---------------------------------
    # Owner requirement: browse the ENTIRE site inside the /marketing prefix,
    # so the classic site (root) and the new direction can be compared as two
    # complete sites. Canon files are read from disk and never modified; the
    # mirror rewrites whitelisted internal links to stay under the prefix and
    # injects the parallel-preview strip plus a noindex tag (previews must
    # not compete with the canonical pages in search).

    _MIRROR_STRIP = (
        '<div class="compare-strip"><span class="cs-note">// Parallel preview '
        "— nothing on the classic site is replaced</span>"
        '<a href="/">View classic site →</a></div>'
    )
    _MIRROR_HEAD = (
        '<link rel="stylesheet" href="/assets/css/marketing.css?v=20260802" />'
        '<meta name="robots" content="noindex" />'
    )

    def _marketize(html_text: str) -> str:
        text = html_text
        text = text.replace('href="/demo/', 'href="/marketing/demo/')
        text = text.replace('href="/demo"', 'href="/marketing/demo"')
        text = text.replace('href="/demo.html"', 'href="/marketing/demo"')
        text = re.sub(
            r'href="/(counsel|estate|capital|signal|risk|pricing)(?:\.html)?(["#?])',
            r'href="/marketing/\1\2', text)
        text = text.replace('href="/executive-briefing/"',
                            'href="/marketing/executive-briefing/"')
        text = text.replace('href="/#', 'href="/marketing#')
        text = text.replace('href="/"', 'href="/marketing"')
        # Injection happens AFTER rewriting so the strip's own escape hatch
        # keeps pointing at the classic site.
        text = text.replace("</head>", _MIRROR_HEAD + "\n</head>", 1)
        text = re.sub(
            r"<body([^>]*)>",
            lambda m: "<body" + m.group(1) + ">\n  " + _MIRROR_STRIP,
            text, count=1)
        return text

    # Redesigned division + pricing pages — real files in marketing/, the
    # whole site rewritten in the transparent treatment (owner: "complete web
    # site redesigned in a more transparent way"). The classic pages at root
    # stay untouched for the comparison.
    @app.route(
        "/marketing/<any(counsel, estate, capital, signal, risk, pricing):page>",
        strict_slashes=False)
    def marketing_division(page: str):
        return send_from_directory(BASE_DIR / "marketing", f"{page}.html")

    # The live-demo hub stays a mirror of the canon page — the desks ARE the
    # product, identical in both sites.
    @app.route("/marketing/demo", strict_slashes=False)
    def marketing_demo_hub():
        text = (BASE_DIR / "demo.html").read_text(encoding="utf-8")
        return app.response_class(_marketize(text), mimetype="text/html")

    @app.route(
        "/marketing/demo/<any(signal, counsel, estate, capital, risk, nexus):desk>",
        strict_slashes=False)
    def marketing_mirror_demo(desk: str):
        text = serve_demo_page(desk).get_data(as_text=True)
        return app.response_class(_marketize(text), mimetype="text/html")

    # The Executive Briefing is a chrome-less full-screen module with relative
    # asset links, so a plain passthrough keeps it working under the prefix.
    @app.route("/marketing/executive-briefing/")
    def marketing_briefing():
        return send_from_directory(BASE_DIR / "executive-briefing", "index.html")

    @app.route("/marketing/executive-briefing/<path:filename>")
    def marketing_briefing_assets(filename: str):
        return executive_briefing_assets(filename)

    # ===== Live product demos (public) ==============================

    @app.route("/intent", strict_slashes=False)
    def intent_experience():
        """Serve the isolated Anticipatory Intelligence application shell."""
        response = send_from_directory(INTENT_DIST_DIR, "index.html")
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.route("/intent/<path:filename>")
    def intent_experience_assets(filename: str):
        """Serve only files produced by the dedicated /intent build."""
        response = send_from_directory(INTENT_DIST_DIR, filename)
        if filename.startswith("assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    def serve_demo_page(demo_key: str):
        """Serve a demo page, embedding sanitized ?scenario=&seed= params as
        data attributes on <body> so the page's JS can autorun a shared,
        deterministic replay (§5.1)."""
        filename = DEMO_PAGE_FILES[demo_key]
        text = (BASE_DIR / filename).read_text(encoding="utf-8")
        attrs = []
        scenario = request.args.get("scenario", "")
        if scenario and scenario in DEMO_RUN_REGISTRY[demo_key]["scenarios"]():
            attrs.append(f'data-scenario="{scenario}"')
        seed_raw = request.args.get("seed")
        if seed_raw is not None:
            try:
                attrs.append(f'data-seed="{int(seed_raw)}"')
            except (TypeError, ValueError):
                pass
        if attrs:
            text = text.replace("<body", "<body " + " ".join(attrs), 1)
        return app.response_class(text, mimetype="text/html")

    # D6 fix: the pretty demo routes tolerate trailing slashes.
    @app.route("/demo", strict_slashes=False)
    @app.route("/demo.html")
    def demo_hub():
        return serve_page("demo.html")

    @app.route("/demo/signal", strict_slashes=False)
    @app.route("/demo-signal.html")
    def demo_signal_page():
        return serve_demo_page("signal")

    @app.route("/demo/counsel", strict_slashes=False)
    @app.route("/demo-counsel.html")
    def demo_counsel_page():
        return serve_demo_page("counsel")

    @app.route("/demo/estate", strict_slashes=False)
    @app.route("/demo-estate.html")
    def demo_estate_page():
        return serve_demo_page("estate")

    @app.route("/demo/capital", strict_slashes=False)
    @app.route("/demo-capital.html")
    def demo_capital_page():
        return serve_demo_page("capital")

    @app.route("/demo/risk", strict_slashes=False)
    @app.route("/demo-risk.html")
    def demo_risk_page():
        return serve_demo_page("risk")

    @app.route("/demo/nexus", strict_slashes=False)
    @app.route("/demo-nexus.html")
    def demo_nexus_page():
        return serve_demo_page("nexus")

    # Executive Demo: served ONLY under /media (media_subpage above,
    # /media/demo; the r1.1 slug /media/executive-demo 308s there) — owner
    # placement ruling 2026-09-13. The /demo
    # namespace does not reference it: the hub keeps the division demos only.

    # D2 fix: the walkthrough is a real page again (was 301-swallowed).
    @app.route("/walkthrough")
    @app.route("/walkthrough.html")
    def walkthrough_page():
        return serve_page("walkthrough.html")

    # §5.6: real lead path — the contact template becomes a real route.
    @app.route("/contact")
    @app.route("/contact.html")
    def contact_page():
        source = request.args.get("source", "")
        # Sanitize: the echoed value is attribute-safe by construction.
        source = "".join(ch for ch in source if ch.isalnum() or ch in "-_")[:64]
        return render_template("contact.html", source=source)

    # The contact page links these two; the templates existed but were never
    # routed — the 2026-08-03 full-site audit found them 404ing in production.
    @app.route("/intelligence")
    def intelligence_page():
        return render_template("intelligence.html")

    @app.route("/vision")
    def vision_page():
        return render_template("vision.html")

    @app.route("/favicon.ico")
    def favicon_ico():
        # Pages link the SVG explicitly, but browsers, crawlers and older clients
        # still request bare /favicon.ico — serve the real multi-size ICO so this
        # is not a site-wide 404. Regenerate via scripts/generate_favicon.py.
        return send_from_directory(
            BASE_DIR / "assets" / "img",
            "favicon.ico",
            mimetype="image/x-icon",
        )

    @app.route("/apple-touch-icon.png")
    @app.route("/apple-touch-icon-precomposed.png")
    def apple_touch_icon():
        # iOS requests these at the root regardless of <link rel="apple-touch-icon">.
        return send_from_directory(
            BASE_DIR / "assets" / "img", "apple-touch-icon.png", mimetype="image/png"
        )

    @app.route("/robots.txt")
    def robots_txt():
        body = (
            "User-agent: *\n"
            "Allow: /\n"
            f"\nSitemap: {CANONICAL_BASE_URL}/sitemap.xml\n"
        )
        return app.response_class(body, mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap_xml():
        # The demos are the marketing asset — index them (closed decision #2).
        pages = [
            "/", "/counsel", "/estate", "/capital", "/signal", "/intent", "/risk",
            "/signal/thresholds", "/signal/budget", "/signal/creative",
            "/signal/audiences", "/signal/measurement", "/shopify",
            "/pricing", "/mizuki3", "/executive-briefing/",
            # The /marketing LANDING is deliberately absent: it is variant B
            # of the /signal A/B/C test — noindex,follow with canonical →
            # /signal (a noindexed URL in the sitemap would be a
            # contradictory signal). The /marketing sub-pages are not test
            # variants and stay listed. /media (variant C) was never listed.
            "/marketing/engine", "/marketing/modules",
            "/marketing/simulator", "/marketing/walkthrough",
            "/marketing/governance", "/marketing/counsel", "/marketing/estate",
            "/marketing/capital", "/marketing/signal", "/marketing/risk",
            "/marketing/pricing",
            "/demo", "/demo/signal", "/demo/counsel", "/demo/estate",
            "/demo/capital", "/demo/risk", "/demo/nexus",
            # /media/demo is deliberately absent: the page ships
            # robots=noindex (presenter surface, reached by link). Listing it
            # would be the same contradictory signal as /marketing above. To
            # index it later, drop the robots meta AND add it here in one PR.
            "/walkthrough.html", "/blog",
        ]
        posts = _load_blog_manifest()
        blog_lastmod = max(
            (p.get("updated", p.get("published", "")) for p in posts), default=""
        )
        # Pages the Signal v2 rollout changed (2026-08-03): the hub, the five
        # capability pages, the demo surfaces that gained the doorman framing,
        # and the briefing whose signal pack was extended.
        rollout_lastmod = {
            # /signal became the A/B/C canonical landing (index,follow +
            # rel=canonical) in the 2026-08-22 test-design fix.
            "/signal": "2026-08-22",
            "/signal/thresholds": "2026-08-03",
            "/signal/budget": "2026-08-03",
            "/signal/creative": "2026-08-03",
            "/signal/audiences": "2026-08-03",
            "/signal/measurement": "2026-08-03",
            "/demo": "2026-08-03",
            "/demo/signal": "2026-08-03",
            "/executive-briefing/": "2026-08-03",
            # Shopify-merchant homepage (owner-directed standalone surface).
            "/shopify": "2026-08-07",
        }
        # Publish every manifest-backed article at the same canonical URL
        # used by the Journal and feeds, including revisions of older posts.
        for post in posts:
            path = f"/blog/{post['slug']}"
            pages.append(path)
            rollout_lastmod[path] = post.get("updated", post.get("published", ""))
        # /learn (S4-1 owner ruling 2026-09-15): the index plus every CURRENT
        # authority page, derived from the loader exactly as /llms.txt is —
        # never hand-listed. Listed ONLY while LEARN_PAGES is on and the pages
        # directory resolves: with the flag off every /learn path answers 404,
        # and a sitemap URL that 404s is the same contradictory signal the
        # /marketing and /media/demo comments above refuse. A page past its
        # `expires` is withheld by the loader and therefore absent here too.
        # lastmod = the page's last_reviewed (the claim-review date).
        if site_flags.learn_pages_enabled():
            learn_dir = learn_pages.pages_dir()
            if learn_dir is not None:
                current_learn = [p for p in learn_pages.load_pages(learn_dir) if not learn_pages.is_overdue(p)]
                if current_learn:
                    pages.append("/learn/")
                    rollout_lastmod["/learn/"] = max(p.last_reviewed for p in current_learn).isoformat()
                    for page in current_learn:
                        pages.append(f"/learn/{page.slug}")
                        rollout_lastmod[f"/learn/{page.slug}"] = page.last_reviewed.isoformat()
        entries = []
        for path in pages:
            stamp = blog_lastmod if path == "/blog" else rollout_lastmod.get(path, "")
            lastmod = f"\n    <lastmod>{_xml_escape(stamp)}</lastmod>" if stamp else ""
            entries.append(
                "  <url>\n"
                f"    <loc>{_xml_escape(CANONICAL_BASE_URL + path)}</loc>{lastmod}\n"
                "  </url>"
            )
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(entries)
            + "\n</urlset>\n"
        )
        return app.response_class(body, mimetype="application/xml")

    @app.route("/how-it-works.html")
    @app.route("/platform.html")
    @app.route("/security.html")
    @app.route("/industries.html")
    @app.route("/case-studies.html")
    @app.route("/resources.html")
    @app.route("/roi.html")
    @app.route("/investor.html")
    @app.route("/sales-one-pager.html")
    @app.route("/demo-opener.html")
    def legacy_marketing_page():
        return redirect(url_for("home"), code=301)

    @app.route("/blogs")
    @app.route("/blogs/")
    @app.route("/blogs.html")
    def blogs_page():
        return redirect(url_for("blog_index"), code=301)

    @app.route("/blog")
    def blog_index():
        return send_from_directory(BASE_DIR / "blog", "index.html")

    @app.route("/blog/")
    @app.route("/blog/index.html")
    def blog_index_legacy():
        return redirect(url_for("blog_index"), code=301)

    @app.route("/blog/decision-control-plane")
    def blog_dcp_article():
        return send_from_directory(BASE_DIR / "blog", "decision-control-plane.html")

    @app.route("/blog/decision-control-plane/")
    @app.route("/blog/decision-control-plane.html")
    def legacy_blog_dcp_article():
        return redirect(url_for("blog_dcp_article"), code=301)

    @app.route("/blog/adc-decision-framework")
    def blog_adc_article():
        return send_from_directory(BASE_DIR / "blog", "adc-decision-framework.html")

    @app.route("/blog/adc-decision-framework/")
    @app.route("/blog/adc-decision-framework.html")
    def legacy_blog_adc_article():
        return redirect(url_for("blog_adc_article"), code=301)

    @app.route("/blog/doorman-problem")
    def blog_doorman_article():
        return send_from_directory(BASE_DIR / "blog", "doorman-problem.html")

    @app.route("/blog/doorman-problem/")
    @app.route("/blog/doorman-problem.html")
    def legacy_blog_doorman_article():
        return redirect(url_for("blog_doorman_article"), code=301)

    @app.route("/blog/relu-lens-meta-algorithm")
    def blog_relu_lens_article():
        return send_from_directory(BASE_DIR / "blog", "relu-lens-meta-algorithm.html")

    @app.route("/blog/relu-lens-meta-algorithm/")
    @app.route("/blog/relu-lens-meta-algorithm.html")
    @app.route("/blog/meta-relu-gate-go-deep-before-wide")
    @app.route("/blog/meta-relu-gate-go-deep-before-wide/")
    @app.route("/blog/meta-relu-gate-go-deep-before-wide.html")
    @app.route("/blog/meta-relu-gate-go-deep-before-wide/index.html")
    def legacy_blog_relu_lens_article():
        return redirect(url_for("blog_relu_lens_article"), code=301)

    @app.route("/blog/feed.xml")
    @app.route("/blog/rss.xml")
    @app.route("/rss.xml")
    def blog_rss_feed():
        from flask import Response
        manifest = _load_blog_manifest()
        # Feeds are consumed off-site: always emit canonical https URLs, never
        # the proxy-derived request scheme (Cloud Run terminates TLS upstream,
        # so request.url_root reports http://).
        rss = _render_rss(manifest, base_url=CANONICAL_BASE_URL)
        return Response(rss, mimetype="application/rss+xml; charset=utf-8")

    @app.route("/blog/feed.json")
    def blog_json_feed():
        manifest = _load_blog_manifest()
        base = CANONICAL_BASE_URL
        items = []
        for post in manifest:
            items.append({
                "id": f"{base}/blog/{post['slug']}",
                "url": f"{base}/blog/{post['slug']}",
                "title": post["title"],
                "summary": post.get("summary", ""),
                "content_text": post.get("summary", ""),
                "date_published": f"{post['published']}T09:00:00Z",
                "date_modified": f"{post.get('updated', post['published'])}T09:00:00Z",
                "authors": [{"name": post.get("author", "MIZ OKI")}],
                "tags": post.get("tags", []),
                "image": f"{base}{post['image']}" if post.get("image") else None,
            })
        return jsonify({
            "version": "https://jsonfeed.org/version/1.1",
            "title": "MIZ OKI 3.5 Journal",
            "home_page_url": f"{base}/blog",
            "feed_url": f"{base}/blog/feed.json",
            "description": "Research and field notes on threshold-aware media buying, decision intelligence, and causal autonomous systems.",
            "language": "en",
            "items": items,
        })

    @app.route("/blog/posts.json")
    def blog_posts_manifest():
        # Raw manifest passthrough (handy for client-side blog listings)
        return send_from_directory(BASE_DIR / "blog", "posts.json", mimetype="application/json")

    @app.route("/blog/<path:filename>")
    def blog_post(filename: str):
        slug = filename.rstrip("/").removesuffix(".html")
        if any(post["slug"] == slug for post in _load_blog_manifest()):
            if filename != slug:
                return redirect(f"/blog/{slug}", code=301)
            return send_from_directory(BASE_DIR / "blog", f"{slug}.html")
        return send_from_directory(BASE_DIR / "blog", filename)

    @app.route("/11/")
    @app.route("/11/index.html")
    def v11_home():
        return send_from_directory(BASE_DIR / "11", "index.html")

    @app.route("/11/<path:filename>")
    def v11_page(filename: str):
        return send_from_directory(BASE_DIR / "11", filename)

    @app.route("/console")
    @app.route("/console/")
    @app.route("/console/index.html")
    def console_home():
        return send_from_directory(BASE_DIR / "mizoki3-site" / "console", "index.html")

    @app.route("/console/<path:filename>")
    def console_asset(filename: str):
        return send_from_directory(BASE_DIR / "mizoki3-site" / "console", filename)

    @app.route("/infrastructure/main.tf")
    def infrastructure_terraform():
        return send_from_directory(
            BASE_DIR / "mizoki3-site" / "infrastructure",
            "main.tf",
            mimetype="text/plain",
        )

    @app.route("/login", methods=["GET"])
    @app.route("/login.html", methods=["GET"])
    def login_page():
        if "user" in session:
            return redirect(EXTERNAL_DASHBOARD_URL)
        return redirect(EXTERNAL_LOGIN_URL, code=302)

    @app.route("/login", methods=["POST"])
    def login():
        # No template posts here — `login_page` (GET) redirects away — so this
        # handler carries no CSRF token to check and is left as-is on that
        # axis. It IS rate-limited and IS constant-time, because it compares
        # the same passwords as /admin/login. Retiring it outright is the real
        # fix and is recorded as follow-up, not done here: removing a live
        # route is a behaviour change beyond a security patch.
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        demo_users = app.config["MIZOKI_DEMO_USERS"]

        if not demo_users:
            flash("Local demo login is disabled. Redirecting to the command center login.", "info")
            return redirect(EXTERNAL_LOGIN_URL)

        if _check_demo_credentials(demo_users, email, password):
            session.permanent = True
            # Drop any pre-auth CSRF token so the authenticated session does
            # not keep a value an attacker may have fixed before sign-in.
            session.pop(_CSRF_SESSION_KEY, None)
            session["user"] = email
            return redirect(EXTERNAL_DASHBOARD_URL)

        flash("Invalid email or password.", "error")
        return redirect(url_for("login_page"))

    @app.route("/logout")
    def logout():
        session.pop("user", None)
        flash("You have been logged out.", "info")
        return redirect(url_for("home"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return redirect(EXTERNAL_DASHBOARD_URL)

    # ===== Admin (local backend) ====================================
    @app.route("/admin")
    @app.route("/admin/")
    def admin_home():
        if "user" not in session:
            return redirect(url_for("admin_login_page"))
        runtime = get_runtime()
        try:
            health = runtime.health_snapshot()
        except Exception:
            health = {"status": "unknown", "version": "?", "skills_count": 0}
        try:
            tools = runtime.list_tools()
        except Exception:
            tools = []
        # Decision traces — runtime exposes either recent_traces() or trace storage
        traces = []
        for attr in ("recent_traces", "list_traces", "get_recent_traces"):
            if hasattr(runtime, attr):
                try:
                    traces = list(getattr(runtime, attr)(limit=50)) or []
                    break
                except TypeError:
                    try:
                        traces = list(getattr(runtime, attr)()) or []
                        break
                    except Exception:
                        pass
                except Exception:
                    pass
        return render_template(
            "admin_dashboard.html",
            user_email=session.get("user"),
            health=health,
            tools=tools,
            traces=traces[:50],
        )

    @app.route("/admin/login", methods=["GET"])
    def admin_login_page():
        if "user" in session:
            return redirect(url_for("admin_home"))
        return render_template("admin_login.html", csrf_token=_issue_csrf_token())

    @app.route("/admin/login", methods=["POST"])
    def admin_login_post():
        # CSRF first: reject a forged cross-site sign-in before the credential
        # is even looked at. Bypassed under TESTING unless a test opts in —
        # same convention as the rate limiter, and pinned in both directions
        # by AdminLoginCsrfTestCase.
        enforce_csrf = not app.config.get("TESTING") or app.config.get(
            "LOGIN_CSRF_ENFORCE_IN_TESTS"
        )
        if enforce_csrf and not _csrf_token_valid(request.form.get(_CSRF_FORM_FIELD)):
            app.logger.warning("Rejected sign-in with missing/invalid CSRF token.")
            flash("Your sign-in form expired. Please try again.", "error")
            return redirect(url_for("admin_login_page"))

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        demo_users = app.config.get("MIZOKI_DEMO_USERS", {})

        if not demo_users:
            flash(
                "Local admin login is disabled. Set MIZOKI_DEMO_USERS_JSON to enable it.",
                "warning",
            )
            return redirect(url_for("admin_login_page"))

        if _check_demo_credentials(demo_users, email, password):
            session.permanent = True
            # Rotate away the pre-auth CSRF token (session fixation): the
            # token a caller may have planted before sign-in must not survive
            # into the authenticated session.
            session.pop(_CSRF_SESSION_KEY, None)
            session["user"] = email
            return redirect(url_for("admin_home"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("admin_login_page"))

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("user", None)
        flash("You have been signed out.", "info")
        return redirect(url_for("admin_login_page"))

    # ===== Admin: API connections (customer key management) =========
    # ALWAYS session-gated, regardless of MIZOKI_REQUIRE_AUTH_FOR_APIS —
    # this surface handles credentials.
    def _require_admin_session():
        if "user" not in session:
            return (
                jsonify(
                    {
                        "error": "authentication required",
                        "hint": "Sign in at /admin/login to obtain a session cookie.",
                    }
                ),
                401,
            )
        return None

    @app.route("/admin/connections")
    def admin_connections_page():
        if "user" not in session:
            return redirect(url_for("admin_login_page"))
        return render_template(
            "admin_connections.html", user_email=session.get("user")
        )

    @app.route("/api/admin/connections", methods=["GET"])
    def api_connections_status():
        denied = _require_admin_session()
        if denied:
            return denied
        return jsonify({"connections": connections.connections_status()})

    @app.route("/api/admin/connections/<provider_id>", methods=["POST", "DELETE"])
    def api_connections_update(provider_id: str):
        denied = _require_admin_session()
        if denied:
            return denied
        try:
            if request.method == "DELETE":
                entry = connections.clear_key(provider_id)
            else:
                payload = request.get_json(silent=True) or {}
                entry = connections.set_key(provider_id, payload.get("api_key", ""))
        except connections.UnknownProviderError:
            return jsonify({"error": f"unknown provider: {provider_id}"}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"connection": entry})

    @app.route("/api/admin/connections/<provider_id>/verify", methods=["POST"])
    def api_connections_verify(provider_id: str):
        denied = _require_admin_session()
        if denied:
            return denied
        try:
            result = connections.verify_connection(provider_id)
        except connections.UnknownProviderError:
            return jsonify({"error": f"unknown provider: {provider_id}"}), 404
        return jsonify({"verification": result})

    @app.route("/templates/<path:filename>")
    def serve_template(filename: str):
        if filename not in ALLOWED_TEMPLATES:
            abort(404)
        return render_template(filename)

    def _unconfigured_enabled_flags() -> list[str]:
        """Flags that are ON without their sink — the fail-closed state both
        health surfaces report (#899 review, Codex P1: /health said "healthy"
        while /api/health said not_configured). Flags OFF contribute nothing."""
        flags = site_flags.snapshot()
        missing: list[str] = []
        if flags["site_events"] and not _site_events_sink().configured():
            missing.append(site_flags.SITE_EVENTS_ENV)
        if flags["pilot_form"] and not _pilot_service().configured():
            missing.append(site_flags.PILOT_FORM_ENV)
        if dpp_flags.pipeline_enabled() and not _design_partner_configured():
            missing.append(dpp_flags.DESIGN_PARTNER_PIPELINE_ENV)
        return missing

    @app.route("/api/health")
    def api_health():
        snapshot = get_runtime().health_snapshot()
        # Non-sensitive operational signal: lets deploy verification (and ops)
        # detect an empty/missing MIZOKI_DEMO_USERS_JSON secret without probing
        # the login form.
        snapshot["admin_login_enabled"] = bool(app.config.get("MIZOKI_DEMO_USERS"))
        # Run 1 item 1.F: flag state as booleans, and "not_configured" when a
        # flag is ON without its sink — never a healthy stub (Part 0 rule 6).
        flags = site_flags.snapshot()
        snapshot["site_events"] = (
            "off" if not flags["site_events"]
            else ("configured" if _site_events_sink().configured() else "not_configured"))
        snapshot["pilot_form"] = (
            "off" if not flags["pilot_form"]
            else ("configured" if _pilot_service().configured() else "not_configured"))
        # WO-33: the design-partner intake leg, same tri-state (never a secret value).
        snapshot["design_partner_pipeline"] = (
            "off" if not dpp_flags.pipeline_enabled()
            else ("configured" if _design_partner_configured() else "not_configured"))
        return jsonify(snapshot)

    @app.route("/health")
    def health():
        # The operational probe (deploy verification, uptime) carries the same
        # fail-closed state as /api/health: a flag ON without its sink is not
        # a healthy revision. With both flags OFF (the default) this answers
        # exactly as before.
        missing = _unconfigured_enabled_flags()
        if missing:
            return "not_configured: " + ",".join(missing), 503
        return "healthy", 200

    @app.route("/api/mcp/tools", methods=["GET"])
    def list_mcp_tools():
        return jsonify({"tools": get_runtime().list_tools()})

    @app.route("/api/mcp/call", methods=["POST"])
    def call_mcp_tool():
        payload = require_json_payload()
        tool_name = payload.get("name")
        arguments = payload.get("arguments", {})
        if not isinstance(tool_name, str) or not tool_name.strip():
            abort(400, description="Field 'name' must be a non-empty string.")
        if not isinstance(arguments, dict):
            abort(400, description="Field 'arguments' must be an object.")
        return jsonify(run_runtime_call(lambda: get_runtime().call_tool(tool_name, arguments)))

    # ===== Canonical reasoning substrate (JourneyEvent v1 → Envelope v2 →
    # ===== identity clusters) + Virtuoso model plane ==================
    @app.route("/schemas/journey-event.json", methods=["GET"])
    def journey_event_schema():
        schema_path = BASE_DIR / "schemas" / "journey-event.json"
        if not schema_path.is_file():
            abort(404)
        return send_from_directory(
            schema_path.parent,
            schema_path.name,
            mimetype="application/schema+json",
        )

    @app.route("/schemas/canonical-event-envelope.json", methods=["GET"])
    def canonical_envelope_schema():
        schema_path = BASE_DIR / "schemas" / "canonical-event-envelope.json"
        if not schema_path.is_file():
            abort(404)
        return send_from_directory(
            schema_path.parent,
            schema_path.name,
            mimetype="application/schema+json",
        )

    @app.route("/api/boss/journey/normalize", methods=["POST"])
    def boss_journey_normalize():
        payload = require_json_payload()
        source = payload.get("source", "")
        record = payload.get("payload")
        if not isinstance(source, str) or not source.strip():
            abort(400, description="Field 'source' must be a non-empty string.")
        if not isinstance(record, dict):
            abort(400, description="Field 'payload' must be an object.")
        return jsonify(run_runtime_call(lambda: get_runtime().normalize_journey_event(source, record)))

    @app.route("/api/boss/journey/ingest", methods=["POST"])
    def boss_journey_ingest():
        payload = require_json_payload()
        source = payload.get("source", "")
        events = payload.get("events")
        replay = payload.get("replay", False)
        if not isinstance(source, str) or not source.strip():
            abort(400, description="Field 'source' must be a non-empty string.")
        if not isinstance(events, list):
            abort(400, description="Field 'events' must be an array of source records.")
        if not isinstance(replay, bool):
            abort(400, description="Field 'replay' must be a boolean.")
        return jsonify(
            run_runtime_call(lambda: get_runtime().ingest_journey_events(source, events, replay=replay))
        )

    @app.route("/api/boss/journey/events", methods=["GET"])
    def boss_journey_events():
        limit = request.args.get("limit", default=10, type=int)
        limit = max(1, min(limit, 100))
        return jsonify({"events": get_runtime().recent_journey_events(limit=limit)})

    @app.route("/api/boss/journey/envelope", methods=["POST"])
    def boss_journey_envelope():
        payload = require_json_payload()
        source = payload.get("source", "")
        record = payload.get("payload")
        if not isinstance(source, str) or not source.strip():
            abort(400, description="Field 'source' must be a non-empty string.")
        if not isinstance(record, dict):
            abort(400, description="Field 'payload' must be an object.")
        context = {
            key: payload[key]
            for key in ("business_context", "reasoning_context", "causal", "intelligence")
            if isinstance(payload.get(key), dict)
        }
        return jsonify(run_runtime_call(lambda: get_runtime().build_journey_envelope(source, record, **context)))

    @app.route("/api/boss/identity/resolve", methods=["POST"])
    def boss_identity_resolve():
        payload = require_json_payload()
        actor = payload.get("actor")
        if not isinstance(actor, dict):
            abort(400, description="Field 'actor' must be an object.")
        return jsonify(run_runtime_call(lambda: get_runtime().resolve_identity(actor)))

    @app.route("/api/boss/identity/stats", methods=["GET"])
    def boss_identity_stats():
        return jsonify(run_runtime_call(lambda: get_runtime().identity_cluster_stats()))

    @app.route("/api/boss/virtuoso/registry", methods=["GET"])
    def boss_virtuoso_registry():
        return jsonify(run_runtime_call(lambda: get_runtime().virtuoso_registry()))

    @app.route("/api/boss/virtuoso/resolve", methods=["POST"])
    def boss_virtuoso_resolve():
        payload = require_json_payload()
        role = payload.get("role")
        if not isinstance(role, str) or not role.strip():
            abort(400, description="Field 'role' must be a non-empty string.")
        return jsonify(run_runtime_call(lambda: get_runtime().resolve_virtuoso_model(role)))

    @app.route("/api/boss/virtuoso/scan", methods=["POST"])
    def boss_virtuoso_scan():
        payload = require_json_payload()
        text = payload.get("text")
        source = payload.get("source", "inline")
        if not isinstance(text, str):
            abort(400, description="Field 'text' must be a string.")
        if not isinstance(source, str):
            abort(400, description="Field 'source' must be a string.")
        return jsonify(run_runtime_call(lambda: get_runtime().scan_legacy_model_strings(text, source=source)))

    @app.route("/api/boss/virtuoso/traces", methods=["GET"])
    def boss_virtuoso_traces():
        limit = request.args.get("limit", default=10, type=int)
        limit = max(1, min(limit, 100))
        return jsonify({"traces": run_runtime_call(lambda: get_runtime().recent_reasoning_traces(limit=limit))})

    # ===== Demo APIs (public — intentionally NOT auth-gated) =========
    demo_pipeline = _signal_pipeline
    demo_synthesizer = _counsel_synthesizer

    def _validated_demo_scenario(demo_key: str, scenario) -> str:
        known_ids = DEMO_RUN_REGISTRY[demo_key]["scenarios"]()
        if not isinstance(scenario, str) or scenario not in known_ids:
            known = ", ".join(sorted(known_ids))
            abort(400, description=f"Field 'scenario' must be one of: {known}.")
        return scenario

    def _validated_signal_scenario(scenario) -> str:
        return _validated_demo_scenario("signal", scenario)

    def _validated_seed(seed) -> int:
        if seed is None:
            return demo_signal.DEFAULT_SEED
        if isinstance(seed, bool) or not isinstance(seed, int):
            abort(400, description="Field 'seed' must be an integer.")
        return seed

    def _run_payload_args(demo_key: str) -> tuple[str, int]:
        payload = require_json_payload()
        scenario = payload.get("scenario")
        if scenario is None:
            scenario = payload.get("scenario_id")
        scenario = _validated_demo_scenario(demo_key, scenario)
        seed = _validated_seed(payload.get("seed"))
        return scenario, seed

    def _stream_query_args(demo_key: str, default_scenario: str) -> tuple[str, int]:
        scenario = _validated_demo_scenario(
            demo_key, request.args.get("scenario", default_scenario)
        )
        try:
            seed = int(request.args.get("seed", demo_signal.DEFAULT_SEED))
        except (TypeError, ValueError):
            abort(400, description="Query parameter 'seed' must be an integer.")
        return scenario, seed

    def _sse_response(frame_iterator):
        from flask import Response

        # Pacing happens here in the Flask layer (never in the engine) so
        # tests can consume frames instantly under TESTING.
        paced = not app.config.get("TESTING")

        def generate():
            for frame in frame_iterator:
                yield f"event: {frame['type']}\ndata: {json.dumps(frame['data'])}\n\n"
                if paced and frame["delay_hint_ms"]:
                    time.sleep(min(frame["delay_hint_ms"], 1500) / 1000.0)

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @app.route("/api/demo/signal/scenarios", methods=["GET"])
    def demo_signal_scenarios():
        return jsonify({"scenarios": demo_signal.list_scenarios()})

    @app.route("/api/demo/signal/run", methods=["POST"])
    def demo_signal_run():
        payload = require_json_payload()
        scenario = _validated_signal_scenario(payload.get("scenario"))
        seed = _validated_seed(payload.get("seed"))
        return jsonify(run_runtime_call(lambda: _signal_run(scenario, seed)))

    @app.route("/api/demo/signal/stream", methods=["GET"])
    def demo_signal_stream():
        scenario, seed = _stream_query_args("signal", "ecommerce_roas")
        return _sse_response(demo_pipeline.run_streaming(scenario, seed=seed))

    @app.route("/api/demo/counsel/scenarios", methods=["GET"])
    def demo_counsel_scenarios():
        return jsonify({"scenarios": demo_counsel.list_scenarios()})

    @app.route("/api/demo/counsel/query", methods=["POST"])
    def demo_counsel_query():
        payload = require_json_payload()
        scenario_id = payload.get("scenario_id")
        query = payload.get("query")
        if scenario_id is not None and not isinstance(scenario_id, str):
            abort(400, description="Field 'scenario_id' must be a string.")
        if query is not None and not isinstance(query, str):
            abort(400, description="Field 'query' must be a string.")
        if not (scenario_id and scenario_id.strip()) and not (query and query.strip()):
            abort(400, description="Provide 'scenario_id' or 'query'.")
        if query and len(query) > demo_counsel.MAX_QUERY_LENGTH:
            abort(400, description=f"Field 'query' must be at most {demo_counsel.MAX_QUERY_LENGTH} characters.")
        return jsonify(
            run_runtime_call(
                lambda: demo_synthesizer.synthesize(
                    scenario_id=(scenario_id or "").strip() or None,
                    free_text=query if (query and query.strip()) else None,
                )
            )
        )

    # ---- Estate Room ------------------------------------------------

    @app.route("/api/demo/estate/scenarios", methods=["GET"])
    def demo_estate_scenarios():
        return jsonify({"scenarios": demo_estate.list_scenarios()})

    @app.route("/api/demo/estate/run", methods=["POST"])
    def demo_estate_run():
        scenario, seed = _run_payload_args("estate")
        return jsonify(run_runtime_call(lambda: _estate_engine.run(scenario, seed=seed)))

    # ---- Capital Desk (Signal pattern, with SSE) --------------------

    @app.route("/api/demo/capital/scenarios", methods=["GET"])
    def demo_capital_scenarios():
        return jsonify({"scenarios": demo_capital.list_scenarios()})

    @app.route("/api/demo/capital/run", methods=["POST"])
    def demo_capital_run():
        scenario, seed = _run_payload_args("capital")
        return jsonify(run_runtime_call(lambda: _capital_pipeline.run(scenario, seed=seed)))

    @app.route("/api/demo/capital/stream", methods=["GET"])
    def demo_capital_stream():
        scenario, seed = _stream_query_args("capital", "growth_reallocation")
        return _sse_response(_capital_pipeline.run_streaming(scenario, seed=seed))

    # ---- Risk Sentinel ----------------------------------------------

    @app.route("/api/demo/risk/scenarios", methods=["GET"])
    def demo_risk_scenarios():
        return jsonify({"scenarios": demo_risk.list_scenarios()})

    @app.route("/api/demo/risk/run", methods=["POST"])
    def demo_risk_run():
        scenario, seed = _run_payload_args("risk")
        return jsonify(run_runtime_call(lambda: _risk_engine.run(scenario, seed=seed)))

    # ---- The Nexus Run (flagship) -----------------------------------

    @app.route("/api/demo/nexus/scenarios", methods=["GET"])
    def demo_nexus_scenarios():
        return jsonify({"scenarios": demo_nexus.list_scenarios()})

    @app.route("/api/demo/nexus/run", methods=["POST"])
    def demo_nexus_run():
        scenario, seed = _run_payload_args("nexus")
        return jsonify(run_runtime_call(lambda: _nexus_engine.run(scenario, seed=seed)))

    @app.route("/api/demo/nexus/stream", methods=["GET"])
    def demo_nexus_stream():
        scenario, seed = _stream_query_args("nexus", "cpm_shock")
        return _sse_response(_nexus_engine.run_streaming(scenario, seed=seed))

    # ---- Trace Narrator (§5.3) — the Boss-chat answer ---------------

    @app.route("/api/demo/<demo_key>/narrate", methods=["GET"])
    def demo_narrate(demo_key: str):
        if demo_key not in DEMO_RUN_REGISTRY:
            abort(404)
        scenario = _validated_demo_scenario(
            demo_key,
            request.args.get("scenario", DEMO_RUN_REGISTRY[demo_key]["default_scenario"]),
        )
        try:
            seed = int(request.args.get("seed", demo_signal.DEFAULT_SEED))
        except (TypeError, ValueError):
            abort(400, description="Query parameter 'seed' must be an integer.")
        return jsonify(run_runtime_call(lambda: demo_narrator.narrate(demo_key, scenario, seed=seed)))

    # ---- Signed audit export (§5.5) ---------------------------------

    @app.route("/api/demo/<demo_key>/export", methods=["GET"])
    def demo_export(demo_key: str):
        if demo_key not in DEMO_RUN_REGISTRY:
            abort(404)
        scenario = _validated_demo_scenario(
            demo_key,
            request.args.get("scenario", DEMO_RUN_REGISTRY[demo_key]["default_scenario"]),
        )
        try:
            seed = int(request.args.get("seed", demo_signal.DEFAULT_SEED))
        except (TypeError, ValueError):
            abort(400, description="Query parameter 'seed' must be an integer.")
        trace = run_runtime_call(lambda: DEMO_RUN_REGISTRY[demo_key]["run"](scenario, seed))
        digest = hashlib.sha256(
            json.dumps(trace, sort_keys=True).encode("utf-8")
        ).hexdigest()
        from datetime import datetime, timezone

        return jsonify({
            "trace": trace,
            "integrity": {
                "algo": "sha256",
                "digest": digest,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        })

    # ---- Cookieless telemetry (§6.6) --------------------------------

    @app.route("/api/demo/telemetry", methods=["POST"])
    def demo_telemetry_ingest():
        payload = require_json_payload()
        extra_keys = set(payload) - {"event", "demo", "scenario"}
        if extra_keys:
            abort(400, description=f"Unexpected fields: {', '.join(sorted(extra_keys))}.")
        for field_name in ("event", "demo", "scenario"):
            if not isinstance(payload.get(field_name), str):
                abort(400, description=f"Field '{field_name}' must be a string.")
        telemetry_path = get_runtime().data_dir / "demo_telemetry.jsonl"
        row = run_runtime_call(
            lambda: demo_telemetry.record_event(
                telemetry_path, payload["event"], payload["demo"], payload["scenario"]
            )
        )
        return jsonify({"status": "recorded", "event": row["event"]})

    # ---- Executive Briefing guide agent (Decision Concierge) --------------
    # Public like /api/demo/*: the guide runs on the anonymous briefing page.
    # Q&A is allowlist-retrieval only (mizoki_runtime.briefing_guide) and every
    # interaction lands in the guide memory ledger for aggregation.

    @app.route("/api/briefing/guide/event", methods=["POST"])
    def briefing_guide_event():
        payload = require_json_payload()
        extra = set(payload) - {"session", "event", "stage", "domain", "role", "payload"}
        if extra:
            abort(400, description=f"Unexpected fields: {', '.join(sorted(extra))}.")
        for field_name in ("session", "event"):
            if not isinstance(payload.get(field_name), str) or not payload[field_name]:
                abort(400, description=f"Field '{field_name}' must be a non-empty string.")
        if payload["event"] not in briefing_guide.ALLOWED_EVENTS:
            abort(400, description="Unknown guide event.")
        detail = payload.get("payload")
        if detail is not None and not isinstance(detail, dict):
            abort(400, description="Field 'payload' must be an object.")
        ledger = get_runtime().data_dir / "guide_interactions.jsonl"
        row = run_runtime_call(
            lambda: briefing_guide.record_event(
                ledger,
                payload["session"],
                payload["event"],
                stage=str(payload.get("stage", "")),
                domain=str(payload.get("domain", "")),
                role=str(payload.get("role", "")),
                payload=detail,
            )
        )
        return jsonify({"status": "recorded", "event": row["event"]})

    @app.route("/api/briefing/guide/ask", methods=["POST"])
    def briefing_guide_ask():
        payload = require_json_payload()
        extra = set(payload) - {"session", "question", "stage", "domain", "role"}
        if extra:
            abort(400, description=f"Unexpected fields: {', '.join(sorted(extra))}.")
        question = payload.get("question")
        if not isinstance(question, str) or not question.strip():
            abort(400, description="Field 'question' must be a non-empty string.")
        if len(question) > 500:
            abort(400, description="Field 'question' is too long (500 chars max).")
        session = payload.get("session")
        if not isinstance(session, str) or not session:
            abort(400, description="Field 'session' must be a non-empty string.")
        domain = str(payload.get("domain", ""))
        role = str(payload.get("role", ""))
        stage = str(payload.get("stage", ""))
        answer = run_runtime_call(lambda: briefing_guide.answer_question(question, domain=domain, role=role))
        ledger = get_runtime().data_dir / "guide_interactions.jsonl"
        briefing_guide.record_event(
            ledger, session, "question_asked", stage=stage, domain=domain, role=role,
            payload={"topic": answer["topic"], "kind": answer["kind"], "q": question[:120]},
        )
        if answer["kind"] == "objection":
            briefing_guide.record_event(
                ledger, session, "objection_raised", stage=stage, domain=domain, role=role,
                payload={"objection": answer["topic"]},
            )
        return jsonify(answer)

    @app.route("/api/briefing/guide/summary", methods=["GET"])
    def briefing_guide_summary():
        ledger = get_runtime().data_dir / "guide_interactions.jsonl"
        return jsonify(run_runtime_call(lambda: briefing_guide.summarize(ledger)))

    @app.route("/api/boss/discover", methods=["GET"])
    def discover_boss_capabilities():
        return jsonify(get_runtime().discover())

    @app.route("/api/boss/graph/subagents", methods=["GET"])
    def list_graph_subagents():
        return jsonify({"subagents": get_runtime().list_subagents()})

    @app.route("/api/boss/graph/context", methods=["POST"])
    def boss_graph_context():
        payload = require_json_payload()
        intent = payload.get("intent", "")
        top_k = payload.get("top_k", 3)
        constraints = payload.get("constraints", [])
        if not isinstance(intent, str) or not intent.strip():
            abort(400, description="Field 'intent' must be a non-empty string.")
        if not isinstance(top_k, int):
            abort(400, description="Field 'top_k' must be an integer.")
        if not isinstance(constraints, list):
            abort(400, description="Field 'constraints' must be an array.")
        return jsonify(
            {
                "context": run_runtime_call(
                    lambda: get_runtime().graph_context(intent, top_k=top_k, constraints=constraints)
                )
            }
        )

    @app.route("/api/boss/graph/simulate", methods=["POST"])
    def boss_graph_simulation():
        payload = require_json_payload()
        intent = payload.get("intent", "")
        proposed_action = payload.get("proposed_action", "")
        top_k = payload.get("top_k", 3)
        constraints = payload.get("constraints", [])
        if not isinstance(intent, str) or not intent.strip():
            abort(400, description="Field 'intent' must be a non-empty string.")
        if not isinstance(proposed_action, str):
            abort(400, description="Field 'proposed_action' must be a string.")
        if not isinstance(top_k, int):
            abort(400, description="Field 'top_k' must be an integer.")
        if not isinstance(constraints, list):
            abort(400, description="Field 'constraints' must be an array.")
        return jsonify(
            run_runtime_call(
                lambda: get_runtime().simulate_graph_action(
                    intent,
                    proposed_action=proposed_action,
                    constraints=constraints,
                    top_k=top_k,
                )
            )
        )

    @app.route("/api/boss/graph/loop", methods=["POST"])
    def boss_graph_loop():
        payload = require_json_payload()
        intent = payload.get("intent", "")
        goal = payload.get("goal", "")
        proposed_action = payload.get("proposed_action", "")
        top_k = payload.get("top_k", 3)
        constraints = payload.get("constraints", [])
        if not isinstance(intent, str) or not intent.strip():
            abort(400, description="Field 'intent' must be a non-empty string.")
        if not isinstance(goal, str):
            abort(400, description="Field 'goal' must be a string.")
        if not isinstance(proposed_action, str):
            abort(400, description="Field 'proposed_action' must be a string.")
        if not isinstance(top_k, int):
            abort(400, description="Field 'top_k' must be an integer.")
        if not isinstance(constraints, list):
            abort(400, description="Field 'constraints' must be an array.")
        return jsonify(
            run_runtime_call(
                lambda: get_runtime().run_decision_loop(
                    intent,
                    goal=goal,
                    proposed_action=proposed_action,
                    constraints=constraints,
                    top_k=top_k,
                )
            )
        )

    @app.route("/api/boss/skills/learn", methods=["POST"])
    def learn_boss_skill():
        payload = require_json_payload()
        required_fields = ("name", "description", "trigger_phrases")
        for field in required_fields:
            if field not in payload:
                abort(400, description=f"Missing required field: {field}")
        return jsonify({"skill": run_runtime_call(lambda: get_runtime().learn_skill(payload))})

    @app.route("/api/boss/skills/learn-from-loop", methods=["POST"])
    def learn_boss_skill_from_loop():
        payload = require_json_payload()
        trace_id = payload.get("trace_id", "")
        name = payload.get("name", "")
        description = payload.get("description", "")
        if not isinstance(trace_id, str):
            abort(400, description="Field 'trace_id' must be a string.")
        if not isinstance(name, str):
            abort(400, description="Field 'name' must be a string.")
        if not isinstance(description, str):
            abort(400, description="Field 'description' must be a string.")
        return jsonify(
            {
                "skill": run_runtime_call(
                    lambda: get_runtime().learn_skill_from_loop(
                        trace_id=trace_id,
                        name=name,
                        description=description,
                    )
                )
            }
        )

    @app.route("/api/boss/execute", methods=["POST"])
    def execute_with_boss():
        payload = require_json_payload()
        intent = payload.get("intent", "")
        arguments = payload.get("arguments", {})
        if not isinstance(intent, str) or not intent.strip():
            abort(400, description="Field 'intent' must be a non-empty string.")
        if not isinstance(arguments, dict):
            abort(400, description="Field 'arguments' must be an object.")
        return jsonify(run_runtime_call(lambda: get_runtime().execute(intent, arguments)))

    @app.route("/api/boss/traces", methods=["GET"])
    def boss_traces():
        limit = request.args.get("limit", default=5, type=int)
        limit = max(1, min(limit, 25))
        return jsonify({"traces": get_runtime().recent_traces(limit=limit)})

    @app.route("/api/boss/google-ads/validate", methods=["POST"])
    def boss_google_ads_validate():
        payload = require_json_payload()
        query = payload.get("query")
        api_version = payload.get("api_version")
        as_of = payload.get("as_of")
        if not isinstance(query, str) or not query.strip():
            abort(400, description="Field 'query' must be a non-empty GAQL string.")
        return jsonify(
            run_runtime_call(
                lambda: get_runtime().validate_gaql(query, api_version=api_version, as_of=as_of)
            )
        )

    @app.route("/api/boss/google-ads/validate-batch", methods=["POST"])
    def boss_google_ads_validate_batch():
        payload = require_json_payload()
        queries = payload.get("queries")
        api_version = payload.get("api_version")
        as_of = payload.get("as_of")
        if not isinstance(queries, list) or not queries:
            abort(400, description="Field 'queries' must be a non-empty array of GAQL strings.")
        return jsonify(
            run_runtime_call(
                lambda: get_runtime().validate_gaql_batch(queries, api_version=api_version, as_of=as_of)
            )
        )

    @app.route("/api/boss/google-ads/versions", methods=["GET"])
    def boss_google_ads_versions():
        api_version = request.args.get("api_version", default=None)
        as_of = request.args.get("as_of", default=None)
        return jsonify(
            run_runtime_call(
                lambda: get_runtime().google_ads_version_status(api_version=api_version, as_of=as_of)
            )
        )

    @app.route("/api/boss/google-ads/fields", methods=["GET"])
    def boss_google_ads_fields():
        resource = request.args.get("resource", default=None)
        return jsonify(
            run_runtime_call(lambda: get_runtime().google_ads_field_metadata(resource=resource))
        )

    @app.route("/api/boss/google-ads/validations", methods=["GET"])
    def boss_google_ads_validations():
        limit = request.args.get("limit", default=10, type=int)
        limit = max(1, min(limit, 100))
        return jsonify({"validations": get_runtime().recent_gaql_validations(limit=limit)})

    @app.route("/<path:filename>")
    def top_level_static(filename: str):
        path = BASE_DIR / filename
        if path.is_file() and path.suffix.lower() in TOP_LEVEL_STATIC_EXTENSIONS and path.parent == BASE_DIR:
            return send_from_directory(BASE_DIR, filename)
        abort(404)

    @app.errorhandler(400)
    def bad_request(error):
        return json_error(getattr(error, "description", "Bad request"), 400)

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return (
            """
            <!DOCTYPE html>
            <html>
            <head>
                <title>404 - Page Not Found</title>
                <link rel="stylesheet" href="/assets/css/styles.css"/>
                <style>
                    .error-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; text-align: center; }
                </style>
            </head>
            <body>
                <div class="error-page">
                    <div>
                        <h1 style="font-size: 4rem; color: var(--accent);">404</h1>
                        <p style="color: var(--muted);">Page not found</p>
                        <a href="/" class="btn primary" style="margin-top: 1rem;">Go Home</a>
                    </div>
                </div>
            </body>
            </html>
            """,
            404,
        )

    @app.errorhandler(500)
    def internal_error(_error):
        return json_error("Internal server error", 500)

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
