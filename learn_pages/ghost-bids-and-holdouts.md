---
title: Ghost bids and holdouts, explained
description: A holdout is a pre-registered group that does not receive the treatment; a ghost bid is the bid that would have been placed for a holdout unit, logged instead of placed, so the withheld arm has a free counterfactual. Ghost bids are PROPOSED at MIZ OKI.
last_reviewed: 2026-09-15
owner: MIZ OKI product
expires: 2026-12-01
status_label: PROPOSED
---
## Direct answer

A holdout is a group registered before any exposure that deliberately receives no treatment, so lift can be measured against it. A ghost bid is the bid the system would have placed for a holdout unit, logged instead of placed, giving the withheld arm a counterfactual without paying for placebo ads. Capability label: **[PROPOSED]** — not built for customers.

## Holdouts first

Every incrementality measurement rests on a group that did not get the ad. The rules that make a holdout trustworthy are simple and strict:

- **Registered before the first exposure.** A holdout registered after exposure fabricates the pre-registration it is meant to prove. MIZ OKI refuses activation without a design already in its holdout registry.
- **A declared minimum detectable effect.** The registry requires the MDE at registration; a design without one cannot authorise anything.
- **Deterministic arm assignment from one source.** A caller that can label its own units treatment or holdout can pick the baseline and therefore pick the answer. Only the registry's write-once assignment surface produces a persistable result; caller-supplied arms are marked unverified on every row.
- **Refutation before reporting.** Placebo-treatment, random-common-cause and subset tests must pass. A refutation pass is necessary, not sufficient.

Designs the registry accepts today: randomised, matched-geo, and — as a registrable type awaiting an execution path — ghost bid.

## What a ghost bid is

The design comes from the "Ghost Ads" methodology, which showed that logging the auction moments where a control user *would have* been served identifies the counterfactual far more cheaply than public-service-announcement placebo ads or intent-to-treat comparisons (Johnson, Lewis & Nubbemeyer, Journal of Marketing Research, Dec 2017). MIZ OKI's version: for every unit in a registered design, decide per auction whether a real bid is authorised or a shadow bid is logged, and append an auction row either way — same shape, same fields — so the withheld arm can be compared like for like.

It only works where the buying platform exposes the necessary auction logs; where it does not, geo holdouts are the fallback.

## Status: PROPOSED, and why the label matters

- **[PROPOSED]** for customers. The shadow-execution module exists in the repository, ships behind a flag that is OFF by design, has never run against real ad spend, and is not claimed on any customer-facing surface. It is described here so the term is understood, not sold.
- **[PARTIAL]** Geo and randomised holdouts: the registry and the matched-market engine are built; no customer holdout has been registered yet.
- Every number on this page is a third-party statistic with its source, or a labelled operating parameter. No lift figure here is a MIZ OKI result.

## Why bother

- Ad platforms grade their own attribution while spend keeps growing: US internet advertising revenue reached $258.6B in 2024, up 14.9% (IAB / PwC, Apr 2025). A holdout is the only measurement the platform cannot influence.
- Observational shortcuts drift. Across 15 large-scale Facebook advertising experiments, observational estimates frequently over-stated lift relative to the randomised result (Gordon, Zettelmeyer, Bhargava & Chapsky, Mar 2019).
- Returns undo "conversions": 19.3% of online sales are expected to be returned in 2025 (NRF / Happy Returns, Oct 2025), which is why MIZ OKI measures lift on net yield after the return window, not on order count.
- Budgets cannot absorb waste: marketing budgets averaged 7.7% of company revenue in 2024, down from 9.1% in 2023 (Gartner CMO Spend Survey, May 2024).
- Search itself is shifting under the measurement: traditional search engine volume is forecast to fall 25% by 2026 as AI answer engines absorb queries (Gartner, Feb 2024), so a holdout design that does not depend on any one platform's logs matters more, not less.

## FAQ

### Are ghost bids live at MIZ OKI?

No. Ghost bids are PROPOSED: a shadow-execution module exists behind a flag that ships OFF, has not run against real ad spend, and is not offered to customers. Geo and randomised holdouts are the supported designs today.

### Why not just run a PSA or "intent-to-treat" test?

Placebo ads cost money to show nothing, and intent-to-treat compares everyone eligible whether or not they would have been served, diluting the effect. Ghost bids identify exactly the moments a control user would have seen the ad, at no media cost.

### Can a merchant supply its own holdout list?

It can be evaluated, but not trusted. Only arms assigned by the registry's write-once surface produce a persistable result; a merchant-supplied arm is marked unverified on every row so it can never become the baseline.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Are ghost bids live at MIZ OKI?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. Ghost bids are PROPOSED: a shadow-execution module exists behind a flag that ships OFF, has not run against real ad spend, and is not offered to customers. Geo and randomised holdouts are the supported designs today."
      }
    },
    {
      "@type": "Question",
      "name": "Why not just run a PSA or \"intent-to-treat\" test?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Placebo ads cost money to show nothing, and intent-to-treat compares everyone eligible whether or not they would have been served, diluting the effect. Ghost bids identify exactly the moments a control user would have seen the ad, at no media cost."
      }
    },
    {
      "@type": "Question",
      "name": "Can a merchant supply its own holdout list?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "It can be evaluated, but not trusted. Only arms assigned by the registry's write-once surface produce a persistable result; a merchant-supplied arm is marked unverified on every row so it can never become the baseline."
      }
    }
  ]
}
```
