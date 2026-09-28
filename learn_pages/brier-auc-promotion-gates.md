---
title: Brier and AUC promotion gates
description: Before any action class may be promoted past observe-only, its model must show calibration (Brier ≤ 0.20), ranking power (AUC ≥ 0.72) and stable measured lift across at least two purchase cycles — and a human must decide. The evaluator is IN BUILD, observe-only.
last_reviewed: 2026-09-15
owner: MIZ OKI product
expires: 2026-12-01
status_label: IN BUILD
---
## Direct answer

Promotion gates are the fixed calibration thresholds a model must meet before the action class it feeds can leave observe-only: Brier score ≤ 0.20, AUC ≥ 0.72, and stable measured lift across at least two purchase cycles, evaluated per (account × action class). A human makes the promotion decision. Capability label: **[IN BUILD]** — the evaluator exists observe-only.

## Two halves of "trustworthy"

A probability is useful only if it is both **discriminating** and **calibrated**. The two gates measure the two halves:

- **AUC (area under the ROC curve)** — the probability that a true converter is ranked above a non-converter. AUC 0.72 means the model orders people meaningfully better than chance; 0.50 is a coin flip.
- **Brier score** — the mean squared distance between predicted probability and outcome, a proper scoring rule first proposed for weather forecasts (Brier, Monthly Weather Review, Jan 1950). Brier ≤ 0.20 means a predicted 0.70 is right about seven times in ten. A model can rank well and still be badly calibrated, which is why both gates exist.
- **Stable lift across ≥ 2 purchase cycles** — measured against a registered holdout on that class's own decision stream, so the gate cannot be passed on a single lucky window or on another class's data.

A flattering number ships with its deflating context: an early evaluation recorded near-zero Brier and calibration error together with the caveat that both are near-trivial at a base rate of a few conversions per ten thousand. The gates are read with base rate attached, always.

## Why fixed gates instead of judgement

Automation is being adopted faster than it is being validated. Gartner expects at least 30% of generative AI projects to be abandoned after proof of concept by the end of 2025, with poor data quality and inadequate risk controls among the causes (Gartner, Jul 2024), and expects over 40% of agentic AI projects to be cancelled by the end of 2027 (Gartner, Jun 2025). Meanwhile 78% of organisations already use AI in at least one business function (McKinsey, Mar 2025), and by 2028, 33% of enterprise software applications will include agentic AI, up from less than 1% in 2024 (Gartner, Jun 2025).

Fixed gates turn "is the model good enough to act?" from an opinion into a measurement that either passes or fails. The thresholds are pinned in the metric contracts and the certification evaluator's source, not in a settings screen: no operator can lower them, and a merchant can only raise a domain's bar above the platform floor.

## The rules around the gates

- **Human promotion, mechanical demotion.** Meeting the gates makes a class *eligible*; a named human promotes it. If Brier rises above 0.20 after promotion, the class returns to observe-only automatically.
- **Per action class.** Certification is granted for one action class in one account. It never transfers to another class and is never a global switch.
- **Prediction never grades itself.** The outcome that scores a prediction comes from the causal credit ledger fed by a registered holdout, never from the predicting model's own attribution.
- **No metric-chasing.** A failed gate is recorded as failed. Binding precedent: an intent model's ranking gate failed against a naive baseline on a time-split evaluation, three attempts were made under a constant protocol, and the gate stays open until real forward labels flow — no synthetic positives, no baseline weakening.

## What is shipped today — honestly

- **[IN BUILD]** The certification evaluator (Brier / AUC / stability, never-auto-upgrade policy) is built observe-only and is deliberately not wired to promotion.
- **[PARTIAL]** Promotion is a manual, human-issued request between the two autonomy stages the shipped code expresses.
- Real evaluations remain blocked on real forward labels: the intent model's gate has not been passed on production data, and no page on this site claims otherwise. The figures above are third-party statistics or code-pinned thresholds — none is a MIZ OKI performance result.

## FAQ

### Why 0.20 and 0.72 rather than some other numbers?

They are the platform's code-pinned floors, chosen so that a promoted class is both usefully discriminating and honestly calibrated. Domains may raise their bar above them; nothing may lower it.

### Does passing the gates promote a class automatically?

No. Passing makes the class eligible; a human decides. Demotion, by contrast, is automatic when calibration degrades.

### What data are the gates evaluated on?

Forward labels from that class's own decision stream, with outcomes scored from a registered holdout via the causal credit ledger. Synthetic or fixture data can never pass a gate.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Why 0.20 and 0.72 rather than some other numbers?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "They are the platform's code-pinned floors, chosen so that a promoted class is both usefully discriminating and honestly calibrated. Domains may raise their bar above them; nothing may lower it."
      }
    },
    {
      "@type": "Question",
      "name": "Does passing the gates promote a class automatically?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. Passing makes the class eligible; a human decides. Demotion, by contrast, is automatic when calibration degrades."
      }
    },
    {
      "@type": "Question",
      "name": "What data are the gates evaluated on?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Forward labels from that class's own decision stream, with outcomes scored from a registered holdout via the causal credit ledger. Synthetic or fixture data can never pass a gate."
      }
    }
  ]
}
```
