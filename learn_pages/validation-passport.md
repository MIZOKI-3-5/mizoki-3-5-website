---
title: What is a ValidationPassport?
description: A ValidationPassport is the sealed, tamper-evident evidence record every governed decision leaves behind — the checks it passed, the pass rate, the hypotheses tried, the consent basis and the model versions — chained per tenant so a later reader can verify the whole series.
last_reviewed: 2026-09-15
owner: MIZ OKI product
expires: 2026-12-01
status_label: PARTIAL
---
## Direct answer

A ValidationPassport is the sealed evidence record a governed decision carries: which validation checks ran and passed, the pass rate, how many hypotheses were tried, the consent basis, model and contract versions, and a hash that makes later tampering detectable. Passports chain per tenant so an auditor can verify the series. Capability label: **[PARTIAL]**.

## Why decisions need passports

Attribution figures are claims; passports are evidence. The distinction matters more as the money and the automation grow: US internet advertising revenue reached $258.6B in 2024, up 14.9% (IAB / PwC, Apr 2025), and Gartner expects 15% of day-to-day work decisions to be made autonomously through agentic AI by 2028, up from 0% in 2024 (Gartner, Oct 2024). Enterprises adopting that automation already report that trust and risk controls are the sticking point: over 40% of agentic AI projects are forecast to be cancelled by the end of 2027 (Gartner, Jun 2025).

A passport answers the question a finance or compliance reviewer actually asks — not "did the model recommend it?" but "what was checked, what passed, on what data, under what consent, and can I prove none of that was edited afterwards?"

## What a passport contains

The passport is one of the platform's closed set of eight decision objects — no ninth object and no private variant may be defined. Its fields:

- **The checks** — each named validation check, its result and its evidence reference.
- **`all_passed` and `pass_rate`** — the summary the Decision Eligibility score reads.
- **`trial_count`** — how many hypotheses were tried before this one, feeding data-snooping controls so a result found on the twentieth attempt is not presented as the first.
- **Issuer, timestamp, contracts version** — who sealed it and under which schema.
- **`immutable_hash`** — a SHA-256 over the canonical body; any later edit changes the hash.

Around the sealed per-path passport sits the **passport package**: a read-model that assembles the decision's whole trace — signals used, model versions, refutation results, confidence, consent basis, realised outcome — and reports honestly which fields have no persisted source rather than inventing them. Each persisted package links to the tenant's previous one, and a chain-walk endpoint verifies a tenant's entire series.

## What the passport does not claim

- A passport records that checks ran and passed. It does not prove causal lift; that comes only from a registered holdout and the causal credit ledger (see [Incrementality vs platform ROAS](/learn/incrementality-vs-platform-roas)).
- A passport does not grade the model that produced the decision. Prediction never grades itself.
- A high pass rate does not by itself authorise anything. Authorisation is the [Decision Control Plane](/learn/decision-control-plane)'s job, using the [DEL Score](/learn/del-score) the passport feeds.

## What is shipped today — honestly

- **[PARTIAL]** The passport object, sealing, the eighteen-field package, per-tenant chaining and the chain-walk verification route are built. Cryptographic signing of packages is real-or-refuse: when a signing key is not configured the package is sealed by hash and reports that it is unsigned — never mock-signed.
- **[PARTIAL]** Some package fields have no persisted writer yet (the learning-update reference, for one) and are reported as absent. The pilot-report generator that renders passports for customers is a skeleton until the first real pilot.
- Context for the returns fields the package will carry: 19.3% of online sales are expected to be returned in 2025 (NRF / Happy Returns, Oct 2025), which is why realised outcome is recorded after the return window, not at order time. Search-side context: traditional search engine volume is forecast to fall 25% by 2026 (Gartner, Feb 2024). No figure here is a MIZ OKI result.

## FAQ

### Is a ValidationPassport a blockchain?

No. It is a hash-sealed record in an append-only ledger with a per-tenant hash chain. There is no distributed consensus and no token; the chain exists so an auditor can detect a rewritten history, nothing more.

### Who can read a passport?

The tenant it belongs to, through authenticated console and API routes, and the platform's audit-replay service. Raw secrets, personal identifiers and forbidden signal types never enter a passport by schema.

### Does a passport prove the ad worked?

No. It proves what was validated before the decision and links to the outcome record afterwards. Whether the ad caused revenue is a separate, holdout-based measurement recorded in the causal credit ledger.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Is a ValidationPassport a blockchain?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. It is a hash-sealed record in an append-only ledger with a per-tenant hash chain. There is no distributed consensus and no token; the chain exists so an auditor can detect a rewritten history, nothing more."
      }
    },
    {
      "@type": "Question",
      "name": "Who can read a passport?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "The tenant it belongs to, through authenticated console and API routes, and the platform's audit-replay service. Raw secrets, personal identifiers and forbidden signal types never enter a passport by schema."
      }
    },
    {
      "@type": "Question",
      "name": "Does a passport prove the ad worked?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. It proves what was validated before the decision and links to the outcome record afterwards. Whether the ad caused revenue is a separate, holdout-based measurement recorded in the causal credit ledger."
      }
    }
  ]
}
```
