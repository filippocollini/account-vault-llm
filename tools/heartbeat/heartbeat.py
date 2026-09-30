#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Battito settimanale del vault — quello che si è mosso, e quello che è rimasto fermo.

Non è un secondo lint. `tools/lint/vault.py` misura lo **stato** (il frontmatter è
completo? i link risolvono? i totali tornano?) e serve a bloccare un commit. Questo
misura il **movimento**: cosa è cambiato dall'ultimo battito, cosa scade adesso, e
cosa è rimasto in silenzio quando invece avrebbe dovuto muoversi.

La ragione per cui esiste è una diagnosi fatta sul vault originale: quasi tutte le deal
aperte non toccate da oltre 30 giorni, la maggior parte del valore aperto con
`expected_close` già passata, il correction log fermo da settimane. Niente di tutto questo
era rotto — era solo che nessuno lo guardava, perché guardarlo richiedeva di ricordarsi di
farlo. Il battito toglie quel "ricordarsi".

    python3 tools/heartbeat/heartbeat.py                # aggiorna snapshot e report
    python3 tools/heartbeat/heartbeat.py --no-state     # prova senza toccare lo snapshot
    python3 tools/heartbeat/heartbeat.py --today 2026-10-01

Lo snapshot vive in `tools/heartbeat/state.json` ed è committato: è lui che rende
possibile il confronto settimana su settimana, e git ne tiene la storia gratis.

Questo script non scrive mai nel vault a parte il proprio report, e non manda niente
a nessuno. Le bozze le produce la skill `battito` leggendo questo report.
"""
from __future__ import print_function

import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "lint"))

# Il parsing del frontmatter, la nozione di "ultima interazione" e la formattazione
# degli euro sono già definiti una volta sola nel lint. Riusarli tiene le due viste
# d'accordo: se cambia la definizione di stale, cambia in un posto.
from vault import (  # noqa: E402
    Note, as_date, as_num, collect, fmt_eur, is_placeholder, last_interaction,
)

# --------------------------------------------------------------------------
# soglie — dichiarate qui, non sparse nel codice
# --------------------------------------------------------------------------
UPCOMING_DAYS = 7        # "questa settimana": next_action_date entro N giorni
SILENCE_DEAL_DAYS = 30   # deal aperta non aggiornata da N giorni
SILENCE_ACCT_DAYS = 21   # account con deal aperte e nessuna interazione da N giorni
STUCK_DAYS = 30          # decisione/deliverable ferma nello stesso stato da N giorni
MAX_PER_BUCKET = 8       # oltre questo il brief non si legge più

REPORT_REL = os.path.join("wiki", "meta", "heartbeat.md")
STATE_REL = os.path.join("tools", "heartbeat", "state.json")

# Campi di una deal il cui cambiamento è un fatto commerciale, non rumore editoriale.
TRACKED = [
    ("stage", "stage"),
    ("forecast_cat", "forecast"),
    ("amount_eur", "importo"),
    ("status", "status"),
    ("expected_close", "close atteso"),
    ("risk_flag", "rischio"),
    ("next_action_date", "prossima azione"),
]


def d_(note, key):
    v = note.fm.get(key, "")
    return "" if v is None else str(v).strip()


def days(a, b):
    return (a - b).days if (a and b) else None


# --------------------------------------------------------------------------
# raccolta
# --------------------------------------------------------------------------
def load(root):
    notes, _assets = collect(root, exclude=[REPORT_REL.replace(os.sep, "/")])
    deals, accounts, decisions, deliverables = [], [], [], []
    for n in notes:
        if n.type == "opportunity":
            deals.append(n)
        elif n.type == "stakeholder" and os.path.basename(n.rel) != "_index.md":
            accounts.append(n)
        elif n.type == "decision":
            decisions.append(n)
        elif n.type == "deliverable":
            deliverables.append(n)
    return notes, deals, accounts, decisions, deliverables


def snapshot(deals, accounts, notes):
    """Lo stato di adesso, nella forma minima che serve per il confronto."""
    snap = {"deals": {}, "accounts": {}, "notes": {}}
    for n in deals:
        did = d_(n, "deal_id") or n.stem
        snap["deals"][did] = {k: d_(n, k) for k, _label in TRACKED}
        snap["deals"][did]["_title"] = n.stem
    for n in accounts:
        li = last_interaction(n)
        snap["accounts"][n.rel] = li.isoformat() if li else ""
    for n in notes:
        snap["notes"][n.rel] = d_(n, "updated")
    return snap


def read_state(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, IOError):
        return None


# --------------------------------------------------------------------------
# i sei secchi
# --------------------------------------------------------------------------
def bucket_upcoming(deals, today):
    """Scade entro una settimana. È l'unica parte davvero proattiva del battito."""
    out = []
    for n in deals:
        if d_(n, "status") != "open":
            continue
        nad = as_date(d_(n, "next_action_date"))
        if not nad:
            continue
        delta = days(nad, today)
        if delta is not None and 0 <= delta <= UPCOMING_DAYS:
            out.append({
                "rel": n.rel, "stem": n.stem, "eur": as_num(d_(n, "amount_eur")) or 0,
                "when": "oggi" if delta == 0 else "fra %d giorni" % delta,
                "what": d_(n, "next_action") or "— nessuna azione scritta",
                "sort": delta,
            })
    out.sort(key=lambda r: (r["sort"], -r["eur"]))
    return out


def bucket_overdue(deals, today):
    """Una data che è passata e uno stato che non l'ha seguita."""
    out = []
    for n in deals:
        if d_(n, "status") != "open":
            continue
        reasons = []
        nad = as_date(d_(n, "next_action_date"))
        if nad and days(today, nad) > 0:
            reasons.append("azione scaduta da %d giorni" % days(today, nad))
        ec = as_date(d_(n, "expected_close"))
        if ec and days(today, ec) > 0:
            reasons.append("close atteso passato da %d giorni" % days(today, ec))
        if is_placeholder(d_(n, "next_action")):
            reasons.append("nessuna prossima azione")
        if reasons:
            out.append({
                "rel": n.rel, "stem": n.stem, "eur": as_num(d_(n, "amount_eur")) or 0,
                "why": " · ".join(reasons),
                "worst": max([days(today, x) for x in (nad, ec) if x] or [0]),
            })
    out.sort(key=lambda r: -r["eur"])
    return out


def bucket_silence(deals, accounts, today, skip_rels=()):
    """Non è scaduto niente. È che non si muove niente."""
    out = []
    skip = set(skip_rels)
    for n in deals:
        if d_(n, "status") != "open" or n.rel in skip:
            continue                      # già elencata fra le scadute: non ripeterla
        lu = as_date(d_(n, "last_update"))
        basis = "last_update"
        if lu is None:
            lu = as_date(d_(n, "updated"))
            basis = "updated"
        age = days(today, lu) if lu else None
        if age is not None and age > SILENCE_DEAL_DAYS:
            out.append({
                "kind": "deal", "rel": n.rel, "stem": n.stem, "basis": basis,
                "eur": as_num(d_(n, "amount_eur")) or 0, "age": age,
            })
    open_accounts = set()
    for n in deals:
        if d_(n, "status") == "open":
            open_accounts.add(d_(n, "account").strip().lower())
    for n in accounts:
        acct = (d_(n, "account") or n.stem).strip().lower()
        if acct not in open_accounts:
            continue
        li = last_interaction(n)
        basis = "ultima interazione"
        if li is None:
            li = as_date(d_(n, "updated"))
            basis = "updated"
        age = days(today, li) if li else None
        if age is not None and age > SILENCE_ACCT_DAYS:
            out.append({
                "kind": "account", "rel": n.rel, "stem": n.stem,
                "eur": 0, "age": age, "basis": basis,
            })
    out.sort(key=lambda r: (-r["eur"], -r["age"]))
    return out


def bucket_movement(now_snap, prev_snap):
    """Cosa è cambiato dall'ultimo battito. Senza uno snapshot precedente non esiste."""
    if not prev_snap:
        return None
    changes, new, closed = [], [], []
    prev_deals = prev_snap.get("deals", {})
    for did, cur in sorted(now_snap["deals"].items()):
        old = prev_deals.get(did)
        if old is None:
            new.append({"id": did, "stem": cur.get("_title", did)})
            continue
        for key, label in TRACKED:
            a, b = old.get(key, ""), cur.get(key, "")
            if a != b:
                changes.append({
                    "id": did, "stem": cur.get("_title", did),
                    "label": label, "from": a or "—", "to": b or "—",
                })
    for did, old in sorted(prev_deals.items()):
        if did not in now_snap["deals"]:
            closed.append({"id": did, "stem": old.get("_title", did)})
    touched = []
    prev_notes = prev_snap.get("notes", {})
    for rel, up in sorted(now_snap["notes"].items()):
        if rel in prev_notes and prev_notes[rel] != up:
            touched.append(rel)
        elif rel not in prev_notes:
            touched.append(rel)
    return {"changes": changes, "new": new, "gone": closed, "touched": touched}


def bucket_stuck(decisions, deliverables, today):
    out = []
    for n in decisions:
        st = d_(n, "status")
        if st not in ("pending", "active"):
            continue
        up = as_date(d_(n, "updated"))
        age = days(today, up) if up else None
        if age is not None and age > STUCK_DAYS:
            out.append({"kind": "decisione", "rel": n.rel, "stem": n.stem, "st": st, "age": age})
    for n in deliverables:
        st = d_(n, "status")
        if st in ("done", "cancelled"):
            continue
        up = as_date(d_(n, "updated"))
        age = days(today, up) if up else None
        if age is not None and age > STUCK_DAYS:
            out.append({"kind": "deliverable", "rel": n.rel, "stem": n.stem, "st": st, "age": age})
    out.sort(key=lambda r: -r["age"])
    return out


def bucket_uningested(root, notes):
    """File in .raw/ che nessuna nota cita. Sono le fonti che il vault non ha ancora letto."""
    raw = os.path.join(root, ".raw")
    if not os.path.isdir(raw):
        return []
    blob = "\n".join(n.text for n in notes)
    out = []
    for dirpath, dirnames, filenames in os.walk(raw):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in sorted(filenames):
            if fn.startswith("."):
                continue
            stem = os.path.splitext(fn)[0]
            if fn in blob or stem in blob:
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            mtime = dt.date.fromtimestamp(os.path.getmtime(os.path.join(dirpath, fn)))
            out.append({"rel": rel, "when": mtime})
    out.sort(key=lambda r: r["when"], reverse=True)
    return out


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def wl(rel, stem):
    return "[[%s|%s]]" % (rel[:-3].replace(os.sep, "/"), stem)


def top(items):
    """I primi MAX_PER_BUCKET. Un brief che non si legge è un brief che non viene letto."""
    return items[:MAX_PER_BUCKET]


def more(items, out):
    """Da chiamare DOPO aver emesso gli elementi, mai prima."""
    rest = len(items) - MAX_PER_BUCKET
    if rest > 0:
        out.append("")
        out.append("*e altre %d sotto la soglia di leggibilità.*" % rest)


def write_report(path, ctx):
    t = ctx["today"]
    o = []
    o.append("---")
    o.append("type: meta")
    o.append('title: "Battito del vault (generato)"')
    o.append("created: %s" % t)
    o.append("updated: %s" % t)
    o.append("tags:")
    o.append("  - meta")
    o.append("  - heartbeat")
    o.append("maturity: generated")
    o.append("related:")
    o.append('  - "[[second-brain-playbook]]"')
    o.append('  - "[[lint-report]]"')
    o.append('  - "[[pipeline-config]]"')
    o.append("---")
    o.append("")
    o.append("# Battito del vault")
    o.append("")
    o.append("Navigation: [[../index]] | [[second-brain-playbook]] | [[lint-report]]")
    o.append("")
    o.append("> [!warning] File generato — non editare a mano")
    o.append("> Prodotto da `tools/heartbeat/heartbeat.py`, sovrascritto a ogni run.")
    o.append("> Il [[lint-report]] misura lo **stato** del vault; questo misura il **movimento**:")
    o.append("> cosa è cambiato dall'ultimo battito, cosa scade adesso, cosa è rimasto in silenzio.")
    o.append("")
    o.append("Battito: %s · confronto con: %s · %d deal aperte · €%s aperti"
             % (t, ctx["prev_date"] or "**primo run, nessun confronto**",
                ctx["n_open"], fmt_eur(ctx["open_eur"])))
    o.append("")

    up, ov, si = ctx["upcoming"], ctx["overdue"], ctx["silence"]
    mv, st, ug = ctx["movement"], ctx["stuck"], ctx["uningested"]
    at_risk = sum(r["eur"] for r in ov)

    o.append("| Secchio | Voci | Valore |")
    o.append("|---|---|---|")
    o.append("| Questa settimana | %d | €%s |" % (len(up), fmt_eur(sum(r["eur"] for r in up))))
    o.append("| Scaduto | %d | €%s |" % (len(ov), fmt_eur(at_risk)))
    o.append("| Silenzio | %d | €%s |" % (len(si), fmt_eur(sum(r["eur"] for r in si))))
    o.append("| Fermo (decisioni/deliverable) | %d | — |" % len(st))
    o.append("| Da ingerire | %d | — |" % len(ug))
    if mv is not None:
        o.append("| Movimento dall'ultimo battito | %d | — |"
                 % (len(mv["changes"]) + len(mv["new"]) + len(mv["gone"])))
    o.append("")

    # ---- questa settimana
    o.append("## Questa settimana")
    o.append("")
    if not up:
        o.append("Niente in scadenza entro %d giorni." % UPCOMING_DAYS)
    else:
        for r in top(up):
            o.append("- **%s** — %s · €%s" % (r["when"], wl(r["rel"], r["stem"]), fmt_eur(r["eur"])))
            o.append("  %s" % r["what"])
        more(up, o)
    o.append("")

    # ---- scaduto
    o.append("## Scaduto")
    o.append("")
    if not ov:
        o.append("Nessuna data sfondata. (Rara: se è vuoto due volte di fila, è vero.)")
    else:
        o.append("Ordinate per valore, perché è così che si decide cosa guardare per primo.")
        o.append("")
        for r in top(ov):
            o.append("- €%s — %s" % (fmt_eur(r["eur"]), wl(r["rel"], r["stem"])))
            o.append("  %s" % r["why"])
        more(ov, o)
    o.append("")

    # ---- silenzio
    o.append("## Silenzio")
    o.append("")
    o.append("Qui **non** c'è niente di scaduto — quelle stanno sopra e non si ripetono.")
    o.append("Questo è quello che semplicemente non si muove: deal senza movimento da oltre %d"
             % SILENCE_DEAL_DAYS)
    o.append("giorni, account con trattative aperte e nessuna interazione da oltre %d."
             % SILENCE_ACCT_DAYS)
    o.append("")
    if not si:
        o.append("Tutto entro soglia.")
    else:
        for r in top(si):
            if r["kind"] == "deal":
                o.append("- €%s — %s · nessun movimento da **%d giorni** (base: `%s`)"
                         % (fmt_eur(r["eur"]), wl(r["rel"], r["stem"]), r["age"], r["basis"]))
            else:
                o.append("- account %s · nessuna interazione da **%d giorni** (base: `%s`)"
                         % (wl(r["rel"], r["stem"]), r["age"], r["basis"]))
        more(si, o)
    o.append("")

    # ---- movimento
    o.append("## Movimento dall'ultimo battito")
    o.append("")
    if mv is None:
        o.append("Primo battito: non c'è uno snapshot precedente con cui confrontarsi.")
        o.append("Dal prossimo run questa sezione dice cosa è cambiato.")
    elif not (mv["changes"] or mv["new"] or mv["gone"]):
        o.append("**Nessun cambiamento su nessuna deal.** Con %d trattative aperte per €%s,"
                 % (ctx["n_open"], fmt_eur(ctx["open_eur"])))
        o.append("una settimana intera senza un solo movimento è di per sé il dato da guardare.")
    else:
        for r in mv["new"]:
            o.append("- **nuova** — %s" % r["stem"])
        for r in mv["gone"]:
            o.append("- **sparita dallo snapshot** — %s" % r["stem"])
        for r in mv["changes"]:
            o.append("- %s — %s: `%s` → `%s`" % (r["stem"], r["label"], r["from"], r["to"]))
        if mv["touched"]:
            o.append("")
            o.append("Pagine toccate in totale: **%d**." % len(mv["touched"]))
    o.append("")

    # ---- fermo
    o.append("## Fermo da oltre %d giorni" % STUCK_DAYS)
    o.append("")
    if not st:
        o.append("Nessuna decisione o deliverable fermo.")
    else:
        for r in top(st):
            o.append("- %s **%s** — %s · %d giorni"
                     % (r["kind"], r["st"], wl(r["rel"], r["stem"]), r["age"]))
        more(st, o)
    o.append("")

    # ---- da ingerire
    o.append("## Da ingerire")
    o.append("")
    if not ug:
        o.append("Ogni file in `.raw/` è citato da almeno una nota.")
    else:
        o.append("File in `.raw/` che nessuna nota cita: il vault non li ha ancora letti.")
        o.append("")
        for r in top(ug):
            o.append("- `%s` — %s" % (r["rel"], r["when"]))
        more(ug, o)
    o.append("")

    o.append("---")
    o.append("")
    o.append("> [!note] Cosa questo file **non** fa")
    o.append("> Non scrive nel vault, non manda niente, non decide niente. Elenca fatti")
    o.append("> meccanici. Le bozze e il giudizio li mette la skill `battito`, e l'invio resta tuo.")
    o.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(o))


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Battito settimanale del vault.")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--report", default=REPORT_REL)
    ap.add_argument("--state", default=STATE_REL)
    ap.add_argument("--today", default=None, help="YYYY-MM-DD, per run riproducibili")
    ap.add_argument("--no-state", action="store_true",
                    help="non aggiornare lo snapshot (prova senza consumare il confronto)")
    ap.add_argument("--no-report", action="store_true", help="solo output a schermo")
    args = ap.parse_args()

    root = args.root
    today = as_date(args.today or os.environ.get("VAULT_TODAY")) or dt.date.today()
    if not os.path.isdir(os.path.join(root, "wiki")):
        sys.stderr.write("wiki/ non trovata sotto %s\n" % root)
        return 2

    notes, deals, accounts, decisions, deliverables = load(root)
    now_snap = snapshot(deals, accounts, notes)

    state_path = args.state if os.path.isabs(args.state) else os.path.join(root, args.state)
    prev = read_state(state_path)
    prev_snap = prev.get("snapshot") if prev else None
    prev_date = prev.get("date") if prev else None

    open_deals = [n for n in deals if d_(n, "status") == "open"]
    ctx = {
        "today": today,
        "prev_date": prev_date,
        "n_open": len(open_deals),
        "open_eur": sum(as_num(d_(n, "amount_eur")) or 0 for n in open_deals),
        "upcoming": bucket_upcoming(deals, today),
        "overdue": bucket_overdue(deals, today),
        "silence": None,   # riempito sotto: dipende da quali deal sono già scadute
        "movement": bucket_movement(now_snap, prev_snap),
        "stuck": bucket_stuck(decisions, deliverables, today),
        "uningested": bucket_uningested(root, notes),
    }
    ctx["silence"] = bucket_silence(deals, accounts, today,
                                    skip_rels=[r["rel"] for r in ctx["overdue"]])

    if not args.no_report:
        rp = args.report if os.path.isabs(args.report) else os.path.join(root, args.report)
        d = os.path.dirname(rp)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        write_report(rp, ctx)

    if not args.no_state:
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump({"date": today.isoformat(), "snapshot": now_snap},
                      fh, indent=1, sort_keys=True, ensure_ascii=False)

    mv = ctx["movement"]
    print("battito · %s · %d deal aperte · €%s" % (today, ctx["n_open"], fmt_eur(ctx["open_eur"])))
    print("  questa settimana %d · scaduto %d (€%s) · silenzio %d · fermo %d · da ingerire %d"
          % (len(ctx["upcoming"]), len(ctx["overdue"]),
             fmt_eur(sum(r["eur"] for r in ctx["overdue"])),
             len(ctx["silence"]), len(ctx["stuck"]), len(ctx["uningested"])))
    if mv is None:
        print("  movimento: primo battito, nessun confronto%s"
              % ("" if args.no_state else " (snapshot scritto)"))
    else:
        print("  movimento dal %s: %d cambi · %d nuove · %d sparite · %d pagine toccate"
              % (prev_date, len(mv["changes"]), len(mv["new"]), len(mv["gone"]),
                 len(mv["touched"])))
    if not args.no_report:
        print("  report → %s" % args.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
