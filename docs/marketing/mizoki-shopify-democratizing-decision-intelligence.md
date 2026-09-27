# Democratizing Enterprise Decision Intelligence: MIZ OKI 3.5 + Shopify — Governed Autonomous Media Buying on Net Contribution Yield

**Version:** 2.2 (v2.0 was cross-validated against WIRING.md / miz-oki-platform-expert skill v3.0; v2.1 reconciles it against shipped-cell reality, the 2026-08-07 net-yield scaffold, and TRUTH.md binding precedent — corrections listed in the change log at the end)
**Status convention (truth discipline):** Every capability in this document is labeled **[LIVE]** (deployed and verified), **[PARTIAL]** (built behind a feature flag or in MVP form — includes implemented-but-not-deployed scaffolds, so stated), or **[PROPOSED]** (this integration's roadmap — not yet built). External research findings are attributed to their authors, never presented as MIZ OKI results.
**Governance:** Bound by `TRUTH.md`, the five story-bank rules (`signal-story-bank.md`), and the claim ledger in `mizoki-shopify-net-yield-positioning.md` §2. This file is a strategy/positioning source, not a served customer surface; it references removed v1 claims (including the banned "Quokka Swarm" term) solely as removal records. Customer-facing copy derived from it must pass `scripts/content_qa.py`.

---

## 1. Operational Context: The Structural Asymmetry in Digital Commerce

Digital commerce is defined by a systemic imbalance between independent merchants on platforms like Shopify and multi-billion-dollar enterprise retailers. Enterprises command proprietary data infrastructure, quantitative research teams, and custom algorithmic engines that parse market shifts in real time. Independent operators rely on fragmented martech stacks, static CRM databases, and backward-looking dashboards that log historic transactions but cannot model causality, predict customer behavior, or execute real-time adjustments.

The asymmetry is compounded by the auction dynamics of walled-garden ad platforms. Meta and Google operate self-grading attribution: they serve impressions and then credit downstream conversions to their own placements — regardless of whether the ad changed behavior. Brand search and bottom-of-funnel retargeting systematically absorb credit for customers who were already going to convert. Without causal measurement, merchants misallocate capital toward inflated platform-reported ROAS while true unit economics erode under fulfillment and acquisition overhead.

MIZ OKI 3.5 addresses this by replacing static reporting with a governed, living causal graph — and, critically, by measuring advertising on **iROAS with registered holdouts**, never platform-reported ROAS alone. This document specifies how that architecture extends to the Shopify ecosystem.

> **Scope note [updated for v2.1]:** Shopify is not yet a live JourneyEvent connector — current production mappers cover Meta, Google Ads, SendGrid, and OpenRTB. Shopify already touches the platform on two narrower, governed paths: a consent-gated Shopify webhook intent extender (deployed fail-closed pending operator credentials) feeding the LII shadow loop, and the order-economics scaffold in `services/net-yield` (**implemented, not deployed** — no deploy workflow, writeback hard-disabled). Everything else Shopify-specific in this document remains a proposed integration built on live platform primitives; each section labels which is which.

---

## 2. Architectural Foundations

### 2.1 Canonical Event Normalization and Living Graph Memory

**[LIVE]** MIZ OKI 3.5 ingests raw payloads through a single governed gateway. Connector-specific mappers normalize events into the schema-valid, provenance-stamped JourneyEvent envelope (`schemas/journey-event.json`), with `response_schema_hash` and `connector_version` auto-stamped from the live schema so provenance cannot drift. LLM-extracted events must carry a model version issued by the Virtuoso model registry — no hardcoded model strings.

**[LIVE]** Normalized events feed the analytical backbone (the unified BigQuery dataset, `mizoki_unified_data`) and the graph layer — the operating knowledge graph plus the intent graph, both Firestore-backed — modeling the business as nodes and weighted edges rather than disconnected relational tables. The platform evaluates canonical evidence across the graph: why a change occurred, which objectives it affects, and what intervention is optimal.

**[PARTIAL / PROPOSED]** The Shopify extension rides the same envelope discipline — no new envelope is invented. Implemented so far (behind flags, nothing deployed): Shopify orders and refunds priced into an `order_economics` payload block on the Canonical Event Envelope, landing in `mizoki_unified_data.order_economics` via deterministic compare-and-set upsert, with per-tenant cost inputs that fail closed — missing costs are named and excluded from cohort math, never defaulted. Proposed on the same rails: JourneyEvent mappers for store session/journey events, inventory levels, and 3PL fulfillment telemetry, with the same consent and provenance guarantees. Klaviyo joins as an email/flow signal source (its consent-gated intent extender is already deployed fail-closed; the analytics-backbone mapper is proposed).

### 2.2 The SRPVDAL Governance Loop

**[LIVE]** Every autonomous action passes through the seven-phase SRPVDAL loop — the authoritative loop per the JourneyEvent provenance Phase enum (legacy five-phase "SRDAL" references are superseded):

1. **Sense** — canonical events captured across all connected nodes (Cells 1–5, plus Cell 33 for consent-gated behavioral micro-signals)
2. **Reason** — current state interpreted against causal memory and graph relationships
3. **Plan** — intervention candidates generated (budget reallocations, creative rotations, pause/scale actions)
4. **Validate** — statistical, causal, policy, and creepiness gates applied; counterfactual checks against guardrails before anything ships
5. **Decide** — eligibility evaluated against autonomy criteria (below); actions either route to human approval or qualify for direct execution
6. **Act** — execution via secure API calls to connected channels (Cells 19–22)
7. **Learn** — realized outcomes compared to predictions; graph edge weights and model calibration updated (Cells 23–25)

### 2.3 Autonomy Promotion: Earned, Measured, Reversible

**[LIVE]** MIZ OKI's autonomy ladder is not a configuration checkbox — it is a governed mechanism in which execution authority is earned against measurable calibration gates. Stage 3 recommend-only is the fleet-wide default; Stage 4 bounded autonomy is earned per actuator and per (domain, action class), and only with the platform's two-key rule satisfied:

- **Observe-only is the default.** New models, new connectors, and new merchant accounts start with zero spend authority.
- **Promotion criteria:** autonomy is granted only when intent models sustain **Brier score ≤ 0.20**, **AUC ≥ 0.72**, and **stable measured lift across ≥ 2 full purchase cycles** — and only via explicit human approval. Metrics alone never promote.
- **Automatic demotion:** if Brier exceeds 0.20 or population stability drifts, the system reverts to observe-only and an incident is opened.
- **Reversion rule:** two consecutive cycles of below-hurdle iROAS reverts any budget reallocation.

This means a Shopify merchant's risk exposure is bounded by calibration evidence, not by a configuration checkbox. Spend authority is earned per account, per model, per cycle — and revoked the moment calibration degrades.

---

## 3. Governance and Privacy: The Differentiator Enterprises Can't Copy Cheaply

**[LIVE]** This section was absent from v1 and is arguably the strongest competitive positioning available:

- **Hard consent gate (Cell 33):** behavioral micro-signals (dwell, scroll velocity, partial watch) are never persisted without consent scope. No consent → no persistence.
- **No audio, ever:** audio signal types are rejected at schema validation. This is architectural, not policy — and it is the honest answer to the "phones are listening" myth. Behavioral prediction works through legitimate signal inference (co-occurrence, sequence modeling, session trajectories), a fact established in the peer-reviewed literature (Northeastern/UCSB, PETS 2018). MIZ OKI's positioning is built on that truth, not on the myth.
- **Creepiness deny-list:** sensitive topics — health, sexuality, religion, financial distress, minors — are never predicted, stored, or surfaced.
- **GDPR access/erasure:** a single subject-deletion call cascades across the governed stores — BigQuery, the graph, and the vector index.
- **Household edges are recall-only:** probabilistic identity edges are never used in causal measurement.

For a Shopify merchant, this converts privacy from a compliance cost into a sales asset: enterprise-grade prediction with provable restraint.

---

## 4. Solving the E-Commerce Cold Start

### 4.1 What the Research Demonstrates (External, Properly Attributed)

Airbnb's published work on LLM-powered synthetic data generation (Wei et al., arXiv:2605.21812) demonstrates that the cold-start problem — no real queries, no relevance labels — can be bridged by combining **contrastive item pairs** from real sessions with a small set of **seed examples** from user research. Their measured results: unguided contrastive generation produced verbose queries with a KL divergence of 4.95 versus real user behavior; seed-guided generation reduced this to 0.66 (a 7.5× improvement) and achieved an attribute-type KL divergence of 0.04 — lower than the seed data itself. From ~500 seed queries they generated millions of production-scale training examples.

**These are Airbnb's results, not MIZ OKI's.** They matter here because they validate the design pattern MIZ OKI's cold-start roadmap adopts: ground synthetic interactions in real catalog attributes, guide linguistic/behavioral realism with small empirical seeds, and validate distributional fidelity before training on the output.

*(Removed from v1: the "Quokka Swarm Optimization inspector panel" claim, which originated in an unrelated sparse-data recommender paper and has no counterpart in the MIZ OKI stack.)*

### 4.2 MIZ OKI's Cold-Start Path for New Shopify Merchants

**[PARTIAL]** The intent-modeling substrate exists today and runs **live in shadow**: BigQuery ML matrix-factorization and boosted-tree next-topic models with isotonic calibration score real consent-gated data on a scheduled batch cadence (MVP), with a Vertex AI two-tower + Vector Search ANN real-time path behind the `LII_REALTIME` feature flag. Truth discipline requires stating the substrate's honest record: the first ranking gate on an order-anchored corpus **failed** (model cumulative-gain area below the naive-recency baseline on a time-split eval) and stays open until live pre-purchase signals flow — cold-started models remain observe-only, which is exactly what the gates below are for.

**[PROPOSED]** For a new store or SKU with no interaction history, the integration applies the Airbnb-validated pattern:

1. Extract contrastive product pairs from whatever session data exists (or category-adjacent catalog structure for day-one stores)
2. Seed generation with a small set of real search/purchase exemplars from the merchant's vertical
3. Validate synthetic distributions (length, attribute mix, KL vs. observed behavior) before any training run — synthetic data that fails distributional checks is discarded, not "cleaned"
4. Warm-start retrieval towers on validated synthetic graphs, then transition to real interaction data as it accumulates (synthetic data is a bridge, never a permanent substitute)
5. **Gate on calibration, not vibes:** cold-started models remain observe-only until they clear the Brier/AUC/lift criteria in §2.3

This bypasses the multi-week exploration burn standard on major ad platforms — while the autonomy gates ensure no cold-started model spends real money before it has proven calibration.

---

## 5. Intention Graphs: Lessons from Enterprise Architectures

**External context (attributed):** Amazon's COSMO distills common-sense knowledge from behavioral logs, linking implicit actions to natural-language customer goals. The Intention Knowledge Graph work (arXiv:2412.11500) maps hundreds of millions of edges between user intentions across three relation types — **synchronous** (intentions pursued together), **asynchronous** (intentions that follow one another in time), and **causal** (one intention producing another). Google's Knowledge Graph interprets intent beyond literal keywords; Meta maps latent interest through social interaction topology.

**[LIVE]** MIZ OKI's counterpart is the LII intent graph (shipped as Cell 35; plan-vintage documents call it "Cell 34") fed by consent-gated micro-signals (Cell 33) and scored by the Intent Scoring API (shipped as Cell 34; plan-vintage "Cell 28"; p95 < 200 ms is a design target, not a measured production figure): intent stage, predicted interests with probabilities, freshness, and an explanation path for every score. Predictions are written with `realized`/`realized_at` fields so the Learn phase closes the loop on its own accuracy. The intent family runs live in shadow — deployed, IAM-locked, scoring real consent-gated data; activation stays gated per §6.1.

**[PROPOSED]** The Shopify extension maps store session trajectories onto this graph, enabling the platform to anticipate downstream purchase goals and bid on contextual inventory before broader demand inflates auction prices.

| Platform | Architecture | Intent Depth | Edge Types | Strategic Position |
|---|---|---|---|---|
| Legacy e-commerce | Relational / CPV tables | Shallow keyword match | Foreign keys | Simple, cheap, blind |
| Google Knowledge Graph | Semantic entity graph | Deep conceptual | Semantic, spatial, temporal | Dominates query interpretation |
| Meta ads engine | Social behavioral graph | Implicit (lookalike) | Engagement vectors | Consumer scale |
| Amazon COSMO / IKG | Relational intention graph | Deep temporal & causal | Synchronous, asynchronous, causal | Predicts session goals |
| **MIZ OKI 3.5 LII** | **Consent-gated living causal graph (SRPVDAL)** | **Dynamic intent + unit economics** | **Causal, policy, intent, profit-erosion** | **Connects intent reasoning to store P&L — with holdout-gated causality** |

---

## 6. Autonomous Media Acquisition on Causal Truth

### 6.1 Incrementality: Always-On, Registered Before the First Impression

**[LIVE]** The experiment registry (shipped on the intent-causal surface, Cell 36; plan-vintage documents call the registry "Cell 35") enforces that **no LII-driven activation runs without a registered holdout**:

- **Methods:** `ghost_bid` (bid-and-withhold at auction), `geo` (matched-market), or `itt` (intent-to-treat)
- **Design:** holdout percentage of 10–20%, minimum detectable effect declared up front, deterministic-hash arm assignment (customer_id + experiment_id) so ACT cells consult assignment before serving
- **Lift computation:** nightly, lift = CVR(treated) − CVR(holdout) with Wilson/bootstrap confidence intervals
- **Causal credit ledger:** each treated conversion is classified **incremental** (lift CI excludes zero AND the model had not already scored the customer in-market at exposure) versus **anticipated** (would have converted anyway)
- **Validation chain:** registry estimates → X-Learner heterogeneous effects (Cell 26) → DoWhy refutation (Cell 27: placebo treatment, random common cause, data subset). An estimate that fails refutation is flagged and never shipped.
- **Activation path:** the only route from intent score to spend is `uplift_export_cohort` → guardrails → Decision Control Plane. There is no side door.

This is the structural answer to self-grading attribution: budget decisions cite **iROAS and holdout status**, never platform-reported ROAS alone. When Meta claims credit for a brand-search conversion, the ledger says whether that claim survived a counterfactual.

### 6.2 Profit-Aware Bidding: Net Contribution Margin, Not GMV

**[PARTIAL — economics layer implemented, not deployed; activation proposed]** Human ad management optimizes GMV, AOV, or platform ROAS — all of which conceal margin erosion. Industry analysis of Shopify bundle economics (Syncost) shows the failure mode: in apparel and other high-return categories, online return rates run 25–40%, and return freight, restocking labor, and markdown write-offs can reduce a $45 gross margin to a net contribution between −$2 and $16 per order.

The integration therefore bids on **Net Contribution Margin per cohort**, defined explicitly (the formula v1 omitted; implemented in `services/net-yield` compute, which writes `mizoki_unified_data.net_contribution` per order and cohort):

```
Margin_net = Revenue_net − COGS_landed − F_fulfill − F_ship − F_payment − E[R] × C_return − A_spend

where:
  Revenue_net   = gross checkout revenue − discounts − expected refunds
  COGS_landed   = component cost of goods incl. inbound freight & duties
  F_fulfill     = pick/pack and 3PL handling fees
  F_ship        = outbound shipping incl. dimensional-weight penalties
  F_payment     = gateway and processing fees
  E[R]          = expected return rate for the SKU × cohort
  C_return      = per-return cost (return freight + restock labor + markdown loss)
  A_spend       = attributed ad spend for the cohort (incrementality-weighted)
```

Cost inputs are per-tenant configuration and **fail closed**: an order with missing cost components is flagged with the named missing costs and excluded from cohort math — never priced on invented defaults. Expected returns use observed per-SKU return rates only after at least one observed return cycle; before that, computation is actual-only and labeled as such.

**[PARTIAL — writeback stubs hard-disabled; activation proposed]** Net contribution values — not top-line checkout revenue — feed back to platform bidding via Meta server-side CAPI and Google Ads conversion value rules, steering third-party algorithms toward high-margin, low-return cohorts. The payload-construction modules exist behind `NET_YIELD_WRITEBACK=false` (send paths raise until explicit owner enablement, pinned by test); live writeback ships recommend-only first and remains "Preview · in development" until a real pilot writes verified numbers. Inventory and returns data gating promotion — pausing low-stock and high-return SKUs — remains **[PROPOSED]** and would run under the same autonomy gates as every other action.

**[PROPOSED]** Execution cadence targets sub-hourly SRPVDAL cycles for budget reallocation and creative rotation. (v1's "15-minute cycles" figure is a design target, not a measured production characteristic — labeled accordingly until benchmarked.)

### 6.3 Capability Comparison

| Category | Manual agency | Rule-based tools | MIZ OKI 3.5 + Shopify |
|---|---|---|---|
| Optimization target | Reported ROAS / gross revenue | Platform ROAS / target CPA | Net Contribution Margin per cohort **[PROPOSED]** |
| Measurement | Platform last-touch | API-reported conversions | Registered holdouts, iROAS, causal credit ledger **[LIVE]** |
| Cold start | Manual guesswork | Static rules | Seed-guided synthetic graphs, calibration-gated **[PROPOSED]**, on live-in-shadow LII substrate **[PARTIAL]** |
| COGS/logistics | Disconnected | Static margin % | Dynamic component COGS + return modeling **[PARTIAL — implemented, not deployed]** |
| Risk control | Human error | Spend caps | Observe-only default; Brier/AUC/lift promotion gates; auto-demotion **[LIVE]** |
| Privacy posture | Undefined | Undefined | Consent gate, no-audio, deny-list, GDPR cascade **[LIVE]** |

---

## 7. Implementation Roadmap

1. **Phase 1 — Connectors:** Shopify + Klaviyo JourneyEvent mappers (orders, COGS, inventory, returns, flows) on the existing envelope; consent scope wired end-to-end. The consent-gated Shopify and Klaviyo intent extenders are already deployed fail-closed (signal side); the analytics-backbone mappers are the open work. Acceptance: schema-valid events with provenance stamps in `mizoki_unified_data.*`.
2. **Phase 2 — Economics layer:** landed-COGS and returns model per SKU; Margin_net computable per cohort in BigQuery. Scaffold implemented 2026-08-07 (`services/net-yield`: DDL, fail-closed cost config, mapper, nightly compute, yield API — tested, not deployed). Acceptance: reconciliation against merchant P&L within agreed tolerance.
3. **Phase 3 — Measurement first:** register holdouts on existing campaigns before any automation; establish iROAS baselines. Acceptance: causal credit ledger populated; ≥1 purchase cycle of lift data.
4. **Phase 4 — Observe-only intent:** LII scoring on store sessions; no activation. Acceptance: Brier ≤ 0.20, AUC ≥ 0.72 sustained.
5. **Phase 5 — Gated activation:** Margin_net value feeds to CAPI/conversion value rules (stubs exist, hard-disabled behind `NET_YIELD_WRITEBACK=false`); budget reallocation under SRPVDAL with reversion rules armed. Requires explicit owner enablement. Acceptance: iROAS above hurdle across 2 cycles; auto-revert verified in test.

Every phase ships with its acceptance test; no phase is marketed as live before its acceptance test passes. That is the discipline that separates this document from the category it competes in.

---

## References

1. Wei, W.R. et al. (2026). *Bridging the Cold-Start Gap: LLM-Powered Synthetic Data Generation for Natural Language Search at Airbnb.* arXiv:2605.21812. — Source of all KL-divergence and seed-guidance results cited in §4.1.
2. Bai, J. et al. (2024). *Intention Knowledge Graph Construction for User Intention Relation Modeling.* arXiv:2412.11500. — Synchronous/asynchronous/causal intention relations, §5.
3. Amazon Science. *COSMO: A large-scale e-commerce common sense knowledge generation and serving system at Amazon.* — §5.
4. Syncost. *The Bundle & Kit Profit Distortion: Shopify Product Analytics.* — Return-economics figures, §6.2.
5. MIZ OKI platform ground truth: WIRING.md §9 and miz-oki-platform-expert skill v3.0 (SRPVDAL loop; shipped intent family Cells 33–36 with plan-vintage numbering 28/34/35 annotated; analytical Cells 26/27; holdout registry, causal credit ledger, autonomy gates, governance rules), reconciled with README.md v6.45.46 shadow-live status and the `services/net-yield` scaffold (2026-08-07).
6. Ren, J. et al. (2018). *Panoptispy / audio exfiltration study*, Proceedings on Privacy Enhancing Technologies (Northeastern/UCSB). — Basis for the no-eavesdropping positioning, §3.

*(Removed from v1's reference list: duplicate entries, circular citations to mizoki3.com used as evidence for claims about mizoki3, a competitor pricing blog cited but never used, and the sparse-data recommender paper whose methods were misattributed to the platform.)*

---

## Change log

- **v2.2 (2026-08-09):** Neo4j references removed. Owner decision 2026-08-09 retired Neo4j; Firestore is the knowledge-graph backend and the Aura host stays unresolvable by choice, so a doc naming Neo4j as the backend is wrong rather than merely stale. §2.1, §3 (erasure cascade) and §5 (intent graph) now name the store layer without pinning a vendor.
- **v2.1 (2026-08-07):** Reconciled against the repository's shipped reality. Cell references corrected to shipped numbering with plan-vintage annotations (Intent Scoring API = Cell 34, intent graph = Cell 35, causal/registry surface = Cell 36; Cell 28 remains a legacy cell — it was never repurposed). p95 < 200 ms explicitly labeled a design target. Autonomy section rewritten to name the real governed autonomy ladder (Stage 3 recommend-only default, two-key rule) and the explicit-human-approval requirement for promotion. Dataset references corrected from `unified.*` to `mizoki_unified_data.*`. Scope note, §2.1, §6.2, §6.3, and the roadmap updated for the implemented-not-deployed net-yield scaffold (order-economics on the Canonical Event Envelope payload; `NET_YIELD_WRITEBACK=false`) and the fail-closed Shopify/Klaviyo intent extenders. §4.2 now records the honest Phase-A ranking-gate failure per TRUTH.md binding precedent. §5 table wording softened from "holdout-proven" to "holdout-gated" (proof claims require refutation-passing experiments). Added the DCP-gated activation path to §6.1.
- **v2.0:** Cross-validated against WIRING.md / miz-oki-platform-expert skill v3.0; removed v1's misattributed and fabricated claims (see strikethrough notes in §4.1 and the reference list).
