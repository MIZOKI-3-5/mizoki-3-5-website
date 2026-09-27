/**
 * MIZ OKI 3.5 — Domain scenario packs + briefing config
 * Integrates with mizoki3.com executive demo surface
 */
window.MIZOKI = window.MIZOKI || {};

MIZOKI.STAGES = [
  { id: "context", number: "01", label: "Context", duration: "1 min", purpose: "Anchor the briefing to your role and operating domain" },
  { id: "exposure", number: "02", label: "Exposure", duration: "2 min", purpose: "Quantify what the status quo is already costing you" },
  { id: "live", number: "03", label: "Live scenario", duration: "3 min", purpose: "Run one real decision end-to-end in the product" },
  { id: "case", number: "04", label: "Business case", duration: "2 min", purpose: "Translate outcomes into ROI, payback, and risk reduction" },
  { id: "decision", number: "05", label: "Decision path", duration: "1 min", purpose: "Leave with a concrete pilot and board-ready next step" },
];

MIZOKI.ROLES = [
  { id: "ceo", label: "CEO / President", focus: "enterprise value and strategic risk" },
  { id: "cfo", label: "CFO", focus: "cash, cost, and controllable leakage" },
  { id: "coo", label: "COO", focus: "throughput, reliability, and execution" },
  { id: "chro", label: "CHRO", focus: "talent risk, attrition cost, and capacity" },
  { id: "cto", label: "CTO / CIO", focus: "system of record and integration risk" },
  { id: "vp", label: "VP / GM", focus: "P&L ownership and operating tempo" },
];

MIZOKI.SIZES = [
  { id: "mid", label: "500–2,000 employees", multiplier: 0.7 },
  { id: "upper", label: "2,000–10,000 employees", multiplier: 1 },
  { id: "enterprise", label: "10,000+ employees", multiplier: 1.6 },
];

MIZOKI.BASE_RECOVERY = 0.28;
MIZOKI.PILOT_COST_BASE = 180000;

MIZOKI.DOMAINS = {
  signal: {
    id: "signal",
    name: "Marketing & Media — Signal",
    short: "Signal",
    icon: "signalIcon",
    headline: "Every media dollar governed like capital — gated, guarded, and provable.",
    promise: "MIZ OKI's most mature domain — the engine the platform was built on — told in three acts: PROVE what your spend caused, PROFIT on what an order truly nets, ANTICIPATE who is entering the market (the profit and anticipate acts are Preview · in development). Incrementality-measured budget moves pass a ReLU gate and hard guardrails before they touch a platform, with provenance and a rollback token on every action.",
    statusQuo: [
      "Platform-reported ROAS counts conversions that would have happened anyway",
      "The doorman problem: retargeting pays to open doors customers were already walking through — and the dashboard books it as return",
      "Revenue up, cash down: checkout revenue can't see component costs, packing, shipping, fees, or the returns that quietly turn winners into losers",
      "Budget shifts ride gut feel and last-click, not measured lift",
      "Creative fatigue is discovered after CPA has already spiked",
    ],
    kpiLabels: ["Incremental ROAS", "CPA vs. target", "Wasted spend recovered"],
    liveTitle: "Cross-channel budget reallocation — Q3 media",
    liveBrief: "Platform dashboards say scale everything; the uplift model says otherwise. Reallocate under guardrails — including one move the gate refuses to let through.",
    baseExposure: 6800000,
    signals: [
      {
        id: "sg1",
        severity: "critical",
        title: "Non-incremental spend — Brand search",
        detail: "Uplift model shows near-zero lift: these conversions occur with or without the spend, despite a stellar platform ROAS.",
        impact: "$1.9M annualized spend with minimal incremental return",
        action: "Shift 60% to prospecting via ReLU gate · 10%/day cap",
        outcome: "Reallocation executed inside guardrails · rollback token issued",
      },
      {
        id: "sg2",
        severity: "watch",
        title: "Creative fatigue — Hero video V3",
        detail: "CTR z-score −2.3 against the 7-day baseline; decay accelerating across top ad sets.",
        impact: "Projected +18% CPA drift within 10 days",
        action: "Rotate challenger set · hold 10% control cell",
        outcome: "Fatigue arrested · challenger promoted on evidence",
      },
      {
        id: "sg3",
        severity: "info",
        title: "Audience overlap — Lookalike stacks",
        detail: "Two ad sets bidding against each other with 41% audience overlap.",
        impact: "Self-competition quietly inflating CPM",
        action: "Merge audiences + exclusion list · no budget change",
        outcome: "CPM normalized · zero new exposure taken",
      },
    ],
    proof: [
      { metric: "24%", label: "of spend identified as non-incremental and redeployed (composite)" },
      { metric: "1.8×", label: "incremental ROAS versus the last-click view (composite)" },
      { metric: "9 of 10", label: "budget moves cleared the gate — the tenth was vetoed (composite)" },
      { metric: "9 of 14", label: "geo-test markets proved lift — doubled down where it worked, cut where it didn't, budget survived (composite)" },
      { metric: "−$2 to $16", label: "what the hero bundle truly netted per order once a third boomeranged; the boring single SKU netted $31 and almost never returned (composite scenario — net-yield pricing is Preview · in development)" },
    ],
    pilotScope: [
      "Two channels (Meta + Google) on one P&L",
      "Uplift measurement + ReLU-gated reallocation",
      "Weekly incrementality scorecard for CMO and CFO",
    ],
    boardTalkingPoints: [
      "Media spend becomes a governed capital allocation, not a faith-based line item",
      "Every move carries provenance and a rollback token",
      "Act III, anticipatory intent, stays Preview · in development — and when it ships, acting on a predicted account always runs against a held-out comparison, so the prediction never grades itself",
      "The platform's most mature domain — it runs these playbooks on its own media",
      "The privacy review that killed the last intent-data vendor approves this one — consent before storage, sensitive categories refused at the schema, no audio anywhere, erasure that cascades",
    ],
  },
  legal: {
    id: "legal",
    name: "Legal & Counsel",
    short: "Legal",
    icon: "scale",
    headline: "Four legal experts on every question — behind a rail that never lets AI practice law.",
    promise: "A Mixture-of-Legal-Experts fans each question out to specialist domains and synthesizes one answer with the cross-domain conflicts a single-lens review misses. Every output is flagged for attorney review — legal conclusions are structurally barred from autonomy.",
    statusQuo: [
      "Cross-domain conflicts surface after documents are signed",
      "Outside-counsel spend climbs with every routine question",
      "Privilege and citation checks depend on whoever is least busy",
    ],
    kpiLabels: ["Review cycle time", "Conflicts caught pre-signature", "Outside-counsel spend"],
    liveTitle: "Trust modification — cross-domain conflict check",
    liveBrief: "A routine modification looks clean to a single reviewer. Fan it out to four experts, watch the tax landmine surface — then route it to counsel, never to autopilot.",
    baseExposure: 3900000,
    signals: [
      {
        id: "lg1",
        severity: "critical",
        title: "Cross-domain conflict — GST grandfathering",
        detail: "The modification is valid under state trust law, but the tax expert flags that it would terminate grandfathered GST status under federal regulations.",
        impact: "Seven-figure transfer-tax exposure if executed as drafted",
        action: "Route to counsel with full IRAC analyses + conflict memo",
        outcome: "Flagged for attorney review — advisory-only, by design",
      },
      {
        id: "lg2",
        severity: "watch",
        title: "Privilege gate — Unreviewed correspondence",
        detail: "A draft memo cites material tagged UNREVIEWED; the privilege gate blocks egress until review.",
        impact: "Waiver risk if shared outside the counsel circle",
        action: "Hold export · queue privilege review",
        outcome: "Privilege preserved · export released after review",
      },
      {
        id: "lg3",
        severity: "info",
        title: "Citation currency check",
        detail: "One cited authority superseded by a recent amendment; the corpus auto-correlates the successor statute.",
        impact: "Stale citation risk in an outbound filing",
        action: "Swap authority · record correlation in the corpus",
        outcome: "Corpus updated · future queries cite current law",
      },
    ],
    proof: [
      { metric: "4", label: "specialist experts on every legal query — one synthesized answer" },
      { metric: "100%", label: "of outputs flagged for attorney review — zero autonomous legal conclusions" },
      { metric: "38%", label: "faster internal review cycles (composite)" },
    ],
    pilotScope: [
      "One practice area (trust & estate or commercial contracts)",
      "Expert fan-out + conflict detection + privilege gates",
      "Attorney-review workflow — advisory-only, by construction",
    ],
    boardTalkingPoints: [
      "AI that assists counsel without practicing law — the guardrail is structural, not policy",
      "Cross-domain conflicts caught before signature, not in litigation",
      "One of the platform's most mature domains — a governed legal toolset in production",
    ],
  },
  logistics: {
    id: "logistics",
    name: "Logistics & Fleet",
    short: "Logistics",
    icon: "truck",
    headline: "Turn every exception into a controlled decision — before it hits the dock.",
    promise: "MIZ OKI surfaces delay, cost, and SLA risk across carriers and nodes so leadership acts on one operating picture — governed by the decision gates.",
    statusQuo: [
      "Exception handling lives in email, spreadsheets, and carrier portals",
      "SLA breaches are discovered after customers escalate",
      "No single view of cost-to-serve versus service trade-offs",
    ],
    kpiLabels: ["On-time delivery", "Cost per shipment", "Exception cycle time"],
    liveTitle: "West corridor delay cascade",
    liveBrief: "Three high-value loads are projected late. Resolve the cascade with the same playbook your ops team would use Monday morning.",
    baseExposure: 4200000,
    signals: [
      {
        id: "l1",
        severity: "critical",
        title: "Carrier ETA slip — Lane W-14",
        detail: "Weather and detention at hub projected to miss SLA by 4.2 hours on 3 premium accounts.",
        impact: "$184k at-risk revenue · 2 contractual penalties",
        action: "Re-route via secondary hub + priority appointment",
        outcome: "SLA recovered · penalty avoided · +1.1h buffer restored",
      },
      {
        id: "l2",
        severity: "watch",
        title: "Detention cost spike — DC North",
        detail: "Average dwell up 37% week-over-week; driver hours approaching HOS limit.",
        impact: "$42k monthly run-rate if uncorrected",
        action: "Release staged appointments · notify yard control",
        outcome: "Dwell trend reversed · detention run-rate −28%",
      },
      {
        id: "l3",
        severity: "info",
        title: "Capacity window opens — Partner fleet",
        detail: "Regional partner has 6 dry-van units free within 90 miles of backlog node.",
        impact: "Optional surge capacity · rate +6% vs. contract",
        action: "Hold as contingency · do not commit yet",
        outcome: "Contingency armed · no cost incurred",
      },
    ],
    proof: [
      { metric: "31%", label: "fewer SLA misses in 60 days (composite)" },
      { metric: "18%", label: "lower exception handling cost (composite)" },
      { metric: "4.6×", label: "faster decision cycle on critical lanes (composite)" },
    ],
    pilotScope: [
      "One corridor + top 3 carriers",
      "Exception playbooks for delay, detention, and capacity",
      "Weekly exec scorecard + war-room view",
    ],
    boardTalkingPoints: [
      "Protects revenue concentration on premium accounts",
      "Converts logistics from reactive firefighting to managed risk",
      "Pilot pays for itself if a single penalty class is avoided",
    ],
  },
  hr: {
    id: "hr",
    name: "People & Talent",
    short: "HR",
    icon: "users",
    headline: "See attrition, capacity, and hiring risk before they show up in the P&L.",
    promise: "MIZ OKI connects flight-risk signals, open reqs, and team load so leaders intervene early — with decision-gate policy and VAL checks on every recommended action.",
    statusQuo: [
      "Flight risk is anecdotal until exit interviews",
      "Hiring plans lag behind actual capacity shortfalls",
      "Manager interventions are inconsistent and unmeasured",
    ],
    kpiLabels: ["Regrettable attrition", "Time-to-fill", "Manager response rate"],
    liveTitle: "Engineering capacity risk — Q3",
    liveBrief: "Two critical product squads show elevated flight risk while three open roles sit unfilled. Stabilize delivery without a blanket headcount freeze reverse.",
    baseExposure: 5800000,
    signals: [
      {
        id: "h1",
        severity: "critical",
        title: "Flight-risk cluster — Platform eng",
        detail: "4 senior ICs flagged: comp drift, manager change, and market pull. 2 own release-critical paths.",
        impact: "Est. $1.2M replacement cost · 11-week roadmap slip",
        action: "Retention package + skip-level + knowledge capture",
        outcome: "2 retained · knowledge plan live · slip risk −60%",
      },
      {
        id: "h2",
        severity: "watch",
        title: "Req aging — Security eng",
        detail: "Role open 67 days; funnel conversion down 40% after recruiter reassignment.",
        impact: "Compliance project gated · audit exposure rising",
        action: "Re-prioritize sourcer capacity · adjust level band",
        outcome: "3 finalists advanced · projected fill in 18 days",
      },
      {
        id: "h3",
        severity: "info",
        title: "Manager coaching opportunity",
        detail: "Team eNPS dip concentrated under 2 new managers — not org-wide.",
        impact: "Preventable attrition if unaddressed this quarter",
        action: "Targeted coaching + workload rebalance",
        outcome: "Intervention scheduled · tracked in scorecard",
      },
    ],
    proof: [
      { metric: "22%", label: "reduction in regrettable attrition (composite)" },
      { metric: "19 days", label: "faster critical-role fill (composite)" },
      { metric: "3.1×", label: "more interventions before resignation (composite)" },
    ],
    pilotScope: [
      "One business unit + critical role families",
      "Flight-risk model + manager playbooks",
      "Monthly people-risk review for the ELT",
    ],
    boardTalkingPoints: [
      "Protects institutional knowledge in high-cost roles",
      "Links people risk directly to delivery and revenue plans",
      "Gives CHRO and CFO a shared early-warning language",
    ],
  },
  finance: {
    id: "finance",
    name: "Finance & Controllership",
    short: "Finance",
    icon: "coins",
    headline: "Close the gap between forecast, actuals, and the decisions that move them.",
    promise: "MIZ OKI flags variance drivers and spend anomalies while there is still time to act — validated and controlled before the board pack is frozen.",
    statusQuo: [
      "Variance explanations arrive days after the close",
      "Spend anomalies hide across cost centers",
      "Forecast confidence is opinion, not signal-backed",
    ],
    kpiLabels: ["Forecast accuracy", "Days to explain variance", "Leakage recovered"],
    liveTitle: "Mid-quarter margin compression",
    liveBrief: "Gross margin is tracking 180 bps below plan. Isolate drivers and commit corrective actions before the next forecast lock.",
    baseExposure: 7100000,
    signals: [
      {
        id: "f1",
        severity: "critical",
        title: "COGS variance — Product line B",
        detail: "Supplier surcharge and scrap rate elevation explaining 120 bps of the miss.",
        impact: "$6.4M annualized if run-rate holds",
        action: "Approve alternate supplier mix · scrap task force",
        outcome: "72 bps recoverable within 2 cycles",
      },
      {
        id: "f2",
        severity: "watch",
        title: "Opex drift — Marketing programs",
        detail: "Three campaigns over-indexing CAC with weak pipeline conversion.",
        impact: "$890k QTD spend at low efficiency",
        action: "Pause underperformers · reallocate to proven channels",
        outcome: "Projected $410k preserved this quarter",
      },
      {
        id: "f3",
        severity: "info",
        title: "Working capital opportunity",
        detail: "DSO elevated in 2 segments; collection playbooks underused.",
        impact: "$2.1M cash unlock potential",
        action: "Trigger collections cadence · exec sponsor on top accounts",
        outcome: "Cash plan updated · tracked weekly",
      },
    ],
    proof: [
      { metric: "35%", label: "faster variance explanation (composite)" },
      { metric: "90 bps", label: "margin recovery in composite scenario units" },
      { metric: "2.4×", label: "more spend interventions in-quarter (composite)" },
    ],
    pilotScope: [
      "One P&L + cost centers feeding the miss",
      "Variance cockpit + intervention workflow",
      "Forecast confidence score for ELT reviews",
    ],
    boardTalkingPoints: [
      "Improves forecast credibility with the board",
      "Turns controllership from reporting to control",
      "Cash and margin actions still movable mid-quarter",
    ],
  },
  ops: {
    id: "ops",
    name: "Operations & Production",
    short: "Ops",
    icon: "gauge",
    headline: "Run the plant and the plan from one decision surface.",
    promise: "MIZ OKI connects throughput, quality, and labor so plant and network leaders clear constraints in hours — with CSE scenarios and decision-gate authority bounds.",
    statusQuo: [
      "Shift handoffs lose context every 8–12 hours",
      "Constraint ownership is unclear across sites",
      "Quality escapes are explained after scrap piles up",
    ],
    kpiLabels: ["OEE", "First-pass yield", "Constraint clearance time"],
    liveTitle: "Line 3 throughput constraint",
    liveBrief: "A critical line is 14% below plan. Diagnose, clear the constraint, and protect the weekly commit.",
    baseExposure: 6400000,
    signals: [
      {
        id: "o1",
        severity: "critical",
        title: "Bottleneck — Changeover overrun",
        detail: "Average changeover +22 min vs. standard; three SKUs driving 80% of loss.",
        impact: "11k units / week short of commit",
        action: "Lock SMED playbook · freeze non-critical changeovers",
        outcome: "Recovered 7.5k units / week run-rate",
      },
      {
        id: "o2",
        severity: "watch",
        title: "Quality drift — Station 4",
        detail: "Defect rate trending up 2 shifts; root cause likely tooling wear.",
        impact: "Scrap cost + customer risk if ships",
        action: "Tooling swap + hold lot review",
        outcome: "Defect rate normalized · no escape",
      },
      {
        id: "o3",
        severity: "info",
        title: "Labor flex available — Site B",
        detail: "Certified cross-trained pool free for 2 shifts.",
        impact: "Optional overtime avoidance",
        action: "Offer transfer · keep OT as backup",
        outcome: "Coverage plan set without OT spike",
      },
    ],
    proof: [
      { metric: "9%", label: "OEE lift in the composite scenario" },
      { metric: "41%", label: "faster constraint clearance (composite)" },
      { metric: "27%", label: "fewer quality escapes (composite)" },
    ],
    pilotScope: [
      "One site + critical line family",
      "Constraint and quality playbooks",
      "Daily ops huddle fed by MIZ OKI",
    ],
    boardTalkingPoints: [
      "Protects customer commit reliability",
      "Creates a repeatable operating cadence",
      "Capital avoidance if throughput recovers without new lines",
    ],
  },
  customer: {
    id: "customer",
    name: "Customer Experience",
    short: "CX",
    icon: "headset",
    headline: "Stop churn and escalation before they become board topics.",
    promise: "MIZ OKI unifies account health, case load, and revenue risk so GMs and CS leaders intervene with precision — not heroics.",
    statusQuo: [
      "Churn risk is visible only after NPS collapses",
      "Escalations jump queues without economic context",
      "Success motions are heroics, not system",
    ],
    kpiLabels: ["Logo retention", "Time-to-resolution", "Expansion pipeline"],
    liveTitle: "Strategic account health — North America",
    liveBrief: "Two enterprise accounts show compounding risk. Stabilize delivery perception and protect renewal.",
    baseExposure: 8200000,
    signals: [
      {
        id: "c1",
        severity: "critical",
        title: "Renewal risk — Acme Global",
        detail: "Support volume, product gap narrative, and sponsor change. Renewal in 47 days.",
        impact: "$2.8M ARR · logo risk",
        action: "Exec sponsor call · recovery plan · product commitment",
        outcome: "Recovery plan accepted · renewal probability +34 pts",
      },
      {
        id: "c2",
        severity: "watch",
        title: "Case backlog — Enterprise tier",
        detail: "P1 median resolution up to 19h (target 8h).",
        impact: "Satisfaction drag across 14 accounts",
        action: "Surge specialist pod · auto-triage rules",
        outcome: "P1 median projected to 9h in 10 days",
      },
      {
        id: "c3",
        severity: "info",
        title: "Expansion signal — Sector vertical",
        detail: "Usage depth up 40% in 3 accounts; white-space modules unused.",
        impact: "$640k expansion potential",
        action: "Queue value review · hold until risk cleared",
        outcome: "Expansion queue staged post-recovery",
      },
    ],
    proof: [
      { metric: "16%", label: "lower logo churn in the composite book (illustrative)" },
      { metric: "2.2×", label: "faster critical escalation path (composite)" },
      { metric: "11%", label: "higher net revenue retention (composite)" },
    ],
    pilotScope: [
      "Top 50 accounts by ARR",
      "Health model + recovery playbooks",
      "Weekly risk review with GMs",
    ],
    boardTalkingPoints: [
      "Defends recurring revenue concentration",
      "Creates early-warning for strategic accounts",
      "Pairs retention savings with expansion discipline",
    ],
  },
  supply: {
    id: "supply",
    name: "Supply Chain & Procurement",
    short: "Supply",
    icon: "package",
    headline: "See supplier, inventory, and demand risk as one system.",
    promise: "MIZ OKI flags shortage, single-source, and inventory imbalance early enough to rebalance — not expedite in panic.",
    statusQuo: [
      "Single-source risk is a slide, not a live control",
      "Expedites mask systemic planning gaps",
      "Inventory dollars and service levels fight each other",
    ],
    kpiLabels: ["Fill rate", "Expedite spend", "Single-source exposure"],
    liveTitle: "Component shortage — Product family A",
    liveBrief: "A critical component is 3 weeks short of plan. Protect revenue SKUs and contain expedite spend.",
    baseExposure: 9500000,
    signals: [
      {
        id: "s1",
        severity: "critical",
        title: "Supplier delay — Part AX-440",
        detail: "Primary supplier push-out 18 days; dual-source not qualified on all plants.",
        impact: "$9.1M revenue at risk · 2 plants affected",
        action: "Allocate to high-margin SKUs · accelerate alt-source qual",
        outcome: "Revenue protection plan locked · risk −55%",
      },
      {
        id: "s2",
        severity: "watch",
        title: "Inventory imbalance — Finished goods",
        detail: "Overstock on slow movers while A-items run thin.",
        impact: "$1.4M trapped working capital",
        action: "Rebalance DC transfer · freeze build on slow movers",
        outcome: "Working capital unlock path defined",
      },
      {
        id: "s3",
        severity: "info",
        title: "Expedite pattern detected",
        detail: "Same commodity expedited 6× in 90 days — planning parameter issue.",
        impact: "Avoidable $220k / quarter pattern",
        action: "Reset safety stock policy · owner assigned",
        outcome: "Policy change queued · tracked in pilot KPI",
      },
    ],
    proof: [
      { metric: "28%", label: "less expedite spend (composite)" },
      { metric: "12 pts", label: "fill-rate improvement on A-items (composite)" },
      { metric: "40%", label: "faster shortage response (composite)" },
    ],
    pilotScope: [
      "One product family + critical components",
      "Allocation + dual-source workflows",
      "Weekly S&OE decision forum",
    ],
    boardTalkingPoints: [
      "Reduces existential single-source exposure",
      "Improves cash without sacrificing service blindly",
      "Replaces expedite culture with planned control",
    ],
  },
};

MIZOKI.computeEconomics = function (domainId, sizeId, resolvedCount) {
  const domain = MIZOKI.DOMAINS[domainId];
  const size = MIZOKI.SIZES.find((s) => s.id === sizeId) || MIZOKI.SIZES[1];
  const mult = size.multiplier;
  const annualExposure = Math.round(domain.baseExposure * mult);
  let recoverable = Math.round(annualExposure * MIZOKI.BASE_RECOVERY);
  const boost = 1 + Math.min((resolvedCount || 0) * 0.04, 0.12);
  recoverable = Math.round(recoverable * boost);
  const pilotCost = Math.round(
    MIZOKI.PILOT_COST_BASE * (mult > 1.2 ? 1.25 : mult < 0.9 ? 0.85 : 1)
  );
  const paybackMonths = Math.max(1, Math.round((pilotCost / recoverable) * 12));
  const firstYearNet = recoverable - pilotCost;
  const roi = Math.round((firstYearNet / pilotCost) * 100);
  return { annualExposure, recoverable, pilotCost, paybackMonths, firstYearNet, roi };
};

MIZOKI.formatCurrency = function (value, compact) {
  if (compact && Math.abs(value) >= 1e6) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
};
