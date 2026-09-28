---
title: Incrementality vs platform ROAS
description: Platform ROAS credits any conversion that followed an exposure; incremental ROAS (iROAS) counts only the revenue an experiment shows the ads caused. MIZ OKI drives budget decisions with iROAS, never platform ROAS.
last_reviewed: 2026-09-15
owner: MIZ OKI product
expires: 2026-12-01
status_label: PARTIAL
---
## Direct answer

Platform ROAS divides all conversions that followed an ad exposure by spend, so it credits sales that would have happened anyway. Incremental ROAS (iROAS) divides only the net-new revenue an experiment shows the ads caused. MIZ OKI drives DECIDE with iROAS, never platform ROAS. Capability label: **[PARTIAL]** — the ledger exists; population needs a registered holdout.

## The difference, in one sentence

Platform attribution answers "what happened after the ad"; incrementality answers "what would not have happened without it". The gap between the two is not a rounding error. Across 15 large-scale Facebook advertising experiments, observational methods frequently over-estimated lift relative to the randomised result, sometimes by a wide margin (Gordon, Zettelmeyer, Bhargava & Chapsky, Mar 2019).

Brand search and retargeting are where the gap is widest, because the audience was already on its way. When iROAS on those lines comes in far below platform ROAS, that is the measurement working, not failing.

## Why it matters more now

- Spend keeps growing on platforms that grade their own homework. US internet advertising revenue reached $258.6B in 2024, up 14.9% (IAB / PwC, Apr 2025); Google Search & other revenue alone was $198.1B in 2024 (Alphabet, Feb 2025), and Amazon's advertising services revenue was $56.2B in 2024 (Amazon, Feb 2025).
- Budgets are not growing with it: marketing budgets averaged 7.7% of company revenue in 2024, down from 9.1% the year before (Gartner CMO Spend Survey, May 2024). A flat budget cannot afford to pay for conversions it would have received anyway.
- Returns erase "conversions" after the fact. 19.3% of online sales are expected to be returned in 2025 (NRF / Happy Returns, Oct 2025), on top of US retail returns projected at $890B for 2024 (NRF / Happy Returns, Dec 2024). Revenue-side attribution counts an order; net-yield measurement counts what survived the return window.

## How MIZ OKI measures it

1. **A holdout is registered before the first exposure.** Randomised, matched-geo or (proposed) ghost-bid designs are registered in the holdout registry with a pre-declared minimum detectable effect. No activation may start without one; the rule is enforced in code, not in a policy document.
2. **Uplift is estimated, then refuted.** Meta-learners estimate who was persuadable; refutation tests (placebo treatment, random common cause, data subsets) must pass before a lift is reported. A refutation pass is necessary, not sufficient.
3. **Every conversion is classified "caused" or "anticipated"** in an immutable causal credit ledger, with confidence intervals — never a bare point estimate.
4. **DECIDE reads iROAS from that ledger.** Budget reallocation is gated on measured incremental return, and the rule that reverts a promotion when iROAS falls below hurdle for two cycles is part of the same machinery.

## What is shipped today — honestly

- **[PARTIAL]** The holdout registry (randomised, ghost-bid and matched-geo designs, deterministic arm assignment, registration mandatory before activation) is built. No customer holdout has been registered yet, so the ledger holds no customer causal credit.
- **[PARTIAL]** Geo holdouts: the matched-market engine is built and a pilot is armed under per-action human approval.
- **[PARTIAL]** The causal credit ledger architecture is live; population requires real holdout data.
- **[PROPOSED]** Ghost bids as a holdout type. See [Ghost bids and holdouts](/learn/ghost-bids-and-holdouts).
- No iROAS figure on this page is a MIZ OKI result. Published business figures are design targets until a benchmark or pilot artifact exists.

## FAQ

### Is a lower iROAS than platform ROAS a bad sign?

Usually not. On brand search and retargeting a much lower iROAS is expected, because most of those buyers were already converting. The comparison tells you where spend is buying attribution rather than revenue.

### Can incrementality be measured without a holdout?

Not credibly. Every method that skips a withheld group — last-click, data-driven attribution, media-mix regressions on their own — has to assume what would have happened. A registered holdout replaces the assumption with an observation.

### Does MIZ OKI ever use platform ROAS?

Platform figures are ingested as inputs and shown for context. They never drive a budget decision; DECIDE reads iROAS from the causal credit ledger.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Is a lower iROAS than platform ROAS a bad sign?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Usually not. On brand search and retargeting a much lower iROAS is expected, because most of those buyers were already converting. The comparison tells you where spend is buying attribution rather than revenue."
      }
    },
    {
      "@type": "Question",
      "name": "Can incrementality be measured without a holdout?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Not credibly. Every method that skips a withheld group — last-click, data-driven attribution, media-mix regressions on their own — has to assume what would have happened. A registered holdout replaces the assumption with an observation."
      }
    },
    {
      "@type": "Question",
      "name": "Does MIZ OKI ever use platform ROAS?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Platform figures are ingested as inputs and shown for context. They never drive a budget decision; DECIDE reads iROAS from the causal credit ledger."
      }
    }
  ]
}
```
