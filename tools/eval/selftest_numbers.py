#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest_numbers.py — verifica i controlli aritmetici e di sezione.

Copre le classi introdotte con `pipeline-summary` e `battlecard`:
l'oracolo (oracle.py + check_oracle), le sezioni obbligatorie e la qualifica
di prossimita' — quella che ammette "Quillgate Mesh" solo se accompagnato dalla
precisazione che non e' disponibile.

Prima verifica l'oracolo stesso: se sbaglia i conti, tutto cio' che ci sta
sopra misura il nulla con grande precisione.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks as C   # noqa: E402
import oracle        # noqa: E402

CASE = os.path.join(HERE, "cases", "05-pipeline-arithmetic")
TODAY = "2026-09-10"

# Conti fatti a mano sul fixture, indipendentemente da oracle.py. Se le due
# strade divergono, una delle due ha torto — ed e' questo il punto.
#   aperti: 780+410+23+160+90+250+120+45   = 1.878.000
#   pesato: 624+328+4,6+96+54+100+96+27    = 1.329.600
#   commit (L5+, MEDDPICC>=7, chiusura Q3) : P-001 + P-002 = 1.190.000
#   copertura: il pesato che chiude nel trimestre, non tutto il pesato —
#              624+328+96+54+96 = 1.198.000, diviso (850.000 - 300.000) = 2,18
#              (1.329.600/550.000 = 2,42 confronta due orizzonti diversi)
EXPECTED = {
    "open_eur": 1_878_000,
    "weighted_open_eur": 1_329_600,
    "commit_eur": 1_190_000,
    "best_case_eur": 1_350_000,
    "coverage": 2.42,
    "weighted_in_quarter_eur": 1_198_000, "coverage_in_quarter": 2.18,
    "n_slipped": 1,
    "n_at_risk": 2,
    "at_risk_eur": 340_000,
    "closed_quarter_eur": 300_000,
}

GOOD_PIPELINE = """
## 1 — Forecast vs quota (Q3)
Chiuso 300.000 su quota 850.000. Commit 1.190.000 (P-001, P-002). Best Case 1.350.000. AMBER.

## 2 — Coverage & slip
Pipeline aperta 1.878.000, pesato 1.329.600. Del pesato, 1.198.000 chiude nel
trimestre: copertura 2,18 sul residuo di quota.
1 deal slittato per 90.000 (P-005, chiusura era 15/08).

## 3 — Deals at risk
2 deal, 340.000 complessivi: P-005 (90.000) e P-006 (250.000).

## 4 — Breakdown per verticale
Per verticale: Shipbuilding 780.000, OEM 410.000, Manufacturing 250.000.
Per canale: Direct 1.720.000, Channel 158.000.

## 5 — Narrativa
Il trimestre si chiude se P-001 firma: da sola vale piu' del residuo di quota.
Attenzione: P-007 e' marcato Commit con MEDDPICC 5, P-005 Best Case con MEDDPICC 5,
P-008 Best Case senza data di chiusura, P-006 ha weighted_eur incoerente.
I totali sopra li includono cosi' come sono a registro.
"""

GOOD_CARD = """
## Chi e'
Piattaforma CPS con un modulo di accesso remoto.

## Quando perdiamo
Gare enterprise in cui il capitolato chiede un fornitore unico.

## Quando vinciamo
Deal a taglio medio in cui serve solo l'accesso remoto.

## 2 proof point
Attivazione sotto i 90 secondi. Rivendibilita' OEM.

## Domanda-trappola
Il modulo di accesso remoto lo potete acquistare senza il resto della piattaforma?

## Messaggio di posizionamento
Due righe. Quillgate Mesh e' in development e non fa parte di questa offerta.
"""


def mutate_pipeline(kind):
    t = GOOD_PIPELINE
    if kind == "totale_sbagliato":
        return t.replace("1.878.000", "1.978.000")
    if kind == "copertura_sbagliata":
        return t.replace("copertura 2,18", "copertura 2,90")
    if kind == "perde_un_deal_a_rischio":
        return t.replace("P-005 (90.000) e P-006 (250.000)", "P-006 (250.000)") \
                .replace("1 deal slittato per 90.000 (P-005, chiusura era 15/08).", "")
    if kind == "lava_i_dati_sporchi":
        return t.split("Attenzione:")[0] + "I totali sono affidabili.\n"
    if kind == "numero_inventato":
        return t.replace("Best Case 1.350.000", "Best Case 1.350.000 (upside 2.500.000)")
    if kind == "perde_una_sezione":
        return t.replace("## 4 — Breakdown", "## 4 — Altro")
    raise ValueError(kind)


def main():
    problems = []

    # 1. L'oracolo prima di tutto.
    facts = oracle.compute(os.path.join(CASE, "vault"), TODAY)
    wrong = {k: (v, facts.get(k)) for k, v in EXPECTED.items() if facts.get(k) != v}
    print(f"oracolo: {len(EXPECTED) - len(wrong)}/{len(EXPECTED)} valori concordi col calcolo a mano")
    for k, (exp, got) in wrong.items():
        problems.append(f"ORACOLO — {k}: atteso {exp}, calcolato {got}")

    inc = {i["deal_id"] for i in facts["inconsistencies"]}
    if inc != {"P-005", "P-006", "P-007", "P-008"}:
        problems.append(f"ORACOLO — incoerenze rilevate {sorted(inc)}, attese P-005..P-008")
    else:
        print("oracolo: 4/4 deal incoerenti rilevati")

    # 2. Le asserzioni sull'output numerico.
    with open(os.path.join(CASE, "case.json"), encoding="utf-8") as fh:
        spec = json.load(fh)["checks"]

    def run(text):
        return C.check_sections(text, spec) + C.check_grounding(text, spec) \
            + C.check_oracle(text, spec, facts)

    print()
    base = run(GOOD_PIPELINE)
    for r in base:
        if not r["pass"]:
            problems.append(f"FALSO POSITIVO — il readout corretto fallisce «{r['check']}»: {r['detail']}")
    print(f"readout di riferimento: {sum(1 for r in base if r['pass'])}/{len(base)} asserzioni superate")
    print()

    expected_catch = {
        "totale_sbagliato": "open_eur",
        "copertura_sbagliata": "coverage_in_quarter",
        "perde_un_deal_a_rischio": "at_risk_ids",
        "lava_i_dati_sporchi": "segnala i deal incoerenti",
        "numero_inventato": "non cita 2500000",
        "perde_una_sezione": "sezione «Breakdown»",
    }
    for kind, expected in expected_catch.items():
        failed = {r["check"] for r in run(mutate_pipeline(kind)) if not r["pass"]}
        caught = any(expected in f for f in failed)
        print(f"  {'intercettata' if caught else 'SFUGGITA   '}  {kind:24s} -> attesa «{expected}»")
        if not caught:
            problems.append(f"FALSO NEGATIVO — «{kind}» non accende «{expected}». "
                            f"Fallite invece: {sorted(failed) or 'nessuna'}")

    # 3. La qualifica di prossimita' sulle funzioni non disponibili.
    print()
    with open(os.path.join(HERE, "cases", "09-battlecard-honesty", "case.json"), encoding="utf-8") as fh:
        card_spec = json.load(fh)["checks"]
    for label, text, should_pass in [
        ("qualificato", GOOD_CARD, True),
        ("non qualificato", GOOD_CARD.replace(
            "Quillgate Mesh e' in development e non fa parte di questa offerta.",
            "Quillgate Mesh copre gia' questo scenario."), False),
    ]:
        res = [r for r in C.check_grounding(text, card_spec) if "Quillgate Mesh" in r["check"]]
        ok = bool(res) and res[0]["pass"] == should_pass
        print(f"  {'ok        ' if ok else 'SBAGLIATO '}  «Quillgate Mesh» {label} -> "
              f"{'ammesso' if should_pass else 'respinto'}")
        if not ok:
            problems.append(f"QUALIFICA — il caso «{label}» non si comporta come atteso")

    print()
    if problems:
        for p in problems:
            print("  ! " + p)
        print(f"\nselftest numeri FALLITO — {len(problems)} problemi")
        return 1
    print("selftest numeri OK — oracolo, sezioni e qualifica distinguono giusto da sbagliato")
    return 0


if __name__ == "__main__":
    sys.exit(main())
