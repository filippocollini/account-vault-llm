---
type: meta
title: "Battito del vault (generato)"
created: 2026-09-30
updated: 2026-09-30
tags:
  - meta
  - heartbeat
maturity: generated
related:
  - "[[second-brain-playbook]]"
  - "[[lint-report]]"
  - "[[pipeline-config]]"
---

# Battito del vault

Navigation: [[../index]] | [[second-brain-playbook]] | [[lint-report]]

> [!warning] File generato — non editare a mano
> Prodotto da `tools/heartbeat/heartbeat.py`, sovrascritto a ogni run.
> Il [[lint-report]] misura lo **stato** del vault; questo misura il **movimento**:
> cosa è cambiato dall'ultimo battito, cosa scade adesso, cosa è rimasto in silenzio.

Battito: 2026-09-30 · confronto con: 2026-09-10 · 9 deal aperte · €1.933.000 aperti

| Secchio | Voci | Valore |
|---|---|---|
| Questa settimana | 0 | €0 |
| Scaduto | 8 | €1.683.000 |
| Silenzio | 10 | €250.000 |
| Fermo (decisioni/deliverable) | 2 | — |
| Da ingerire | 1 | — |
| Movimento dall'ultimo battito | 0 | — |

## Questa settimana

Niente in scadenza entro 7 giorni.

## Scaduto

Ordinate per valore, perché è così che si decide cosa guardare per primo.

- €780.000 — [[wiki/pipeline/P-001 Northwind Marine|P-001 Northwind Marine]]
  azione scaduta da 18 giorni
- €410.000 — [[wiki/pipeline/P-002 Verta Robotics|P-002 Verta Robotics]]
  azione scaduta da 15 giorni
- €160.000 — [[wiki/pipeline/P-004 Kestrel Pharma|P-004 Kestrel Pharma]]
  azione scaduta da 18 giorni · close atteso passato da 10 giorni
- €120.000 — [[wiki/pipeline/P-007 Marrow Water|P-007 Marrow Water]]
  azione scaduta da 16 giorni · close atteso passato da 2 giorni
- €90.000 — [[wiki/pipeline/P-005 Orbit Logistics|P-005 Orbit Logistics]]
  azione scaduta da 32 giorni · close atteso passato da 46 giorni
- €55.000 — [[wiki/pipeline/P-010 Verta Robotics Iberia|P-010 Verta Robotics Iberia]]
  azione scaduta da 12 giorni
- €45.000 — [[wiki/pipeline/P-008 Brenner Mobility|P-008 Brenner Mobility]]
  nessuna prossima azione
- €23.000 — [[wiki/pipeline/P-003 Halden Energie|P-003 Halden Energie]]
  nessuna prossima azione

## Silenzio

Qui **non** c'è niente di scaduto — quelle stanno sopra e non si ripetono.
Questo è quello che semplicemente non si muove: deal senza movimento da oltre 30
giorni, account con trattative aperte e nessuna interazione da oltre 21.

- €250.000 — [[wiki/pipeline/P-006 Talvik Steel|P-006 Talvik Steel]] · nessun movimento da **47 giorni** (base: `last_update`)
- account [[wiki/stakeholders/Halden Energie|Halden Energie]] · nessuna interazione da **57 giorni** (base: `ultima interazione`)
- account [[wiki/stakeholders/Brenner Mobility|Brenner Mobility]] · nessuna interazione da **49 giorni** (base: `ultima interazione`)
- account [[wiki/stakeholders/Orbit Logistics|Orbit Logistics]] · nessuna interazione da **49 giorni** (base: `ultima interazione`)
- account [[wiki/stakeholders/Talvik Steel|Talvik Steel]] · nessuna interazione da **47 giorni** (base: `ultima interazione`)
- account [[wiki/stakeholders/Northwind Marine|Northwind Marine]] · nessuna interazione da **41 giorni** (base: `ultima interazione`)
- account [[wiki/stakeholders/Verta Robotics Iberia|Verta Robotics Iberia]] · nessuna interazione da **33 giorni** (base: `ultima interazione`)
- account [[wiki/stakeholders/Verta Robotics|Verta Robotics]] · nessuna interazione da **27 giorni** (base: `ultima interazione`)

*e altre 2 sotto la soglia di leggibilità.*

## Movimento dall'ultimo battito

**Nessun cambiamento su nessuna deal.** Con 9 trattative aperte per €1.933.000,
una settimana intera senza un solo movimento è di per sé il dato da guardare.

## Fermo da oltre 30 giorni

- decisione **active** — [[wiki/decisions/channel-deals-owner|channel-deals-owner]] · 90 giorni
- deliverable **in-progress** — [[wiki/deliverables/kestrel-tisax-questionnaire|kestrel-tisax-questionnaire]] · 60 giorni

## Da ingerire

File in `.raw/` che nessuna nota cita: il vault non li ha ancora letti.

- `.raw/calls/2026-09-09_brenner-mobility-call.md` — 2026-09-30

---

> [!note] Cosa questo file **non** fa
> Non scrive nel vault, non manda niente, non decide niente. Elenca fatti
> meccanici. Le bozze e il giudizio li mette la skill `battito`, e l'invio resta tuo.
