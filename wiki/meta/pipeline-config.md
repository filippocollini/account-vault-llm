---
type: meta
title: "Pipeline config & legend"
created: 2026-07-13
updated: 2026-08-06
tags:
  - meta
  - pipeline
maturity: evergreen
related:
  - "[[sales-methodology|Sales methodology]]"
---

# Pipeline config & legend

Navigation: [[_index|Meta]] | [[../index|Index]]

È il regolamento che seguono le deal note, il lint e la skill `pipeline-summary`.
Quote e nomi sono inventati. Decisione sui campi valore: [[pipeline-eur-definition]].

## Stages & exit criteria

| Stage | % | Exit criteria (must be done to leave the stage) |
|---|---|---|
| L1 — Lead | 10% | Contact identified, first touch done |
| L2 — Discovery | 20% | Pain confirmed, Champion identified, Decision Process sketched |
| L3 — Solution Fit | 40% | Tech meeting done, solution validated, Decision Criteria explicit |
| L4 — Proposal | 60% | Proposal sent, Economic Buyer identified, Paper Process known |
| L5 — Negotiation | 80% | Commercial terms discussed, legal review started, close date confirmed by customer |
| L6 — Closed Won | 100% | PO received |
| Lost | 0% | Deal lost (Lost Reason mandatory) |

## Forecast categories

| Category | Criteria | In management forecast? |
|---|---|---|
| **Commit** | Stage L5+, MEDDPICC ≥7, Paper Process confirmed, close date in current quarter | Yes — floor |
| **Best Case** | Stage L4+, MEDDPICC ≥6, close date in current quarter | Yes — target |
| **Pipeline** | Stage L2–L4, pain confirmed, no clear close timing | No — qualifying |
| **Upside** | Stage L1, early lead, no tech meeting yet | No — strategic visibility |
| **Closed** | Stage L6 (Won) — already booked | No |
| **Omitted** | Lost or de-prioritized | No |

## MEDDPICC field guide

| Field | What to fill | Required from |
|---|---|---|
| M — Metrics | Quantified business outcome (€/year saved) | > €25k |
| E — Economic Buyer | Who signs the PO (name + role) | All deals |
| D — Decision Criteria | What drives the choice (compliance, cost…) | > €25k |
| D — Decision Process | Internal approval steps | > €25k |
| I — Identify Pain | Documented pain (Yes/Partial/No) | All deals |
| C — Champion | Internal advocate pushing our solution | All deals |
| C — Competition | Competitor list + who's ahead | > €100k |
| P — Paper Process | Who signs, legal timing, NDA/MSA | > €100k |

## Lost reason taxonomy

Price · Competition (specify who in "Lost To") · No Decision · Project Cancelled · Timing · Internal Reorg · Other.

## Quotas 2026

| Bucket | Q1 | Q2 | Q3 | Q4 | Annual |
|---|---|---|---|---|---|
| Quota | 650k | 800k | 850k | 1.1M | 3.4M |

## Definizione dei campi valore

| Campo | Dove | Significato |
|---|---|---|
| `amount_eur` | deal note | valore dell'opportunità, qualunque sia lo stato |
| `pipeline_eur` | pagina account | **solo pipeline aperta** — somma di `amount_eur` sulle deal note con `status: open` |
| `won_eur` | pagina account | somma di `amount_eur` sulle deal note con `status: won` — separata dalla pipeline |

**Reason obbligatoria sulle chiusure:** `lost_reason` su ogni nota con `status: lost`,
`win_reason` su ogni nota con `status: won`.

## Update process

- **Deal pipeline — owner:** igiene settimanale il venerdì (stage, forecast cat, next action, MEDDPICC — 15 min); alla chiusura, win/lost reason + `status`; forecast review mensile.
- **Readout per il management:** generato su richiesta dalla skill `pipeline-summary`, non un foglio con formule salvato.
