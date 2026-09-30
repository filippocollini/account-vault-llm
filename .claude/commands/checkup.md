---
description: Verifica che il vault e il suo tooling siano allineati, poi proponi il prossimo passo
allowed-tools: Bash(sh tools/lint/run.sh), Bash(python3 tools/lint/vault.py *), Bash(python3 tools/eval/*), Bash(git *), Bash(test *), Bash(ls *), Bash(diff *), Bash(cmp *)
argument-hint: (nessun argomento)
---

# Checkup del vault

Prima di qualunque altra cosa leggi, in quest'ordine: `wiki/hot.md`,
`wiki/meta/vault-usage-guide.md`, `wiki/meta/lint-report.md`. Poi verifica i punti sotto.

Se il vault è fatto bene, questi tre file ti bastano per sapere dove siamo. **Se non ti bastano,
quello è il primo finding da riportare.**

## 1. Verifiche tecniche

Un numero diverso dall'atteso non è un errore: è un'informazione, e va spiegata.

```!
echo "── lint ─────────────────────────────"; sh tools/lint/run.sh 2>&1 | head -18
echo; echo "── idempotenza ──────────────────────"
cp wiki/meta/lint-report.md /tmp/_r1.md 2>/dev/null
sh tools/lint/run.sh >/dev/null 2>&1
cmp -s /tmp/_r1.md wiki/meta/lint-report.md && echo "OK: due run producono un report identico" || echo "ATTENZIONE: il report non è deterministico"
echo; echo "── schema allineato al codice ───────"
python3 tools/lint/vault.py --emit-schema >/dev/null 2>&1
git diff --quiet wiki/meta/frontmatter-schema.md 2>/dev/null && echo "OK: lo schema pubblicato corrisponde al codice del lint" || echo "ATTENZIONE: schema pubblicato diverso da quello nel codice (rigenerato ora)"
echo; echo "── gate pre-commit ──────────────────"
test -x .git/hooks/pre-commit && echo "hook installato ed eseguibile" || echo "MANCANTE: cp tools/githooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit"
cmp -s tools/githooks/pre-commit .git/hooks/pre-commit && echo "hook attivo identico a quello versionato" || echo "ATTENZIONE: hook attivo diverso dal versionato"
echo "soglia ERROR: $(cat tools/lint/error-baseline.txt)"
echo; echo "── eval ─────────────────────────────"
python3 tools/eval/selftest.py 2>&1 | tail -1
python3 tools/eval/run.py 2>&1 | grep -E '^\[|fallite'
echo; echo "── stato git ────────────────────────"
git status --short | head -30
```

## 2. Riporta così

1. **Allineato / non allineato**, con ogni scostamento spiegato.
2. **Se `hot.md` + `vault-usage-guide` + `lint-report` non ti sono bastati** per capire lo stato,
   dillo: è il difetto più importante da correggere.
3. **Il prossimo passo che proponi**, con il perché. I candidati aperti sono nel debito
   dichiarato di `wiki/meta/vault-usage-guide.md` e nelle ultime voci di `wiki/log.md`.

**Non correggere niente e non committare niente in questo giro.** Verifica, riporta, proponi.
Se una correzione richiede un fatto che non è nel vault — una data di chiusura vera, un lost
reason, una tariffa — dillo e fermati: quei dati non si inventano.
