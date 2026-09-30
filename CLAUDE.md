# Account vault — LLM-maintained second brain

Purpose: a structured, version-controlled knowledge base for key-account work — accounts,
deals, decisions, deliverables, competitive intel, meeting notes — written and maintained by
Claude Code, curated by a human. This repository ships a **synthetic demo vault**: every
account, person, amount, vendor and competitor is invented.

## Structure

```
.raw/              source documents (meeting notes, call notes, exports) — immutable
wiki/
├── stakeholders/  accounts and partners — the hub page of every account
├── pipeline/      one note per opportunity + deals.base
├── decisions/     decisions with date, owner, status, rationale
├── deliverables/  outputs with status
├── intel/         competitive and market context
├── comms/         synthesized meeting notes
├── sources/       provenance map (.raw → pages)
├── meta/          method, config, generated reports
├── index.md       master catalog
├── log.md         append-only operation log (newest at TOP)
├── hot.md         ~500-word recent-context cache (overwritten)
└── overview.md    executive summary
_templates/        note templates, checked against the schema by the lint
tools/             lint, heartbeat, eval suite
```

## Conventions

- Flat YAML frontmatter: `type`, `created`, `updated`, `tags` on every note; the full schema
  lives in code (`tools/lint/vault.py`) and is published to `wiki/meta/frontmatter-schema.md`.
- `status` is lifecycle state; `maturity` is how complete a reference page is. Never both.
- Wikilinks use `[[Note Name]]`.
- `.raw/` is never modified.
- `wiki/index.md` is updated on every ingest; `wiki/log.md` is append-only with new entries at
  the TOP; `wiki/hot.md` is overwritten after every ingest or significant session.
- Nothing is ever sent externally. Drafts stay drafts.

## Operations

- **Ingest:** drop a source in `.raw/`, say "ingest <file>".
- **Query:** ask anything — read `hot.md`, then `index.md`, then drill in.
- **Skills:** `SNAPSHOT`, `DEAL REVIEW`, `PIPELINE SUMMARY`, `BATTLECARD`, `NOTE`, `BATTITO`
  (see `.claude/skills/README.md`).
- **Lint:** `/lint` or `sh tools/lint/run.sh`. **Checkup:** `/checkup`.

The demo vault pins its date in `.vault-today` (2026-09-10) so lint and heartbeat are
reproducible. Delete that file to run against the real calendar.
