/**
 * MIZ OKI 3.5 — Executive Briefing application
 * Embeddable on mizoki3.com or standalone at /executive-briefing
 */
(function () {
  "use strict";

  const STORAGE_KEY = "mizoki-exec-briefing-v1";

  const state = {
    started: false,
    stageIndex: 0,
    role: "coo",
    domain: "signal",
    companyName: "",
    companySize: "upper",
    resolved: [],
    activeSignal: null,
    decisionIntent: null,
  };

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (saved && typeof saved === "object") Object.assign(state, saved);
    } catch (_) {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch (_ignored) {
        /* ignore */
      }
    }
    // Saved state from an older pack version — or hand-edited storage — must
    // never brick render: re-anchor anything that no longer resolves.
    if (!MIZOKI.DOMAINS[state.domain]) state.domain = "logistics";
    if (!MIZOKI.ROLES.some((r) => r.id === state.role)) state.role = "coo";
    if (!MIZOKI.SIZES.some((s) => s.id === state.companySize)) state.companySize = "upper";
    const stage = parseInt(state.stageIndex, 10);
    state.stageIndex = Math.min(Math.max(isNaN(stage) ? 0 : stage, 0), MIZOKI.STAGES.length - 1);
    state.resolved = Array.isArray(state.resolved)
      ? state.resolved.filter((id) => typeof id === "string")
      : [];
    if (["pilot", "board", "deep-dive"].indexOf(state.decisionIntent) === -1) state.decisionIntent = null;
    if (typeof state.activeSignal !== "string") state.activeSignal = null;
    if (typeof state.companyName !== "string") state.companyName = "";
    state.started = state.started === true;
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (_) {
      /* ignore */
    }
  }

  function domain() {
    return MIZOKI.DOMAINS[state.domain];
  }

  function role() {
    return MIZOKI.ROLES.find((r) => r.id === state.role) || MIZOKI.ROLES[0];
  }

  function criticalDone() {
    return domain()
      .signals.filter((s) => s.severity === "critical")
      .every((s) => state.resolved.includes(s.id));
  }

  function notifyParent(event, detail) {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage(
        { source: "mizoki-executive-briefing", event, detail },
        "*"
      );
    }
    // Same event stream, in-page: the Decision Concierge (js/guide.js)
    // subscribes here. Detail is enriched with the live state snapshot so the
    // guide never reaches into this closure.
    try {
      document.dispatchEvent(
        new CustomEvent("mizoki:briefing", {
          detail: {
            event,
            detail: detail || {},
            stageIndex: state.stageIndex,
            stageId: (MIZOKI.STAGES[state.stageIndex] || {}).id || "",
            domain: state.domain,
            role: state.role,
            started: state.started,
            resolved: state.resolved.length,
            decisionIntent: state.decisionIntent,
          },
        })
      );
    } catch (err) { /* telemetry only — never brick the briefing */ }
  }

  function svg(name) {
    const icons = {
      truck:
        '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>',
      users:
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
      coins:
        '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
      gauge:
        '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
      headset:
        '<path d="M3 11v4a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2Z"/><path d="M15 11v4a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2Z"/><path d="M4 15v-3a8 8 0 0 1 16 0v3"/>',
      package:
        '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
      signalIcon:
        '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.48 12H2"/>',
      scale:
        '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
      arrowRight: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
      arrowLeft: '<path d="M19 12H5"/><path d="m12 19-7-7 7-7"/>',
      check:
        '<path d="M20 6 9 17l-5-5"/>',
      rotate:
        '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
      clock:
        '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
      target:
        '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
      shield:
        '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
      rocket:
        '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
      file: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>',
      calendar:
        '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    };
    return (
      '<svg class="mb-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      (icons[name] || "") +
      "</svg>"
    );
  }

  function render() {
    const root = document.getElementById("mizoki-briefing");
    if (!root) return;

    root.innerHTML =
      headerHTML() +
      '<main class="mb-main" id="mb-main">' +
      (state.started ? stageHTML() : welcomeHTML()) +
      "</main>" +
      footerHTML();

    bind();
    notifyParent("render", { started: state.started, stage: state.stageIndex, domain: state.domain });
  }

  function headerHTML() {
    let progress = "";
    if (state.started) {
      progress =
        '<div class="mb-progress"><nav class="mb-stages" aria-label="Briefing stages">' +
        MIZOKI.STAGES.map((s, i) => {
          const active = i === state.stageIndex;
          const done = i < state.stageIndex;
          const reachable = i <= state.stageIndex;
          return (
            '<button type="button" class="mb-stage-btn' +
            (active ? " is-active" : "") +
            (done ? " is-done" : "") +
            '" data-go-stage="' +
            i +
            '"' +
            (reachable ? "" : " disabled") +
            ">" +
            '<div class="mb-stage-meta"><span>' +
            s.number +
            "</span><span>" +
            s.duration +
            "</span></div>" +
            '<span class="mb-stage-label">' +
            s.label +
            "</span>" +
            '<div class="mb-stage-bar"><span></span></div>' +
            "</button>"
          );
        }).join("") +
        '</nav><p class="mb-purpose">' +
        MIZOKI.STAGES[state.stageIndex].purpose +
        "</p></div>";
    }

    return (
      '<header class="mb-header"><div class="mb-header-inner">' +
      '<div class="mb-brand"><div class="mb-mark">M</div><div class="mb-brand-text"><strong>MIZ OKI 3.5</strong><span>Executive briefing</span></div></div>' +
      (state.started
        ? '<button type="button" class="mb-ghost" id="mb-restart">' +
          svg("rotate") +
          '<span class="mb-restart-label">Restart</span></button>'
        : "") +
      "</div>" +
      progress +
      "</header>"
    );
  }

  function footerHTML() {
    return (
      '<footer class="mb-footer"><div class="mb-footer-inner">' +
      "<p>MIZ OKI 3.5 · Autonomous Decision Intelligence · mizoki3.com</p>" +
      "<p>~9 minutes · domain-adaptive · decision gates</p>" +
      "</div></footer>"
    );
  }

  function welcomeHTML() {
    return (
      '<div class="mb-welcome mb-enter">' +
      "<div>" +
      '<p class="mb-kicker">Executive product demo</p>' +
      '<h1 class="mb-title mb-title-lg">A clear process for executives who need to know — in one sitting — if this belongs in the company.</h1>' +
      '<p class="mb-lead">MIZ OKI 3.5 is verifiable autonomous BI. This briefing is not a feature tour. It is a structured path from your domain reality to a board-ready decision — marketing, legal, logistics, HR, finance, ops, CX, or supply chain — with the decision gates in the loop.</p>' +
      '<div class="mb-actions" style="justify-content:flex-start;margin-top:2rem">' +
      '<button type="button" class="mb-btn mb-btn-primary mb-btn-lg mb-btn-block mb-btn-block-sm" id="mb-start">' +
      "Begin executive briefing " +
      svg("arrowRight") +
      "</button>" +
      '<p class="mb-text-subtle" style="font-size:0.875rem;margin:0">No account · ~9 minutes · adaptive by domain</p>' +
      "</div>" +
      '<ul class="mb-grid-3 mb-mt-8" style="list-style:none;padding:0;margin-top:2.5rem">' +
      featureCard("clock", "Time-boxed", "Five stages with stated purpose and duration. No open-ended wander.") +
      featureCard("target", "Domain-true", "Scenarios for marketing, legal, logistics, HR, finance, CX, and supply.") +
      featureCard("shield", "Decision-grade", "Exposure, live action, ROI, and a pilot path you can take to the board.") +
      "</ul></div>" +
      '<aside class="mb-panel">' +
      '<p class="mb-mono" style="letter-spacing:0.14em;text-transform:uppercase">The process</p>' +
      '<ol class="mb-process-list">' +
      MIZOKI.STAGES.map(
        (s) =>
          "<li><span class=\"mb-step-num\">" +
          s.number +
          '</span><div><div style="display:flex;justify-content:space-between;gap:0.5rem"><strong style="font-size:0.875rem">' +
          s.label +
          '</strong><span class="mb-text-subtle" style="font-size:0.6875rem">' +
          s.duration +
          '</span></div><p class="mb-text-muted mb-mt-1" style="font-size:0.75rem;margin:0.25rem 0 0">' +
          s.purpose +
          "</p></div></li>"
      ).join("") +
      "</ol>" +
      '<div style="border-top:1px solid var(--border);margin-top:1.5rem;padding-top:1rem">' +
      '<p class="mb-text-subtle" style="font-size:0.75rem;margin:0">Domains available in this demo</p>' +
      '<div class="mb-row mb-mt-2">' +
      Object.values(MIZOKI.DOMAINS)
        .map((d) => '<span class="mb-chip">' + d.short + "</span>")
        .join("") +
      "</div></div></aside></div>"
    );
  }

  function featureCard(icon, title, body) {
    return (
      '<li class="mb-card"><div class="mb-text-muted mb-mt-1">' +
      svg(icon) +
      '</div><p style="margin:0.75rem 0 0;font-size:0.875rem;font-weight:500">' +
      title +
      '</p><p class="mb-text-muted mb-mt-1" style="font-size:0.75rem;margin:0.25rem 0 0;line-height:1.5">' +
      body +
      "</p></li>"
    );
  }

  function stageHTML() {
    const id = MIZOKI.STAGES[state.stageIndex].id;
    if (id === "context") return stageContext();
    if (id === "exposure") return stageExposure();
    if (id === "live") return stageLive();
    if (id === "case") return stageCase();
    if (id === "decision") return stageDecision();
    return "";
  }

  function navHTML(nextLabel, nextDisabled) {
    const back =
      state.stageIndex > 0
        ? '<button type="button" class="mb-btn mb-ghost" id="mb-back">' +
          svg("arrowLeft") +
          " Back</button>"
        : "<div></div>";
    const isLast = state.stageIndex >= MIZOKI.STAGES.length - 1;
    const next = !isLast
      ? '<button type="button" class="mb-btn mb-btn-primary mb-btn-lg mb-btn-block mb-btn-block-sm" id="mb-next"' +
        (nextDisabled ? " disabled" : "") +
        ">" +
        (nextLabel || "Continue") +
        " " +
        svg("arrowRight") +
        "</button>"
      : "";
    return '<div class="mb-actions">' + back + next + "</div>";
  }

  function stageContext() {
    const d = domain();
    return (
      '<div class="mb-enter"><p class="mb-kicker">Stage 01 · Context</p>' +
      '<h2 class="mb-title mb-title-md">Anchor this briefing to your reality</h2>' +
      '<p class="mb-lead">Choose the operating domain you care about most. Exposure math, live scenario, and pilot recommendation all adapt — media and legal are fully different worlds; so are logistics, HR, finance, CX, and supply.</p>' +
      '<div class="mb-grid-2 mb-mt-8">' +
      "<section><h3 class=\"mb-section-title\">Operating domain</h3>" +
      '<p class="mb-hint">Select one primary lens for this session</p>' +
      '<div class="mb-grid-domains mb-mt-3">' +
      Object.values(MIZOKI.DOMAINS)
        .map(
          (dom) =>
            '<button type="button" class="mb-card mb-card-select' +
            (state.domain === dom.id ? " is-selected" : "") +
            '" data-domain="' +
            dom.id +
            '"><span style="display:flex;gap:0.75rem;align-items:flex-start">' +
            '<span class="mb-domain-icon">' +
            svg(dom.icon) +
            '</span><span><strong style="display:block;font-size:0.875rem">' +
            dom.name +
            '</strong><span class="mb-text-muted" style="display:block;font-size:0.75rem;margin-top:0.25rem;line-height:1.35">' +
            dom.headline +
            "</span></span></span></button>"
        )
        .join("") +
      "</div></section>" +
      '<section class="mb-stack">' +
      "<div><h3 class=\"mb-section-title\">Your role</h3>" +
      '<p class="mb-hint">Shapes emphasis in the business case</p>' +
      '<div class="mb-row mb-mt-3">' +
      MIZOKI.ROLES.map(
        (r) =>
          '<button type="button" class="mb-btn mb-btn-sm ' +
          (state.role === r.id ? "mb-btn-primary" : "mb-btn-secondary") +
          '" data-role="' +
          r.id +
          '">' +
          r.label +
          "</button>"
      ).join("") +
      "</div></div>" +
      "<div><h3 class=\"mb-section-title\">Company scale</h3>" +
      '<div class="mb-stack" style="gap:0.5rem;margin-top:0.75rem">' +
      MIZOKI.SIZES.map(
        (s) =>
          '<button type="button" class="mb-card mb-card-select' +
          (state.companySize === s.id ? " is-selected" : "") +
          '" data-size="' +
          s.id +
          '" style="font-size:0.875rem">' +
          s.label +
          "</button>"
      ).join("") +
      "</div></div>" +
      '<div><label for="mb-company" class="mb-section-title">Company name <span class="mb-text-subtle" style="font-weight:400">(optional)</span></label>' +
      '<input class="mb-input mb-mt-2" id="mb-company" maxlength="48" placeholder="e.g. Northline Industries" value="' +
      escapeAttr(state.companyName) +
      '" /></div>' +
      '<div class="mb-panel"><p class="mb-mono" style="letter-spacing:0.14em;text-transform:uppercase">Briefing lock</p>' +
      '<p class="mb-title" style="font-size:1.25rem;margin-top:0.5rem">' +
      d.short +
      '</p><p class="mb-text-muted mb-mt-2" style="font-size:0.875rem;margin:0.5rem 0 0;line-height:1.55">' +
      d.promise +
      "</p></div></section></div>" +
      navHTML("Quantify exposure", false) +
      "</div>"
    );
  }

  function stageExposure() {
    const d = domain();
    const r = role();
    const econ = MIZOKI.computeEconomics(state.domain, state.companySize, state.resolved.length);
    const org = state.companyName.trim() || "companies at your scale";
    const lag =
      state.domain === "hr"
        ? "11–18 days"
        : state.domain === "legal"
          ? "6–15 days"
          : state.domain === "finance"
            ? "5–12 days"
            : "18–48 hrs";

    return (
      '<div class="mb-enter"><p class="mb-kicker">Stage 02 · Exposure</p>' +
      '<h2 class="mb-title mb-title-md">What the status quo already costs ' +
      escapeHtml(state.companyName.trim() || "you") +
      "</h2>" +
      '<p class="mb-lead">Before product screens: the annual drag of late decisions in <span style="color:var(--fg)">' +
      d.name.toLowerCase() +
      "</span>. Sized for " +
      escapeHtml(org) +
      ". Emphasized for " +
      r.focus +
      ".</p>" +
      '<div class="mb-grid-3 mb-mt-8">' +
      metricCard("Estimated annual exposure", MIZOKI.formatCurrency(econ.annualExposure, true), "Leakage, risk, and avoidable cost in this domain") +
      metricCard(
        "Recoverable with disciplined process",
        MIZOKI.formatCurrency(econ.recoverable, true),
        "~" + Math.round((econ.recoverable / econ.annualExposure) * 100) + "% of exposure addressable in year one"
      ) +
      metricCard("Typical decision lag today", lag, "From first signal to committed action in peer orgs") +
      "</div>" +
      '<div class="mb-grid-2 mb-mt-4">' +
      '<section class="mb-card"><h3 class="mb-section-title">How the drag shows up</h3><ul class="mb-list-plain mb-mt-4">' +
      d.statusQuo.map((item) => '<li><span class="mb-dot"></span><span>' + item + "</span></li>").join("") +
      "</ul></section>" +
      '<section class="mb-card"><h3 class="mb-section-title">Leading indicators we track</h3><div class="mb-stack mb-mt-4" style="gap:0.75rem">' +
      d.kpiLabels
        .map(
          (kpi, i) =>
            '<div class="mb-card mb-card-muted" style="display:flex;justify-content:space-between;align-items:center"><span class="mb-text-muted" style="font-size:0.875rem">' +
            kpi +
            '</span><span class="mb-mono">KPI ' +
            (i + 1) +
            "</span></div>"
        )
        .join("") +
      '</div><p class="mb-text-subtle mb-mt-4" style="font-size:0.75rem;margin:1rem 0 0">Next you will resolve a live ' +
      d.short.toLowerCase() +
      " scenario using those same signals — governed by the decision gates, not a slide deck.</p></section></div>" +
      navHTML("Run live scenario", false) +
      "</div>"
    );
  }

  function metricCard(label, value, hint) {
    return (
      '<div class="mb-panel"><p class="mb-text-subtle" style="font-size:0.75rem;margin:0">' +
      label +
      '</p><p class="mb-metric mb-metric-lg">' +
      value +
      '</p><p class="mb-text-muted mb-mt-2" style="font-size:0.75rem;margin:0.5rem 0 0;line-height:1.5">' +
      hint +
      "</p></div>"
    );
  }

  function stageLive() {
    const d = domain();
    if (!state.activeSignal || !d.signals.find((s) => s.id === state.activeSignal)) {
      state.activeSignal = d.signals[0].id;
    }
    const active = d.signals.find((s) => s.id === state.activeSignal);
    const progress = Math.round((state.resolved.length / d.signals.length) * 100);
    const allDone = d.signals.every((s) => state.resolved.includes(s.id));
    const gate = criticalDone();

    return (
      '<div class="mb-enter">' +
      '<div style="display:flex;flex-direction:column;gap:1rem">' +
      "<div><p class=\"mb-kicker\">Stage 03 · Live scenario</p>" +
      '<h2 class="mb-title mb-title-md">' +
      d.liveTitle +
      '</h2><p class="mb-lead">' +
      d.liveBrief +
      "</p></div>" +
      '<div style="display:flex;align-items:center;gap:0.75rem;justify-content:flex-end">' +
      '<div style="text-align:right"><p class="mb-mono" style="margin:0">Resolved</p><p class="mb-metric" style="font-size:1.125rem">' +
      state.resolved.length +
      "/" +
      d.signals.length +
      '</p></div><button type="button" class="mb-ghost" id="mb-reset-live">' +
      svg("rotate") +
      " Reset</button></div></div>" +
      '<div class="mb-live-progress"><span style="width:' +
      progress +
      '%"></span></div>' +
      '<div class="mb-grid-2 mb-grid-live">' +
      '<div><p class="mb-hint" style="margin-bottom:0.5rem">Signal queue</p>' +
      d.signals
        .map((sig) => {
          const resolved = state.resolved.includes(sig.id);
          const isActive = sig.id === active.id;
          return (
            '<button type="button" class="mb-card mb-card-select' +
            (isActive ? " is-selected" : "") +
            '" data-signal="' +
            sig.id +
            '" style="margin-bottom:0.5rem"><span style="display:flex;gap:0.75rem;align-items:flex-start">' +
            (resolved
              ? '<span class="mb-text-signal">' + svg("check") + "</span>"
              : '<span class="mb-text-subtle" style="width:1rem;height:1rem;border:1.5px solid currentColor;border-radius:999px;display:inline-block;margin-top:0.15rem;flex-shrink:0"></span>') +
            '<span style="min-width:0;flex:1"><span style="display:flex;flex-wrap:wrap;gap:0.5rem;align-items:center">' +
            '<span class="mb-sev mb-sev-' +
            sig.severity +
            '">' +
            sig.severity +
            "</span>" +
            (resolved ? '<span class="mb-text-signal" style="font-size:0.625rem">Resolved</span>' : "") +
            '</span><strong style="display:block;font-size:0.875rem;margin-top:0.35rem;line-height:1.35">' +
            sig.title +
            '</strong><span class="mb-text-muted" style="display:block;font-size:0.75rem;margin-top:0.25rem">' +
            sig.impact +
            "</span></span></span></button>"
          );
        })
        .join("") +
      "</div>" +
      '<div class="mb-panel">' +
      '<div class="mb-row"><span class="mb-sev mb-sev-' +
      active.severity +
      '">' +
      active.severity +
      '</span><span class="mb-mono">' +
      active.id.toUpperCase() +
      "</span></div>" +
      '<h3 class="mb-title" style="font-size:1.5rem;margin-top:0.75rem">' +
      active.title +
      '</h3><p class="mb-text-muted mb-mt-3" style="font-size:0.875rem;margin:0.75rem 0 0;line-height:1.55">' +
      active.detail +
      "</p>" +
      '<div class="mb-grid-2 mb-mt-4" style="grid-template-columns:1fr 1fr">' +
      '<div class="mb-card mb-card-muted"><p class="mb-text-subtle" style="font-size:0.6875rem;margin:0">If ignored</p><p style="margin:0.35rem 0 0;font-size:0.875rem;font-weight:500;line-height:1.35">' +
      active.impact +
      '</p></div><div class="mb-card mb-card-muted"><p class="mb-text-subtle" style="font-size:0.6875rem;margin:0">Recommended action</p><p style="margin:0.35rem 0 0;font-size:0.875rem;font-weight:500;line-height:1.35">' +
      active.action +
      "</p></div></div>" +
      (state.resolved.includes(active.id)
        ? '<div class="mb-signal-box mb-mt-4"><p class="mb-text-signal" style="font-size:0.75rem;font-weight:500;margin:0">Outcome locked</p><p style="font-size:0.875rem;margin:0.35rem 0 0">' +
          active.outcome +
          "</p></div>"
        : '<button type="button" class="mb-btn mb-btn-signal mb-mt-4 mb-btn-block mb-btn-block-sm" id="mb-resolve">Commit action · resolve signal</button>') +
      "</div></div>" +
      (!gate
        ? '<p class="mb-text-subtle mb-mt-6" style="font-size:0.875rem">Resolve at least the critical signal to unlock a decision-grade business case.</p>'
        : allDone
          ? '<p class="mb-text-signal mb-mt-6" style="font-size:0.875rem">Scenario complete. You just ran the same loop MIZ OKI operationalizes every day — signal, VAL check, gate-governed action, outcome.</p>'
          : '<p class="mb-text-signal mb-mt-6" style="font-size:0.875rem">Critical path secured. Optional: clear remaining signals for a fuller scorecard.</p>') +
      navHTML("Build the business case", !gate) +
      "</div>"
    );
  }

  function stageCase() {
    const d = domain();
    const r = role();
    const econ = MIZOKI.computeEconomics(state.domain, state.companySize, state.resolved.length);
    const companyBit = state.companyName.trim() ? " at " + escapeHtml(state.companyName.trim()) : "";

    return (
      '<div class="mb-enter"><p class="mb-kicker">Stage 04 · Business case · Illustrative figures</p>' +
      '<h2 class="mb-title mb-title-md">Numbers a ' +
      escapeHtml(r.label.split(" / ")[0]) +
      " can take upstairs</h2>" +
      '<p class="mb-lead">Conservative year-one model for ' +
      d.name.toLowerCase() +
      companyBit +
      ". Tuned by company scale and how thoroughly you worked the live scenario (" +
      state.resolved.length +
      " signals resolved).</p>" +
      '<div class="mb-grid-3 mb-mt-8" style="grid-template-columns:repeat(auto-fit,minmax(10rem,1fr))">' +
      metricCard("Year-one recovery", MIZOKI.formatCurrency(econ.recoverable, true), "Illustrative · replace with your data") +
      metricCard("Pilot investment", MIZOKI.formatCurrency(econ.pilotCost, true), "Controlled-scope 30-day pilot") +
      metricCard("Payback", econ.paybackMonths + " mo", "Months to recover pilot cost") +
      metricCard("ROI on pilot", econ.roi + "%", "First-year net / pilot investment") +
      "</div>" +
      '<div class="mb-grid-2 mb-grid-case mb-mt-4">' +
      '<section class="mb-panel"><h3 class="mb-section-title">Peer outcomes in this domain</h3><ul class="mb-list-plain mb-mt-4">' +
      d.proof
        .map(
          (p) =>
            '<li style="border-bottom:1px solid var(--border);padding-bottom:1rem;align-items:baseline"><span class="mb-text-signal" style="font-family:var(--font-display);font-size:1.5rem;font-weight:500;min-width:4.5rem">' +
            p.metric +
            '</span><span class="mb-text-muted" style="font-size:0.875rem">' +
            p.label +
            "</span></li>"
        )
        .join("") +
      "</ul></section>" +
      '<section class="mb-card"><h3 class="mb-section-title">Board talking points</h3><ul class="mb-list-plain mb-mt-3">' +
      d.boardTalkingPoints
        .map(
          (pt) =>
            '<li class="mb-card mb-card-muted" style="display:block;font-size:0.875rem;line-height:1.5">' +
            pt +
            "</li>"
        )
        .join("") +
      "</ul></section></div>" +
      navHTML("Lock the decision path", false) +
      "</div>"
    );
  }

  function stageDecision() {
    const d = domain();
    const r = role();
    const econ = MIZOKI.computeEconomics(state.domain, state.companySize, state.resolved.length);
    const org = state.companyName.trim() || "your organization";

    const intents = [
      {
        id: "pilot",
        icon: "rocket",
        title: "Approve 30-day pilot",
        body: "One domain, one operating unit, weekly ELT scorecard. Low blast radius, measurable lift.",
      },
      {
        id: "board",
        icon: "file",
        title: "Request board packet",
        body: "One-pager: exposure model, pilot scope, security posture, and decision ask.",
      },
      {
        id: "deep-dive",
        icon: "calendar",
        title: "Book technical deep-dive",
        body: "90 minutes with your domain owners + MIZ OKI solution lead on data and integration.",
      },
    ];

    let confirm = "";
    if (state.decisionIntent) {
      const msg =
        state.decisionIntent === "pilot"
          ? "Pilot path selected for " +
            d.name +
            ". Scope is locked to a controlled unit so " +
            escapeHtml(org) +
            " can prove value without enterprise-wide risk."
          : state.decisionIntent === "board"
            ? "Board packet queued for " +
              d.name +
              ". It will include exposure, pilot economics, security posture, and a single clear ask."
            : "Deep-dive scheduled intent for " +
              d.name +
              ". Bring domain owners and data stewards — we will map systems and success metrics.";
      confirm =
        '<div class="mb-signal-box mb-mt-6 mb-enter"><p class="mb-text-signal" style="font-size:0.875rem;font-weight:500;margin:0">Decision captured</p>' +
        '<p style="font-size:1rem;margin:0.5rem 0 0;line-height:1.55">' +
        msg +
        '</p><p class="mb-text-muted mb-mt-4" style="font-size:0.875rem;margin:1rem 0 0">After this briefing, the residual doubt should not be “do we have a problem?” — it should only be “how fast do we start.”</p>' +
        '<div class="mb-row mb-mt-4">' +
        '<button type="button" class="mb-btn mb-btn-primary mb-btn-lg" id="mb-confirm-cta">Confirm next step ' +
        svg("arrowRight") +
        '</button><button type="button" class="mb-btn mb-btn-secondary mb-btn-lg" id="mb-another-domain">Run another domain</button>' +
        "</div></div>";
    }

    return (
      '<div class="mb-enter"><p class="mb-kicker">Stage 05 · Decision path</p>' +
      '<h2 class="mb-title mb-title-md">Leave with no ambiguity</h2>' +
      '<p class="mb-lead">You have seen the cost of inaction in ' +
      d.name.toLowerCase() +
      ", executed a live scenario under the decision gates, and modeled recovery for " +
      escapeHtml(org) +
      ". The only open question is how you proceed — not whether the problem is real.</p>" +
      '<div class="mb-grid-2 mb-mt-8">' +
      '<section class="mb-panel"><p class="mb-mono" style="letter-spacing:0.14em;text-transform:uppercase">Recommended pilot</p>' +
      '<h3 class="mb-title" style="font-size:1.5rem;margin-top:0.5rem">' +
      d.short +
      " · 30-day controlled pilot</h3>" +
      '<p class="mb-text-muted mb-mt-2" style="font-size:0.875rem;margin:0.5rem 0 0">Investment ' +
      MIZOKI.formatCurrency(econ.pilotCost) +
      " · target recovery " +
      MIZOKI.formatCurrency(econ.recoverable, true) +
      " annualized · payback ~" +
      econ.paybackMonths +
      " months</p>" +
      '<ul class="mb-list-plain mb-mt-4">' +
      d.pilotScope
        .map(
          (item) =>
            '<li><span class="mb-check">' +
            svg("check") +
            "</span><span>" +
            item +
            "</span></li>"
        )
        .join("") +
      "</ul></section>" +
      "<section><p class=\"mb-section-title\">Choose your next step</p>" +
      '<p class="mb-hint">For a ' +
      escapeHtml(r.label) +
      " focused on " +
      r.focus +
      '</p><div class="mb-stack mb-mt-3" style="gap:0.5rem">' +
      intents
        .map((intent) => {
          const active = state.decisionIntent === intent.id;
          return (
            '<button type="button" class="mb-card mb-card-select' +
            (active ? " is-selected" : "") +
            '" data-intent="' +
            intent.id +
            '"><span style="display:flex;gap:0.75rem;align-items:flex-start">' +
            '<span class="mb-domain-icon">' +
            svg(intent.icon) +
            '</span><span style="min-width:0"><span style="display:flex;align-items:center;gap:0.5rem"><strong style="font-size:0.875rem">' +
            intent.title +
            "</strong>" +
            (active ? '<span class="mb-text-signal">' + svg("check") + "</span>" : "") +
            '</span><span class="mb-text-muted" style="display:block;font-size:0.75rem;margin-top:0.35rem;line-height:1.45">' +
            intent.body +
            "</span></span></span></button>"
          );
        })
        .join("") +
      "</div></section></div>" +
      confirm +
      (!state.decisionIntent
        ? '<p class="mb-text-subtle mb-mt-6" style="font-size:0.875rem">Select a path above to close the briefing with a concrete commitment.</p>'
        : "") +
      navHTML("", false) +
      "</div>"
    );
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(str) {
    return escapeHtml(str).replace(/'/g, "&#39;");
  }

  function bind() {
    const start = document.getElementById("mb-start");
    if (start) {
      start.addEventListener("click", () => {
        state.started = true;
        state.stageIndex = 0;
        save();
        render();
        notifyParent("briefing_started", {});
      });
    }

    const restart = document.getElementById("mb-restart");
    if (restart) {
      restart.addEventListener("click", () => {
        Object.assign(state, {
          started: false,
          stageIndex: 0,
          role: "coo",
          domain: "signal",
          companyName: "",
          companySize: "upper",
          resolved: [],
          activeSignal: null,
          decisionIntent: null,
        });
        save();
        render();
        notifyParent("briefing_restarted", {});
      });
    }

    document.querySelectorAll("[data-go-stage]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = Number(btn.getAttribute("data-go-stage"));
        if (i <= state.stageIndex) {
          state.stageIndex = i;
          save();
          render();
        }
      });
    });

    document.querySelectorAll("[data-domain]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.domain = btn.getAttribute("data-domain");
        state.resolved = [];
        state.activeSignal = null;
        state.decisionIntent = null;
        save();
        render();
      });
    });

    document.querySelectorAll("[data-role]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.role = btn.getAttribute("data-role");
        save();
        render();
      });
    });

    document.querySelectorAll("[data-size]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.companySize = btn.getAttribute("data-size");
        save();
        render();
      });
    });

    const company = document.getElementById("mb-company");
    if (company) {
      company.addEventListener("change", () => {
        state.companyName = company.value;
        save();
      });
      company.addEventListener("blur", () => {
        state.companyName = company.value;
        save();
      });
    }

    document.querySelectorAll("[data-signal]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.activeSignal = btn.getAttribute("data-signal");
        save();
        render();
      });
    });

    const resolve = document.getElementById("mb-resolve");
    if (resolve) {
      resolve.addEventListener("click", () => {
        if (state.activeSignal && !state.resolved.includes(state.activeSignal)) {
          state.resolved = state.resolved.concat(state.activeSignal);
          save();
          render();
          notifyParent("signal_resolved", { id: state.activeSignal, domain: state.domain });
        }
      });
    }

    const resetLive = document.getElementById("mb-reset-live");
    if (resetLive) {
      resetLive.addEventListener("click", () => {
        state.resolved = [];
        save();
        render();
      });
    }

    document.querySelectorAll("[data-intent]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.decisionIntent = btn.getAttribute("data-intent");
        save();
        render();
        notifyParent("decision_intent", {
          intent: state.decisionIntent,
          domain: state.domain,
          role: state.role,
        });
      });
    });

    const another = document.getElementById("mb-another-domain");
    if (another) {
      another.addEventListener("click", () => {
        state.stageIndex = 0;
        state.resolved = [];
        state.activeSignal = null;
        state.decisionIntent = null;
        save();
        render();
      });
    }

    const confirmCta = document.getElementById("mb-confirm-cta");
    if (confirmCta) {
      confirmCta.addEventListener("click", () => {
        notifyParent("decision_confirmed", {
          intent: state.decisionIntent,
          domain: state.domain,
          role: state.role,
          companyName: state.companyName,
          companySize: state.companySize,
        });
        // Site integration: navigate parent or open contact
        if (window.MIZOKI_CONFIG && typeof window.MIZOKI_CONFIG.onDecisionConfirmed === "function") {
          window.MIZOKI_CONFIG.onDecisionConfirmed({
            intent: state.decisionIntent,
            domain: state.domain,
            role: state.role,
            companyName: state.companyName,
            companySize: state.companySize,
          });
        } else {
          window.location.href =
            (window.MIZOKI_CONFIG && window.MIZOKI_CONFIG.contactUrl) ||
            "/contact";
        }
      });
    }

    const back = document.getElementById("mb-back");
    if (back) {
      back.addEventListener("click", () => {
        if (state.stageIndex > 0) {
          state.stageIndex -= 1;
          save();
          render();
        }
      });
    }

    const next = document.getElementById("mb-next");
    if (next) {
      next.addEventListener("click", () => {
        if (MIZOKI.STAGES[state.stageIndex].id === "live" && !criticalDone()) return;
        if (state.stageIndex < MIZOKI.STAGES.length - 1) {
          state.stageIndex += 1;
          save();
          render();
          notifyParent("stage_changed", { stage: state.stageIndex });
        }
      });
    }
  }

  // Public API for site integration
  window.MIZOKI_Briefing = {
    reset: function () {
      localStorage.removeItem(STORAGE_KEY);
      Object.assign(state, {
        started: false,
        stageIndex: 0,
        role: "coo",
        domain: "signal",
        companyName: "",
        companySize: "upper",
        resolved: [],
        activeSignal: null,
        decisionIntent: null,
      });
      render();
    },
    start: function () {
      state.started = true;
      state.stageIndex = 0;
      save();
      render();
    },
    getState: function () {
      return Object.assign({}, state);
    },
  };

  load();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }
})();
