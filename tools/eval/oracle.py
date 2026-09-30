#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oracle.py — calcola la risposta giusta invece di scriverla a mano.

Per le skill che producono numeri esiste una verifica piu' forte del confronto
con valori attesi: **una seconda implementazione, indipendente, della stessa
aritmetica**. Legge il frontmatter dei deal del fixture e ricalcola totali,
ponderato, copertura, commit/best-case, slittamenti e incoerenze.

Perche' non scrivere i numeri attesi in case.json:

  1. Se il fixture cambia, i valori attesi si aggiornano da soli. Un numero
     copiato a mano invecchia in silenzio e la suite comincia a misurare il
     passato.
  2. Costringe a esprimere le regole (Commit = L5+ & MEDDPICC>=7 & chiusura in
     trimestre) come codice eseguibile invece che come prosa in un prompt. Se
     le due implementazioni divergono, una delle due ha torto ed e' bene
     scoprirlo.
  3. Rende falsificabile "il modello ha sbagliato la somma": si sa di quanto.

L'oracolo NON e' la verita' assoluta: e' una seconda opinione scritta in un
linguaggio che non allucina. Le regole vengono da wiki/meta/pipeline-config.md.

Solo stdlib.
"""

import datetime as dt
import glob
import os
import re

# Regole da pipeline-config.md. Se cambiano li', cambiano qui, e la divergenza
# va notata: sono la stessa regola scritta due volte, di proposito.
COMMIT_MIN_PCT = 0.8      # L5+
COMMIT_MIN_MEDDPICC = 7
BESTCASE_MIN_PCT = 0.6    # L4+
BESTCASE_MIN_MEDDPICC = 6

QUOTA_BY_Q = {1: 650_000, 2: 800_000, 3: 850_000, 4: 1_100_000}
QUOTA_YEAR = 3_400_000

CLOSED_MARKERS = ("l6", "closed", "won", "lost")


def read_frontmatter(path):
    """Parser YAML piatto: coppie chiave: valore, niente annidamento.

    Il vault usa solo frontmatter piatto (convenzione in CLAUDE.md), quindi
    una dipendenza a yaml sarebbe costo senza beneficio. Se un giorno il
    frontmatter si annida, questo parser deve rompersi in modo rumoroso.
    """
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    data = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line.startswith(" "):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.split("  #")[0].strip().strip('"').strip("'")
        data[k.strip()] = v
    return data


def _num(v, default=0.0):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _date(v):
    try:
        return dt.date.fromisoformat(str(v).strip())
    except (TypeError, ValueError):
        return None


def is_open(fm):
    status = (fm.get("status") or "").strip().lower()
    if status in ("won", "lost", "closed"):
        return False
    stage = (fm.get("stage") or "").strip().lower()
    return not any(m in stage for m in CLOSED_MARKERS)


def compute(vault_dir, today):
    """Aggregati della pipeline aperta, piu' le incoerenze nei dati."""
    today = _date(today) or dt.date.today()
    quarter = (today.month - 1) // 3 + 1

    deals = []
    for path in sorted(glob.glob(os.path.join(vault_dir, "wiki", "pipeline", "*.md"))):
        if os.path.basename(path).startswith("_"):
            continue
        fm = read_frontmatter(path)
        if not fm.get("deal_id"):
            continue
        fm["_amount"] = _num(fm.get("amount_eur"))
        fm["_pct"] = _num(fm.get("stage_pct"))
        fm["_weighted_stored"] = _num(fm.get("weighted_eur"))
        fm["_weighted_calc"] = round(fm["_amount"] * fm["_pct"], 2)
        fm["_close"] = _date(fm.get("expected_close"))
        fm["_score"] = int(_num(fm.get("meddpicc_score")))
        fm["_open"] = is_open(fm)
        deals.append(fm)

    open_deals = [d for d in deals if d["_open"]]

    def in_quarter(d):
        return d["_close"] is not None and (d["_close"].month - 1) // 3 + 1 == quarter \
            and d["_close"].year == today.year

    commit = [d for d in open_deals if in_quarter(d)
              and d["_pct"] >= COMMIT_MIN_PCT and d["_score"] >= COMMIT_MIN_MEDDPICC]
    best = [d for d in open_deals if in_quarter(d)
            and d["_pct"] >= BESTCASE_MIN_PCT and d["_score"] >= BESTCASE_MIN_MEDDPICC]
    slipped = [d for d in open_deals if d["_close"] and d["_close"] < today]
    at_risk = [d for d in open_deals
               if (d.get("risk_flag") or "").strip().upper() in ("AT RISK", "AT-RISK", "RISK")]
    won = [d for d in deals if (d.get("status") or "").lower() == "won"
           or "won" in (d.get("stage") or "").lower()]

    def total(ds, key="_amount"):
        return round(sum(d[key] for d in ds), 2)

    def by(field, ds):
        out = {}
        for d in ds:
            out[(d.get(field) or "—").strip()] = round(out.get((d.get(field) or "—").strip(), 0) + d["_amount"], 2)
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    # Copertura: numeratore e denominatore devono riferirsi allo stesso
    # periodo. Il pesato dell'intera pipeline diviso la quota residua di UN
    # trimestre confronta due orizzonti diversi e gonfia il numero.
    w_q = round(sum(d["_weighted_calc"] for d in open_deals if in_quarter(d)), 2)
    quota_q = QUOTA_BY_Q.get(quarter, 0)
    closed_q = total([d for d in won if in_quarter(d)])
    weighted_open = total(open_deals, "_weighted_calc")
    remaining = max(quota_q - closed_q, 0)

    return {
        "today": today.isoformat(),
        "quarter": quarter,
        "n_deals": len(deals),
        "n_open": len(open_deals),
        "open_eur": total(open_deals),
        "weighted_open_eur": weighted_open,
        "quota_quarter": quota_q,
        "quota_year": QUOTA_YEAR,
        "closed_quarter_eur": closed_q,
        "commit_eur": total(commit),
        "commit_ids": [d["deal_id"] for d in commit],
        "best_case_eur": total(best),
        "best_case_ids": [d["deal_id"] for d in best],
        "weighted_in_quarter_eur": w_q,
        "coverage_in_quarter": round(w_q / remaining, 2) if remaining else None,
        "coverage": round(weighted_open / remaining, 2) if remaining else None,
        "n_slipped": len(slipped),
        "slipped_eur": total(slipped),
        "slipped_ids": [d["deal_id"] for d in slipped],
        "n_at_risk": len(at_risk),
        "at_risk_eur": total(at_risk),
        "at_risk_ids": [d["deal_id"] for d in at_risk],
        "amounts_by_id": {d["deal_id"]: d["_amount"] for d in open_deals},
        "by_vertical": by("vertical", open_deals),
        "by_country": by("country", open_deals),
        "by_channel": by("channel_type", open_deals),
        "inconsistencies": find_inconsistencies(open_deals, in_quarter),
    }


def find_inconsistencies(open_deals, in_quarter):
    """I difetti nei dati che la skill deve dichiarare invece di ripulire.

    La regola della skill e' 'report faithfully': un totale pulito ottenuto
    ignorando una categoria di forecast sbagliata e' peggio di un numero
    sporco dichiarato tale, perche' non si vede.
    """
    out = []
    for d in open_deals:
        cat = (d.get("forecast_cat") or "").strip().lower()
        did = d["deal_id"]
        if abs(d["_weighted_stored"] - d["_weighted_calc"]) > 1:
            out.append({"deal_id": did, "kind": "weighted_drift",
                        "detail": f"weighted_eur {d['_weighted_stored']:.0f} "
                                  f"ma amount x stage_pct = {d['_weighted_calc']:.0f}"})
        if cat == "commit" and not (d["_pct"] >= COMMIT_MIN_PCT
                                    and d["_score"] >= COMMIT_MIN_MEDDPICC and in_quarter(d)):
            out.append({"deal_id": did, "kind": "forecast_cat_non_valida",
                        "detail": f"marcato Commit ma stage_pct={d['_pct']}, "
                                  f"MEDDPICC={d['_score']}, chiusura {d.get('expected_close')}"})
        if cat == "best case" and not (d["_pct"] >= BESTCASE_MIN_PCT
                                       and d["_score"] >= BESTCASE_MIN_MEDDPICC and in_quarter(d)):
            out.append({"deal_id": did, "kind": "forecast_cat_non_valida",
                        "detail": f"marcato Best Case ma stage_pct={d['_pct']}, "
                                  f"MEDDPICC={d['_score']}, chiusura {d.get('expected_close')}"})
        if not d.get("expected_close"):
            out.append({"deal_id": did, "kind": "close_date_mancante",
                        "detail": "expected_close vuoto"})
    return out


if __name__ == "__main__":
    import json
    import sys
    vault = sys.argv[1]
    today = sys.argv[2] if len(sys.argv) > 2 else dt.date.today().isoformat()
    print(json.dumps(compute(vault, today), indent=2, ensure_ascii=False))
