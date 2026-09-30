#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checks.py — le asserzioni dell'eval, divise per classe.

La divisione è il punto di questo file, non un dettaglio organizzativo. Segue
la stessa regola di tools/lint/vault.py: quello che si può verificare
meccanicamente NON si fa verificare a un modello.

  STRUTTURA   il formato dell'output       -> parsing, deterministico
  GROUNDING   i fatti citati vs. la fonte  -> confronto testuale, deterministico
  GIUDIZIO    la qualita del ragionamento  -> LLM-judge (judge.py), costoso

Le prime due classi girano offline, gratis, e danno sempre lo stesso risultato.
La terza gira solo quando serve e viene marcata come tale nel report, perche un
giudizio non deterministico non ha lo stesso peso probatorio di un parsing.

Solo stdlib.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# vocabolario
# ---------------------------------------------------------------------------

# Le 8 dimensioni MEDDPICC, con le varianti di scrittura ammesse nella tabella.
DIMENSIONS = {
    "metrics": ["metrics", "metriche"],
    "economic_buyer": ["economic buyer", "economic-buyer"],
    "decision_criteria": ["decision criteria", "criteri di decisione"],
    "decision_process": ["decision process", "processo di decisione"],
    "paper_process": ["paper process", "processo contrattuale"],
    "identify_pain": ["identify pain", "pain"],
    "champion": ["champion"],
    "competition": ["competition", "concorrenza"],
}

# Come si scrive "non lo sappiamo". Se una cella contiene uno di questi
# marcatori, la dimensione e' dichiarata scoperta. Serve per verificare in modo
# deterministico che il modello non abbia riempito un buco.
UNKNOWN_MARKERS = [
    "gap", "unknown", "empty", "vuoto", "sconosciut", "non confermat",
    "non identificat", "non document", "non stabilit", "mancante", "assente",
    "da confermare", "n/d", "n.d.", "non noto", "non nota", "nessun dato",
    "nessuno", "todo",
]
# "?" stava in questa lista ed era troppo largo: una cella che finisce con
# una domanda vera veniva letta come dimensione scoperta. Un segno di
# punteggiatura non e' un vocabolario.

# Marcatori di inferenza: il prompt chiede di distinguere inferito da confermato.
INFERENCE_MARKERS = ["inferit", "inferred", "ipotes", "presum", "da verificare",
                     "non confermat", "non verificat", "unconfirmed"]

# "Nessun gap critico" scritto come bullet e' una riga che dice zero, non un gap.
# Senza il filtro il caso di controllo (deal sano) fallisce per un dettaglio
# tipografico: il falso positivo che fa perdere fiducia in una suite.
#
# Ma il filtro va stretto, e l'ha dimostrato selftest.py: la prima versione
# scartava qualunque bullet iniziasse per "nessun", quindi anche
# "Nessun champion: Sollner non porta il caso" — che e' un gap, non la sua
# assenza. Serve che il soggetto negato sia proprio il gap.
NO_GAP_RE = re.compile(
    r"^(nessun\w*|non ci sono|no)\s+"
    r"(gap|criticit\w*|problem\w*|element\w*|blocc\w*|critical)\b"
)
NO_GAP_BARE = {"nessuno", "nessuna", "none", "n/a", "n.a.", "n/d", "-", "--"}


# ---------------------------------------------------------------------------
# normalizzazione
# ---------------------------------------------------------------------------

def norm(s):
    """Minuscolo, senza accenti, spazi collassati. Per confronti testuali."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def number_variants(n):
    """Forms a number can legitimately take in prose.

    1878000 -> 1878000 | 1,878,000 | 1.878.000 | 1 878 000
             | 1878k | 1,878k | 1.878k | 1878.0k
             | 1.9m | 1,9m | 1.88m

    The k and M suffixes matter more than they look. A real forecast readout
    writes "EUR 1,878k" and "EUR 1.0M", and an earlier version of this
    function produced only a bare "1878k" — so entirely correct figures were
    reported missing, six times in one case. A suite that cries wolf on
    formatting stops being read, which costs more than the check is worth.
    """
    n = int(n)
    out = {str(n)}
    for sep in (",", ".", " ", "\u00a0", "'"):
        out.add(f"{n:,}".replace(",", sep))

    if n >= 1000:
        k = n / 1000
        forms = {f"{k:.1f}", f"{k:.2f}".rstrip("0").rstrip(".")}
        if k.is_integer():
            forms.add(str(int(k)))
        for form in forms:
            whole, _, frac = form.partition(".")
            for sep in ("", ",", ".", " "):
                grouped = whole if not sep else f"{int(whole):,}".replace(",", sep)
                if frac:
                    out.add(f"{grouped}.{frac}k")
                    out.add(f"{grouped},{frac}k")
                else:
                    out.add(f"{grouped}k")

    if n >= 100_000:
        for d in (1, 2):
            m = f"{n / 1_000_000:.{d}f}"
            for form in (m, m.rstrip("0").rstrip(".")):
                out.add(form + "m")
                out.add(form.replace(".", ",") + "m")
    return {norm(v) for v in out}


def parse_table(text):
    """Estrae {dimensione: testo cella} dalla tabella MEDDPICC.

    Tollerante: accetta grassetto, la lettera isolata (**M**etrics), colonne
    extra. Non tollerante sul fatto che le 8 righe ci siano.
    """
    found = {}
    for line in text.splitlines():
        if line.count("|") < 2:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        label = norm(re.sub(r"[*_`]", "", cells[0]))
        for key, aliases in DIMENSIONS.items():
            if key in found:
                continue
            if any(label.startswith(a) or label == a for a in aliases):
                found[key] = {"state": cells[1].strip(),
                              "full": " ".join(cells[1:]).strip()}
    return found


def cell_state(table, dim):
    """Il verdetto di una dimensione, senza la prosa di supporto.

    Unirli era sbagliato: in una tabella a tre colonne il verdetto sta nella
    seconda e l'evidenza nella terza, e una riga ben compilata falliva perche'
    la *prosa* conteneva "ma vedi il gap sotto". Con due sole colonne non c'e'
    separazione da fare e lo stato e' la cella intera.
    """
    entry = table.get(dim)
    return norm(entry["state"]) if entry else ""


def cell_full(table, dim):
    entry = table.get(dim)
    return norm(entry["full"]) if entry else ""


def parse_section(text, *titles):
    """Restituisce i bullet di una sezione, cercata per titolo (## o **bold**)."""
    keys = [norm(t) for t in titles]
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        bare = norm(re.sub(r"[#*_`:\-]", " ", line))
        if any(bare.startswith(k) for k in keys):
            start = i + 1
            break
    if start is None:
        return None
    bullets, blanks = [], 0
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            blanks += 1
            if blanks >= 2 and bullets:
                break
            continue
        if re.match(r"^#{1,6}\s", stripped):
            break
        # un nuovo titolo in grassetto su riga propria chiude la sezione
        if re.match(r"^\*\*[^*]+\*\*:?$", stripped) and bullets:
            break
        if re.match(r"^([-*+]|\d+[.)])\s+", stripped):
            bullets.append(re.sub(r"^([-*+]|\d+[.)])\s+", "", stripped))
        blanks = 0
    return bullets


def is_no_gap_line(bullet):
    """Il bullet dichiara che non ci sono gap, invece di esserne uno?"""
    n = norm(re.sub(r"[*_`.]", "", bullet)).strip()
    return n in NO_GAP_BARE or bool(NO_GAP_RE.match(n))


def real_items(bullets):
    """Scarta i bullet che dichiarano l'assenza di elementi."""
    if bullets is None:
        return None
    return [b for b in bullets if not is_no_gap_line(b)]


# ---------------------------------------------------------------------------
# CLASSE 1 — STRUTTURA
# ---------------------------------------------------------------------------

def check_structure(text, spec):
    """Il formato promesso dalla skill c'e' tutto?

    Un output che salta la sezione azioni non e' 'un po' peggiore': e'
    inutilizzabile a valle, perche' chi legge il review cerca cosa fare.
    """
    out = []
    table = parse_table(text)
    missing = [k for k in DIMENSIONS if k not in table]
    out.append(_r("structure", "tabella-8-dimensioni",
                  not missing,
                  "tutte e 8 le dimensioni presenti" if not missing
                  else f"dimensioni mancanti: {', '.join(missing)}"))

    empty = [k for k in table if not cell_full(table, k)]
    out.append(_r("structure", "nessuna-cella-vuota", not empty,
                  "ogni dimensione ha un contenuto" if not empty
                  else f"celle vuote: {', '.join(empty)}"))

    raw_gaps = parse_section(text, "gap critici", "critical gaps")
    raw_actions = parse_section(text, "azione per gap", "azioni", "action per gap", "next actions")
    gaps, actions = real_items(raw_gaps), real_items(raw_actions)
    # Alcuni output mettono l'azione sotto il proprio gap invece che in una
    # sezione a parte. Soddisfa "un'azione per gap" benissimo: solo un
    # controllo che confonde impaginazione e sostanza protesta.
    inline = re.findall(r"(?im)^\s*(?:[-*+]\s*)?\*\*(?:azione|action)[^:*]*:?\*\*:?\s*(.+)$", text)
    if inline and (actions is None or len(inline) > len(actions)):
        actions, raw_actions = inline, inline
    out.append(_r("structure", "sezione-gap-presente", raw_gaps is not None,
                  f"{len(gaps)} gap reali" if gaps is not None else "sezione 'Gap critici' assente"))
    out.append(_r("structure", "sezione-azioni-presente", raw_actions is not None,
                  f"{len(actions)} azioni elencate" if actions is not None else "sezione 'Azione per gap' assente"))

    # La regola della skill: esattamente un'azione per gap critico.
    if gaps is not None and actions is not None:
        ok = len(actions) == len(gaps)
        out.append(_r("structure", "una-azione-per-gap", ok,
                      f"{len(gaps)} gap / {len(actions)} azioni"))
        # Un'azione senza owner non e' azionabile.
        ownerless = [a for a in actions if not re.search(r"\(([^)]{2,40})\)|owner\s*:", a, re.I)]
        out.append(_r("structure", "azioni-con-owner", not ownerless,
                      "ogni azione ha un owner" if not ownerless
                      else f"{len(ownerless)} azioni senza owner indicato"))

    # Quanti gap ci si aspetta. Il limite superiore e' il controllo che rileva
    # il modello che inventa problemi per sembrare utile su un deal sano.
    st = spec.get("structure", {})
    if gaps is not None and "max_gaps" in st:
        out.append(_r("structure", f"al-massimo-{st['max_gaps']}-gap",
                      len(gaps) <= st["max_gaps"], f"{len(gaps)} gap dichiarati"))
    if gaps is not None and "min_gaps" in st:
        out.append(_r("structure", f"almeno-{st['min_gaps']}-gap",
                      len(gaps) >= st["min_gaps"], f"{len(gaps)} gap dichiarati"))
    return out


# ---------------------------------------------------------------------------
# variante: l'output atteso NON e' un review
# ---------------------------------------------------------------------------

def check_clarification(text, spec):
    """Quando il nome dell'account e' ambiguo, la risposta giusta e' una domanda.

    Va verificato l'opposto del caso normale: la tabella NON deve esserci.
    Un review prodotto sull'entita' sbagliata e' il fallimento peggiore della
    skill, perche' e' perfettamente formato e nessuno se ne accorge.
    """
    out = []
    table = parse_table(text)
    out.append(_r("structure", "nessuna-tabella-prodotta", len(table) < 4,
                  f"{len(table)} dimensioni trovate (attese 0)"))
    out.append(_r("structure", "pone-una-domanda", "?" in text,
                  "l'output contiene una domanda" if "?" in text else "nessuna domanda posta"))
    hay = norm(text)
    for cand in spec.get("must_offer", []):
        ok = norm(cand) in hay
        out.append(_r("grounding", f"elenca «{cand}»", ok,
                      "presente" if ok else "candidato non offerto"))
    for item in spec.get("grounding", {}).get("must_absent", []):
        ok = norm(item) not in hay
        out.append(_r("grounding", f"non inventa «{item}»", ok,
                      "assente, corretto" if ok else "PRESENTE ma non esiste nella fonte"))
    return out


# ---------------------------------------------------------------------------
# CLASSE 2 — GROUNDING
# ---------------------------------------------------------------------------

def check_grounding(text, spec):
    """Quello che l'output afferma sta nella fonte? E quello che non c'e' resta fuori?

    Il secondo controllo (must_absent) e' quello che conta davvero: misura
    l'invenzione, che e' il modo tipico in cui questi sistemi falliscono in
    silenzio. Un output allucinato e' formalmente perfetto.
    """
    out = []
    hay = norm(text)
    g = spec.get("grounding", {})

    for item in g.get("must_cite", []):
        if isinstance(item, dict) and "number" in item:
            ok = contains_number(hay, number_variants(item["number"]))
            label = f"cita {item['number']}"
        else:
            ok = norm(item) in hay
            label = f"cita «{item}»"
        out.append(_r("grounding", label, ok,
                      "presente" if ok else "assente dall'output"))

    for item in g.get("must_absent", []):
        ok = norm(item) not in hay
        out.append(_r("grounding", f"non inventa «{item}»", ok,
                      "assente, corretto" if ok
                      else "PRESENTE ma non esiste nella fonte — invenzione"))

    # Le dimensioni che la fonte non copre devono restare dichiarate scoperte.
    table = parse_table(text)
    for dim in g.get("must_flag_unknown", []):
        cell = cell_state(table, dim)
        ok = bool(cell) and any(m in cell for m in UNKNOWN_MARKERS)
        out.append(_r("grounding", f"{dim} dichiarato scoperto", ok,
                      f"«{cell[:70]}»" if cell else "riga assente"))

    # ...e quelle che la fonte copre non devono essere svalutate a gap.
    for dim in g.get("must_be_filled", []):
        cell = cell_state(table, dim)
        ok = bool(cell) and not any(m in cell for m in UNKNOWN_MARKERS)
        out.append(_r("grounding", f"{dim} valorizzato", ok,
                      f"«{cell[:70]}»" if cell else "riga assente"))

    # Se la fonte marca un dato come inferito, l'output deve conservarlo.
    for dim in g.get("must_mark_inferred", []):
        cell = cell_full(table, dim)
        ok = any(m in cell for m in INFERENCE_MARKERS)
        out.append(_r("grounding", f"{dim} marcato come inferito", ok,
                      f"«{cell[:70]}»" if cell else "riga assente"))

    # Alcuni termini non sono vietati: sono vietati *da soli*. "Quillgate Mesh"
    # puo' comparire, ma non senza la qualifica che non e' ancora disponibile.
    # Un divieto secco spingerebbe a non nominarlo mai, che non e' l'obiettivo.
    for q in g.get("must_qualify", []):
        term, window = norm(q["term"]), q.get("within", 150)
        quals = [norm(x) for x in q["qualifier"]]
        hits = [m.start() for m in re.finditer(re.escape(term), hay)]
        unqualified = [
            i for i in hits
            if not any(x in hay[max(0, i - window):i + len(term) + window] for x in quals)
        ]
        ok = not unqualified
        out.append(_r("grounding", f"«{q['term']}» sempre qualificato", ok,
                      f"{len(hits)} occorrenze, tutte qualificate" if ok
                      else f"{len(unqualified)} occorrenze su {len(hits)} senza la qualifica richiesta"))

    for pat in g.get("must_match", []):
        ok = re.search(pat, text, re.I | re.S) is not None
        out.append(_r("grounding", f"pattern /{pat[:44]}/", ok,
                      "trovato" if ok else "non trovato"))
    return out


# ---------------------------------------------------------------------------
# utilita
# ---------------------------------------------------------------------------

def _r(cls, name, passed, detail=""):
    return {"class": cls, "check": name, "pass": bool(passed), "detail": detail}


# ---------------------------------------------------------------------------
# CLASSE 2b — GROUNDING CONTRO ORACOLO
# ---------------------------------------------------------------------------

def contains_number(hay, variants):
    """La forma numerica c'e' *come numero*?

    Il confronto per sottostringa e' sbagliato, e l'ha dimostrato il selftest
    della versione pubblica: una copertura di 1,9 veniva trovata dentro il
    totale "1.331.900", quindi un readout che citava la copertura sbagliata
    passava. I numeri vanno delimitati: non adiacenti a un'altra cifra e non
    dentro un numero con separatori di migliaia.
    """
    for v in variants:
        if re.search(r"(?<!\d)(?<![\d][.,'\s])" + re.escape(v) + r"(?!\d)(?![.,'\s]\d)", hay):
            return True
    return False


def ratio_variants(x):
    """Le scritture ammesse per un rapporto: 1.9, 1,9, 1.90, 190%."""
    out = set()
    for d in (1, 2):
        s = f"{x:.{d}f}"
        out.add(s)
        out.add(s.replace(".", ","))
    out.add(f"{x:.0%}".replace("%", " %"))
    out.add(f"{x:.0%}")
    return {norm(v) for v in out}


def check_oracle(text, spec, facts):
    """Confronta i numeri dell'output con quelli ricalcolati dal fixture.

    L'oracolo (oracle.py) e' una seconda implementazione della stessa
    aritmetica. Qui non si verifica che il modello abbia scritto il numero che
    ci aspettavamo di leggere: si verifica che abbia scritto il numero che
    esce dai dati. Se il fixture cambia, l'atteso cambia da solo.
    """
    out = []
    hay = norm(text)
    o = spec.get("oracle", {})

    for key in o.get("must_cite", []):
        val = facts.get(key)
        if val is None:
            out.append(_r("oracle", f"{key}", False, "chiave assente dall'oracolo"))
            continue
        if isinstance(val, float) and not val.is_integer():
            variants = ratio_variants(val)
        else:
            variants = number_variants(int(val))
        ok = contains_number(hay, variants)
        out.append(_r("oracle", f"{key} = {val:g}", ok,
                      "citato" if ok else f"nessuna delle forme {sorted(variants)[:4]} compare"))

    # Un identificativo che compare "da qualche parte" non prova che il deal
    # sia stato elencato dove serve: selftest_numbers.py ha bocciato la prima
    # versione di questo controllo, perche' un P-005 rimosso dall'elenco dei
    # deal a rischio restava citato in una nota sui dati incoerenti, e il
    # controllo passava. Serve che l'identificativo compaia *con il suo
    # importo* — che e' poi il modo in cui un deal viene davvero elencato.
    amounts = facts.get("amounts_by_id") or {}
    for key in o.get("must_list_ids", []):
        ids = facts.get(key) or []
        missing = []
        for i in ids:
            positions = [m.start() for m in re.finditer(re.escape(norm(i)), hay)]
            amt = amounts.get(i)
            variants = number_variants(int(amt)) if amt else set()
            listed = any(
                contains_number(hay[max(0, p - 160):p + 160], variants)
                for p in positions
            ) if variants else bool(positions)
            if not listed:
                missing.append(i)
        out.append(_r("oracle", f"{key} ({len(ids)}) elencati con l'importo", not missing,
                      "tutti elencati" if not missing
                      else f"non elencati con il proprio valore: {', '.join(missing)}"))

    for key in o.get("must_not_list_ids", []):
        ids = facts.get(key) or []
        leaked = [i for i in ids if norm(i) in hay]
        out.append(_r("oracle", f"fuori scope: {key} ({len(ids)})", not leaked,
                      "nessuna fuga" if not leaked
                      else f"compaiono fuori dal taglio richiesto: {', '.join(leaked)}"))

    # I difetti nei dati vanno dichiarati, non ripuliti in un numero pulito.
    if o.get("must_flag_inconsistencies"):
        bad_ids = sorted({i["deal_id"] for i in facts.get("inconsistencies", [])})
        missing = [i for i in bad_ids if norm(i) not in hay]
        out.append(_r("oracle", f"segnala i deal incoerenti ({len(bad_ids)})", not missing,
                      "tutti nominati" if not missing
                      else f"non nominati: {', '.join(missing)} — il report li ha lavati via"))

    # Un numero che non esiste nei dati e non e' derivabile: invenzione.
    for bad in o.get("must_not_cite_numbers", []):
        ok = not contains_number(hay, number_variants(int(bad)))
        out.append(_r("oracle", f"non cita {bad}", ok,
                      "assente, corretto" if ok else "PRESENTE — numero non nei dati"))
    return out


# ---------------------------------------------------------------------------
# CLASSE 1b — STRUTTURA GENERICA (skill che non producono la tabella MEDDPICC)
# ---------------------------------------------------------------------------

def check_sections(text, spec):
    """Le sezioni promesse dalla skill ci sono, e quelle vietate no.

    Ogni skill dichiara un formato nel proprio SKILL.md. Il formato non e'
    estetica: e' il contratto con chi legge a valle. Una battlecard senza
    'quando perdiamo' e' una brochure, e chi la porta in trattativa se ne
    accorge davanti al cliente.
    """
    out = []
    st = spec.get("sections", {})
    hay = norm(text)

    for title in st.get("required", []):
        # Titolo presente come intestazione, grassetto o inizio riga.
        ok = re.search(rf"(^|\n)\s*(#{{1,6}}\s*|\*\*|\d+\s*[—.\-]\s*)?{re.escape(title)}",
                       text, re.I) is not None or norm(title) in hay
        out.append(_r("structure", f"sezione «{title}»", ok,
                      "presente" if ok else "assente"))

    for title in st.get("forbidden", []):
        ok = norm(title) not in hay
        out.append(_r("structure", f"nessuna sezione «{title}»", ok,
                      "assente, corretto" if ok else "presente ma non prevista"))

    if "min_bullets" in st:
        bullets = [l for l in text.splitlines() if re.match(r"^\s*([-*+]|\d+[.)])\s+", l)]
        out.append(_r("structure", f"almeno-{st['min_bullets']}-bullet",
                      len(bullets) >= st["min_bullets"], f"{len(bullets)} bullet"))

    if "max_words" in st:
        n = len(text.split())
        out.append(_r("structure", f"al-massimo-{st['max_words']}-parole",
                      n <= st["max_words"], f"{n} parole"))
    return out


def read_frontmatter_text(text):
    """Frontmatter piatto da una stringa gia' letta (usato da statecheck.py)."""
    m = re.match(r"^---\n(.*?)\n---", text or "", re.S)
    if not m:
        return {}
    data = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.startswith(" ") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        data[k.strip()] = v.split("  #")[0].strip().strip('"').strip("'")
    return data
