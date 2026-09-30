---
description: Lint del vault — igiene dati, provenienza, coerenza pipeline. Genera wiki/meta/lint-report.md
allowed-tools: Bash(sh tools/lint/run.sh)
argument-hint: (nessun argomento)
---

# Lint del vault

Output del lint:

```!
sh tools/lint/run.sh
```

Leggi l'output qui sopra e comportati così:

1. **Se ci sono ERROR**, elencali per gravità pratica, non nell'ordine in cui compaiono.
   Metti per primi: riconciliazione e provenienza (un numero che nessuna fonte sostiene),
   poi le reason di chiusura mancanti, poi frontmatter e link.
2. **Per ogni finding, proponi la correzione concreta** — non ripetere il messaggio del lint.
   Se la correzione richiede un fatto che non è nel vault (una data di chiusura reale, un
   lost reason, una tariffa), **dillo e fermati**: quel dato non si inventa.
3. **Non correggere niente senza conferma.** Elenca, proponi, aspetta.
4. Chiudi dicendo **quanti ERROR si potrebbero chiudere senza input esterno** e di quanto
   si potrebbe abbassare la soglia in `tools/lint/error-baseline.txt`.

Regole del vault da tenere presenti: `pipeline_eur` è solo pipeline aperta e il vinto sta in
`won_eur`; `status` è lo stato e `maturity` la maturità della pagina; `[da compilare]` non
conta come compilato. Riferimenti: `wiki/meta/pipeline-config.md`,
`wiki/meta/frontmatter-schema.md`, `wiki/meta/vault-usage-guide.md`.
