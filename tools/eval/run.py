#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py — esegue la suite di eval sulle skill del vault.

Due modalita', ed e' la scelta di progetto piu' importante del file:

  REPLAY (default)  ricontrolla gli output gia' registrati in cases/*/recorded.md
                    Gratis, offline, deterministico, si mette in CI.

  RECORD (--record) chiama davvero il modello e riscrive gli output registrati.
                    Costa token e va fatto quando cambia la skill, non a ogni commit.

Serve perche' il sistema sotto test non e' deterministico. Se ogni verifica
richiedesse una chiamata al modello, la suite sarebbe lenta, costosa e
instabile — e nessuno la eseguirebbe. Separando le due cose, il 90% dei
controlli gira in un secondo e la spesa diventa una decisione esplicita.

Uso:
    python3 tools/eval/run.py                      # replay, solo deterministico
    python3 tools/eval/run.py --record             # rigenera gli output
    python3 tools/eval/run.py --judge              # aggiunge la classe giudizio
    python3 tools/eval/run.py --case 01            # un caso solo

Exit code: 1 se un'asserzione deterministica fallisce (usabile come gate),
altrimenti 0. Il giudizio non alza mai l'exit code: si riporta, non si blocca.
"""

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import checks as C  # noqa: E402

CASES_DIR = os.path.join(HERE, "cases")
SHARED = os.path.join(CASES_DIR, "_shared")
RUNS_DIR = os.path.join(HERE, "runs")
SKILLS_DIR = os.path.abspath(os.path.join(HERE, "..", "..", ".claude", "skills"))


def load_cases(filt):
    out = []
    for name in sorted(os.listdir(CASES_DIR)):
        path = os.path.join(CASES_DIR, name)
        spec_file = os.path.join(path, "case.json")
        if name.startswith("_") or not os.path.isfile(spec_file):
            continue
        if filt and filt not in name:
            continue
        with open(spec_file, encoding="utf-8") as fh:
            spec = json.load(fh)
        spec["_dir"] = path
        out.append(spec)
    return out


def vault_of(case):
    """Il fixture del caso, o quello di un altro caso se lo riusa.

    Duplicare un vault per porgli una domanda diversa significa doverlo
    aggiornare in due punti: la seconda copia diverge e la suite comincia a
    misurare due mondi.
    """
    src = case.get("vault_from")
    if src:
        return os.path.join(CASES_DIR, src, "vault")
    return os.path.join(case["_dir"], "vault")


def build_vault(case):
    """Compone il vault sintetico del caso: _shared + i file del caso.

    Ogni caso gira in una copia isolata. Senza questo, un caso che scrive
    sporca il successivo e i fallimenti diventano dipendenti dall'ordine —
    il modo piu' rapido per rendere una suite inutile.
    """
    tmp = tempfile.mkdtemp(prefix="eval-vault-")
    for src in (SHARED, vault_of(case)):
        if os.path.isdir(src):
            shutil.copytree(src, tmp, dirs_exist_ok=True)
    # Ogni caso dichiara le skill che gli servono. La prima versione copiava
    # sempre e solo `deal-review`: i sette casi sulle altre skill giravano
    # senza la skill che dovevano misurare, e i loro rossi non dicevano niente
    # sulle skill. La suite ha misurato per un giro l'assenza di se stessa.
    for skill in case.get("skills", []):
        src = os.path.join(SKILLS_DIR, skill)
        if not os.path.isdir(src):
            raise SystemExit(f"{case['id']}: skill «{skill}» non trovata in {SKILLS_DIR}")
        shutil.copytree(src, os.path.join(tmp, ".claude", "skills", skill),
                        dirs_exist_ok=True)
    return tmp


def record(case, model, timeout):
    """Esegue la skill. Per i casi che scrivono, conserva il vault risultante.

    Il prodotto di `account-note` non e' il testo in chat ma il vault dopo:
    va salvato come si salva un output, cosi' il replay puo' ricontrollarlo
    offline senza richiamare il modello.
    """
    vault = build_vault(case)
    mutation = case.get("expect") == "mutation"
    try:
        prompt = case["prompt"]
        if case.get("today"):
            # L'oracolo calcola alla data del caso; il modello, senza questa riga,
            # usa quella di sistema. Finche' coincidevano il difetto era invisibile:
            # alla prima registrazione fatta in un altro giorno, slittamenti e
            # trimestre di riferimento misuravano due mondi diversi.
            prompt += f"\n\n(Data di oggi per questa esecuzione: {case['today']}.)"
        cmd = ["claude", "-p", prompt, "--model", model]
        if mutation:
            # Limitato alla copia usa-e-getta del fixture in /tmp, e solo per
            # i casi che si dichiarano scriventi. Senza, il record produce un
            # rifiuto cortese e tutte le asserzioni di stato falliscono per un
            # motivo che non riguarda la skill.
            cmd += ["--permission-mode", "acceptEdits"]
        p = subprocess.run(
            cmd, cwd=vault, capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL,  # senza questo la CLI aspetta stdin per 3s e avvisa
        )
    except FileNotFoundError:
        return None, "CLI 'claude' non trovata nel PATH"
    except subprocess.TimeoutExpired:
        return None, f"timeout dopo {timeout}s"
    finally:
        if mutation:
            dest = os.path.join(case["_dir"], "recorded-vault")
            shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(vault, dest, ignore=shutil.ignore_patterns(".claude"))
        shutil.rmtree(vault, ignore_errors=True)
    # La CLI puo' fallire uscendo con 0 e stampando l'errore su stdout (per
    # esempio un token scaduto). Fidarsi del solo returncode faceva salvare
    # None come output registrato: un caso "verde" che non conteneva nulla.
    if p.returncode != 0:
        return None, ((p.stderr or p.stdout or "").strip()[:200] or f"exit {p.returncode}")
    out = p.stdout or ""
    if "Failed to authenticate" in out or "API Error" in out:
        return None, out.strip().splitlines()[0][:200]
    if len(out.strip()) < 40:
        return None, f"output troppo corto ({len(out.strip())} caratteri) — probabile errore silenzioso"
    return out, None


def evaluate(case, text, use_judge, judge_opts):
    # Non tutti i casi attendono un review. Quello sull'account ambiguo attende
    # una domanda, e li' le asserzioni sono l'opposto.
    kind = case.get("expect", "review")
    if kind == "mutation":
        # Il fixture di partenza si ricostruisce (e' deterministico), il
        # risultato e' la copia salvata durante la registrazione.
        import statecheck
        pristine = build_vault(case)
        try:
            results = statecheck.check_state(
                pristine, os.path.join(case["_dir"], "recorded-vault"), case["checks"])
        finally:
            shutil.rmtree(pristine, ignore_errors=True)
        results += C.check_grounding(text, case["checks"])
        if use_judge and case["checks"].get("judgment"):
            import judge
            results += judge.check_judgment(text, case["checks"], **judge_opts)
        return results
    if kind == "clarification":
        results = C.check_clarification(text, case["checks"])
    else:
        # "review" attende la tabella MEDDPICC; le altre skill dichiarano le
        # proprie sezioni in case.json.
        results = (C.check_structure(text, case["checks"]) if kind == "review"
                   else C.check_sections(text, case["checks"]))
        results += C.check_grounding(text, case["checks"])
        # Per le skill che producono numeri, l'atteso non e' scritto a mano:
        # lo ricalcola oracle.py dal fixture del caso.
        if case["checks"].get("oracle"):
            import oracle
            facts = oracle.compute(vault_of(case), case.get("today"))
            results += C.check_oracle(text, case["checks"], facts)
    if use_judge and case["checks"].get("judgment"):
        import judge
        results += judge.check_judgment(text, case["checks"], **judge_opts)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true", help="chiama il modello e riscrive gli output")
    ap.add_argument("--judge", action="store_true", help="abilita le asserzioni di giudizio (costa)")
    ap.add_argument("--case", default="", help="filtra i casi per sottostringa")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--judge-model", default="claude-sonnet-5")
    ap.add_argument("--votes", type=int, default=3, help="voti per asserzione di giudizio")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--report", default=os.path.join(HERE, "runs", "latest.md"))
    args = ap.parse_args()

    cases = load_cases(args.case)
    if not cases:
        print("nessun caso trovato", file=sys.stderr)
        return 2

    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    rows, failed_hard = [], 0

    for case in cases:
        rec_path = os.path.join(case["_dir"], "recorded.md")
        if args.record:
            text, err = record(case, args.model, args.timeout)
            if err or text is None:
                err = err or "nessun output"
                print(f"  ! {case['id']}: registrazione fallita — {err}", file=sys.stderr)
                rows.append((case, None, [], err))
                continue
            with open(rec_path, "w", encoding="utf-8") as fh:
                fh.write(text)
        elif os.path.isfile(rec_path) and not (
                case.get("expect") == "mutation"
                and not os.path.isdir(os.path.join(case["_dir"], "recorded-vault"))):
            with open(rec_path, encoding="utf-8") as fh:
                text = fh.read()
        else:
            rows.append((case, None, [], "nessun output registrato — esegui con --record"))
            continue

        res = evaluate(case, text, args.judge,
                       {"model": args.judge_model, "votes": args.votes, "timeout": args.timeout})
        hard = [r for r in res if r["class"] != "judgment" and not r["pass"]]
        failed_hard += len(hard)
        rows.append((case, text, res, None))

        ok = sum(1 for r in res if r["pass"])
        tot = len(res)
        mark = "PASS" if not hard else "FAIL"
        print(f"[{mark}] {case['id']}  {ok}/{tot}  — {case['title']}")
        for r in res:
            if r["pass"] is True:
                continue
            flag = "?" if r["pass"] is None else "x"
            print(f"       {flag} [{r['class']}] {r['check']}: {r['detail']}")

    write_report(args.report, stamp, rows, args)
    # Una suite senza output registrati non e' verde: e' senza misura. Se
    # uscisse 0, la CI direbbe "tutto a posto" per non aver controllato nulla.
    unmeasured = [c["id"] for c, t, r, e in rows if t is None]
    print(f"\nreport: {os.path.relpath(args.report)}")
    print("asserzioni deterministiche fallite:", failed_hard)
    if unmeasured:
        print("casi senza misura:", ", ".join(unmeasured))
        print("  -> esegui con --record (richiede la CLI 'claude' autenticata)")
    return 1 if (failed_hard or unmeasured) else 0


def write_report(path, stamp, rows, args):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    L = [
        "# Eval — skill del vault",
        "",
        f"Eseguito il {stamp} · modalita: {'record' if args.record else 'replay'}"
        f" · giudizio: {'attivo' if args.judge else 'disattivo'}",
        "",
        "| Caso | Struttura | Grounding | Giudizio | Esito |",
        "|---|---|---|---|---|",
    ]
    for case, text, res, err in rows:
        if err:
            L.append(f"| {case['id']} | — | — | — | errore: {err} |")
            continue
        def score(cls):
            sub = [r for r in res if r["class"] == cls]
            if not sub:
                return "—"
            return f"{sum(1 for r in sub if r['pass'])}/{len(sub)}"
        hard = any(r["class"] != "judgment" and not r["pass"] for r in res)
        L.append(f"| {case['id']} | {score('structure')} | {score('grounding')} "
                 f"| {score('judgment')} | {'FAIL' if hard else 'PASS'} |")

    L += ["", "## Dettaglio", ""]
    for case, text, res, err in rows:
        L.append(f"### {case['id']} — {case['title']}")
        L.append("")
        L.append(f"**Modo di fallire sotto test:** {case.get('failure_mode', '—')}")
        L.append("")
        if err:
            L += [f"Errore: {err}", ""]
            continue
        for r in res:
            icon = {True: "ok", False: "FALLITA", None: "non valutata"}[r["pass"]]
            L.append(f"- `{r['class']}` **{r['check']}** — {icon}. {r['detail']}")
        L.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
