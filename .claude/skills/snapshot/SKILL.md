---
name: snapshot
description: Produce an actionable account recap (context / status / open points / next step, plus an optional C-level block) for a key account in this vault. Trigger on "SNAPSHOT [account] [meeting|CEO]", "snapshot Kestrel Pharma", "snapshot Verta Robotics CEO", or "recap on [account] before a call". Reads the vault, does not write to it unless asked.
---

# SNAPSHOT

Produces a fast, actionable recap of an account so the owner can walk into a call without re-reading the pages by hand.

## Syntax

`SNAPSHOT [account] [scope?]` — e.g. `SNAPSHOT Kestrel Pharma`, `SNAPSHOT Kestrel Pharma meeting`, `SNAPSHOT Verta Robotics CEO`.

Scope (optional):
- (none) or `meeting` → blocks 1–4 (operational).
- `CEO` → blocks 1–5, higher-level tone, executive framing.

## Sources (read these, in order)

1. `wiki/stakeholders/<Account>.md` — the account page (frontmatter is machine-readable state: `stage`, `stage_name`, `pipeline_eur`, `risk`, `owner`, `economic_buyer`, `champion`; prose has deal context, open items, MEDDPICC, threads).
2. `wiki/hot.md` — for the most recent cross-account context.
3. Any `related:` pages the account frontmatter links (deal notes, decisions, deliverables, comms) — drill in only if relevant to open items.

Resolve the account name fuzzily (files can have spaces: `Kestrel Pharma.md`, `Verta Robotics.md`). If two accounts match, ask which one. If none match, list the available accounts from `wiki/stakeholders/_index.md`.

## Output format

**Block 1 — Contesto** (2–3 lines): what this account is, sector, why it matters, pipeline value + stage.
**Block 2 — Stato** (bullets): current deal state, forecast category, key numbers, latest movement.
**Block 3 — Punti aperti** (bullets): unresolved items, blockers, MEDDPICC gaps — pull the real gaps, don't invent closure.
**Block 4 — Next step** (bullets, each with an owner where known): the concrete next actions.
**Block 5 — C-level** (only if scope = `CEO`): 3–4 sentences at executive altitude — the one risk, the one opportunity, the ask.

## Rules

- Product terminology per [[wiki/meta/product-facts]] when present; anything marked In Development is named as such, never as available.
- Empty MEDDPICC fields are the signal, not an error — surface them as gaps, per [[wiki/meta/sales-methodology]].
- Read-only by default: produce the recap in chat. Only write to the vault if the owner explicitly says "save this" / "/save" (then follow the vault-mutation conventions: frontmatter, log.md at TOP, hot.md overwrite).
- Never draft or send anything external here — SNAPSHOT is an internal briefing.
