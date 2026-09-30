---
type: meta
title: "Frontmatter schema (generato)"
created: 2026-09-10
updated: 2026-09-10
tags:
  - meta
  - schema
maturity: generated
related:
  - "[[vault-usage-guide]]"
  - "[[pipeline-config]]"
---

# Frontmatter schema

Navigation: [[../index]] | [[vault-usage-guide]]

> [!warning] Pagina generata — non editare a mano
> Prodotta da `python3 tools/lint/vault.py --emit-schema`. La definizione vive nel
> codice del lint, che è anche ciò che la verifica: **una sola fonte**. Prima lo schema
> stava in tre posti (`_templates/`, il blocco YAML in `stakeholders/_index.md`, e le
> aspettative implicite delle skill) e derivavano l'uno dall'altro.

## Le due chiavi che venivano confuse

- **`status` = stato.** Solo sui tipi che hanno un ciclo di vita. `deals.base` filtra su questo.
- **`maturity` = maturità della pagina.** Quanto è completa e curata, non cosa sta succedendo.

Erano la stessa chiave: su 13 note erano stati scritti entrambi i significati e YAML
tiene l'ultimo, quindi lo stato reale si perdeva in silenzio (`done` sovrascritto da
`mature`, `in-progress` da `developing`).

## Campi obbligatori su ogni nota

`type`, `created`, `updated`, `tags`

## Per tipo

| type | `status` ammessi | usa `maturity`? | altri campi obbligatori |
|---|---|---|---|
| `decision` | `active`, `done`, `pending`, `resolved`, `superseded` | opzionale | `date`, `owner` |
| `deliverable` | `active`, `cancelled`, `done`, `in-progress` | opzionale | `date`, `owner` |
| `index` | — (non usa status) | **sì, obbligatoria** | — |
| `intel` | `active`, `archived` | opzionale | `date` |
| `meeting` | `cancelled`, `done`, `pending` | opzionale | `date`, `account` |
| `meta` | — (non usa status) | **sì, obbligatoria** | — |
| `opportunity` | `lost`, `open`, `won` | opzionale | `deal_id`, `account`, `stage`, `stage_pct`, `forecast_cat`, `amount_eur`, `expected_close`, `owner`, `channel_type`, `status` |
| `overview` | — (non usa status) | **sì, obbligatoria** | — |
| `source` | `active`, `archived` | opzionale | `source_type` |
| `stakeholder` | — (non usa status) | **sì, obbligatoria** | — |

`maturity` ammessi su qualunque tipo: `developing`, `evergreen`, `generated`, `mature`, `seed`

## Pagine partner

Una nota `stakeholder` con `partner` fra i tag deve dichiarare anche `partner_type` e
`partner_autonomy`. Valori ammessi per l'autonomia, dal meno al più autonomo: `none`, `assisted`, `semi-autonomous`, `autonomous`.
L'autonomia è la metrica dell'enablement: dichiararla obbliga a dire cosa manca per
salire di livello.

## Grafie prodotto non approvate

| Trovata | Da usare |
|---|---|
| `QG Mesh` | Quillgate Mesh (nome approvato, In Development) | 
| `QGA` | Quillgate Access | 
| `Quillgate 2` | Quillgate Mesh (nome approvato, In Development) | 
| `Quillgate Remote` | Quillgate Access | 

## Regole verificate altrove

- Definizione di `pipeline_eur` / `won_eur` e reason obbligatorie sulle chiusure: [[pipeline-config]].
- Ogni voce `sources:` che punta a `.raw/` deve puntare a un file esistente, altrimenti
  le affermazioni della pagina non sono ri-derivabili dal vault.
- I template in `_templates/` sono verificati contro questo schema: un default fuori
  vocabolario è un ERROR, perché ogni nota creata da quel template nasce sbagliata.

