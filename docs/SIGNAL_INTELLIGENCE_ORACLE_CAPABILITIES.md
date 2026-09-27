<!--
Archived capabilities documentation (owner-supplied, 2026-07-30).
Incorporated into the public site per owner instruction:
  - /signal        — Signal Intelligence division marketing page (full treatment)
  - /demo/signal   — ORACLE section on the Signal Factory demo (canon re-pinned)
Claim discipline is binding: "anticipatory intent with proof of causal lift",
never "mind-reading"; calibrated probabilities, never certainties; targets are
labeled design targets, never guaranteed; no audio ever; consent-first.
-->

<!--
CORRECTION 2026-08-11 (owner cell-registry ruling; INTEGRATION PROMPT v2.3 F7):
the original mapping "Cell 28 = Intent Scoring API, Cell 34 = intent graph,
Cell 35 = Incrementality & Causal Credit" was IN ERROR. Corrected throughout to
the measured service bindings: Cell 33 = intent-signal-ingest, Cell 34 =
intent-scoring-api, Cell 35 = intent-graph, Cell 36 = intent-causal;
Cell 37 = Data Injector & External Intelligence Gateway (market-signal-ingest).
Cell 28 remains a legacy production cell (A/B Testing), not an intent cell.
Number authority: docs/architecture/CELL_REGISTRY.md in MIZOKICloudRun.
Backend references (Neo4j / TigerGraph) predate the 2026-08-09 Neo4j
retirement (KG backend is Firestore) and are left for the repo-wide
compliance sweep. External copy references services by NAME, never number.

CORRECTION 2026-09-02 (cell count): the "37-cell" compute line below reflects
the 2026-08-11 count. The owner's 2026-08-16 ruling added Cells 38–39 (CRE
Prospecting), so the registered fleet is 39 cells (32 production + 4 LII +
Cell 37 gateway + Cells 38–39). Body left as supplied; CELL_REGISTRY.md v1.1
remains the number authority.
-->

# MIZ OKI 3.5 — Signal Intelligence Division

## Marketing Capabilities Documentation

*Prepared for the Marketing Organization · Platform version: MIZ OKI 3.5 (“Operating Knowledge Intelligence”) · Division: Signal Intelligence, featuring the ORACLE / Latent Intent Inference (LII) family*

-----

## 1. Executive Overview

**Mission.** The Signal Intelligence division turns every fragmented marketing signal — a paid-search click, a bidstream request, an email open, a cart event, a scroll — into governed, causal evidence a marketer can act on with confidence. Where most marketing stacks show you *what happened*, Signal Intelligence tells you *what is about to happen* and *whether your marketing actually caused it*.

**What “signal intelligence” means for marketers.** It is the discipline of (1) capturing behavioral signals across every channel, (2) resolving them to people and households under consent, (3) inferring latent intent — what a person is likely to want next and when — and (4) proving, with causal experiments, which marketing dollars produced net-new outcomes versus which merely took credit for conversions that would have happened anyway.

**The positioning: “crystal ball plus proof.”** The flagship capability, ORACLE (Latent Intent Inference), is an *anticipatory intent engine* — it predicts intent stage, next-best interest, and purchase timing with calibrated probabilities. But ORACLE never ships a prediction without its companion: a causal credit ledger that distinguishes conversions we *caused* from conversions we merely *anticipated*. This is the core differentiator. We say **“anticipatory intent with proof of causal lift.” We never say “mind-reading.”**

**Business goals.** Signal Intelligence is engineered to drive MIZ OKI’s three headline marketing targets: a **40% reduction in CAC**, a **35% increase in ROAS**, and a **67% improvement in ROI**. (Per MIZ OKI claim-discipline policy, these are design/benchmark targets — to be labeled verified, benchmarked, pilot, or illustrative depending on the evidence available in a given deployment — not guaranteed outcomes.)

**How it fits the platform.** Signal Intelligence is a family of Domain Intelligence Cells operating inside MIZ OKI’s SRPVDAL loop (Sense → Reason → Plan → Validate → Decide → Act → Learn). Every intent score and lift estimate is an *evidence-backed, governed decision object*, not a black-box number — it carries provenance, confidence, an explanation path, and a governance label.

-----

## 2. Platform Foundation (Technical Grounding)

Signal Intelligence runs on the same production architecture as the rest of MIZ OKI 3.5:

- **Compute:** 37-cell FastAPI microservices platform (32 production cells + LII Cells 33–36 + Cell 37 — number authority: MIZOKICloudRun docs/architecture/CELL_REGISTRY.md) on **Google Cloud Run** (region `us-central1`), each cell independently deployable and scalable.
- **Data:** a unified **BigQuery** dataset as the analytical backbone; **Firestore** for operational evidence; **Neo4j / TigerGraph** knowledge graphs for the temporal-causal and intent graphs.
- **ML:** **BigQuery ML → Vertex AI Vector Search** for embeddings and approximate-nearest-neighbor retrieval.
- **Frontend:** **React / TypeScript / MUI** with **D3 and Cytoscape** for graph and journey visualization.
- **Performance:** **sub-100ms query latency** on served intent scores.
- **The SRPVDAL cell map** (as it pertains to Signal Intelligence):
  - **Sense Cells 1–5** — omnichannel ingestion.
  - **Reason Cells 6–12** — analysis, attribution, entity resolution.
  - **Decide Cells 13–18** — strategy and budget planning.
  - **Act Cells 19–22** — execution through governed integrations.
  - **Learn Cells 23–25** — knowledge graph and learning ledger.
  - **Cells 26–27** — causal uplift measurement (X-Learner, DR-Learner / DoWhy refutation).
  - **Cells 29–31** — meta-orchestration.
  - **Cell 3-1** — knowledge-graph visualization bridge.
- **The ORACLE / LII cells (newly incorporated flagship):**
  - **Cell 33** — micro-signal ingestion with a hard consent gate.
  - **Cell 34** — Intent Scoring API.
  - **Cell 35** — Neo4j intent graph.
  - **Cell 36** — Incrementality & Causal Credit.
- **Boss agent:** an AI assistant with MCP tools (Gmail, Google Calendar, Google Drive, Chrome automation, scheduled tasks) that can query intent, run experiments, and prepare approval packages on the marketer’s behalf.

> **Note on ground truth:** The division inherits MIZ OKI 3.5’s core constructs from the master positioning document — the Canonical Event Envelope, the Temporal-Causal Knowledge Base, Domain Intelligence Cells, the Decision Control Plane, and the Immutable Learning Ledger. Signal Intelligence is an application of that operating system to the marketing signal problem, not a separate stack.

-----

## 3. Omnichannel Signal Capture

### 3.1 Channels and sources ingested (Sense Cells 1–5 + Cell 33)

Signal Intelligence ingests from the full marketing surface:

- **Paid search — Google Ads (GAQL):** campaigns, ad groups, keywords, search terms, assets, conversions, budgets, audiences, geographies, and attribution data, extracted via `GoogleAdsService.SearchStream` with `GoogleAdsFieldService` field validation and MCC traversal.
- **Programmatic — OpenRTB bidstream:** bid requests, win/loss notices, buyer and seat IDs, exchange and DSP metadata, device signals, price floors, currency, and consent signals.
- **Email / ESP:** sends, opens, clicks, bounces, unsubscribes, spam complaints, conversions, suppression events, segments, and campaign metadata.
- **CRM & ecommerce:** accounts, contacts, opportunities, orders, carts, catalog/product data, revenue, and margin.
- **Web / app behavioral SDK (Cell 33 micro-signals):** search sessions, dwell time, scroll velocity, hover, partial video watches, rewatches, cart events, and email opens/clicks.
- **Offline / CTV where applicable:** ingested through the same canonical envelope for geo-level measurement (CTV prospecting is a natural fit for geo experiments because it is broadly targeted and hard to measure at the user level).

### 3.2 The canonical event envelope

Every signal — regardless of source — becomes a **Canonical Event** with tenant ID, loop ID, source system, connector, event type, event time, ingestion time, raw payload reference, normalized fields, entity candidates, metric values, provenance, governance labels, confidence scores, and audit IDs. This is what lets marketers reason across channels without hard-coding each source into a siloed report.

### 3.3 Identity resolution — deterministic-first, household graph

Signal Intelligence resolves signals to people and households using a **deterministic-first** strategy (exact matches on authenticated identifiers such as email or login), then extends reach with **probabilistic** matching (statistical inference from device, IP, and behavioral signals) only where governance permits. This mirrors best-in-class CDP practice: as CDP.com’s identity-graph glossary puts it, “Deterministic matching…offers near-100% accuracy but limited reach, since it requires an authenticated event to create a link. Probabilistic matching uses statistical models to infer connections based on signals like IP address, device characteristics, location, and behavioral patterns.” Cell 35’s intent graph explicitly labels each household link as **deterministic vs. probabilistic**, so a marketer always knows the confidence behind a “household” rollup.

### 3.4 Consent-first architecture

Micro-signal ingestion (Cell 33) sits behind a **hard consent gate**: no consent, no ingestion. This is not a compliance afterthought bolted on at the end — it is embedded in the Sense layer, consistent with MIZ OKI’s principle that governance lives *inside* the operating loop.

-----

## 4. Acquisition Intelligence (Toward 40% CAC Reduction)

### 4.1 CAC-reduction levers

1. **Stop paying for anticipated conversions.** ORACLE’s causal credit ledger (Cell 36) separates conversions marketing *caused* from those it merely *anticipated*. Spend that only “claims credit” for organic demand is the first budget to cut — directly lowering CAC without lowering volume.
1. **Reallocate to proven-incremental channels.** Budget planning (Decide Cells 13–18) shifts spend toward channels and campaigns with the highest *incremental* ROAS (iROAS), not the highest platform-reported ROAS.
1. **Target in-market people/accounts earlier.** Intent-stage scoring lets you concentrate acquisition spend on “in-market” and “purchase-imminent” segments instead of spraying awareness budget across cold audiences.

### 4.2 Attribution — multi-touch *and* causal

Signal Intelligence runs multi-touch attribution (Reason Cells 6–12) to map path-to-conversion across channels, then **calibrates it against causal experiments** (Cells 26–27, 36). This is the emerging industry consensus — the “trifecta” of MTA + MMM + incrementality — where incrementality acts as the causal “calibration layer.” The incrementality vendor Measured (measured.com) frames controlled experiments as the gold standard that calibrates correlational attribution, noting that “iROAS is typically lower than platform-reported ROAS because it isolates true causal impact.” Northbeam similarly positions its 2026 incrementality launch as completing “the trifecta of digital attribution,” with incrementality as the “calibration layer between the mainstays of MTA and MMM.”

### 4.3 Budget reallocation from anticipated-vs-caused insight

Because every conversion in the ledger is tagged *caused* or *anticipated* with a confidence interval, budget-reallocation plans are grounded in causal credit rather than last-click artifacts. Plans pass through the VALIDATE gate (financial, statistical, causal, policy) before any spend moves.

### 4.4 Predictive audiences & lookalike-style expansion

ORACLE’s two-tower embeddings (Section 6) produce dense customer and topic/product vectors. Marketers can expand from a high-value seed to a lookalike-style audience via nearest-neighbor retrieval in Vertex AI Vector Search — but with a crucial upgrade over classic lookalikes: each expansion candidate carries a *calibrated intent probability and stage*, so you expand toward people who are actually approaching in-market, not just people who demographically resemble your seed.

### 4.5 In-market account/person detection

Intent-stage classification (awareness / consideration / in-market / purchase-imminent) surfaces accounts and people entering a buying window. Marketers can subscribe to “notify when account enters in-market” alerts (Section 5.6 / 6.6).

-----

## 5. Journey Intelligence

### 5.1 Journey mapping in the knowledge graph

Cell 35’s Neo4j **intent graph** models the journey as a living graph of **Customer / Household / Topic / Product / Campaign** nodes connected by **SHOWED_INTEREST** edges (a person/household showed interest in a topic/product) and **PRECEDES** co-occurrence edges (interest in X tends to precede interest in Y). Rendered in the Command Center with D3/Cytoscape, this replaces the flat “funnel” with an honest map of how interest actually propagates.

### 5.2 Journey timelines with predicted-next-interest overlays

The predicted journey timeline shows each customer’s observed touchpoints and overlays ORACLE’s **predicted next interests** with calibrated probabilities — so a lifecycle marketer sees not just where a customer *has been* but where they are *likely to go next*.

### 5.3 Stage-progression analytics

Because intent stage is scored continuously, marketers can measure stage-to-stage progression rates, velocity, and where cohorts stall — the analytical equivalent of “which messages actually move accounts forward.”

### 5.4 Drop-off and dark-funnel inference

Much of the modern buyer journey is invisible to conventional analytics — research on review sites, communities, podcasts, and private channels that never touches your CRM. The scale is striking: Gartner’s B2B buyer research finds buyers spend only about 17% of their total buying journey meeting with potential suppliers (and just 5–6% with any single sales rep), leaving the large majority for independent, largely untrackable research. Signal Intelligence infers dark-funnel activity from the *shape* of observed micro-signals and PRECEDES co-occurrence patterns in the intent graph, flagging likely-active journeys even before a form fill — while being explicit that this is inference, not observation.

### 5.5 Journey-optimization recommendations

Planning skills (intervention generation, journey optimization, next-best-action) propose stage-appropriate moves — e.g., “shift this consideration-stage cohort from awareness display to retargeting + email nurture” — each with expected impact, confidence, reversibility, and a measurement plan attached.

-----

## 6. Predictive Capabilities — The ORACLE Flagship

ORACLE (Latent Intent Inference) is the anticipatory core of Signal Intelligence. It is positioned as an **“anticipatory intent crystal ball with proof of causal lift.”**

### 6.1 Latent Intent Inference

ORACLE infers *latent* intent — intent that hasn’t yet expressed itself as a click or form fill — from behavioral micro-signals (Cell 33). The modeling pattern is deliberately the **candidate-generation + ranking** architecture proven at web scale in recommendation systems. It is the same two-stage design introduced in Covington, Adams & Sargin, “Deep Neural Networks for YouTube Recommendations” (RecSys ’16), whose authors describe splitting the system “according to the classic two-stage information retrieval dichotomy: first, we detail a deep candidate generation model and then describe a separate deep ranking model” — the pattern now standard across YouTube, Meta, and TikTok-scale systems:

- **Two-tower embeddings** (a customer/query tower and a topic-product/candidate tower) learned in BigQuery ML, retrieving candidate interests via approximate-nearest-neighbor search in Vertex AI Vector Search — the “candidate generation” step that reduces a huge catalog of possible interests to a manageable shortlist in milliseconds.
- **Sequence models** that read the ordered micro-signal stream to rank and time predictions — the “ranking” step.

### 6.2 The Intent Scoring API (Cell 34)

Cell 34 serves, at sub-100ms latency:

- **Intent vectors** (the dense embedding of a customer’s current intent state).
- **Predicted next interests** with **calibrated probabilities**.
- **Intent-stage classification:** awareness / consideration / in-market / purchase-imminent.
- **Confidence and explanation paths** — *why* the model believes what it believes, traced through the intent graph.

Calibration matters: ORACLE reports both **discrimination** (AUC — the ability to rank a true positive above a true negative) and **calibration** (Brier score — the mean squared error between predicted probabilities and actual outcomes, where a well-calibrated “70% likely” is right about 70% of the time). This is why intent scores are *decision-grade*, not vanity scores — and it is the direct answer to the most common complaint leveled at opaque intent vendors, whose scores “feel opaque” and are “hard to validate.”

### 6.3 Purchase-timing prediction

Beyond “will they buy,” ORACLE estimates *when* — mapping a customer toward a predicted purchase window so demand-gen and lifecycle teams can time outreach to the moment of maximum receptivity rather than blasting on a fixed cadence.

### 6.4 Churn / expansion propensity

Where the signal base supports it, the same architecture infers churn risk and expansion/upsell propensity (e.g., a customer’s intent vector drifting toward adjacent products, or toward competitor-associated topics). These are surfaced only when calibration thresholds are met.

### 6.5 KG-based predictions

The intent graph (Cell 35) powers predictions that pure embeddings cannot:

- **PRECEDES co-occurrence edges** enable “customers who showed interest in X next showed interest in Y” reasoning.
- **Explanation paths** give every prediction a human-readable trace through nodes and edges — the antidote to the “black box” complaint.
- **Household inference** rolls individual signals up to household-level intent, with deterministic vs. probabilistic links clearly labeled.

### 6.6 Real-time alerts and subscriptions

Marketers can subscribe to intent events — e.g., **“notify when this account enters in-market”** or “alert when purchase-imminent probability crosses 0.7.” Alerts stream via Pub/Sub and SSE dashboards and can trigger Boss-agent workflows.

### 6.7 Autonomy and promotion criteria

Consistent with MIZ OKI governance, ORACLE ships in **observe-only** mode by default. A model is **promoted** to higher autonomy only when it clears explicit gates: **Brier ≤ 0.20, AUC ≥ 0.72, and stable lift across ≥ 2 purchase cycles.** Until then, predictions inform humans; they do not act autonomously.

-----

## 7. Causal Measurement & Incrementality (Cells 26–27, 36)

This is the “proof” half of “crystal ball plus proof,” and the reason Signal Intelligence beats last-click, platform self-attribution, and correlation-only intent vendors.

### 7.1 Uplift modeling — X-Learner and DR-Learner

Cells 26–27 estimate **heterogeneous treatment effects** (who is *persuadable*, not just who converts) using meta-learners:

- **X-Learner** (Künzel et al., 2019) — provably efficient when treatment and control groups are very different in size (the norm in marketing holdouts) and when treatment effects are heterogeneous.
- **DR-Learner** (doubly robust; Kennedy) — uses a doubly-robust pseudo-outcome so that estimates stay consistent under weaker assumptions about the nuisance models.

### 7.2 DoWhy refutation

Every causal estimate is **stress-tested** with DoWhy refuters before it is trusted: **placebo-treatment** (replace the real treatment with a random variable — the effect should collapse to zero), **random-common-cause** (add a random confounder — the estimate should not move), and **data-subset** refuters. An estimate that fails refutation is flagged, not shipped.

### 7.3 Experiment designs — holdout, ghost-bid, geo

- **Holdout experiments** withhold media from a randomized control group and compare against the exposed group. 
- **Ghost-bid / ghost-ad experiments** are the most efficient control-group design in modern ad platforms. Based on the “Ghost Ads” methodology (Johnson, Lewis & Nubbemeyer, “Ghost Ads: Improving the Economics of Measuring Online Ad Effectiveness,” *Journal of Marketing Research*, 2017; two of the three authors were Google researchers), the platform *logs the auction instances where a control user would have been served the ad* — identifying the counterfactual control group without spending money on placebo (PSA) ads.  As the paper’s authors put it, ghost ads “facilitate this comparison by identifying the control group counterparts of the exposed consumers in a randomized experiment,” and “relative to public service announcement and intent-to-treat A/B tests, ghost ads can reduce the cost of experimentation, improve measurement precision, [and] deliver the relevant strategic baseline.” A “predicted ghost ad” variant supports display platforms.
- **Geo experiments** run a channel in test markets while holding it out of statistically matched control markets  — essential for broadly-targeted, hard-to-address channels. As Measured describes it, “a geo-split is used when an audience is unaddressable… This applies to any channel that employs broad targeting like social prospecting, CTV prospecting, and paid search.”

### 7.4 The caused-vs-anticipated credit ledger

Cell 36 maintains a **causal credit ledger** that classifies each conversion as **caused** (marketing produced net-new outcome, proven by experiment) or **anticipated** (ORACLE predicted the customer would convert anyway), each with a **confidence interval**. This is the artifact that turns intent prediction from a liability (“you’re just taking credit for demand that already existed”) into an asset (“here is exactly what we caused, and here is what we would have gotten for free”).

### 7.5 Why this beats the alternatives

- **vs. last-click:** last-click credits one touchpoint and ignores the journey and the counterfactual entirely.
- **vs. platform self-attribution:** ad platforms grade their own homework;  reported ROAS credits any conversion after exposure. Incremental ROAS (iROAS) reflects only net-new revenue proven by experiment,  and the gap between the two is frequently large — Common Thread Collective’s geo-holdout database, for example, reports a median iROAS for Google branded search of roughly **0.27x** (only about 27 cents of each branded-search dollar is truly incremental), and public geo-test case studies (e.g., Haus with Bombas, True Classic, Liquid Death) commonly show platform-reported ROAS overstating measured iROAS by ~1.5x–3x, widest on brand search and retargeting.
- **vs. correlation-only intent vendors:** surge/topic vendors (e.g., account-level “Company Surge”–style signals) tell you an account is “researching” — a correlation, and typically only at the account level, not the person. ORACLE gives you the calibrated probability *and* proves, via experiment, whether your response actually moved the outcome.

-----

## 8. Activation & Access (Democratized Signal)

### 8.1 Dashboards (Command Center)

- **Intent Scores Grid:** every account/person with intent stage, calibrated next-interest probabilities, confidence, and drill-down explanation paths.
- **Predicted Journey Timeline:** observed touchpoints plus predicted-next-interest overlays.
- **Incrementality Panel:** iROAS by channel/campaign, uplift with confidence intervals, refutation status, and the caused-vs-anticipated ledger.

### 8.2 API, SDK, and real-time feeds

- **Intent Signal API** (Cell 34) for synchronous scoring.
- **Python SDK** for data scientists and analysts.
- **Pub/Sub real-time feed** for event-driven activation.
- **SSE dashboards** for live streaming to the UI.

### 8.3 Boss-agent / AI-assistant workflows (MCP)

The Boss agent exposes Signal Intelligence through **MCP tools**, so a marketer can ask, in natural language, “which in-market accounts entered this week, and what’s the proven-incremental channel to reach them?” — and the agent will query intent, pull the ledger, draft the plan, and (with approval) schedule the activation via Calendar/Gmail/Chrome automation.

### 8.4 Role-based access & alerting

Access is tenant-isolated and role-scoped; alerting is subscription-based (per Section 6.6). Sensitive capabilities default to observe-only.

-----

## 9. Governance, Privacy & Trust as a Marketing Advantage

Trust is not a tax on Signal Intelligence — it is a *feature marketers can sell to their own customers and their own legal teams*.

- **Consent-first ingestion.** Cell 33’s hard consent gate means micro-signals are only ingested with consent. No consent, no data.
- **GDPR / CCPA profiling rights.** The platform honors data-subject rights around profiling and automated decision-making. GDPR Article 22 gives individuals “the right not to be subject to a decision based solely on automated processing, including profiling, which produces legal effects…or similarly significantly affects” them, plus a right to human intervention — which is exactly why ORACLE defaults to observe-only and routes significant actions through human approval.
- **Sensitive-topic “creepiness” deny-list.** Certain topics are hard-blocked from intent modeling and activation, so the system cannot infer or target on sensitive categories.
- **No audio signals — ever.** The platform categorically excludes audio capture. This is a bright-line policy that directly rebuts the “is my phone listening to me” fear.
- **Governance inside the loop.** Every prediction and action carries provenance, confidence, an explanation path, and a governance eligibility status (eligible / needs approval / blocked by policy / blocked by low confidence, etc.), written to the immutable learning ledger.

-----

## 10. Use Cases & Playbooks by Marketing Function

Each playbook ties to the 40% CAC / 35% ROAS / 67% ROI targets (labeled per claim discipline).

### 10.1 Demand Generation

**Play:** Subscribe to “account enters in-market” alerts → concentrate paid budget on in-market + purchase-imminent segments → validate channel with a ghost-bid/geo holdout → reallocate from anticipated-only channels.
**Expected outcome:** lower CAC by cutting spend on demand that would have converted anyway; higher iROAS on retained spend.

### 10.2 Lifecycle / CRM

**Play:** Use predicted next-interest overlays and purchase-timing to trigger nurtures at the moment of receptivity → suppress messaging to “anticipated-anyway” customers to protect margin and deliverability.
**Expected outcome:** higher conversion per send, lower fatigue/unsubscribe, improved ROI.

### 10.3 Growth / Performance

**Play:** Run always-on incrementality (holdout + ghost-bid) across the media mix → optimize to iROAS, not platform ROAS → feed proven-incremental audiences back into predictive expansion.
**Expected outcome:** the 35% ROAS-lift target, driven by moving budget to genuinely incremental channels.

### 10.4 Brand

**Play:** Use geo experiments to measure the incremental lift of hard-to-track brand/CTV spend → measure downstream intent-stage progression (awareness → consideration) as a leading indicator.
**Expected outcome:** defensible causal evidence for brand budgets that last-click cannot provide.

### 10.5 RevOps

**Play:** Wire the Intent Signal API + Pub/Sub feed into CRM to prioritize pipeline by calibrated intent and stage → use the causal credit ledger as the single shared source of truth for marketing-sourced vs. marketing-influenced pipeline.
**Expected outcome:** marketing/sales alignment on one causal reality; better forecast accuracy.

-----

## 11. Regional / Segment Views

The “regions” requirement maps to **geographic and segment-level intent aggregation** plus **geo-experimentation**:

- **Geo/segment intent heatmaps.** Because intent is scored per person/household and rolled up through the intent graph, Signal Intelligence can aggregate calibrated intent by region, DMA, or segment — a heatmap of “where is in-market demand concentrating right now.”
- **Geo experimentation.** The same regional structure powers geo holdouts (Cell 36): the platform identifies statistically representative test markets and matched control markets, runs the treatment, and compares aggregate conversion behavior — the rigorous way to measure channels that can’t be held out at the user level. (This is the same method Wayfair documents for measuring incrementality across ~210 DMAs while holding out only a small, precisely-matched share of market.)
- **Segment-level uplift.** X-Learner/DR-Learner estimate heterogeneous effects, so lift can be read per segment/region — revealing where a channel is genuinely incremental versus where it is wasted.

-----

## 12. Glossary & Claim-Discipline Guidance

### 12.1 Glossary for marketers

- **Latent intent** — intent inferred from behavior before it is explicitly expressed (a click/form fill).
- **Intent vector** — the dense embedding representing a customer’s current intent state.
- **Intent stage** — awareness / consideration / in-market / purchase-imminent.
- **Calibrated probability** — a probability that means what it says (70% ≈ right 70% of the time), measured by Brier score.
- **AUC** — discrimination: the probability the model ranks a true converter above a non-converter.
- **Brier score** — calibration/accuracy of probabilistic predictions; lower is better (0 = perfect).
- **Two-tower model** — the candidate-generation architecture (separate user and item encoders) used for fast retrieval.
- **Incrementality / iROAS** — the net-new revenue marketing *caused*, divided by spend — as opposed to platform-reported ROAS, which credits any conversion after exposure. 
- **Ghost bid / ghost ad** — a control-group method that logs auction instances where a user *would have* seen an ad, without serving it, to measure true lift. 
- **Holdout / geo test** — experiments that withhold media from a randomized audience or matched geographies.
- **X-Learner / DR-Learner** — meta-learners for estimating who is persuadable (heterogeneous treatment effects).
- **DoWhy refutation** — automated stress tests (placebo, random common cause, data subset) that try to break a causal estimate before you trust it.
- **PRECEDES edge** — a co-occurrence relationship in the intent graph: interest in X tends to precede interest in Y.
- **Caused vs. anticipated** — the ledger distinction between conversions marketing produced and conversions that would have happened anyway.
- **Dark funnel** — the majority of the buyer journey that happens off your trackable channels.

### 12.2 Claim discipline — what we say and don’t say

- ✅ **Say:** “anticipatory intent with proof of causal lift.”
- ❌ **Don’t say:** “mind-reading,” “we know what customers are thinking,” or “we listen to your conversations.”
- ✅ **Say:** “calibrated probability that this account is in-market,” with the confidence and explanation path.
- ❌ **Don’t say:** “this account *will* buy.”
- ✅ **Say:** “proven-incremental” only when an experiment (holdout/ghost-bid/geo) passed refutation.
- ❌ **Don’t say:** “incremental” for correlation-only or platform-reported numbers.
- Every metric (40% CAC / 35% ROAS / 67% ROI) must be labeled **verified, benchmarked, pilot-target, or illustrative** — never presented as guaranteed.
- No audio, ever. Sensitive topics are denied. Consent is required. Humans stay in the loop on significant decisions.

-----

## Recommendations (Staged Rollout)

**Stage 1 — Sense & See (Weeks 0–6).** Stand up Cells 1–5 + Cell 33 ingestion for your two highest-spend channels (typically Google Ads and one programmatic/CTV source) plus ESP and CRM. Turn on deterministic-first identity resolution and the consent gate. **Benchmark to advance:** ≥ 80% attribution/identity coverage and a populated intent graph. *Ship ORACLE in observe-only.*

**Stage 2 — Score & Explain (Weeks 6–12).** Enable Cell 34 intent scoring and the Command Center Intent Scores Grid + Predicted Journey Timeline for one marketing function (recommend Demand Gen or Lifecycle). **Benchmark to advance / promote a model past observe-only:** **Brier ≤ 0.20, AUC ≥ 0.72, stable lift across ≥ 2 purchase cycles.** If a model fails these, keep it advisory and retrain.

**Stage 3 — Prove (Weeks 8–16, overlapping).** Launch Cell 36 incrementality with a ghost-bid or geo holdout on your single most-questioned channel (usually branded search or retargeting). Require DoWhy refutation to pass before any estimate informs budget. **Benchmark to reallocate budget:** a refutation-passing iROAS with a confidence interval that excludes your target hurdle rate.

**Stage 4 — Act & Compound (Quarter 2+).** Move budget on the caused-vs-anticipated ledger; wire Pub/Sub + Boss-agent MCP workflows for in-market alerting; expand predictive audiences from proven-incremental seeds. **Benchmarks that change the plan:** if measured iROAS on a reallocated channel drops below hurdle for two cycles, revert; if a promoted model’s Brier degrades above 0.20, demote to observe-only.

**Thresholds that should change your decisions.** Promote autonomy only at Brier ≤ 0.20 / AUC ≥ 0.72 / stable ≥ 2 cycles; trust incrementality only after refutation passes; treat any channel whose iROAS materially trails its platform-reported ROAS as a reallocation candidate; never activate on a sensitive/denied topic regardless of model confidence.

-----

## Caveats

- **Metric targets are not guarantees.** The 40% CAC / 35% ROAS / 67% ROI figures are MIZ OKI design/benchmark targets and must be labeled (verified / benchmarked / pilot / illustrative) per the platform’s claim-discipline policy. They should be validated per-deployment against a matched control, not asserted.
- **Internal-document coverage.** The internal ground truth was corroborated primarily from the MIZ OKI 3.5 master positioning whitepaper and the Signal Factory demo README in Google Drive. A dedicated, standalone “ORACLE / LII spec,” “cell registry,” and “attribution/causal inference” document were **not** located in Drive during research; the ORACLE cell definitions (Cells 28, 33, 34, 35), the promotion thresholds, and the governance policy in this document are therefore taken from the task’s authoritative platform brief rather than from a separately-versioned internal spec. Reconcile against the canonical cell registry when it is published.
- **Predictions are probabilistic and inferential.** Latent intent, dark-funnel activity, and household rollups are *inferences*, not observations. Probabilistic identity and probabilistic household matching carry false-positive risk; label confidence and prefer deterministic links for high-stakes personalization.
- **Causal estimates depend on design.** X-Learner/DR-Learner and geo/ghost-bid tests rest on assumptions (overlap, correct causal graph, clean control markets, no geographic spillover). DoWhy refuters reduce but do not eliminate this risk — a passing refutation is necessary, not sufficient. Geo tests need adequate markets per arm and pre-periods to be defensible.
- **Benchmarking is external and vendor-sourced.** Competitor and industry figures (6sense, Bombora, Northbeam, Rockerbox, Measured, Salesforce; the ~0.27x branded-search iROAS; the ~1.5–3x reported-vs-measured gap; Gartner’s ~17% supplier-meeting share) are drawn from those vendors’ own materials and third-party analyses and are included to benchmark *language and structure*. They describe the market context, not MIZ OKI’s own verified results, and several originate in vendor marketing content.
- **Availability by channel varies.** Ghost-bid measurement is only possible where the ad platform exposes the necessary auction/would-be-impression logs (largely walled-garden environments); elsewhere, geo or holdout designs are the fallback.
