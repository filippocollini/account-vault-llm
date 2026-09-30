---
name: deal-review
description: Run a MEDDPICC deal review on a key account in this vault — fill the qualification table from vault data, highlight the gaps, and give one concrete action per critical gap. Trigger on "DEAL REVIEW [account]", "deal review Northwind Marine", "qualify the [account] deal", or "MEDDPICC on [account]". Reads the vault, does not write to it unless asked.
---

# DEAL REVIEW

Produces a MEDDPICC qualification pass so gaps in a deal are explicit before they cost the deal.

## Syntax

`DEAL REVIEW [account]` — e.g. `DEAL REVIEW Northwind Marine`, `DEAL REVIEW Verta Robotics`.

## Sources

1. `wiki/stakeholders/<Account>.md` — frontmatter (`economic_buyer`, `champion`, `stage`, `pipeline_eur`, `risk`) + prose (deal context, open items, existing MEDDPICC section if present).
2. [[wiki/meta/sales-methodology]] — the MEDDPICC definition and the 6-stage pipeline.

Resolve the account fuzzily; if ambiguous, ask; if not found, list accounts from `wiki/stakeholders/_index.md`.

## Output format

A MEDDPICC table, one row per dimension, filled from the vault:

| Dimension | Stato | Fonte / nota |
|---|---|---|
| **M**etrics | … | … |
| **E**conomic Buyer | … | … |
| **D**ecision Criteria | … | … |
| **D**ecision Process | … | … |
| **P**aper Process | … | … |
| **I**dentify Pain | … | … |
| **C**hampion | … | … |
| **C**ompetition | … | … |

Then:
- **Gap critici** — the empty/weak dimensions that most threaten the deal (rank them).
- **Azione per gap** — exactly one concrete next action per critical gap, **with the owner named in parentheses at the end of the line**, e.g. `… entro venerdì (Sam)`. The convention exists so the actions stay machine-readable when they are filed back into the vault; an owner mentioned only in prose does not count.

## Rules

- **Empty fields are the signal, not an error.** Do not paper over a missing Economic Buyer or Champion — name it as the gap. (A large deal in Negotiation with an Economic Buyer nobody has met is the canonical example.)
- Pull only what the vault actually supports; mark inferred vs. confirmed. Do not invent qualification data.
- Read-only by default: output in chat. Write back to the vault only if the owner says so — if so, update the account page's MEDDPICC section + `updated` frontmatter, and log per vault conventions (log.md at TOP, hot.md overwrite).
- Internal analysis only — no external drafting here.
