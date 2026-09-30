---
name: battlecard
description: Produce a one-page competitive battlecard against a named competitor — when we lose, when we win, two proof points, a trap question, and a two-line positioning message. Trigger on "BATTLECARD [competitor]", "battlecard Halberd", "how do we position against Quorra", or "competitive card for [competitor]". Reads the vault only.
---

# BATTLECARD

Produces a tight, sales-ready competitive card.

## Syntax

`BATTLECARD [competitor]` — e.g. `BATTLECARD Halberd`, `BATTLECARD Ferrocore`.

**Supported competitors** (the ones the intel page covers): Halberd · Quorra · Ferrocore · Sablewave · Lattix · Norvane. For a competitor not on this list, produce the card anyway from available intel but flag it as best-effort.

## Sources

1. [[wiki/intel/competitive-landscape-2026]] — the vault's mapped landscape. This is the primary source.
2. [[wiki/meta/product-facts]] when present — what our product does today (GA) versus what is In Development.

## Output format (one page)

- **Chi è** (1 line): the competitor's category and where they overlap with us.
- **Quando perdiamo**: the scenarios where they beat us — be honest, this is the useful part.
- **Quando vinciamo**: the scenarios where we win.
- **2 proof point**: concrete, defensible (a capability, a reference pattern, a compliance angle).
- **Domanda-trappola**: one discovery question that surfaces the competitor's weakness without naming them.
- **Messaggio di posizionamento** (2 lines): the crisp positioning vs. this competitor.

## Rules

- Never claim In-Development features as available: if one comes up, it is named together with its status.
- Honest "when we lose" — a battlecard that pretends we always win is useless in the field.
- Read-only by default: output in chat. File into `wiki/intel/` only if the owner asks (then follow vault conventions).
- Internal use — this is a sales-enablement artifact, not a customer-facing document.
