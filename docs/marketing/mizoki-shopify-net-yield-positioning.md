# MIZOKI 3.5 × Shopify — Net Contribution Yield: Positioning & Spiel Integration v1.0
*Incorporates the Shopify/decision-intelligence techniques into the media-acquisition narrative, with claim discipline enforced.*

## 1. What this adds to the offering (ranked by commercial impact)

**A. Profit-aware bidding — the category changer.** Optimization target shifts from platform ROAS (or even iROAS) to **Net Contribution Margin per cohort**: revenue minus component COGS, pick-and-pack, shipping dim-weight, payment fees, and reverse logistics. Mechanism: feed net-contribution values (not checkout revenue) back through Meta CAPI and Google Conversion Value Rules, steering the platforms' own bidders toward high-margin, low-return cohorts. Buildable on existing connectors (Shopify + Google Ads + Meta). This is the wedge: returns of 25–40% in apparel routinely turn a "winning" campaign into a losing one, and no dashboard the merchant owns can see it.

**B. Cold-start seeding — the "new store" answer.** Contrastive, seed-guided synthetic interaction data warm-starts the two-tower retrieval/ranking stack for new stores and new SKUs, replacing weeks of expensive platform "learning phase." Approach follows published work by Airbnb (LLM synthetic search data) and standard two-tower practice. Sales value: kills the "we don't have enough data for you" objection on day one.

**C. Intention graphs (COSMO/RIG-style) — deepens ORACLE.** Session trajectories mapped to intention nodes with asynchronous/synchronous/causal edges — this slots directly into Cell 35's intent-graph design (SHOWED_INTEREST / PRECEDES; corrected 2026-08-19 — plan-vintage copy said "Cell 34"/Neo4j, and the graph is Firestore-backed since the 2026-08-09 Neo4j retirement) and strengthens the §Preview story. Same status as ORACLE: preview.

**D. The Shopify asymmetry frame — the emotional spine.** "Enterprise platforms have quant departments; you have dashboards that grade their own homework." This is the villain the whole spiel needed.

## 2. Claim ledger (enforce in ALL copy — extends content_qa rules)

| Claim | Status | How to say it |
|---|---|---|
| Caused-vs-anticipated ledger, holdouts, geo | Core design; demo live | Present tense, illustrative numbers |
| Ghost bids | **Registration shipped; execution path in development** | "In development" — never "on your spend". No live ghost-bid experiment has run against real ad spend (BUILD_DEBT GB-1) |
| SRPVDAL 7-stage, DEL score, autonomy ladder | Live platform | Present tense |
| Net-contribution bidding via CAPI / Value Rules | **Buildable now — not yet shipped** | "In development · preview" until first pilot |
| 15-minute autonomous cycles; <1s streaming | Design targets | Label as design targets, never observed performance |
| Cold-start synthetic seeding | Design, research-backed | "Our approach follows published work by Airbnb/Amazon" |
| KL divergence 4.95→0.66 / 0.04 | **Airbnb's published results — NOT ours** | Cite as research context only; NEVER as Mizoki performance |
| "Quokka Swarm Optimization" inspector | Unverified novelty | Do not use until validated; say "uncertainty-based validation" |
| 25–40% return rates in apparel | Industry statistic | Cite as industry data, not customer result |
| Intention graph (IGC-RC / COSMO-style) | ORACLE preview scope | Preview framing, married to the ledger rule |

**Banned:** presenting any table row above its status; the Airbnb numbers as ours; "autonomous profit machine" without the autonomy-ladder caveat (starts L0/L1, spend authority earned over ≥2 purchase cycles).

## 3. The upgraded spiel

**One-liner:** *Other tools optimize the number your ad platform reports. Mizoki optimizes the number your bank account reports.*

**60-second version:** "Shopify merchants are competing against enterprises with quant departments, armed with dashboards that grade their own homework. Mizoki closes that gap in three moves. First, **prove**: we run the actual experiment — holdouts and matched cities — so you know which conversions your spend caused and which were coming anyway. Second, **profit**: we plug your real economics into the bidding loop — landed COGS, pick-and-pack, shipping, and the returns that quietly turn winning campaigns into losing ones — so the ad platforms optimize toward your net contribution, not your top line. Third, **anticipate** (in preview): an intention graph in the style of Amazon's COSMO reads where a shopper is heading before they say it — and by house rule, a prediction never claims credit without an experiment behind it. All of it runs on one governed loop that starts in observe-only and earns spend authority the way you'd let a new hire earn it."

**The three-beat structure for every surface:** PROVE → PROFIT → ANTICIPATE (preview). Profit moved to slot two deliberately: for SMB Shopify it converts harder than intent.

## 4. New stories for the bank (v1.1 additions — same rules, same grammar)

### Story 7 — The Bundle That Lost Money (net yield)
**Question:** "Our $180 bundle is our best seller. Why is cash down while revenue is up?"
**The test:** Signal priced every order at what it truly nets — components, packing, dim-weight shipping, fees, and the returns coming back.
**The ledger:** The hero bundle netted between −$2 and $16 an order after a third of them came back. The 'boring' single SKU netted $31 and almost never returned.
**The change:** The bidding signal switched from checkout revenue to net contribution. Platforms started hunting buyers who keep what they buy. Revenue flattened; cash grew.
**Verdict line:** *The dashboard applauded the bundle. The bank account preferred the boring one.*
**Status label:** composite scenario · net-yield capability in preview.

### Story 8 — Day One (cold start)
**Question:** "We just launched. Every tool says 'come back when you have data.'"
**The test:** Instead of waiting, Mizoki seeded the targeting models with statistically realistic synthetic shoppers built from the catalog itself — an approach drawn from published enterprise research — then let real signals take over as they arrived.
**The ledger:** The expensive multi-week platform learning phase compressed; early spend went to plausible buyers, not random exploration.
**The change:** The store's first ad dollar had a hypothesis behind it.
**Verdict line:** *New stores don't lack intelligence. They lack history — and history can be scaffolded.*
**Status label:** composite scenario · preview capability · research-backed approach (Airbnb/Amazon), results not yet claimed as ours.

## 5. Ecosystem integration checklist
1. **Story bank → v1.1:** append Stories 7–8; update placement map (Story 7 leads all Shopify-audience surfaces).
2. **signal.html:** add a "Net contribution, not top line" card to the roadmap/preview section (§ with the intent preview), same Preview tag; content_qa gains the claim-ledger bans above.
3. **Shopify app listing / partner copy:** lead with the one-liner + Story 7; asymmetry frame in the opening paragraph.
4. **Executive briefing:** insert PROVE → PROFIT → ANTICIPATE as the act structure (supersedes waste → defense → trust; those stories slot inside the acts).
5. **Build backlog (for a future Claude Code prompt):** Net Yield service = extension of Cell 35 + Financial cell — ingest Shopify COGS/refunds + 3PL costs into the canonical envelope; nightly net-contribution per order/cohort; CAPI + Value Rules writeback behind the autonomy ladder (L1 recommend first). Cold-start seeding = pre-phase of ORACLE Phase 1. Do NOT market as live until these ship.
6. **Skillpack/skill v3.1 (after build):** add net-yield tools and the claim ledger to §9 claim discipline.

## 6. How much better? (honest scorecard)
- **Category:** analytics/measurement → governed profit engine. Step change.
- **ICP fit:** the Shopify merchant now has a reason to buy that a CFO signs off in one sentence.
- **Competitive:** measurement vendors can't execute; execution tools can't prove; neither sees COGS/returns. The trifecta is defensible.
- **Risk if mislabeled:** the whole "proof, not attribution theatre" brand collapses the first time a claimed number turns out to be Airbnb's. The claim ledger above is what keeps the upgrade an asset instead of a liability.
