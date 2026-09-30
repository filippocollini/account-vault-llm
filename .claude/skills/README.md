# Vault skills

Recurring requests turned into invocable Claude Code skills: no syntax to remember,
consistent behaviour, and every one of them reads from the vault instead of from memory.

| Skill | Trigger | Writes to vault? | Source of truth |
|---|---|---|---|
| `snapshot` | `SNAPSHOT [account] [meeting\|CEO]` | No (read-only briefing) | account page + hot.md |
| `deal-review` | `DEAL REVIEW [account]` | No (analysis output) | account page + sales-methodology |
| `battlecard` | `BATTLECARD [competitor]` | No (enablement output) | competitive-landscape + product-facts |
| `account-note` | `NOTE [account]` + raw text | **Yes** | account page + deal note + index/log/hot |
| `pipeline-summary` | `PIPELINE SUMMARY [slice]` / "com'è la pipeline" | No (read-only readout) | `wiki/pipeline/*` deal notes + pipeline-config |
| `battito` | `BATTITO` / "cosa mi sono perso" / brief del lunedì | Only on explicit instruction, and only `next_action`/`next_action_date`/`risk_flag` | `tools/heartbeat/heartbeat.py` → `wiki/meta/heartbeat.md` |

Guardrails: none of these send or draft external communications as a side effect; only
`account-note` mutates the vault, and only with internal, extractive content.
Human-in-the-loop on anything customer-facing.

Five of the six are measured by the eval suite in `tools/eval/` (`battito` is not yet).
