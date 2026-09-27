---
title: What is a Decision Control Plane?
description: The Decision Control Plane is the deterministic service through which every governed action must pass — identity, policy, context-sufficiency and hard-constraint gates in fixed order — before any actuator may execute it. Agents propose; the control plane authorises.
last_reviewed: 2026-09-02
owner: MIZ OKI product
expires: 2026-12-01
status_label: PARTIAL
---
## Direct answer

A Decision Control Plane is the single deterministic service every governed action must pass through before execution. Agents and models only propose; the control plane checks identity, policy, context sufficiency and hard constraints in fixed order, signs an authorisation or refuses, and is the only path to an actuator. Capability label: **[PARTIAL]** — deployed, with a documented formula gap.

## Why a control plane, not a prompt

Agents are being handed authority quickly. Gartner forecasts that by 2028, 15% of day-to-day work decisions will be made autonomously through agentic AI, up from 0% in 2024 (Gartner, Oct 2024); McKinsey found 62% of organisations at least experimenting with AI agents and 23% scaling one somewhere in the enterprise (McKinsey, Nov 2025). The same research bodies expect much of it to fail on controls: over 40% of agentic AI projects are forecast to be cancelled by the end of 2027 (Gartner, Jun 2025).

The failure mode is structural. A negotiating agent can be persuaded; a probabilistic model can be wrong with confidence. Money should not move on either. The control plane is the place where "the agent thinks this is a good idea" becomes "this exact action, by this actor, is inside the authority that exists" — or does not.

## The four gates, in order

Every governed action passes four deterministic gates. A failure at any gate is a refusal, never a downgrade to a smaller version of the same action.

1. **Identity and signature.** The actor and the authorisation are authenticated, and the grant is bound to the exact action — not to a class of actions, not to a session.
2. **Policy alignment.** Corporate policy, role-based access and regulatory exposure are checked against the declared, hash-versioned policy.
3. **Context sufficiency.** Data lineage, freshness and confidence must meet the floor. Stale or unsourced inputs stop here.
4. **Hard-constraint / fiduciary floor.** Forbidden-autonomy scopes, treasury and liquidity floors, and the platform-wide Decision Eligibility floor of DEL ≥ 80.0 cannot be configured around. A domain may raise its bar; none may lower it.

A proposal that clears all four receives a signed authorisation whose scope is proportional to its margin over the floor — the smallest reversible version of the action when the margin is thin (see [DEL Score](/learn/del-score)) — and leaves a [ValidationPassport](/learn/validation-passport) in the immutable ledger either way.

## What the control plane never does

- It never executes. Execution belongs to a separate action runner that re-checks the ceiling and refuses anything the control plane did not sign.
- It never grades the model that proposed the action. Outcomes come from the causal credit ledger, fed by a registered holdout.
- It never coordinates across merchants: no cross-merchant bid, budget or pacing coordination exists by construction.
- It never learns its own floors upward or downward. Threshold changes are logged, human-approved configuration.

## What is shipped today — honestly

- **[PARTIAL]** The control-plane service is deployed and signs authorisations; the Decision Eligibility score it applies is computed by the policy engine as a weighted linear formula, while the canonical description is a clipped-ReLU authority function. The concept — threshold-gated, margin-proportional authority — is present; the activation-function shape differs, and the gap is recorded in the platform's coverage matrix.
- **[PARTIAL]** The four gates exist as roughly nine sequential veto and threshold checks in the policy engine; they are not yet organised in code as four named stages.
- Spend context: the control plane governs actions against budgets that are not growing — marketing budgets averaged 7.7% of company revenue in 2024 (Gartner CMO Spend Survey, May 2024) — in a market where US internet advertising revenue reached $258.6B in 2024 (IAB / PwC, Apr 2025). No figure here is a MIZ OKI result.

## FAQ

### Is the Decision Control Plane an AI model?

No. It is a deterministic service. Models and agents propose; the control plane evaluates the proposal against identity, policy, context and hard constraints, then signs or refuses. Two identical proposals get the same answer.

### What happens to a refused action?

It is routed to a named human with the reasoning path that produced it and, where one exists, a smaller alternative. It is never silently dropped and never executed at reduced scope without a new authorisation.

### Can the control plane be bypassed for urgent actions?

No. The action runner executes only signed authorisations, and it re-checks the ceiling before acting. Urgency raises a human's priority; it does not open a side door.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Is the Decision Control Plane an AI model?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. It is a deterministic service. Models and agents propose; the control plane evaluates the proposal against identity, policy, context and hard constraints, then signs or refuses. Two identical proposals get the same answer."
      }
    },
    {
      "@type": "Question",
      "name": "What happens to a refused action?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "It is routed to a named human with the reasoning path that produced it and, where one exists, a smaller alternative. It is never silently dropped and never executed at reduced scope without a new authorisation."
      }
    },
    {
      "@type": "Question",
      "name": "Can the control plane be bypassed for urgent actions?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. The action runner executes only signed authorisations, and it re-checks the ceiling before acting. Urgency raises a human's priority; it does not open a side door."
      }
    }
  ]
}
```
