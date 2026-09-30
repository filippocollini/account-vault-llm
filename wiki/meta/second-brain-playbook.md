---
type: meta
title: "Second-brain playbook"
created: 2026-07-13
updated: 2026-09-10
tags:
  - meta
  - playbook
maturity: mature
related:
  - "[[corrections]]"
  - "[[vault-usage-guide]]"
---

# Second-brain playbook

Navigation: [[_index|Meta]] | [[../index|Index]]

> [!key-insight] Il principio
> L'umano cura le fonti e fa le domande. L'LLM scrive e mantiene il wiki. L'automazione sta
> sulla manutenzione tediosa (cross-reference, coerenza, sintesi), non sulle decisioni né
> sulle azioni verso l'esterno.

## Il ciclo di ingest

1. Leggere la fonte in `.raw/` per intero.
2. Aggiornare o creare le pagine giuste (account, deal, decisione, deliverable, intel, comms).
3. Aggiornare gli `_index.md` toccati, `index.md`, `hot.md`, e una voce in cima a `log.md`.
4. Se qualcosa contraddice una pagina esistente, un callout `> [!contradiction]` su entrambe.

## I loop di misura

- **Loop 0 — battito settimanale.** `tools/heartbeat/heartbeat.py` + skill `battito`: cosa
  scade, cosa è scaduto, cosa non si muove. Esiste perché tutti gli altri loop dipendono dal
  ricordarsi di eseguirli.
- **Loop 1 — forecast accuracy (trimestrale).** Previsto contro reale, deal per deal.
- **Loop 2 — error analysis sugli ingest (mensile).** Tre pagine a caso rilette contro la
  fonte; si contano le correzioni.
- **Loop 3 — correction tracking (continuo).** Una riga in [[corrections]] per ogni output
  sbagliato intercettato prima dell'uso.

## Dove NON usare l'LLM per controllare

I controlli meccanici — frontmatter, wikilink morti, totali che tornano — appartengono a uno
script (`tools/lint/vault.py`): il codice non allucina e rieseguirlo costa zero. Al giudizio
di un modello resta solo ciò che richiede giudizio, e anche lì separato e misurato
(`tools/eval/judge.py`).

## Cosa resta sempre umano

Comunicazioni esterne (l'invio, non la bozza), impegni commerciali e di prezzo, e ogni
modifica a stage, importo o forecast di una deal.
