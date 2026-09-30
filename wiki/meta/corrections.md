---
type: meta
title: "Correction log"
created: 2026-07-13
updated: 2026-09-05
tags:
  - meta
  - eval
maturity: developing
related:
  - "[[second-brain-playbook]]"
---

# Correction log

Navigation: [[_index|Meta]] | [[../index|Index]]

Loop 3 del [[second-brain-playbook]]: una riga ogni volta che un output è sbagliato **prima**
che venga usato. Trenta secondi per voce. Quando le correzioni restano a zero per qualche
settimana, quello è il gate misurato per dare più autonomia al sistema.

| Data | Skill / operazione | Cosa era sbagliato | Classe | Ora coperto da |
|---|---|---|---|---|
| 2026-09-05 | `pipeline-summary` | copertura calcolata sul pesato di tutta la pipeline invece che del trimestre | aritmetica | regola nella skill + oracolo (`tools/eval/oracle.py`) |
| 2026-08-21 | ingest | data della PoC Verta riportata come 21/08 invece di 20/08 | fatto | — |
| 2026-08-06 | lint | `pipeline_eur` includeva il vinto su un account | definizione | [[pipeline-eur-definition]] + check di riconciliazione |
| 2026-07-29 | `deal-review` | referente tecnico promosso a champion | invenzione | eval caso 01 |
