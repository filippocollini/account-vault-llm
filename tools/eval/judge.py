#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
judge.py — CLASSE 3: le asserzioni che richiedono giudizio.

Qui, e solo qui, si usa un modello per valutare. La regola per finire in questo
file e' una sola:

    se esiste un modo di verificarlo con un parser, non passa da qui.

Cosa resta davvero: "il gap messo al primo posto e' quello giusto?". Non e'
esprimibile come regola perche' dipende dal merito del caso.

Due precauzioni, perche' un giudice e' a sua volta non deterministico:

  1. Il giudice vede la rubrica e l'output, NON la risposta attesa. Altrimenti
     valuta la somiglianza a un testo invece del merito.
  2. Ogni asserzione viene votata piu' volte (default 3) e si prende la
     maggioranza. Il tasso di disaccordo viene riportato: se un'asserzione fa
     2-1 in modo sistematico, il problema e' la rubrica, non il sistema.

Il giudizio e' marcato come tale nel report finale. Non ha lo stesso peso
probatorio di un parsing e non deve sembrare che ce l'abbia.
"""

import json
import re
import subprocess
from collections import Counter

RUBRIC = """Sei un valutatore. Ricevi l'output di una qualificazione commerciale
MEDDPICC e una singola domanda di valutazione. Rispondi solo alla domanda posta.

Non giudicare stile, lunghezza o formattazione. Non premiare la sicurezza del tono.
Se l'output non contiene abbastanza per decidere, la risposta e' false.

Rispondi ESCLUSIVAMENTE con questo JSON, senza testo attorno:
{"verdict": true|false, "reason": "<max 25 parole>"}

--- DOMANDA ---
{question}

--- OUTPUT DA VALUTARE ---
{output}
--- FINE OUTPUT ---
"""


def _ask(question, output, model, timeout):
    prompt = RUBRIC.replace("{question}", question).replace("{output}", output)
    try:
        p = subprocess.run(
            ["claude", "-p", prompt, "--model", model],
            capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return None, "CLI 'claude' non trovata"
    except subprocess.TimeoutExpired:
        return None, "timeout"
    if p.returncode != 0:
        return None, (p.stderr or "").strip()[:120]
    m = re.search(r"\{.*\}", p.stdout, re.S)
    if not m:
        return None, "nessun JSON nella risposta del giudice"
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, "JSON del giudice non valido"
    return bool(data.get("verdict")), str(data.get("reason", ""))[:160]


def check_judgment(text, spec, model="claude-sonnet-5", votes=3, timeout=120):
    """Vota ogni asserzione di giudizio `votes` volte e prende la maggioranza."""
    out = []
    for item in spec.get("judgment", []):
        ballots, reasons = [], []
        for _ in range(votes):
            verdict, reason = _ask(item["question"], text, model, timeout)
            if verdict is None:
                out.append({"class": "judgment", "check": item["id"], "pass": None,
                            "detail": f"non valutato: {reason}"})
                ballots = []
                break
            ballots.append(verdict)
            reasons.append(reason)
        if not ballots:
            continue
        tally = Counter(ballots)
        winner, count = tally.most_common(1)[0]
        agreement = count / len(ballots)
        note = reasons[ballots.index(winner)]
        out.append({
            "class": "judgment",
            "check": item["id"],
            "pass": winner,
            "detail": f"{count}/{len(ballots)} concordi — {note}",
            "agreement": round(agreement, 2),
        })
    return out
