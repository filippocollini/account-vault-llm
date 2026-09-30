---
type: meta
title: "Vault usage guide"
created: 2026-07-20
updated: 2026-09-10
tags:
  - meta
  - guide
maturity: developing
related:
  - "[[second-brain-playbook]]"
  - "[[frontmatter-schema]]"
---

# Vault usage guide

Navigation: [[_index|Meta]] | [[../index|Index]]

## Da dove partire

1. [[../hot|hot.md]] — il contesto recente.
2. [[../index|index.md]] — il catalogo.
3. La pagina account, sotto `wiki/stakeholders/`.

## Comandi

| Comando | Cosa fa |
|---|---|
| `SNAPSHOT <account>` | recap prima di una call |
| `DEAL REVIEW <account>` | qualificazione MEDDPICC con i gap |
| `PIPELINE SUMMARY` | forecast vs quota, copertura, rischio |
| `BATTLECARD <concorrente>` | scheda competitiva |
| `NOTE <account>` + testo | registra un'interazione (**scrive**) |
| `BATTITO` | brief settimanale |
| `/lint`, `/checkup` | salute del vault |

## Regole dei campi

`pipeline_eur` è solo pipeline aperta, il vinto sta in `won_eur` ([[pipeline-eur-definition]]).
`status` è lo stato, `maturity` la maturità della pagina ([[frontmatter-schema]]).
`[da compilare]` non conta come compilato.

## Debito dichiarato

Difetti noti, lasciati nel vault demo di proposito perché lint e battito abbiano qualcosa di
vero da trovare:

- [[P-005 Orbit Logistics]] — `expected_close` passata con la deal ancora aperta.
- [[P-006 Talvik Steel]] — `weighted_eur` incoerente con `amount_eur × stage_pct`.
- [[P-008 Brenner Mobility]] — nessuna data di chiusura.
- [[Marrow Water]] — `pipeline_eur` non riconciliato con la deal note.
- [[P-001 Northwind Marine]] e [[P-007 Marrow Water]] — forecast `Commit` non supportato dalle regole.
- Una call di settembre in `.raw/calls/` non ancora ingerita: la trova il battito, secchio «Da ingerire».
