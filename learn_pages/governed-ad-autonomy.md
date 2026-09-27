---
title: What is governed ad autonomy?
description: Governed ad autonomy is advertising automation whose authority is earned per action class on an L0–L5 ladder, with fixed promotion gates, a human promotion decision and automatic demotion — never a global switch.
last_reviewed: 2026-09-02
owner: MIZ OKI product
expires: 2026-12-01
status_label: PARTIAL
---
## Direct answer

Governed ad autonomy is advertising automation whose authority is earned, bounded and revocable per action class. Each class climbs an L0 (observe) to L5 ladder only after fixed calibration gates are met and a human approves; authority contracts automatically when calibration degrades. Capability label: **[PARTIAL]** — the shipped code expresses two stages of that ladder.

## Why "governed" is the operative word

Platform automation is now the default way ad money is spent. US internet advertising revenue reached $258.6B in 2024, up 14.9% year over year (IAB / PwC, Apr 2025), after $225.0B in 2023 (IAB / PwC, Apr 2024). At the same time the budgets funding that spend are under pressure: marketing budgets averaged 7.7% of company revenue in 2024, down from 9.1% in 2023 (Gartner CMO Spend Survey, May 2024), and held at 7.7% in 2025 (Gartner CMO Spend Survey, May 2025).

Autonomy is arriving faster than governance. Gartner forecasts that by 2028, 15% of day-to-day work decisions will be made autonomously through agentic AI, up from 0% in 2024 (Gartner, Oct 2024) — and also that over 40% of agentic AI projects will be cancelled by the end of 2027, largely for unclear value and inadequate risk controls (Gartner, Jun 2025). Governed autonomy is the answer to the second forecast: authority that can be shown, bounded, and taken back.

## The ladder

MIZ OKI describes autonomy as a ladder from **L0 (observe only)** to **L5 (bounded autonomous)**, evaluated **per (account × action class)** — budget reallocation within clamps, bid changes, audience activation and creative rotation are separate classes with separate authority. Nothing is a global switch.

- **Promotion is gated, not scheduled.** A class may be promoted only when the model feeding it meets the fixed gates — Brier ≤ 0.20, AUC ≥ 0.72, and stable measured lift across at least two purchase cycles — and only by a human decision. See [Brier and AUC promotion gates](/learn/brier-auc-promotion-gates).
- **Demotion is mechanical.** Calibration drift (Brier above 0.20), consent-drop spikes, refutation failures or volatility shocks tighten clamps and demote toward L0/L1 automatically. Contraction never needs a meeting; expansion always does.
- **Authority is proportional to margin.** Above the Decision Eligibility floor, a barely-cleared score earns only the smallest reversible version of an action. See [DEL Score](/learn/del-score).
- **Every action leaves a trace.** Each governed decision carries a [ValidationPassport](/learn/validation-passport) and passes the [Decision Control Plane](/learn/decision-control-plane).

## What is shipped today — honestly

- **[PARTIAL]** The shipped policy engine expresses two stages of the ladder in code — a recommend-only stage and a bounded-autonomy stage — and promotion between them is a manual, human-issued request. The six-level L0–L5 vocabulary is the canonical description; the code cannot yet express every rung.
- **[IN BUILD]** The promotion-gate evaluator (Brier / AUC / stability) exists observe-only and is deliberately not wired to promotion; promotion stays a human act by policy.
- **[PARTIAL]** The measurement writebacks that would let the system grade its own actions are held OFF by tests that fail if the default flips. Prediction never grades itself.
- **[PROPOSED]** Ghost bids as a holdout mechanism. See [Ghost bids and holdouts](/learn/ghost-bids-and-holdouts).

## What governed autonomy is not

It is not a promise of outcomes: no figure on this page is a MIZ OKI result, and every business figure the platform publishes is a design target until a benchmark or pilot artifact exists. It is not cross-merchant coordination: the platform never coordinates bids, budgets or pacing across merchants — each tenant's decisions run inside its own account. And it is not mind-reading: the positioning is anticipatory intent with proof of causal lift.

## FAQ

### Is governed ad autonomy the same as Smart Bidding or Advantage+?

No. Platform automation optimises inside one platform's auction toward that platform's attribution. Governed autonomy sits above the platforms, is measured on incremental return (iROAS) rather than platform ROAS, and can only act within authority a human granted per action class.

### Can a merchant turn autonomy up?

A merchant can raise thresholds and tighten clamps at any time. A merchant cannot lower platform floors, skip the calibration gates, or promote a class without the human decision the ladder requires. Safety is not configurable downward.

### What happens when the model gets worse?

Demotion is automatic: a promoted class whose calibration degrades past Brier 0.20 returns to observe-only without waiting for a review, and its clamps tighten. Re-promotion requires the gates to be met again.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Is governed ad autonomy the same as Smart Bidding or Advantage+?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. Platform automation optimises inside one platform's auction toward that platform's attribution. Governed autonomy sits above the platforms, is measured on incremental return (iROAS) rather than platform ROAS, and can only act within authority a human granted per action class."
      }
    },
    {
      "@type": "Question",
      "name": "Can a merchant turn autonomy up?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "A merchant can raise thresholds and tighten clamps at any time. A merchant cannot lower platform floors, skip the calibration gates, or promote a class without the human decision the ladder requires. Safety is not configurable downward."
      }
    },
    {
      "@type": "Question",
      "name": "What happens when the model gets worse?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Demotion is automatic: a promoted class whose calibration degrades past Brier 0.20 returns to observe-only without waiting for a review, and its clamps tighten. Re-promotion requires the gates to be met again."
      }
    }
  ]
}
```
