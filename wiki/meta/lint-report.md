---
type: meta
title: "Lint report (generato)"
created: 2026-09-10
updated: 2026-09-10
tags:
  - meta
  - lint
  - eval
maturity: generated
related:
  - "[[second-brain-playbook]]"
  - "[[corrections]]"
  - "[[pipeline-config]]"
---

# Lint report

Navigation: [[../index]] | [[second-brain-playbook]]

> [!warning] File generato — non editare a mano
> Prodotto da `tools/lint/vault.py`, sovrascritto a ogni run. Copre solo i controlli
> **meccanici**: il lint dei claim stale resta un pass a giudizio.

Run: 2026-09-10 · note analizzate: 48 · deal note: 11 · trimestre di riferimento: 2026Q3

| Severità | Conteggio |
|---|---|
| ERROR | 4 |
| WARN | 38 |
| INFO | 3 |

| Controllo | ERROR | WARN | INFO |
|---|---|---|---|
| Frontmatter | 1 | 0 | 0 |
| Wikilink | 0 | 1 | 0 |
| Igiene pipeline | 2 | 6 | 2 |
| MEDDPICC | 0 | 23 | 0 |
| Coerenza forecast | 0 | 4 | 0 |
| Riconciliazione deal ↔ account | 1 | 0 | 0 |
| Staleness | 0 | 4 | 1 |

## Riconciliazione deal ↔ account

Somma `amount_eur` delle deal note **aperte** contro `pipeline_eur` sulle pagine account.
Definizione in [[pipeline-config]]: `pipeline_eur` = **solo pipeline aperta**, il valore
vinto vive in `won_eur` e si somma separatamente.

| Account | Deal aperte | pipeline_eur | Già vinto | Delta | Causa |
|---|---:|---:|---:|---:|---|
| Marrow Water | €120.000 | €110.000 | €0 | €10.000 | drift reale |
| **Totale pagine account** | **€1.933.000** | **€1.923.000** | | **€10.000** | |

Scomposizione del delta per causa:

- drift reale: €10.000

## Frontmatter

**ERROR (1)**

- `wiki/pipeline/P-008 Brenner Mobility.md` — campi mancanti o vuoti: expected_close

## Wikilink

**WARN (1)**

- `wiki/index.md` — link ambiguo [[heartbeat]] → risolto su wiki/meta/heartbeat.md

## Igiene pipeline

**ERROR (2)**

- `wiki/pipeline/P-005 Orbit Logistics.md` — expected_close 2026-08-15 è passata ma status è open
- `wiki/pipeline/P-006 Talvik Steel.md` — weighted_eur 120000.00 ≠ amount_eur × stage_pct (100000.00)

**WARN (6)**

- `wiki/pipeline/P-001 Northwind Marine.md` — non aggiornata da 21 giorni (updated 2026-08-20)
- `wiki/pipeline/P-003 Halden Energie.md` — next_action vuoto
- `wiki/pipeline/P-003 Halden Energie.md` — non aggiornata da 35 giorni (updated 2026-08-06)
- `wiki/pipeline/P-005 Orbit Logistics.md` — non aggiornata da 29 giorni (updated 2026-08-12)
- `wiki/pipeline/P-006 Talvik Steel.md` — non aggiornata da 27 giorni (updated 2026-08-14)
- `wiki/pipeline/P-008 Brenner Mobility.md` — next_action vuoto

**INFO (2)**

- `wiki/pipeline/P-003 Halden Energie.md` — next_action_date vuota
- `wiki/pipeline/P-008 Brenner Mobility.md` — next_action_date vuota

## MEDDPICC

**WARN (23)**

- `wiki/pipeline/P-001 Northwind Marine.md` — meddpicc_econ_buyer richiesto sopra €0 ed è vuoto
- `wiki/pipeline/P-001 Northwind Marine.md` — meddpicc_champion richiesto sopra €0 ed è vuoto
- `wiki/pipeline/P-001 Northwind Marine.md` — meddpicc_decision_proc richiesto sopra €25.000 ed è vuoto
- `wiki/pipeline/P-001 Northwind Marine.md` — meddpicc_paper richiesto sopra €100.000 ed è vuoto
- `wiki/pipeline/P-003 Halden Energie.md` — meddpicc_econ_buyer richiesto sopra €0 ed è vuoto
- `wiki/pipeline/P-003 Halden Energie.md` — meddpicc_champion richiesto sopra €0 ed è vuoto
- `wiki/pipeline/P-004 Kestrel Pharma.md` — meddpicc_decision_proc richiesto sopra €25.000 ed è vuoto
- `wiki/pipeline/P-004 Kestrel Pharma.md` — meddpicc_competition richiesto sopra €100.000 ed è vuoto
- `wiki/pipeline/P-005 Orbit Logistics.md` — meddpicc_decision_proc richiesto sopra €25.000 ed è vuoto
- `wiki/pipeline/P-006 Talvik Steel.md` — meddpicc_econ_buyer richiesto sopra €0 ed è vuoto
- `wiki/pipeline/P-006 Talvik Steel.md` — meddpicc_champion richiesto sopra €0 ed è vuoto
- `wiki/pipeline/P-006 Talvik Steel.md` — meddpicc_decision_proc richiesto sopra €25.000 ed è vuoto
- `wiki/pipeline/P-006 Talvik Steel.md` — meddpicc_paper richiesto sopra €100.000 ed è vuoto
- `wiki/pipeline/P-007 Marrow Water.md` — meddpicc_decision_proc richiesto sopra €25.000 ed è vuoto
- `wiki/pipeline/P-007 Marrow Water.md` — meddpicc_competition richiesto sopra €100.000 ed è vuoto
- `wiki/pipeline/P-007 Marrow Water.md` — meddpicc_paper richiesto sopra €100.000 ed è vuoto
- `wiki/pipeline/P-008 Brenner Mobility.md` — meddpicc_econ_buyer richiesto sopra €0 ed è vuoto
- `wiki/pipeline/P-008 Brenner Mobility.md` — meddpicc_champion richiesto sopra €0 ed è vuoto
- `wiki/pipeline/P-010 Verta Robotics Iberia.md` — meddpicc_econ_buyer richiesto sopra €0 ed è vuoto
- `wiki/pipeline/P-010 Verta Robotics Iberia.md` — meddpicc_champion richiesto sopra €0 ed è vuoto
- `wiki/pipeline/P-010 Verta Robotics Iberia.md` — meddpicc_metrics richiesto sopra €25.000 ed è vuoto
- `wiki/pipeline/P-010 Verta Robotics Iberia.md` — meddpicc_decision_crit richiesto sopra €25.000 ed è vuoto
- `wiki/pipeline/P-010 Verta Robotics Iberia.md` — meddpicc_decision_proc richiesto sopra €25.000 ed è vuoto

## Coerenza forecast

**WARN (4)**

- `wiki/pipeline/P-001 Northwind Marine.md` — forecast_cat 'Commit' non supportata dalle regole: MEDDPICC 4 < 7; close 2026-12-15 fuori dal trimestre corrente
- `wiki/pipeline/P-005 Orbit Logistics.md` — forecast_cat 'Best Case' non supportata dalle regole: MEDDPICC 5 < 6
- `wiki/pipeline/P-007 Marrow Water.md` — forecast_cat 'Commit' non supportata dalle regole: MEDDPICC 5 < 7
- `wiki/pipeline/P-008 Brenner Mobility.md` — forecast_cat 'Best Case' non supportata dalle regole: MEDDPICC 5 < 6; close n/d fuori dal trimestre corrente

## Staleness

**WARN (4)**

- `wiki/stakeholders/Brenner Mobility.md` — ha deal aperte e nessun movimento da 29 giorni (base: ultima interazione)
- `wiki/stakeholders/Halden Energie.md` — ha deal aperte e nessun movimento da 37 giorni (base: ultima interazione)
- `wiki/stakeholders/Orbit Logistics.md` — ha deal aperte e nessun movimento da 29 giorni (base: ultima interazione)
- `wiki/stakeholders/Talvik Steel.md` — ha deal aperte e nessun movimento da 27 giorni (base: ultima interazione)

**INFO (1)**

- `wiki/stakeholders/Ferro Group.md` — nessun movimento da 52 giorni (base: ultima interazione)

## Cosa questo lint NON copre

Dichiarato per non far leggere "tutto verde" come "tutto verificato":

- **Claim stale** — un fatto corretto alla scrittura e superato dopo. Richiede giudizio: resta un pass LLM.
- **Accuratezza contro la fonte** — è il loop 2 del playbook (3 pagine a caso vs `.raw/`), non automatizzabile qui.
- **`wiki/pipeline/_index.md`** non è controllato voce per voce: l'indice riporta i totali aggregati, non una riga per deal (scelta dichiarata).
- **`wiki/sources/_index.md`** non è controllato voce per voce: consolida la provenienza in una mappa unica invece di una pagina per fonte (scelta dichiarata).
- **Note di tipo `opportunity`** escluse dal controllo orfani: le deal note sono raggiunte da `deals.base`, non da wikilink: decine di WARN identiche seppellirebbero gli orfani veri.
- **Conformità del materiale esterno** (GA-only, roadmap, pricing) — è un controllo separato sui file consegnati, non sul vault.
- **La staleness si misura sul campo `updated`, che è autodichiarato**: toccare il
  frontmatter azzera l'allarme senza che il contenuto sia stato rivisto. Da agganciare
  alla data dell'ultima voce in `## Interazioni`, che non è falsificabile allo stesso modo.

