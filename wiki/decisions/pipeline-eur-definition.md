---
type: decision
status: done
date: 2026-08-06
owner: "Alex"
created: 2026-08-06
updated: 2026-08-06
tags:
  - decision
  - pipeline
related:
  - "[[pipeline-config]]"
---

# `pipeline_eur` è solo pipeline aperta

Navigation: [[_index|Decisions]] | [[../index|Index]]

## Decision

Sulle pagine account `pipeline_eur` somma solo le deal con `status: open`. Il valore vinto
vive in `won_eur` e si somma separatamente.

## Rationale

Il lint aveva segnalato un "gap di riconciliazione" fra deal note e pagine account. Scomposto,
erano tre problemi diversi: deal su account senza pagina, valore già vinto contato nei rollup,
e un drift reale. Nessuno dei due layer era sbagliato: lo stesso campo significava due cose.

## Impact

`tools/lint/vault.py` verifica entrambe le somme a ogni run. Un rollup che include il vinto è
un ERROR, non una differenza da interpretare. Definizione in [[pipeline-config]].
