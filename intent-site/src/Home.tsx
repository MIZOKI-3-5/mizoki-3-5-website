"use client";

import { useEffect, useRef, useState } from "react";

const stages = [
  { key: "SENSE", number: "01", title: "Permitted signals", body: "Capture consented, provenance-bearing first-party interaction telemetry." },
  { key: "REASON", number: "02", title: "Calibrated hypotheses", body: "Forecast defined outcomes and form temporary, uncertainty-bearing intent hypotheses." },
  { key: "PLAN", number: "03", title: "Eligible candidates", body: "Generate message, creative, timing, or no-action candidates—never direct activation." },
  { key: "VALIDATE", number: "04", title: "Proof before authority", body: "Test consent, quality, policy, calibration, causality, risk, and rollback." },
  { key: "DECIDE", number: "05", title: "Governed selection", body: "Compare expected incremental value, uncertainty, budget, and downside risk." },
  { key: "ACT", number: "06", title: "Controlled execution", body: "Use the existing action pathway only after every gate passes and an exact-mutation capability is authorized." },
  { key: "LEARN", number: "07", title: "Auditable learning", body: "Reconcile verified outcomes, recalibrate, expire hypotheses, and preserve evidence." },
];

const stageTrace = [
  "Consent + provenance verified",
  "Configured-horizon evaluation hypothesis formed",
  "Risk-reduction evidence candidate proposed",
  "Causal evidence insufficient for execution",
  "No-action selected under uncertainty",
  "Action withheld by authority gate",
  "Shadow outcome committed to audit ledger",
];

const capabilities = [
  { index: "A1", title: "Passive attention", body: "Viewport deceleration is normalized against the active session baseline across declared page regions.", foot: "Behavioral proxy · not physiology" },
  { index: "A2", title: "Session sequence forecast", body: "Ordered, privacy-minimized events estimate a configurable near-term outcome horizon.", foot: "Sequence-aware · watermark-bound" },
  { index: "A3", title: "Creative-semantic alignment", body: "Versioned multimodal asset representations produce bounded creative-compatibility signals.", foot: "Asset-level · not psychological profiling" },
  { index: "A4", title: "Latent intent bridges", body: "Temporary graph links connect session evidence to a revocable IntentHypothesis with explicit TTL.", foot: "Provenance · uncertainty · expiry" },
];

const gates = [
  ["CONSENT", "PASS", "pass"],
  ["DATA QUALITY", "PASS", "pass"],
  ["CALIBRATION", "PASS", "pass"],
  ["POLICY", "PASS", "pass"],
  ["CAUSAL EVIDENCE", "EXPERIMENT REQUIRED", "warn"],
];

function Arrow() {
  return <span aria-hidden="true">↗</span>;
}

export default function Home() {
  const [activeStage, setActiveStage] = useState(-1);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearInterval(timer.current);
  }, []);

  const runLoop = () => {
    if (timer.current) clearInterval(timer.current);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setActiveStage(stages.length - 1);
      return;
    }
    setActiveStage(0);
    timer.current = setInterval(() => {
      setActiveStage((current) => {
        if (current >= stages.length - 1) {
          if (timer.current) clearInterval(timer.current);
          timer.current = null;
          return current;
        }
        return current + 1;
      });
    }, 720);
  };

  const displayStage = activeStage < 0 ? 0 : activeStage;

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="site-header">
        <div className="brand-lockup">
          <a className="wordmark" href="#top" aria-label="MIZOKI3 home">MIZOKI<span>3</span></a>
          <span className="preview-status">Preview · in development</span>
        </div>
        <nav aria-label="Primary navigation">
          <a href="#system">System</a><a href="/signal">Signal</a><a href="#loop">SRPVDAL</a><a href="#intent">Intent</a><a href="#control">Control</a><a href="/animation">Animation</a><a href="https://decisionstudio.mizoki3.com/intent">Decision Studio</a>
        </nav>
        <a className="nav-cta" href="#briefing">Executive briefing <Arrow /></a>
      </header>

      <main id="main-content">

      <section className="hero paper-section" id="top">
        <div className="hero-copy">
          <p className="eyebrow"><span className="signal-dot" /> Verifiable Autonomous Decision Intelligence</p>
          <h1>A nervous system<br />for your business.</h1>
          <p className="hero-lede">MIZOKI3 turns consented first-party signals into calibrated hypotheses, governed decisions, and auditable learning—before the cost of delay compounds.</p>
          <div className="hero-actions">
            <a className="button button-dark" href="#loop">Explore the loop <Arrow /></a>
            <a className="button button-ghost" href="#control">Open control plane</a>
          </div>
          <p className="hero-proof"><span>Signals may propose.</span><span>Causal evidence must qualify.</span><span>Policy gates authority.</span></p>
        </div>

        <div className="graph-shell" role="img" aria-label="Illustrative governed intelligence graph">
          <div className="terminal-topbar"><span>MIZOKI3 / ILLUSTRATIVE SHADOW MAP</span><span className="terminal-health"><i /> DEMO TRACE</span></div>
          <div className="graph-grid">
            <svg className="graph-lines" viewBox="0 0 600 430" role="img" aria-label="Evidence moves through forecast, hypothesis, validation, and decision nodes">
              <defs><linearGradient id="trace" x1="0" x2="1"><stop offset="0" stopColor="#3fdcf2" stopOpacity=".2" /><stop offset=".55" stopColor="#3fdcf2" /><stop offset="1" stopColor="#b07a18" /></linearGradient></defs>
              <path d="M92 98 C170 98, 160 196, 246 196" /><path d="M248 196 C330 196, 315 90, 420 90" /><path d="M248 196 C342 196, 328 292, 435 292" /><path d="M420 90 C500 90, 500 190, 527 190" /><path d="M435 292 C500 292, 500 210, 527 210" />
              <path className="trace-path" d="M92 98 C170 98, 160 196, 246 196 C330 196, 315 90, 420 90 C500 90, 500 190, 527 190" />
            </svg>
            <div className="graph-node node-evidence"><small>ENVELOPE</small><strong>Evidence</strong><em>consented</em></div>
            <div className="graph-node node-sequence"><small>SESSION</small><strong>Sequence</strong><em>ephemeral</em></div>
            <div className="graph-node node-forecast"><small>EXAMPLE HORIZON</small><strong>Forecast</strong><em>illustrative · 0.74 ±0.09</em></div>
            <div className="graph-node node-hypothesis"><small>EXAMPLE TTL</small><strong>Intent hypothesis</strong><em>illustrative · supported</em></div>
            <div className="graph-node node-passport"><small>VALIDATION</small><strong>Passport</strong><em>causal gate closed</em></div>
            <div className="decision-orbit"><span>DECISION</span><strong>WITHHOLD</strong><small>SHADOW / NO ACTION</small></div>
            <div className="graph-caption"><span>Every edge carries provenance.</span><span>Every hypothesis expires.</span></div>
          </div>
        </div>
      </section>

      <div className="status-rail" role="list" aria-label="Current system status">
        <span role="listitem"><i className="teal" /> Shadow mode</span><span role="listitem"><i className="amber" /> O-1 privacy lock</span><span role="listitem"><i className="red" /> No request_execution</span><span role="listitem"><i className="teal pulse" /> Demo trace</span>
      </div>

      <section className="positioning" id="system">
        <p className="section-kicker">01 / THE SYSTEM</p>
        <div className="positioning-grid">
          <h2>Know what changed.<br />Test why.<br /><em>Act within policy.</em></h2>
          <div>
            <p className="large-copy">Not an AI assistant. A governed Decision Control Plane that turns fragmented signals into decisions an enterprise can inspect, reverse, and defend.</p>
            <div className="assurance-row">
              <div><strong>01</strong><span>Causal credit</span><small>Incrementality before attribution.</small></div>
              <div><strong>02</strong><span>Calibrated confidence</span><small>Forecast quality measured, never proclaimed.</small></div>
              <div><strong>03</strong><span>Governed authority</span><small>Every decision traceable and permissioned.</small></div>
            </div>
          </div>
        </div>
      </section>

      <section className="loop-section paper-section" id="loop">
        <div className="section-heading">
          <div><p className="section-kicker">02 / SRPVDAL</p><h2>From signal to<br />governed action.</h2></div>
          <p>One closed control loop. Seven accountable stages. No shortcut from prediction to execution.</p>
        </div>
        <div className="stage-grid">
          {stages.map((stage, index) => (
            <article className={`stage-card ${activeStage === index ? "active" : ""}`} key={stage.key}>
              <div className="stage-top"><span>{stage.number}</span><i /></div><h3>{stage.key}</h3><strong>{stage.title}</strong><p>{stage.body}</p>
            </article>
          ))}
        </div>
        <div className="loop-demo">
          <div className="demo-command">
            <p className="mono-label">ILLUSTRATIVE SHADOW TRACE</p><h3>Run the governed loop.</h3>
            <div className="event-chips"><span>viewport deceleration</span><span>return visit</span><span>technical creative dwell</span></div>
            <button onClick={runLoop} type="button" disabled={activeStage >= 0 && activeStage < 6} aria-busy={activeStage >= 0 && activeStage < 6}>{activeStage >= 0 && activeStage < 6 ? "Trace running" : "Run governed loop"}<Arrow /></button>
          </div>
          <div className="demo-output" aria-live={activeStage === 6 ? "polite" : "off"} aria-busy={activeStage >= 0 && activeStage < 6}>
            <div className="trace-head"><span>TRACE / ACT-991-SHADOW</span><span>{activeStage < 0 ? "READY" : activeStage < 6 ? "PROCESSING" : "COMPLETE"}</span></div>
            <div className="trace-stage"><span>{stages[displayStage].number}</span><div><small>{stages[displayStage].key}</small><strong>{stageTrace[displayStage]}</strong></div></div>
            <div className="trace-meters"><div><span>FORECAST</span><strong>Evaluation hypothesis · example 0.74</strong></div><div><span>CANDIDATE</span><strong>Surface risk-reduction evidence</strong></div><div><span>CAUSAL</span><strong className="amber-text">Experiment required</strong></div></div>
            <div className="trace-verdict"><div><small>FINAL VERDICT</small><strong>SHADOW / NO ACTION</strong></div><span>WITHHOLD EXECUTION</span></div>
          </div>
        </div>
        <p className="advisory">Prediction is advisory. Authority remains gated.</p>
      </section>

      <section className="intent-section" id="intent">
        <div className="section-heading light-heading">
          <div><p className="section-kicker">03 / ANTICIPATORY INTENT ENGINE V2 · Preview · in development</p><h2>See interaction patterns emerge—<br /><em>before the click.</em></h2></div>
          <p>Session-level inference recognizes changing patterns without converting identity, biometrics, or raw input into a durable profile.</p>
        </div>
        <div className="intent-grid">
          {capabilities.map((capability) => (
            <article className="intent-card" key={capability.index}>
              <div className="intent-card-top"><span>{capability.index}</span><div className="mini-signal"><i /><i /><i /><i /><i /></div></div>
              <h3>{capability.title}</h3><p>{capability.body}</p><small>{capability.foot}</small>
            </article>
          ))}
        </div>
        <div className="sequence-panel">
          <div className="sequence-title"><span className="mono-label">ILLUSTRATIVE / SHADOW SESSION</span><strong>Behavior becomes a sequence—not a dossier.</strong></div>
          <div className="sequence-flow">
            <div className="sequence-item"><small>00:01.420</small><strong>CONTENT REGION</strong><span>baseline established</span></div><b aria-hidden="true">→</b>
            <div className="sequence-item hot"><small>EXAMPLE 00:03</small><strong>VDI SIGNAL</strong><span>technical diagram</span></div><b aria-hidden="true">→</b>
            <div className="sequence-item"><small>00:05.110</small><strong>TAB HIDDEN</strong><span>content-free</span></div><b aria-hidden="true">→</b>
            <div className="sequence-item hot"><small>00:08.760</small><strong>RETURN</strong><span>price region dwell</span></div><b aria-hidden="true">→</b>
            <div className="sequence-item hypothesis"><small>EXAMPLE TTL</small><strong>EVALUATION HYPOTHESIS</strong><span>illustrative · 0.74</span></div>
          </div>
          <div className="sequence-foot"><span>Cell bindings must be resolved from the live registry—never hard-coded.</span><span>Illustrative inference only.</span></div>
        </div>
      </section>

      <section className="control-section" id="control">
        <div className="control-copy">
          <p className="section-kicker">04 / DECISION CONTROL PLANE</p><h2>Every recommendation<br />carries its evidence.</h2>
          <p>The ValidationPassport binds evidence, consent, uncertainty, model versions, policy checks, approvals, and rollback into one inspectable record.</p>
          <div className="evidence-stack"><span>X- / DR-Learner</span><span>DoWhy refutation</span><span>Ghost-ad where supported</span><span>Material BSS Δ + lower-bound gate</span></div>
        </div>
        <div className="passport">
          <div className="passport-head"><div><small>VALIDATION PASSPORT</small><strong>VP-28-00491</strong></div><span>IMMUTABLE TRACE</span></div>
          <div className="gate-list">{gates.map(([label, result, state]) => <div className="gate-row" key={label}><span>{label}</span><i className="gate-line" /><strong className={state}>{result}</strong></div>)}</div>
          <div className="passport-result"><div><small>ELIGIBILITY</small><strong>WITHHOLD EXECUTION</strong></div><div className="veto-stamp">VETO<br /><span>ACT-991</span></div></div>
          <div className="passport-meta"><span>NO REQUEST_EXECUTION</span><span>REVERSIBLE</span><span>AUDIT LOGGED</span></div>
        </div>
      </section>

      <section className="gates-section paper-section">
        <p className="section-kicker">05 / AUTHORIZED ROLLOUT</p><h2>Two gates. No hidden third.</h2>
        <div className="rollout-grid">
          <article><span>GATE 01</span><div className="gate-icon">DARK</div><h3>Safe additive integration</h3><p>Backward-compatible implementation, evidence-backed tests, kill switches, immutable image, zero traffic-changing authority.</p><strong>PRODUCTION DARK</strong></article>
          <article><span>GATE 02</span><div className="gate-icon amber-icon">SHDW</div><h3>Narrowly allowlisted evaluation</h3><p>Consented scope, strict isolation, shadow comparison, guardrails, audit, and verified rollback. No customer-impacting mutation.</p><strong className="amber-text">PRODUCTION SHADOW</strong></article>
          <aside><small>OUTSIDE CURRENT AUTHORITY</small><strong>Production activation</strong><strong>Exact-mutation REQUEST_EXECUTION</strong><p>Both require separate explicit approval, a passing ValidationPassport, qualified causal evidence, successful experiment and guardrail results, an exact-mutation capability, and verified rollback.</p></aside>
        </div>
      </section>

      <section className="privacy-section">
        <div className="privacy-title"><p className="section-kicker">O-1 / PRIVACY LOCKED</p><h2>What the system refuses<br />to learn <em>matters.</em></h2><p>Keystroke dynamics are excluded from Phase 1 and production ingestion.</p></div>
        <div className="privacy-matrix">
          <div className="privacy-col allowed"><div className="privacy-head"><span>✓</span><strong>PERMITTED</strong><small>CONTENT-FREE LIFECYCLE ONLY</small></div><ul><li><code>form_started</code></li><li><code>field_focused</code></li><li><code>form_completed</code></li><li><code>form_abandoned</code></li></ul><p className="allowed-note">Field references must be coarse, allowlisted, and non-sensitive.</p></div>
          <div className="privacy-col prohibited"><div className="privacy-head"><span>×</span><strong>REJECTED</strong><small>COLLECTOR + INGESTION</small></div><ul><li>Raw keyboard, input, or composition events</li><li>Entered text, key identity, or edit history</li><li>Dwell / flight time, cadence, repeat, or pressure</li><li>Typing profiles, embeddings, fingerprints, or baselines</li></ul><div className="reject-code">DISALLOWED_KEYSTROKE_DYNAMICS</div></div>
        </div>
      </section>

      <section className="closing" id="briefing">
        <div className="closing-orbit" aria-hidden="true"><i /><i /><i /></div><p className="section-kicker">THE OPERATING ADVANTAGE</p><h2>Move earlier.<br /><em>Act only when the evidence permits.</em></h2><p>Build faster decision velocity without surrendering qualified causal evidence, operator control, or enterprise governance.</p><a className="button button-light" href="mailto:briefing@mizoki.ai">Schedule executive briefing <Arrow /></a>
      </section>

      </main>
      <footer><a className="wordmark footer-mark" href="#top">MIZOKI<span>3</span></a><p>A nervous system for your business.</p><div><a href="/signal">Signal</a><a href="/animation">Animation</a><a href="https://decisionstudio.mizoki3.com/intent">Decision Studio</a><span>Verifiable</span><span>Reversible</span><span>Governed</span></div></footer>
    </>
  );
}
