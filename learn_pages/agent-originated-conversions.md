---
title: Agent-originated conversions
description: An agent-originated conversion is a purchase whose buying journey ran partly or wholly through an AI answer engine or shopping agent rather than a search results page. MIZ OKI is building the classification, shadow measurement and read-side stratification for them — IN BUILD, nothing customer-facing yet.
last_reviewed: 2026-09-02
owner: MIZ OKI product
expires: 2026-12-01
status_label: IN BUILD
---
## Direct answer

An agent-originated conversion is a purchase whose journey ran partly or wholly through an AI answer engine or shopping agent — a recommendation, comparison, or agent-placed order — rather than a classic search results page. MIZ OKI is building additive event fields, a flag-off classifier, a shadow table and read-side stratification to measure them. Capability label: **[IN BUILD]**.

## Why this is a new measurement problem

The referral path is changing. Traditional search engine volume is forecast to fall 25% by 2026 as AI answer engines absorb queries (Gartner, Feb 2024). Traffic to US retail sites from generative AI sources rose 1,200% between July 2024 and February 2025 (Adobe Analytics, Mar 2025). ChatGPT reached 800 million weekly users (OpenAI DevDay, Oct 2025), and enterprise adoption is following — 78% of organisations already use AI in at least one business function (McKinsey, Mar 2025) and 23% are scaling an agentic AI system somewhere in the enterprise (McKinsey, Nov 2025).

Attribution built for click-through from a results page mislabels these journeys. A visitor who arrives from an answer engine looks "direct" or "referral"; an order placed by an agent on the buyer's behalf may carry no session at all. Counting them wrong distorts two things at once: the incrementality of the media that reached the buyer earlier, and the measured value of being cited by the engine.

## What "agent-originated" means at MIZ OKI

The definition is deliberately narrow and evidence-led:

- **Origin is classified from the canonical event, never guessed from the destination page.** The classifier reads additive fields on the platform's journey-event schema — referrer class, agent-protocol markers where a protocol exposes them, and order metadata — and emits a class with a confidence, never a bare label.
- **Classification is additive.** New fields are appended to the schema; old events validate unchanged; nothing existing is rewritten.
- **Shadow first.** Classified events land in a shadow table that feeds read-side stratification (agent-originated vs not) in reports; they change no budget decision until a registered holdout shows the stratum behaves differently.
- **Consent and erasure travel with the event.** The consent gate runs fail-closed on every event regardless of origin, and the erasure path covers the shadow table like any other store.

## The citation KPI, and what it is not

The site's own referral class is measured the same way. The identity-free site-events schema classifies the `Referer` **host** into `direct | search | ai_answer_engine | social | other` and stores only the class — the host itself is dropped before the row is built, and the schema test asserts no host, IP, user-agent or cookie can be stored. `referrer_class = ai_answer_engine` on a page view is therefore the citation KPI: the share of visits that arrived from an answer engine. It says nothing about which engine, which query, or who the visitor was, and it is a page-view count, never a conversion count.

## What is shipped today — honestly

- **[IN BUILD]** Additive schema fields, the flag-off origin classifier, the shadow table and read-side stratification are being built in the current wave; nothing is customer-facing and no customer figure exists.
- **[PARTIAL]** The identity-free site-events schema with the `ai_answer_engine` referrer class is built and flag-gated OFF on the site.
- **[PROPOSED]** A governed decision feed that would let an agent read a tenant's eligible decisions through the [Decision Control Plane](/learn/decision-control-plane) is specified only.
- No conversion figure on this page is a MIZ OKI result. Third-party statistics carry their source and month inline.

## FAQ

### Does MIZ OKI track visitors coming from ChatGPT or Perplexity?

It classifies the referring host into a coarse class and stores only the class, aggregated to the hour. The host, the query, the IP, the user agent and any cookie are never stored — the schema forbids the columns.

### Will agent-originated conversions change my budget decisions?

Not yet, and not automatically. They are measured in a shadow table and shown as a stratum in reports. Only a registered holdout showing the stratum responds differently to media can change a decision, and that follows the normal promotion path.

### Is this the same as "AI attribution"?

No. Attribution assigns credit by rule. Agent-originated classification labels the journey's origin with a confidence, and incrementality is still measured against a holdout. The label says where the buyer came through, not what caused the purchase.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Does MIZ OKI track visitors coming from ChatGPT or Perplexity?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "It classifies the referring host into a coarse class and stores only the class, aggregated to the hour. The host, the query, the IP, the user agent and any cookie are never stored — the schema forbids the columns."
      }
    },
    {
      "@type": "Question",
      "name": "Will agent-originated conversions change my budget decisions?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Not yet, and not automatically. They are measured in a shadow table and shown as a stratum in reports. Only a registered holdout showing the stratum responds differently to media can change a decision, and that follows the normal promotion path."
      }
    },
    {
      "@type": "Question",
      "name": "Is this the same as \"AI attribution\"?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. Attribution assigns credit by rule. Agent-originated classification labels the journey's origin with a confidence, and incrementality is still measured against a holdout. The label says where the buyer came through, not what caused the purchase."
      }
    }
  ]
}
```
