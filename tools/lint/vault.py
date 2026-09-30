#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vault.py — lint deterministico del vault.

Controlli meccanici che NON richiedono giudizio: frontmatter, wikilink morti,
pagine orfane, index drift, igiene pipeline, riconciliazione deal-vs-account.
Il lint LLM resta per i claim stale (cfr. wiki/meta/second-brain-playbook.md §3,
"Dove NON usare l'LLM per controllare").

Solo stdlib. Nessuna rete. Nessuna nota modificata: scrive solo il report.

Uso:
    python3 tools/lint/vault.py
    python3 tools/lint/vault.py --report wiki/meta/lint-report.md --stale-days 14
    python3 tools/lint/vault.py --today 2026-08-05      # per run riproducibili

Exit code: 1 se esistono finding ERROR, altrimenti 0 (usabile come gate).
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import defaultdict

# --------------------------------------------------------------------------
# configurazione dei controlli
# --------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# SCHEMA — fonte unica.
# Questo blocco è la definizione del frontmatter del vault. `--emit-schema` la
# pubblica in wiki/meta/frontmatter-schema.md, e i template in `_templates/` sono
# verificati contro di essa. Non ricopiarla altrove: era in tre posti e derivavano.
# ---------------------------------------------------------------------------

# Frontmatter minimo per ogni nota
REQUIRED_ALL = ["type", "created", "updated", "tags"]

# `status` = STATO (dove un ciclo di vita esiste). `maturity` = MATURITÀ della pagina.
# Erano la stessa chiave, e su 13 note uno dei due si perdeva in silenzio.
STATUS_VOCAB = {
    "opportunity": {"open", "won", "lost"},
    "decision": {"active", "pending", "resolved", "done", "superseded"},
    "deliverable": {"active", "in-progress", "done", "cancelled"},
    "meeting": {"done", "pending", "cancelled"},
    "intel": {"active", "archived"},
    "source": {"active", "archived"},
}
MATURITY_VOCAB = {"seed", "developing", "mature", "evergreen", "generated"}

# Quanto un partner vende senza passare da noi. È la metrica dell'enablement: se non si
# dichiara, non si sa cosa manca per farlo salire di livello.
PARTNER_AUTONOMY = ["none", "assisted", "semi-autonomous", "autonomous"]

# Tipi che descrivono una pagina di riferimento: non hanno uno stato, hanno una maturità.
MATURITY_ONLY_TYPES = {"stakeholder", "meta", "index", "overview"}

# Campi obbligatori per tipo di nota
REQUIRED_BY_TYPE = {
    "opportunity": [
        "deal_id", "account", "stage", "stage_pct", "forecast_cat",
        "amount_eur", "expected_close", "owner", "channel_type", "status",
    ],
    "stakeholder": [],   # account/owner richiesti solo se taggata 'account' (vedi check_frontmatter)
    "decision": ["date", "owner"],
    "deliverable": ["date", "owner"],
    "intel": ["date"],
    "meeting": ["date", "account"],
    "source": ["source_type"],
}

# File radice del vault che non sono orfani per definizione
NEVER_ORPHAN = {"index.md", "hot.md", "log.md", "overview.md"}

# Tipi di nota esenti dal controllo orfani, con motivo dichiarato (stampato nel report).
ORPHAN_EXEMPT_TYPES = {
    "opportunity": "le deal note sono raggiunte da `deals.base`, non da wikilink: decine di WARN identiche seppellirebbero gli orfani veri",
}

# Cartelle il cui _index.md, per scelta esplicita, NON elenca una voce per nota.
# Dichiarate qui e stampate nel report: nessun cap silenzioso.
INDEX_LISTING_EXEMPT = {
    "wiki/pipeline": "l'indice riporta i totali aggregati, non una riga per deal (scelta dichiarata)",
    "wiki/sources": "consolida la provenienza in una mappa unica invece di una pagina per fonte (scelta dichiarata)",
}

# Regole forecast da wiki/meta/pipeline-config.md
FORECAST_RULES = {
    "Commit": {"min_stage": 5, "min_meddpicc": 7, "in_quarter": True},
    "Best Case": {"min_stage": 4, "min_meddpicc": 6, "in_quarter": True},
    "Pipeline": {"min_stage": 2, "max_stage": 4, "in_quarter": False},
    "Upside": {"min_stage": 1, "max_stage": 1, "in_quarter": False},
}

# Nomi prodotto approvati. Le grafie alternative diventano ambiguità nei materiali:
# il loop 2 ha trovato il prodotto in sviluppo chiamato in quattro modi diversi.
# (Vendor e prodotti di questo vault demo sono inventati.)
PRODUCT_ALIASES = {
    "QG Mesh": "Quillgate Mesh (nome approvato, In Development)",
    "Quillgate 2": "Quillgate Mesh (nome approvato, In Development)",
    "QGA": "Quillgate Access",
    "Quillgate Remote": "Quillgate Access",
}

MEDDPICC_FIELDS = [
    "meddpicc_metrics", "meddpicc_econ_buyer", "meddpicc_decision_crit",
    "meddpicc_decision_proc", "meddpicc_pain", "meddpicc_champion",
    "meddpicc_competition", "meddpicc_paper",
]

# Soglie da pipeline-config.md "MEDDPICC field guide"
MEDDPICC_REQUIRED = [
    (0, ["meddpicc_econ_buyer", "meddpicc_pain", "meddpicc_champion"]),
    (25000, ["meddpicc_metrics", "meddpicc_decision_crit", "meddpicc_decision_proc"]),
    (100000, ["meddpicc_competition", "meddpicc_paper"]),
]

WIKILINK_RE = re.compile(r"\[\[([^\[\]]+?)\]\]")
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

# --------------------------------------------------------------------------
# parsing frontmatter (YAML piatto, come da convenzione del vault)
# --------------------------------------------------------------------------


def _scalar(raw):
    """Estrae uno scalare da un valore YAML piatto, togliendo i commenti in coda."""
    s = raw.strip()
    if not s:
        return ""
    if s[0] in "\"'":
        q = s[0]
        end = s.find(q, 1)
        if end != -1:
            return s[1:end]
        return s[1:]
    # commento in coda solo se fuori da quote
    hash_pos = s.find(" #")
    if hash_pos != -1:
        s = s[:hash_pos]
    return s.strip()


def parse_frontmatter(text):
    """Ritorna (frontmatter_dict, body). frontmatter_dict vuoto se assente."""
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text

    fm = {}
    key = None
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        stripped = raw.strip()
        if stripped.startswith("#"):          # commento a riga intera
            continue
        if stripped.startswith("- ") and key is not None:
            if not isinstance(fm.get(key), list):
                fm[key] = []
            fm[key].append(_scalar(stripped[2:]))
            continue
        if raw[0] in " \t":                   # nesting non usato dalle convenzioni: ignorato
            continue
        if ":" not in stripped:
            continue
        k, _, v = stripped.partition(":")
        key = k.strip()
        v = v.strip()
        if v in ("", "[]"):
            fm[key] = [] if v == "[]" else ""
        else:
            fm[key] = _scalar(v)
    body = "\n".join(lines[end + 1:])
    return fm, body


def as_date(value):
    if value is None:
        return None
    m = DATE_RE.match(str(value).strip())
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def as_num(value):
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(".", "").replace(",", ".")) if "," in str(value) else float(value)
    except ValueError:
        return None


def stage_num(value):
    m = re.match(r"\s*L(\d)", str(value or ""))
    return int(m.group(1)) if m else None


def quarter_of(date):
    return (date.year, (date.month - 1) // 3 + 1) if date else None


def is_placeholder(value):
    """Vuoto, oppure un segnaposto tipo '[da compilare]' / '[TBD]' — non è un dato."""
    s = str(value or "").strip().lower()
    return s == "" or bool(re.match(r"^\[.*\]$", s)) or s in ("tbd", "n/d", "n/a", "-")


def norm_account(name):
    s = re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).strip()
    return re.sub(r"\s+", " ", s)


# --------------------------------------------------------------------------
# raccolta note
# --------------------------------------------------------------------------


class Note(object):
    def __init__(self, root, relpath):
        self.rel = relpath
        self.abs = os.path.join(root, relpath)
        with open(self.abs, "r", encoding="utf-8") as fh:
            self.text = fh.read()
        self.fm, self.body = parse_frontmatter(self.text)
        self.type = self.fm.get("type", "")
        self.stem = os.path.splitext(os.path.basename(relpath))[0]
        self.dirrel = os.path.dirname(relpath)


def collect(root, exclude=()):
    notes, assets = [], []
    exclude = set(e.replace(os.sep, "/") for e in exclude)
    for dirpath, dirnames, filenames in os.walk(os.path.join(root, "wiki")):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            if rel.replace(os.sep, "/") in exclude:
                continue                      # il report generato non linta se stesso
            if fn.endswith(".md"):
                notes.append(Note(root, rel))
            elif fn.endswith((".base", ".canvas")):
                assets.append(rel)
    notes.sort(key=lambda n: n.rel)
    return notes, sorted(assets)


def index_link_targets(root, notes, assets, extra_targets=()):
    """Indice dei bersagli linkabili: percorso completo, e stem (con collisioni)."""
    by_path, by_stem = {}, defaultdict(list)
    # pagine escluse dai check ma comunque linkabili (es. il report generato)
    for rel in extra_targets:
        rel = rel.replace(os.sep, "/")
        by_path[rel] = rel
        by_path[os.path.splitext(rel)[0]] = rel
        by_stem[os.path.splitext(os.path.basename(rel))[0]].append(rel)
    for n in notes:
        by_path[n.rel[:-3]] = n.rel
        by_stem[n.stem].append(n.rel)
    for a in assets:
        by_path[a] = a
        by_path[os.path.splitext(a)[0]] = a
        by_stem[os.path.basename(a)].append(a)
        by_stem[os.path.splitext(os.path.basename(a))[0]].append(a)
    # bersagli fuori da wiki/: .raw/, tools/, radice — esistono come file, non come note
    for extra_dir in (".raw", "tools", "_templates", ""):
        base = os.path.join(root, extra_dir) if extra_dir else root
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "build", "wiki") and not d.startswith(".git")]
            for fn in filenames:
                rel = os.path.relpath(os.path.join(dirpath, fn), root)
                if rel.startswith("wiki" + os.sep):
                    continue
                by_path.setdefault(rel, rel)
                by_path.setdefault(os.path.splitext(rel)[0], rel)
                by_stem[os.path.splitext(fn)[0]].append(rel)
            if extra_dir == "":
                break
    return by_path, by_stem


def resolve_link(target, from_note, by_path, by_stem):
    """Risolve un wikilink. Ritorna (rel_path | None, ambiguo?)."""
    t = target.split("|")[0].split("#")[0].strip()
    if not t:
        return None, False
    candidates = []
    if "/" in t or t.startswith(".."):
        joined = os.path.normpath(os.path.join(from_note.dirrel, t))
        candidates += [joined, os.path.normpath(t)]
    else:
        candidates.append(os.path.normpath(os.path.join(from_note.dirrel, t)))
        candidates.append(t)
    for c in candidates:
        c = c.replace(os.sep, "/")
        if c in by_path:
            return by_path[c], False
    hits = by_stem.get(os.path.basename(t), [])
    if len(hits) == 1:
        return hits[0], False
    if len(hits) > 1:
        same_dir = [h for h in hits if os.path.dirname(h) == from_note.dirrel]
        if len(same_dir) == 1:
            return same_dir[0], False
        return hits[0], True
    return None, False


# --------------------------------------------------------------------------
# controlli
# --------------------------------------------------------------------------


class Findings(object):
    def __init__(self):
        self.items = []

    def add(self, sev, check, where, msg):
        self.items.append({"sev": sev, "check": check, "where": where, "msg": msg})

    def by_check(self, check):
        return [i for i in self.items if i["check"] == check]

    def count(self, sev):
        return len([i for i in self.items if i["sev"] == sev])


def check_frontmatter(notes, f):
    for n in notes:
        if not n.fm:
            f.add("ERROR", "frontmatter", n.rel, "nessun frontmatter YAML")
            continue
        missing = [k for k in REQUIRED_ALL if k not in n.fm or n.fm.get(k) in ("", [])]
        required = list(REQUIRED_BY_TYPE.get(n.type, []))
        tags = n.fm.get("tags") or []
        tags = tags if isinstance(tags, list) else [tags]
        if n.type == "stakeholder" and "account" in tags:
            required += ["account", "owner"]
        # una pagina partner deve dichiarare che tipo di partner è e quanto è autonomo:
        # senza l'autonomia non si sa cosa serve per farlo vendere da solo
        if n.type == "stakeholder" and "partner" in tags:
            required += ["partner_type", "partner_autonomy"]
            aut = str(n.fm.get("partner_autonomy", "")).strip()
            if aut and aut not in PARTNER_AUTONOMY:
                f.add("WARN", "frontmatter", n.rel,
                      "partner_autonomy '%s' fuori vocabolario (ammessi: %s)"
                      % (aut, ", ".join(PARTNER_AUTONOMY)))
        # status dove esiste uno stato; maturity sulle pagine di riferimento
        if n.type in STATUS_VOCAB:
            required.append("status")
        if n.type in MATURITY_ONLY_TYPES:
            required.append("maturity")
            if str(n.fm.get("status", "")).strip():
                f.add("WARN", "frontmatter", n.rel,
                      "type '%s' non usa 'status' (usa 'maturity'): trovato status '%s'"
                      % (n.type, n.fm.get("status")))
        mat = str(n.fm.get("maturity", "")).strip()
        if mat and mat not in MATURITY_VOCAB:
            f.add("WARN", "frontmatter", n.rel,
                  "maturity '%s' fuori vocabolario (ammessi: %s)" % (mat, ", ".join(sorted(MATURITY_VOCAB))))
        for k in required:
            if k not in n.fm or n.fm.get(k) in ("", []):
                missing.append(k)
        if missing:
            sev = "ERROR" if n.type == "opportunity" else "WARN"
            f.add(sev, "frontmatter", n.rel, "campi mancanti o vuoti: " + ", ".join(sorted(set(missing))))
        created, updated = as_date(n.fm.get("created")), as_date(n.fm.get("updated"))
        if n.fm.get("created") and not created:
            f.add("ERROR", "frontmatter", n.rel, "created non è una data valida: %r" % n.fm.get("created"))
        if n.fm.get("updated") and not updated:
            f.add("ERROR", "frontmatter", n.rel, "updated non è una data valida: %r" % n.fm.get("updated"))
        if created and updated and updated < created:
            f.add("ERROR", "frontmatter", n.rel, "updated (%s) precede created (%s)" % (updated, created))
        # 'status' duplicato nel frontmatter è un errore silenzioso: l'ultimo vince
        raw_fm = n.text.split("---")[1] if n.text.startswith("---") and n.text.count("---") >= 2 else ""
        for key in ("status", "type", "updated"):
            vals = re.findall(r"(?m)^%s: *(.*)$" % key, raw_fm)
            if len(vals) > 1:
                f.add("ERROR", "frontmatter", n.rel,
                      "chiave '%s' dichiarata %d volte: %s — vince '%s', %s viene perso silenziosamente"
                      % (key, len(vals), " + ".join(repr(v.strip()) for v in vals),
                         vals[-1].strip(), " e ".join(repr(v.strip()) for v in vals[:-1])))
        # vocabolario di 'status' per tipo: impedisce che lo stato e la maturità si mescolino
        allowed = STATUS_VOCAB.get(n.type)
        if allowed:
            val = str(n.fm.get("status", "")).strip()
            if val and val not in allowed:
                f.add("WARN", "frontmatter", n.rel,
                      "status '%s' fuori vocabolario per type '%s' (ammessi: %s)"
                      % (val, n.type, ", ".join(sorted(allowed))))


PLACEHOLDER_RE = re.compile(r"%[sdfr]\b|\{[A-Za-z_][A-Za-z0-9_]*\}|\{\{[^}]*\}\}")


def check_placeholders(notes, f):
    """Segnaposto di formattazione rimasti nel testo (es. un %s non interpolato).

    Nato da un bug reale: una voce di log scritta come '## [%s] tooling'. Il testo dentro
    backtick è escluso — là un %s può essere citazione legittima.
    """
    for n in notes:
        body = re.sub(r"`[^`\n]*`", "", n.body)          # via il codice inline
        body = re.sub(r"(?s)```.*?```", "", body)        # via i blocchi di codice
        for m in PLACEHOLDER_RE.finditer(body):
            line = body[:m.start()].count("\n") + 1
            f.add("ERROR", "segnaposto", n.rel,
                  "segnaposto di formattazione non risolto: %r (riga ~%d del corpo)" % (m.group(0), line))


def check_sources_exist(root, notes, f):
    """Ogni `sources:` che punta a `.raw/` deve puntare a un file che esiste.

    Nato dal loop 2: due pagine con cifre commerciali citavano file mai ingeriti, quindi
    nessun numero era ri-derivabile dal vault.
    """
    for n in notes:
        srcs = n.fm.get("sources")
        if not isinstance(srcs, list):
            continue
        raw_names = set()
        raw_dir = os.path.join(root, ".raw")
        for dirpath, _, filenames in os.walk(raw_dir):
            for fn in filenames:
                raw_names.add(fn)
        for s in srcs:
            s = str(s)
            m = re.search(r"\.raw/[^|\]\"'`\s]+", s)
            if m:
                target = m.group(0).rstrip(" .")
                # l'entry può omettere l'estensione: accetta qualunque estensione reale
                base = os.path.join(root, target)
                if os.path.exists(base) or os.path.exists(base + ".md") or \
                   any(p_.startswith(os.path.basename(target) + ".")
                       for p_ in os.listdir(os.path.dirname(base)) if os.path.isdir(os.path.dirname(base))):
                    continue
                f.add("ERROR", "provenienza", n.rel,
                      "sources cita %s, che non esiste in .raw/ — le sue affermazioni non sono "
                      "ri-derivabili dal vault" % target)
                continue
            # nome di file nudo (es. "2026-06-26_inventario-dispositivi.xlsx")
            m = re.search(r"[\w \-\.\(\)]+\.(xlsx|pptx|docx|pdf|eml|csv|msg)", s, re.I)
            if m and m.group(0).strip() not in raw_names:
                f.add("WARN", "provenienza", n.rel,
                      "sources cita '%s', che non è in .raw/: la fonte non è stata ingerita e i "
                      "dati che ne derivano non sono verificabili nel vault" % m.group(0).strip())


# NOTA — controllo grafie prodotto rimosso di proposito.
# Provato e scartato: su tutto il vault produceva 12 WARN quasi tutte legittime — il nome di
# una pagina che contiene la grafia storica, citazioni storiche in `log.md`, e pagine fedeli alla
# loro fonte. Il posto giusto per questo controllo è il materiale **esterno**, non il vault:
# internamente si deve poter parlare dei prodotti In Development col nome che avevano nella
# fonte. Va in `check-external.py`, che non esiste ancora. Le grafie da normalizzare là sono
# in PRODUCT_ALIASES. Dodici WARN che si impara a ignorare sono peggio di un check assente.


def check_templates(root, f):
    """I template in `_templates/` devono rispettare lo schema, o divergeranno da esso."""
    tdir = os.path.join(root, "_templates")
    if not os.path.isdir(tdir):
        return
    for fn in sorted(os.listdir(tdir)):
        if not fn.endswith(".md"):
            continue
        rel = os.path.join("_templates", fn)
        with open(os.path.join(tdir, fn), "r", encoding="utf-8") as fh:
            fm, _ = parse_frontmatter(fh.read())
        ty = fm.get("type", "")
        if not ty:
            f.add("WARN", "template", rel, "nessun 'type' nel frontmatter")
            continue
        if ty in STATUS_VOCAB:
            val = str(fm.get("status", "")).strip()
            if val and val not in STATUS_VOCAB[ty]:
                f.add("ERROR", "template", rel,
                      "status di default '%s' non è nel vocabolario di '%s' — ogni nota creata "
                      "da questo template nasce fuori schema" % (val, ty))
        if ty in MATURITY_ONLY_TYPES:
            if str(fm.get("status", "")).strip():
                f.add("ERROR", "template", rel,
                      "type '%s' usa 'maturity', non 'status': il template semina la chiave sbagliata" % ty)
            mat = str(fm.get("maturity", "")).strip()
            if mat and mat not in MATURITY_VOCAB:
                f.add("ERROR", "template", rel, "maturity di default '%s' fuori vocabolario" % mat)


def check_links(root, notes, assets, f, extra_targets=()):
    by_path, by_stem = index_link_targets(root, notes, assets, extra_targets)
    inbound = defaultdict(set)
    for n in notes:
        for raw in WIKILINK_RE.findall(n.text):
            target, ambiguous = resolve_link(raw, n, by_path, by_stem)
            if target is None:
                f.add("ERROR", "wikilink", n.rel, "link morto: [[%s]]" % raw.split("|")[0].strip())
            else:
                if ambiguous:
                    f.add("WARN", "wikilink", n.rel, "link ambiguo [[%s]] → risolto su %s" % (raw.split("|")[0].strip(), target))
                inbound[target].add(n.rel)
    for n in notes:
        base = os.path.basename(n.rel)
        if base == "_index.md" or base in NEVER_ORPHAN or n.type in ORPHAN_EXEMPT_TYPES:
            continue
        if not inbound.get(n.rel):
            f.add("WARN", "orfani", n.rel, "nessun wikilink in entrata")
    # nodi file dei canvas
    for a in assets:
        if not a.endswith(".canvas"):
            continue
        try:
            data = json.load(open(os.path.join(root, a), "r", encoding="utf-8"))
        except Exception as exc:
            f.add("ERROR", "canvas", a, "JSON non parsabile: %s" % exc)
            continue
        for node in data.get("nodes", []):
            fp = node.get("file")
            if fp and not os.path.exists(os.path.join(root, fp)):
                f.add("ERROR", "canvas", a, "nodo file inesistente: %s" % fp)
    return inbound


def check_index_drift(root, notes, f):
    by_dir = defaultdict(list)
    for n in notes:
        by_dir[n.dirrel.replace(os.sep, "/")].append(n)
    for dirrel, group in sorted(by_dir.items()):
        idx = [n for n in group if os.path.basename(n.rel) == "_index.md"]
        if not idx:
            continue
        if dirrel in INDEX_LISTING_EXEMPT:
            continue
        text = idx[0].text
        for n in group:
            if os.path.basename(n.rel) == "_index.md":
                continue
            if n.stem not in text:
                f.add("WARN", "index-drift", idx[0].rel, "non elenca %s" % n.stem)
    master = os.path.join(root, "wiki", "index.md")
    if os.path.exists(master):
        mtext = open(master, "r", encoding="utf-8").read()
        for n in notes:
            if n.dirrel.replace(os.sep, "/") in INDEX_LISTING_EXEMPT:
                continue
            if os.path.basename(n.rel) in ("_index.md",) or n.rel.count("/") < 2:
                continue
            if n.stem not in mtext:
                f.add("INFO", "index-drift", "wiki/index.md", "non cita %s" % n.stem)


def check_pipeline(notes, f, today, stale_days):
    deals = [n for n in notes if n.type == "opportunity"]
    seen_ids = defaultdict(list)
    cur_q = quarter_of(today)
    for n in deals:
        fm = n.fm
        did = fm.get("deal_id", "")
        seen_ids[did].append(n.rel)
        status = str(fm.get("status", "")).lower()
        stage = stage_num(fm.get("stage"))

        # reason obbligatoria sulle chiusure (pipeline-config: "Lost Reason mandatory")
        if status == "lost":
            if is_placeholder(fm.get("lost_reason")):
                f.add("ERROR", "chiusure", n.rel, "status lost senza lost_reason (obbligatoria per pipeline-config)")
        elif "won" in status:
            if is_placeholder(fm.get("win_reason")):
                f.add("WARN", "chiusure", n.rel, "status won senza win_reason")

        amount = as_num(fm.get("amount_eur"))
        weighted = as_num(fm.get("weighted_eur"))
        pct = as_num(fm.get("stage_pct"))
        close = as_date(fm.get("expected_close"))
        original = as_date(fm.get("original_close"))
        updated = as_date(fm.get("updated"))
        md_score = as_num(fm.get("meddpicc_score"))
        cat = str(fm.get("forecast_cat", "")).strip()

        if status != "open":
            continue

        if not str(fm.get("next_action", "")).strip():
            f.add("WARN", "igiene-pipeline", n.rel, "next_action vuoto")
        if not fm.get("next_action_date"):
            f.add("INFO", "igiene-pipeline", n.rel, "next_action_date vuota")
        if updated and (today - updated).days > stale_days:
            f.add("WARN", "igiene-pipeline", n.rel, "non aggiornata da %d giorni (updated %s)" % ((today - updated).days, updated))
        if close and close < today:
            f.add("ERROR", "igiene-pipeline", n.rel, "expected_close %s è passata ma status è open" % close)
        if close and original and close != original and as_num(fm.get("slips")) in (0, None):
            f.add("WARN", "igiene-pipeline", n.rel, "expected_close ≠ original_close ma slips = %s" % fm.get("slips"))
        if amount is not None and pct is not None and weighted is not None:
            expected = round(amount * pct, 2)
            if abs(expected - weighted) > 1.0:
                f.add("ERROR", "igiene-pipeline", n.rel, "weighted_eur %.2f ≠ amount_eur × stage_pct (%.2f)" % (weighted, expected))
        if not str(fm.get("product", "")).strip():
            f.add("INFO", "igiene-pipeline", n.rel, "product vuoto")

        filled = [k for k in MEDDPICC_FIELDS if str(fm.get(k, "")).strip()]
        if md_score is not None and int(md_score) != len(filled):
            f.add("WARN", "meddpicc", n.rel, "meddpicc_score %d ma %d campi compilati" % (int(md_score), len(filled)))
        if amount is not None:
            for threshold, keys in MEDDPICC_REQUIRED:
                if amount > threshold:
                    for k in keys:
                        if not str(fm.get(k, "")).strip():
                            f.add("WARN", "meddpicc", n.rel, "%s richiesto sopra €%s ed è vuoto" % (k, format(threshold, ",d").replace(",", ".")))

        rule = FORECAST_RULES.get(cat)
        if rule and stage is not None:
            problems = []
            if stage < rule.get("min_stage", 0):
                problems.append("stage L%d < L%d" % (stage, rule["min_stage"]))
            if "max_stage" in rule and stage > rule["max_stage"]:
                problems.append("stage L%d > L%d" % (stage, rule["max_stage"]))
            if rule.get("min_meddpicc") and (md_score is None or md_score < rule["min_meddpicc"]):
                problems.append("MEDDPICC %s < %d" % (int(md_score) if md_score is not None else "n/d", rule["min_meddpicc"]))
            if rule.get("in_quarter") and quarter_of(close) != cur_q:
                problems.append("close %s fuori dal trimestre corrente" % (close if close else "n/d"))
            if problems:
                f.add("WARN", "forecast", n.rel, "forecast_cat '%s' non supportata dalle regole: %s" % (cat, "; ".join(problems)))
        elif cat and cat not in FORECAST_RULES and cat not in ("Closed", "Omitted"):
            f.add("WARN", "forecast", n.rel, "forecast_cat '%s' non è una categoria prevista" % cat)

    for did, files in sorted(seen_ids.items()):
        if len(files) > 1:
            f.add("ERROR", "deal-id", files[0], "deal_id %s usato da %d note: %s" % (did, len(files), ", ".join(files)))
    return deals


def check_reconciliation(notes, deals, f):
    accounts = [n for n in notes if n.type == "stakeholder" and os.path.basename(n.rel) != "_index.md"]
    page_by_key = {}
    for n in accounts:
        for key in {norm_account(n.stem), norm_account(n.fm.get("account"))}:
            if key:
                page_by_key.setdefault(key, n)

    def page_for(deal):
        key = norm_account(deal.fm.get("account"))
        page = page_by_key.get(key)
        if page is None:
            # match parziale: "verta robotics" vs "verta robotics spa"
            for pk, pn in page_by_key.items():
                if pk and (pk in key or key in pk):
                    return pn
        return page

    deal_sum, won_sum = defaultdict(float), defaultdict(float)
    orphan_accounts = defaultdict(float)
    for d in deals:
        amount = as_num(d.fm.get("amount_eur")) or 0.0
        status = str(d.fm.get("status", "")).lower()
        page = page_for(d)
        if status == "open":
            if page is None:
                orphan_accounts[str(d.fm.get("account"))] += amount
            else:
                deal_sum[page.rel] += amount
        elif status in ("won", "closed won", "closed-won") or "won" in status:
            if page is not None:
                won_sum[page.rel] += amount

    rows, tot_deals, tot_pages = [], 0.0, 0.0
    for n in sorted(accounts, key=lambda x: x.rel):
        page_val = as_num(n.fm.get("pipeline_eur")) or 0.0
        deal_val = deal_sum.get(n.rel, 0.0)
        won_val = won_sum.get(n.rel, 0.0)
        tot_deals += deal_val
        tot_pages += page_val
        delta = deal_val - page_val
        if abs(delta) <= 1.0:
            continue
        # classificazione: il delta è spiegato dal valore già vinto?
        # tolleranza relativa: i rollup account sono arrotondati (es. 50.000 dichiarati vs 50.400 vinti)
        if won_val > 0 and abs(delta + won_val) <= max(1.0, 0.02 * won_val):
            cause = ("viola la definizione: pipeline_eur include il valore vinto (€%s) — "
                     "va in won_eur (pipeline-config)" % fmt_eur(won_val))
            sev = "ERROR"
        elif page_val == 0:
            cause = "pipeline_eur mai valorizzato"
            sev = "ERROR"
        elif deal_val == 0:
            cause = "nessuna deal aperta: pipeline_eur residuo"
            sev = "ERROR"
        else:
            cause = "drift reale"
            sev = "ERROR"
        rows.append((n.stem, deal_val, page_val, won_val, delta, cause))
        f.add(sev, "riconciliazione", n.rel,
              "pipeline_eur €%s vs deal aperte €%s (delta €%s) — %s"
              % (fmt_eur(page_val), fmt_eur(deal_val), fmt_eur(delta), cause))

    # won_eur dichiarato sulla pagina vs somma effettiva delle deal vinte
    for n in sorted(accounts, key=lambda x: x.rel):
        declared = as_num(n.fm.get("won_eur"))
        actual = won_sum.get(n.rel, 0.0)
        if declared is None and actual > 0:
            f.add("WARN", "riconciliazione", n.rel,
                  "€%s di deal vinte e nessun won_eur in frontmatter" % fmt_eur(actual))
        elif declared is not None and abs(declared - actual) > 1.0:
            f.add("WARN", "riconciliazione", n.rel,
                  "won_eur €%s ≠ somma deal vinte €%s" % (fmt_eur(declared), fmt_eur(actual)))
    for acct, amount in sorted(orphan_accounts.items(), key=lambda kv: -kv[1]):
        f.add("WARN", "account-senza-pagina", "wiki/pipeline/",
              "%s: €%s aperti, nessuna pagina in wiki/stakeholders/" % (acct, fmt_eur(amount)))
    with_deals = set(k for k, v in deal_sum.items() if v > 0)
    return rows, tot_deals, tot_pages, orphan_accounts, with_deals


INTERACTION_HEADING = re.compile(r"(?mi)^##+\s*(Interazioni|Key Interactions|Interactions)\s*$")


def last_interaction(note):
    """Data dell'ultima voce datata nel log interazioni. Non falsificabile toccando updated."""
    m = INTERACTION_HEADING.search(note.text)
    if not m:
        return None
    rest = note.text[m.end():]
    nxt = re.search(r"(?m)^##\s", rest)
    section = rest[:nxt.start()] if nxt else rest
    dates = [as_date(d) for d in re.findall(r"\d{4}-\d{2}-\d{2}", section)]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def check_stakeholder_freshness(notes, f, today, stale_days, with_deals):
    for n in notes:
        if n.type != "stakeholder" or os.path.basename(n.rel) == "_index.md":
            continue
        # la freschezza si misura sull'ultima interazione registrata, non su 'updated':
        # 'updated' è autodichiarato e si azzera toccando il frontmatter
        last = last_interaction(n)
        basis = "ultima interazione"
        if last is None:
            last = as_date(n.fm.get("updated"))
            basis = "updated (nessun log interazioni)"
        age = (today - last).days if last else None
        if not INTERACTION_HEADING.search(n.text):
            f.add("INFO", "staleness", n.rel,
                  "nessuna sezione '## Interazioni': niente storia datata su cui misurare, "
                  "e `account-note` non ha dove scrivere")
        if age is not None and n.rel in with_deals and age > stale_days + 7:
            f.add("WARN", "staleness", n.rel,
                  "ha deal aperte e nessun movimento da %d giorni (base: %s)" % (age, basis))
        elif age is not None and age > stale_days * 3:
            f.add("INFO", "staleness", n.rel, "nessun movimento da %d giorni (base: %s)" % (age, basis))
        if str(n.fm.get("status", "")).strip() == "seed":
            f.add("INFO", "staleness", n.rel, "status ancora 'seed'")


def fmt_eur(value):
    s = "{:,.0f}".format(abs(value)).replace(",", ".")
    return ("-" if value < 0 else "") + s


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

CHECK_TITLES = [
    ("frontmatter", "Frontmatter"),
    ("wikilink", "Wikilink"),
    ("orfani", "Pagine orfane"),
    ("canvas", "Canvas"),
    ("segnaposto", "Segnaposto non risolti"),
    ("provenienza", "Provenienza (sources → .raw/)"),
    ("template", "Template vs schema"),
    ("index-drift", "Index drift"),
    ("igiene-pipeline", "Igiene pipeline"),
    ("meddpicc", "MEDDPICC"),
    ("forecast", "Coerenza forecast"),
    ("chiusure", "Reason su deal chiuse"),
    ("deal-id", "Collisioni deal_id"),
    ("riconciliazione", "Riconciliazione deal ↔ account"),
    ("account-senza-pagina", "Account senza pagina"),
    ("staleness", "Staleness"),
]


def write_report(path, f, ctx):
    out = []
    a = out.append
    a("---")
    a("type: meta")
    a('title: "Lint report (generato)"')
    a("created: %s" % ctx["today"])
    a("updated: %s" % ctx["today"])
    a("tags:")
    a("  - meta")
    a("  - lint")
    a("  - eval")
    a("maturity: generated")
    a("related:")
    a('  - "[[second-brain-playbook]]"')
    a('  - "[[corrections]]"')
    a('  - "[[pipeline-config]]"')
    a("---")
    a("")
    a("# Lint report")
    a("")
    a("Navigation: [[../index]] | [[second-brain-playbook]]")
    a("")
    a("> [!warning] File generato — non editare a mano")
    a("> Prodotto da `tools/lint/vault.py`, sovrascritto a ogni run. Copre solo i controlli")
    a("> **meccanici**: il lint dei claim stale resta un pass a giudizio.")
    a("")
    a("Run: %s · note analizzate: %d · deal note: %d · trimestre di riferimento: %dQ%d"
      % (ctx["today"], ctx["n_notes"], ctx["n_deals"], ctx["quarter"][0], ctx["quarter"][1]))
    a("")
    a("| Severità | Conteggio |")
    a("|---|---|")
    a("| ERROR | %d |" % f.count("ERROR"))
    a("| WARN | %d |" % f.count("WARN"))
    a("| INFO | %d |" % f.count("INFO"))
    a("")
    a("| Controllo | ERROR | WARN | INFO |")
    a("|---|---|---|---|")
    for key, title in CHECK_TITLES:
        items = f.by_check(key)
        if not items:
            continue
        a("| %s | %d | %d | %d |" % (
            title,
            len([i for i in items if i["sev"] == "ERROR"]),
            len([i for i in items if i["sev"] == "WARN"]),
            len([i for i in items if i["sev"] == "INFO"]),
        ))
    a("")

    rows = ctx["recon_rows"]
    a("## Riconciliazione deal ↔ account")
    a("")
    a("Somma `amount_eur` delle deal note **aperte** contro `pipeline_eur` sulle pagine account.")
    a("Definizione in [[pipeline-config]]: `pipeline_eur` = **solo pipeline aperta**, il valore")
    a("vinto vive in `won_eur` e si somma separatamente.")
    a("")
    if not rows:
        a("> [!success] Nessun delta")
        a("> Ogni `pipeline_eur` corrisponde alla somma delle deal aperte dell'account, e ogni")
        a("> `won_eur` alla somma delle deal vinte. Sezione vuota = verificata, non saltata.")
        a("")
    if rows:
        a("| Account | Deal aperte | pipeline_eur | Già vinto | Delta | Causa |")
        a("|---|---:|---:|---:|---:|---|")
        for stem, deal_val, page_val, won_val, delta, cause in sorted(rows, key=lambda r: -abs(r[4])):
            a("| %s | €%s | €%s | €%s | €%s | %s |" % (
                stem, fmt_eur(deal_val), fmt_eur(page_val), fmt_eur(won_val), fmt_eur(delta), cause))
        a("| **Totale pagine account** | **€%s** | **€%s** | | **€%s** | |"
          % (fmt_eur(ctx["tot_deals"]), fmt_eur(ctx["tot_pages"]), fmt_eur(ctx["tot_deals"] - ctx["tot_pages"])))
        a("")
        by_cause = defaultdict(float)
        for _, _, _, _, delta, cause in rows:
            by_cause[cause.split(":")[0].split("(")[0].strip()] += delta
        a("Scomposizione del delta per causa:")
        a("")
        for cause, amount in sorted(by_cause.items(), key=lambda kv: -abs(kv[1])):
            a("- %s: €%s" % (cause, fmt_eur(amount)))
        a("")
    if ctx["orphan_accounts"]:
        a("Deal aperte su account **senza pagina** in `wiki/stakeholders/` (escluse dal rollup sopra):")
        a("")
        a("| Account | Deal aperte |")
        a("|---|---:|")
        orph_tot = 0.0
        for acct, amount in sorted(ctx["orphan_accounts"].items(), key=lambda kv: -kv[1]):
            orph_tot += amount
            a("| %s | €%s |" % (acct, fmt_eur(amount)))
        a("| **Totale** | **€%s** |" % fmt_eur(orph_tot))
        a("")
        a("Totale pipeline aperta = €%s (con pagina) + €%s (senza pagina) = **€%s**."
          % (fmt_eur(ctx["tot_deals"]), fmt_eur(orph_tot), fmt_eur(ctx["tot_deals"] + orph_tot)))
        a("")

    for key, title in CHECK_TITLES:
        items = f.by_check(key)
        if not items or key in ("riconciliazione", "account-senza-pagina"):
            continue
        a("## %s" % title)
        a("")
        for sev in ("ERROR", "WARN", "INFO"):
            group = [i for i in items if i["sev"] == sev]
            if not group:
                continue
            a("**%s (%d)**" % (sev, len(group)))
            a("")
            for i in group:
                a("- `%s` — %s" % (i["where"], i["msg"]))
            a("")

    a("## Cosa questo lint NON copre")
    a("")
    a("Dichiarato per non far leggere \"tutto verde\" come \"tutto verificato\":")
    a("")
    a("- **Claim stale** — un fatto corretto alla scrittura e superato dopo. Richiede giudizio: resta un pass LLM.")
    a("- **Accuratezza contro la fonte** — è il loop 2 del playbook (3 pagine a caso vs `.raw/`), non automatizzabile qui.")
    for folder, why in sorted(INDEX_LISTING_EXEMPT.items()):
        a("- **`%s/_index.md`** non è controllato voce per voce: %s." % (folder, why))
    for ntype, why in sorted(ORPHAN_EXEMPT_TYPES.items()):
        a("- **Note di tipo `%s`** escluse dal controllo orfani: %s." % (ntype, why))
    a("- **Conformità del materiale esterno** (GA-only, roadmap, pricing) — è un controllo separato sui file consegnati, non sul vault.")
    a("- **La staleness si misura sul campo `updated`, che è autodichiarato**: toccare il")
    a("  frontmatter azzera l'allarme senza che il contenuto sia stato rivisto. Da agganciare")
    a("  alla data dell'ultima voce in `## Interazioni`, che non è falsificabile allo stesso modo.")
    a("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


# --------------------------------------------------------------------------


def emit_schema(path, today):
    """Pubblica lo schema come pagina del vault. La definizione vive nel codice: questa
    pagina è generata, così non esiste una seconda copia da tenere allineata."""
    out = ["---", "type: meta", 'title: "Frontmatter schema (generato)"',
           "created: %s" % today, "updated: %s" % today, "tags:", "  - meta", "  - schema",
           "maturity: generated", "related:", '  - "[[vault-usage-guide]]"',
           '  - "[[pipeline-config]]"', "---", "",
           "# Frontmatter schema", "",
           "Navigation: [[../index]] | [[vault-usage-guide]]", "",
           "> [!warning] Pagina generata — non editare a mano",
           "> Prodotta da `python3 tools/lint/vault.py --emit-schema`. La definizione vive nel",
           "> codice del lint, che è anche ciò che la verifica: **una sola fonte**. Prima lo schema",
           "> stava in tre posti (`_templates/`, il blocco YAML in `stakeholders/_index.md`, e le",
           "> aspettative implicite delle skill) e derivavano l'uno dall'altro.", "",
           "## Le due chiavi che venivano confuse", "",
           "- **`status` = stato.** Solo sui tipi che hanno un ciclo di vita. `deals.base` filtra su questo.",
           "- **`maturity` = maturità della pagina.** Quanto è completa e curata, non cosa sta succedendo.",
           "",
           "Erano la stessa chiave: su 13 note erano stati scritti entrambi i significati e YAML",
           "tiene l'ultimo, quindi lo stato reale si perdeva in silenzio (`done` sovrascritto da",
           "`mature`, `in-progress` da `developing`).", "",
           "## Campi obbligatori su ogni nota", "",
           ", ".join("`%s`" % k for k in REQUIRED_ALL), "",
           "## Per tipo", "",
           "| type | `status` ammessi | usa `maturity`? | altri campi obbligatori |",
           "|---|---|---|---|"]
    types = sorted(set(list(STATUS_VOCAB) + list(MATURITY_ONLY_TYPES) + list(REQUIRED_BY_TYPE)))
    for ty in types:
        st = ", ".join("`%s`" % v for v in sorted(STATUS_VOCAB.get(ty, []))) or "— (non usa status)"
        ma = "**sì, obbligatoria**" if ty in MATURITY_ONLY_TYPES else "opzionale"
        extra = ", ".join("`%s`" % k for k in REQUIRED_BY_TYPE.get(ty, [])) or "—"
        out.append("| `%s` | %s | %s | %s |" % (ty, st, ma, extra))
    out += ["", "`maturity` ammessi su qualunque tipo: " +
            ", ".join("`%s`" % v for v in sorted(MATURITY_VOCAB)), "",
            "## Pagine partner", "",
            "Una nota `stakeholder` con `partner` fra i tag deve dichiarare anche `partner_type` e",
            "`partner_autonomy`. Valori ammessi per l'autonomia, dal meno al più autonomo: " +
            ", ".join("`%s`" % v for v in PARTNER_AUTONOMY) + ".",
            "L'autonomia è la metrica dell'enablement: dichiararla obbliga a dire cosa manca per",
            "salire di livello.", "",
            "## Grafie prodotto non approvate", "",
            "| Trovata | Da usare |", "|---|---|"]
    for alias, correct in sorted(PRODUCT_ALIASES.items()):
        out.append("| `%s` | %s | " % (alias, correct))
    out += ["", "## Regole verificate altrove", "",
            "- Definizione di `pipeline_eur` / `won_eur` e reason obbligatorie sulle chiusure: [[pipeline-config]].",
            "- Ogni voce `sources:` che punta a `.raw/` deve puntare a un file esistente, altrimenti",
            "  le affermazioni della pagina non sono ri-derivabili dal vault.",
            "- I template in `_templates/` sono verificati contro questo schema: un default fuori",
            "  vocabolario è un ERROR, perché ogni nota creata da quel template nasce sbagliata.", ""]
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Lint deterministico del vault.")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument("--report", default=os.path.join("wiki", "meta", "lint-report.md"))
    ap.add_argument("--stale-days", type=int, default=14)
    ap.add_argument("--today", default=None, help="YYYY-MM-DD, per run riproducibili")
    ap.add_argument("--no-report", action="store_true", help="solo output a schermo")
    ap.add_argument("--max-errors", type=int, default=0,
                    help="fallisce solo se gli ERROR superano N (ratchet sul debito esistente)")
    ap.add_argument("--emit-schema", metavar="PATH", nargs="?", const=os.path.join("wiki", "meta", "frontmatter-schema.md"),
                    help="pubblica lo schema del frontmatter come pagina del vault ed esce")
    args = ap.parse_args()

    root = args.root
    # VAULT_TODAY fissa la data per run riproducibili (lo usa il vault demo, via .vault-today)
    today = as_date(args.today or os.environ.get("VAULT_TODAY")) or dt.date.today()
    if not os.path.isdir(os.path.join(root, "wiki")):
        sys.stderr.write("wiki/ non trovata sotto %s\n" % root)
        return 2

    report_rel = args.report if not os.path.isabs(args.report) else os.path.relpath(args.report, root)
    if args.emit_schema:
        sp = args.emit_schema if os.path.isabs(args.emit_schema) else os.path.join(root, args.emit_schema)
        emit_schema(sp, today)
        print("schema → %s" % args.emit_schema)
        return 0

    notes, assets = collect(root, exclude=[report_rel])
    f = Findings()
    check_frontmatter(notes, f)
    check_placeholders(notes, f)
    check_sources_exist(root, notes, f)
    check_templates(root, f)
    check_links(root, notes, assets, f, extra_targets=[report_rel])
    check_index_drift(root, notes, f)
    deals = check_pipeline(notes, f, today, args.stale_days)
    recon_rows, tot_deals, tot_pages, orphan_accounts, with_deals = check_reconciliation(notes, deals, f)
    check_stakeholder_freshness(notes, f, today, args.stale_days, with_deals)

    ctx = {
        "today": today, "n_notes": len(notes), "n_deals": len(deals),
        "quarter": quarter_of(today), "recon_rows": recon_rows,
        "tot_deals": tot_deals, "tot_pages": tot_pages,
        "orphan_accounts": orphan_accounts,
    }

    if not args.no_report:
        report_path = args.report if os.path.isabs(args.report) else os.path.join(root, args.report)
        d = os.path.dirname(report_path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        write_report(report_path, f, ctx)

    print("vault lint · %s · %d note · %d deal" % (today, len(notes), len(deals)))
    print("  ERROR %d · WARN %d · INFO %d" % (f.count("ERROR"), f.count("WARN"), f.count("INFO")))
    for key, title in CHECK_TITLES:
        items = f.by_check(key)
        if items:
            print("  %-28s E%-3d W%-3d I%-3d" % (
                title,
                len([i for i in items if i["sev"] == "ERROR"]),
                len([i for i in items if i["sev"] == "WARN"]),
                len([i for i in items if i["sev"] == "INFO"])))
    if not args.no_report:
        print("  report → %s" % args.report)
    errs = f.count("ERROR")
    if args.max_errors:
        if errs > args.max_errors:
            print("  FAIL: %d ERROR > soglia %d — il debito è aumentato" % (errs, args.max_errors))
            return 1
        print("  OK: %d ERROR ≤ soglia %d%s" % (errs, args.max_errors,
              " — abbassa la soglia in tools/lint/error-baseline.txt" if errs < args.max_errors else ""))
        return 0
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
