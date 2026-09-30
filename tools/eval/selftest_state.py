#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest_state.py — verifica i controlli di stato (statecheck.py).

Stessa logica di selftest.py, applicata alla skill che scrive: si costruisce
il vault "dopo" corretto, lo si rompe in cinque modi, e si verifica che ogni
rottura accenda il controllo giusto.

Serve piu' qui che altrove. I controlli di stato sono i piu' complicati del
progetto — confronti di hash, sentinelle CHANGED/UNCHANGED, ordine delle voci
di log — quindi sono i piu' facili da scrivere in modo che non falliscano mai.

Non chiama nessun modello.
"""

import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import statecheck  # noqa: E402

CASE = os.path.join(HERE, "cases", "11-account-note-write")
FIXTURE = os.path.join(CASE, "vault")

ACCOUNT = "wiki/stakeholders/Brenner Mobility.md"
DEAL = "wiki/pipeline/P-008 Brenner Mobility.md"
OTHER = "wiki/stakeholders/Talvik Steel.md"

INTERAZIONI = """
## Interazioni

### 2026-09-09 — call
- Anna Kofler (Head of Maintenance) porta il caso al comitato investimenti di ottobre
- Luca Varesi chiede se l'agente edge gira su ARM: verifica col team prodotto entro venerdi'
- Nessuna data di chiusura concordata: dipende dal comitato
"""

LOG_ENTRY = """## 2026-09-10 — Call Brenner Mobility, Kofler si espone
Kofler porta il caso al comitato di ottobre. Aperta la verifica ARM sull'agente edge.
"""


def edit(path, fn):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(fn(text))


def set_fm(text, key, value):
    return re.sub(rf"^{re.escape(key)}:.*$", f"{key}: {value}", text, count=1, flags=re.M)


def build_good():
    """Il vault come dovrebbe essere dopo una NOTE eseguita correttamente."""
    tmp = tempfile.mkdtemp(prefix="selftest-after-")
    shutil.copytree(FIXTURE, tmp, dirs_exist_ok=True)

    edit(os.path.join(tmp, ACCOUNT), lambda t: set_fm(
        set_fm(t, "champion", '"Anna Kofler — Head of Maintenance"'),
        "updated", "2026-09-10") + INTERAZIONI)

    edit(os.path.join(tmp, DEAL), lambda t: set_fm(
        set_fm(t, "next_action", "\"Verificare col team prodotto il supporto ARM dell'agente edge\""),
        "last_update", "2026-09-10")
        + "\n### 2026-09-09\n- Kofler al comitato di ottobre; verifica ARM aperta\n")

    edit(os.path.join(tmp, "wiki/log.md"),
         lambda t: t.replace("## 2026-08-30", LOG_ENTRY + "\n## 2026-08-30", 1))
    edit(os.path.join(tmp, "wiki/hot.md"),
         lambda t: t.replace("## Last Updated",
                             "## Last Updated\n\n**2026-09-10 — Brenner Mobility: "
                             "Kofler porta il caso al comitato di ottobre.**", 1))
    return tmp


MUTATIONS = {
    # (descrizione) -> (funzione che rompe, frammento del controllo atteso)
    "danno_collaterale": (
        lambda d: edit(os.path.join(d, OTHER), lambda t: set_fm(t, "risk", "monitor")),
        "intatti gli altri"),
    "stadio_avanzato": (
        lambda d: edit(os.path.join(d, DEAL), lambda t: set_fm(t, "stage", '"L5 — Negotiation"')),
        "stage = UNCHANGED"),
    "data_inventata": (
        lambda d: edit(os.path.join(d, DEAL), lambda t: set_fm(t, "expected_close", "2026-10-31")),
        "expected_close = EMPTY"),
    "next_action_vuoto": (
        lambda d: edit(os.path.join(d, DEAL), lambda t: set_fm(t, "next_action", '""')),
        "next_action = NONEMPTY"),
    "log_in_fondo": (
        lambda d: edit(os.path.join(d, "wiki/log.md"),
                       lambda t: t.replace(LOG_ENTRY + "\n", "") + "\n" + LOG_ENTRY),
        "voce di log in cima"),
    "champion_non_scritto": (
        lambda d: edit(os.path.join(d, ACCOUNT), lambda t: set_fm(t, "champion", '""')),
        "champion = Kofler"),
}


def run(after_dir, spec):
    return statecheck.check_state(FIXTURE, after_dir, spec)


def main():
    with open(os.path.join(CASE, "case.json"), encoding="utf-8") as fh:
        spec = json.load(fh)["checks"]

    problems = []
    good = build_good()
    try:
        base = run(good, spec)
        for r in base:
            if not r["pass"]:
                problems.append(f"FALSO POSITIVO — il vault corretto fallisce «{r['check']}»: {r['detail']}")
        print(f"vault di riferimento: {sum(1 for r in base if r['pass'])}/{len(base)} asserzioni superate")
        print()

        for name, (breaker, expected) in MUTATIONS.items():
            broken = tempfile.mkdtemp(prefix="selftest-broken-")
            try:
                shutil.copytree(good, broken, dirs_exist_ok=True)
                breaker(broken)
                failed = {r["check"] for r in run(broken, spec) if not r["pass"]}
                caught = any(expected in f for f in failed)
                print(f"  {'intercettata' if caught else 'SFUGGITA   '}  {name:22s} -> attesa «{expected}»")
                if not caught:
                    problems.append(
                        f"FALSO NEGATIVO — «{name}» non accende «{expected}». "
                        f"Fallite invece: {sorted(failed) or 'nessuna'}")
            finally:
                shutil.rmtree(broken, ignore_errors=True)
    finally:
        shutil.rmtree(good, ignore_errors=True)

    print()
    if problems:
        for p in problems:
            print("  ! " + p)
        print(f"\nselftest stato FALLITO — {len(problems)} problemi")
        return 1
    print("selftest stato OK — i controlli di stato distinguono un vault corretto da uno rotto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
