---
title: What is a DEL Score?
description: The DEL (Decision Eligibility Level) Score is a 0–100 measure of how much evidence stands behind a proposed action. Below the platform floor of 80.0 the action is refused; above it, authority grows with the margin and is capped. Floors can be raised, never lowered.
last_reviewed: 2026-09-15
owner: MIZ OKI product
expires: 2026-12-01
status_label: PARTIAL
---
## Direct answer

The DEL Score — Decision Eligibility Level — is a 0–100 number summarising the evidence behind a proposed action: validation pass rate, evidence completeness and verification weight. Below the platform floor of DEL ≥ 80.0 the action is refused outright; above it, authority grows with the margin and saturates at a cap. Floors can only be raised. Capability label: **[PARTIAL]**.

## The idea in one line

Authority should be a function of evidence, deterministic, and flat zero below a floor. The canonical form is a clipped rectified-linear function per action class *c*:

```
authority_c = min(cap_c, max(0, DEL_score − threshold_c))
```

- **Flat zero below the threshold** — deterministic denial. No partial execution, no probabilistic leakage. A refused proposal goes to a human with its reasoning path and a smaller alternative.
- **Margin-proportional above it** — a barely-cleared score earns only the smallest reversible version of the action.
- **Saturation at the cap** — the covenant cap bounds authority regardless of margin.
- **Guardrail envelopes shift the threshold up** under volatility; they never lower a floor.

## Where the score comes from

The shipped policy engine computes the score from three inputs the [ValidationPassport](/learn/validation-passport) and the evidence bundle supply — the validation pass rate, evidence completeness and verification weight — as a weighted average scaled to 0–100, then compares it to the domain's threshold, which defaults to the platform floor of 80.0. Domains may set a higher bar (several run at 90); a conformance check fails the build if any domain's threshold sits below the floor. The [Decision Control Plane](/learn/decision-control-plane) signs the resulting authorisation.

## Why floors are not merchant-configurable downward

Merchants may raise thresholds and tighten caps through their covenant; they may never lower them below platform floors. The reasoning is the same one that keeps promotion gates fixed (see [Brier and AUC promotion gates](/learn/brier-auc-promotion-gates)): safety that can be dialled down under quarter-end pressure is not safety.

The pressure is real. Marketing budgets averaged 7.7% of company revenue in 2024, down from 9.1% in 2023 (Gartner CMO Spend Survey, May 2024), and held at 7.7% in 2025 (Gartner CMO Spend Survey, May 2025), while US internet advertising revenue reached $258.6B in 2024, up 14.9% (IAB / PwC, Apr 2025). A rule that lets a thin evidence base authorise a large action is how a flat budget buys attribution instead of revenue. Add returns — 19.3% of online sales are expected to be returned in 2025 (NRF / Happy Returns, Oct 2025) — and the case for an evidence floor that includes net-yield inputs writes itself. And as traditional search engine volume is forecast to fall 25% by 2026 (Gartner, Feb 2024), the evidence behind any search-side action will be thinner, not thicker.

## What is shipped today — honestly

- **[PARTIAL]** The score, the 80.0 floor, per-domain raise-only thresholds, the conformance check and signed authorisation are built and deployed.
- **[PARTIAL]** The shipped formula is a weighted linear average; the canonical description is the clipped-ReLU authority function above. The concept — threshold-gated, margin-proportional authority — is present in code; the activation-function shape differs, and the gap is recorded in the coverage matrix as a build item.
- **[ROADMAP]** Per-action-class parameterisation (a distinct threshold and cap per class) remains to be built; today the threshold is per domain.
- No DEL value on this page is a customer result; the worked narrative the platform uses to illustrate a DEL below the floor is labelled an illustrative scenario wherever it appears.

## FAQ

### What is a good DEL Score?

Any score at or above the platform floor of 80.0 is eligible; higher margin earns proportionally more authority up to the class cap. Below 80.0 the action is refused, and no configuration can change that floor downward.

### Can two identical proposals get different DEL Scores?

No. The score is a deterministic function of the passport pass rate, evidence completeness and verification weight. Same inputs, same score, same decision.

### Does a high DEL Score mean the action will work?

No. DEL measures how much validated evidence stands behind an action, not its outcome. Whether it worked is measured afterwards against a registered holdout and recorded in the causal credit ledger.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is a good DEL Score?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Any score at or above the platform floor of 80.0 is eligible; higher margin earns proportionally more authority up to the class cap. Below 80.0 the action is refused, and no configuration can change that floor downward."
      }
    },
    {
      "@type": "Question",
      "name": "Can two identical proposals get different DEL Scores?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. The score is a deterministic function of the passport pass rate, evidence completeness and verification weight. Same inputs, same score, same decision."
      }
    },
    {
      "@type": "Question",
      "name": "Does a high DEL Score mean the action will work?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. DEL measures how much validated evidence stands behind an action, not its outcome. Whether it worked is measured afterwards against a registered holdout and recorded in the causal credit ledger."
      }
    }
  ]
}
```
