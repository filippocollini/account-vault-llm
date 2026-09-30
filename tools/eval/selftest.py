#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest.py — chi controlla i controlli.

Una suite di eval ha un modo silenzioso di essere inutile: passare sempre.
Se le asserzioni sono scritte larghe, il report e' verde qualunque cosa
produca il modello, e la suite diventa un rituale invece di una misura.

Questo file lo esclude. Prende un output corretto scritto a mano, ne produce
delle versioni deliberatamente rotte — una per ciascun modo di fallire che la
suite dovrebbe intercettare — e verifica che il controllo giusto si accenda su
ognuna. Se una mutazione passa, la suite non serve.

Non chiama nessun modello. Gira in un secondo. Va in CI.

    python3 tools/eval/selftest.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks as C  # noqa: E402

# --------------------------------------------------------------------------
# Output di riferimento per il caso 01: quello che la skill deve produrre.
# --------------------------------------------------------------------------

GOOD_01 = """
## Northwind Marine — MEDDPICC

| Dimension | Stato | Fonte / nota |
|---|---|---|
| **M**etrics | Parziale — €195.000/12 mesi sulla tranche Kalmar (300 gateway x €650) | pagina account |
| **E**conomic Buyer | **Gap** — mai incontrato. M. Falk citato per la firma, zero contatti | frontmatter vuoto |
| **D**ecision Criteria | Continuita' del supporto + termini commerciali — inferito, non confermato | call 18 giu |
| **D**ecision Process | Sconosciuto — nessun passaggio ne' data documentati | — |
| **P**aper Process | Sconosciuto — legal e security review non mappati | — |
| **I**dentify Pain | EOS marzo 2027 contro manutenzione contrattualizzata fino al 2029 | call 18 giu, per iscritto |
| **C**hampion | Non identificato — Sollner e' referente tecnico, dichiara di non avere budget | call 18 giu |
| **C**ompetition | Nessun concorrente nominato dal cliente | — |

**Gap critici**

1. Economic Buyer mai incontrato su €780.000 allo stadio 5 — si negozia senza sapere chi firma.
2. Nessun champion: Sollner non porta il caso quando non ci siamo.
3. Decision Process e Paper Process sconosciuti a due mesi dalla chiusura attesa.

**Azione per gap**

- Chiedere a Sollner un'introduzione a Falk entro venerdi', motivata dalla scadenza EOS (Alex)
- Proporre a Sollner di costruire insieme il business case interno sui 4 siti (Alex)
- Mappare in call le date di legal e procurement, con la firma del 15 dicembre come vincolo (Alex)
"""


def mutate(text, kind):
    """Le rotture che la suite deve vedere. Una per modo di fallire."""
    if kind == "papera_il_gap":
        # Il fallimento numero uno: riempire la casella vuota.
        return text.replace(
            "| **E**conomic Buyer | **Gap** — mai incontrato. M. Falk citato per la firma, zero contatti | frontmatter vuoto |",
            "| **E**conomic Buyer | M. Falk, ufficio acquisti | pagina account |")
    if kind == "promuove_il_tecnico":
        return text.replace(
            "| **C**hampion | Non identificato — Sollner e' referente tecnico, dichiara di non avere budget | call 18 giu |",
            "| **C**hampion | Ingrid Sollner, OT manager | call 18 giu |")
    if kind == "inventa_concorrente":
        return text.replace(
            "| **C**ompetition | Nessun concorrente nominato dal cliente | — |",
            "| **C**ompetition | In gara contro Halberd | — |")
    if kind == "perde_le_azioni":
        return text.split("**Azione per gap**")[0]
    if kind == "azioni_senza_owner":
        return text.replace(" (Alex)", "")
    if kind == "sbaglia_importo":
        return text.replace("€195.000", "€400.000").replace("780.000", "1.200.000")
    if kind == "perde_una_dimensione":
        return "\n".join(l for l in text.splitlines() if "**P**aper Process" not in l)
    if kind == "cancella_inferenza":
        # Presenta come confermato cio' che era inferito.
        return text.replace("— inferito, non confermato", "— confermati dal cliente")
    raise ValueError(kind)


# mutazione -> il controllo che DEVE fallire
EXPECTED = {
    "papera_il_gap":        "economic_buyer dichiarato scoperto",
    "promuove_il_tecnico":  "champion dichiarato scoperto",
    "inventa_concorrente":  "non inventa «Halberd»",
    "perde_le_azioni":      "sezione-azioni-presente",
    "azioni_senza_owner":   "azioni-con-owner",
    "sbaglia_importo":      "cita 780000",
    "perde_una_dimensione": "tabella-8-dimensioni",
    "cancella_inferenza":   "decision_criteria marcato come inferito",
}


# Il filtro "questo bullet e' un gap o dice che non ce ne sono?" ha gia'
# sbagliato una volta: scartava "Nessun champion: ..." trattandolo come
# dichiarazione di assenza. Da allora ha i suoi casi.
GAP_LINES = [
    ("Nessun gap critico",                                   False),
    ("Nessuno",                                              False),
    ("None",                                                 False),
    ("Non ci sono elementi bloccanti",                       False),
    ("Nessun champion: Sollner non porta il caso",           True),
    ("Nessun processo decisionale documentato",              True),
    ("Economic Buyer mai incontrato su 780.000 euro",        True),
]


def check_gap_filter():
    bad = []
    for line, is_real in GAP_LINES:
        got = not C.is_no_gap_line(line)
        if got != is_real:
            bad.append(f"«{line}» -> {'gap' if got else 'assenza'}, atteso {'gap' if is_real else 'assenza'}")
    print(f"filtro gap: {len(GAP_LINES) - len(bad)}/{len(GAP_LINES)} righe classificate correttamente")
    return [f"FILTRO GAP — {b}" for b in bad]


def run_checks(text, spec):
    return C.check_structure(text, spec) + C.check_grounding(text, spec)


def main():
    spec_file = os.path.join(HERE, "cases", "01-missing-eb-high-value", "case.json")
    with open(spec_file, encoding="utf-8") as fh:
        spec = json.load(fh)["checks"]

    problems = check_gap_filter()
    print()

    # 1. L'output corretto deve passare tutto. Se no, le asserzioni sono
    #    troppo strette e la suite produrra' rumore invece di segnale.
    base = run_checks(GOOD_01, spec)
    for r in base:
        if not r["pass"]:
            problems.append(f"FALSO POSITIVO — l'output corretto fallisce «{r['check']}»: {r['detail']}")
    print(f"riferimento corretto: {sum(1 for r in base if r['pass'])}/{len(base)} asserzioni superate")

    # 2. Ogni rottura deve accendere il controllo giusto, e solo per quello.
    print()
    for kind, expected_check in EXPECTED.items():
        res = run_checks(mutate(GOOD_01, kind), spec)
        failed = {r["check"] for r in res if not r["pass"]}
        caught = expected_check in failed
        print(f"  {'intercettata' if caught else 'SFUGGITA   '}  {kind:22s} -> attesa «{expected_check}»")
        if not caught:
            problems.append(
                f"FALSO NEGATIVO — la rottura «{kind}» non accende «{expected_check}». "
                f"Fallite invece: {sorted(failed) or 'nessuna'}")

    print()
    if problems:
        for p in problems:
            print("  ! " + p)
        print(f"selftest testo FALLITO — {len(problems)} problemi nelle asserzioni")
    else:
        print("selftest testo OK — le asserzioni distinguono un output corretto da uno rotto")

    # Le altre due suite coprono le classi introdotte dopo deal-review:
    # l'aritmetica (oracolo, sezioni, qualifica) e lo stato del vault.
    # Un solo comando le esegue tutte, altrimenti se ne dimentica una.
    import selftest_numbers
    import selftest_state
    rc = 1 if problems else 0
    for name, mod in (("numeri", selftest_numbers), ("stato", selftest_state)):
        print("\n" + "-" * 68 + f"\n{name}\n" + "-" * 68)
        rc |= mod.main()
    print()
    print("SELFTEST COMPLESSIVO:", "OK" if rc == 0 else "FALLITO")
    return rc


if __name__ == "__main__":
    sys.exit(main())
