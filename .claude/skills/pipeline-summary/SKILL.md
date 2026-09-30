---
name: pipeline-summary
description: Produce a management-level pipeline readout — forecast vs quota, coverage, weighted value, deals at risk, and movement — from the deal-level notes in the vault. This is the "someone asks how's the pipeline and finds out" trigger. Fire on "PIPELINE SUMMARY", "how's the pipeline", "com'è la pipeline", "pipeline status", "forecast this quarter", or a named slice ("pipeline Verta Robotics", "pipeline Q3", "pipeline at risk"). Reads the vault, does not write unless asked.
---

# PIPELINE SUMMARY

Computes, on demand, the readout a forecast spreadsheet would give — but from the deal notes, so it is never stale. This is the query non-owners (a manager, a colleague) run to see pipeline state without opening the vault.

## Syntax

`PIPELINE SUMMARY [slice?]` — e.g. `PIPELINE SUMMARY`, `com'è la pipeline`, `pipeline Q3`, `pipeline at risk`, `pipeline Verta Robotics`, `pipeline channel:direct`.

Slice (optional): a quarter (`Q1..Q4`), an account, a forecast category (`commit`/`best-case`/`pipeline`/`upside`), `at risk`, or a channel type. No slice → whole open pipeline.

## Sources (read these, in order)

1. `wiki/pipeline/*.md` — the deal notes. Frontmatter is machine-readable: `deal_id`, `account`, `stage`, `stage_pct`, `forecast_cat`, `amount_eur`, `weighted_eur`, `expected_close`, `risk_flag`, `status`, `owner`, `channel_type`, `meddpicc_*`. **These are the source of truth.**
2. `wiki/meta/pipeline-config.md` — stages, forecast-category rules, quarterly quotas.
3. `wiki/hot.md` — recent cross-account movement, for the narrative line.

Compute in code where possible (sum amounts, weighted, coverage) rather than eyeballing — read all frontmatter, then aggregate. Use today's date to detect slipped deals (`expected_close` in the past while `status == open`).

## Output format

**1 — Forecast vs quota** — for the relevant quarter(s): Closed / Commit / Best Case cumulative, each vs quota, with a RED/AMBER/GREEN status. (Commit = L5+ & MEDDPICC≥7 & close in-quarter; Best Case = L4+ & MEDDPICC≥6 & close in-quarter — per config.)
**2 — Coverage & slip** — pipeline coverage ratio (weighted open ÷ remaining quota), # deals slipped and € pushed.
- **Coverage is computed within the quarter.** Numerator and denominator must cover the same horizon: the weighted value of deals that can close in the quarter, divided by that quarter's remaining quota. Dividing the whole open pipeline by one quarter's remaining quota compares two different horizons and inflates the number.
**3 — Deals at risk** — count, € at risk, and the top 3 by value (`risk_flag == AT RISK`).
**4 — Breakdown** — value by vertical · country · channel type.
**5 — One-line narrative** — plain-language "will we make the number, and what's the single biggest lever" — this is the sentence a non-owner actually wants.

For a single-account or single-slice query, collapse to the deals in scope: list them (id · opportunity · stage · value · forecast · risk) and give totals + the one next action per open deal.

## Rules

- **Report faithfully.** If data is stale (e.g. close dates in the past, forecast categories that don't match the stage rules), say so — don't launder it into a clean number. Flag the imprecision inline.
- Weighted € = `amount_eur × stage_pct`; prefer the stored `weighted_eur` but recompute if it looks inconsistent.
- **Forecast categories are stated at full deal value, not weighted.** Commit and Best Case answer "how much lands if these close", so they sum `amount_eur`. Weighting belongs to coverage, which is a different question. Report open pipeline at full value with the weighted figure alongside — never one instead of the other.
- Empty MEDDPICC / missing close date is a signal, not an error — it downgrades a deal's forecast category; surface it.
- Read-only by default: produce the readout in chat. Only write (e.g. file a snapshot page) if explicitly asked — then follow vault-mutation conventions (frontmatter, `log.md` at TOP, `hot.md` overwrite).
- Never send anything external here — this is an internal briefing.
