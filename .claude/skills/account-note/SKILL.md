---
name: account-note
description: Record a raw meeting / call / email into the right account page of this vault — dated, typed, distilled to bullets — and update the account frontmatter, the deal note, the log, and the hot cache. This is the vault-write trigger. Fire on "NOTE [account]" followed by raw notes, "log this meeting on [account]", or "record this call for [account]". Writes to the vault.
---

# NOTE (account-note)

Updates the account page in `wiki/stakeholders/`, the deal note in `wiki/pipeline/`, files a comms page for substantial meetings, then keeps the index/log/hot cache in sync.

## Syntax

```
NOTE [account]
<raw text of the meeting / call / email>
```

e.g.

```
NOTE Kestrel Pharma
Call 2026-09-15. Havel confirmed the quality office starts the TISAX review as soon as it receives the questionnaire. Lindqvist wants the Verona scope quoted separately. Next step: send the questionnaire by Friday.
```

Resolve the account fuzzily against `wiki/stakeholders/` (files may have spaces). If not found, ask whether to create a new account page.

## What it does

1. **Distill** the raw text into: date, interaction type (meeting / call / email / note), and 3–6 crisp bullets. Do not editorialize or invent — extractive, not generative.
2. **Update the account page** `wiki/stakeholders/<Account>.md`:
   - Append a dated entry under an `## Interazioni` section (create the section if missing — append-only, newest at TOP, never rewrite past entries).
   - Update relevant frontmatter if the note changes state (`stage`, `risk`, `economic_buyer`, `champion`, `updated`) — only when the raw text clearly supports it; otherwise just bump `updated`.
   - Close/adjust any `## Open threads` items the note resolves.
3. **Update the deal note(s)** in `wiki/pipeline/` for the deals the note moves — this is the step that keeps the pipeline layer alive instead of frozen at import:
   - `next_action` + `next_action_date` — the concrete next step the interaction produced. Never leave `next_action` empty after a real interaction.
   - `last_update` and `updated` — today's date.
   - `stage` / `stage_pct` / `forecast_cat` / `expected_close` / `risk_flag` — **only** when the raw text clearly supports the change, and check the new `forecast_cat` against the stage + MEDDPICC + quarter rules in [[wiki/meta/pipeline-config]] before writing it.
   - `meddpicc_*` fields the interaction actually fills, and `meddpicc_score` = count of filled fields.
   - Append the interaction under the deal note's `## Notes` section, newest first.
   - Resolve the deal fuzzily by account + opportunity; if several deals on that account could match, ask which one rather than guessing.
4. **File a comms page** in `wiki/comms/` only for a substantial meeting worth its own page; for a quick call/email, the account-page entry is enough. Cross-link both ways if you create one.
5. **Keep the vault in sync** (mandatory, per CLAUDE.md):
   - `wiki/index.md` — if a new page was created.
   - `wiki/log.md` — add an entry at the **TOP** (append-only).
   - `wiki/hot.md` — overwrite the recent-context section.
   - Relevant `_index.md` files.
6. If the note **contradicts** an existing page, add a `> [!contradiction]` callout on both sides — do not silently overwrite.

## Rules

- Extractive distillation only — capture what was said, don't infer commitments that weren't made.
- Never auto-send or draft external comms as a side effect. If the owner wants a recap email after, that's a separate step (chain it explicitly).
- Frontmatter stays flat YAML; wikilinks in `[[Note Name]]` format; product terminology per [[wiki/meta/product-facts]] when present.
- After writing, report exactly what was created and what was modified.
- Then run `python3 tools/lint/vault.py` and report whether the ERROR count moved. A NOTE that
  leaves `next_action` empty or an unsupported `forecast_cat` behind will show up there.
