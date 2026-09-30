#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
statecheck.py — asserzioni su cosa una skill ha *fatto*, non su cosa ha detto.

`account-note` e' l'unica skill del vault che scrive. Valutarne la prosa non
serve a niente: il suo prodotto e' la differenza tra il vault prima e dopo.
Cambia l'oggetto della misura, quindi cambia il tipo di asserzione.

Le due classi che contano qui non hanno un equivalente nelle altre skill:

  CIO' CHE DEVE CAMBIARE     un campo aggiornato, una sezione creata, una
                             riga aggiunta in cima al log
  CIO' CHE NON DEVE CAMBIARE ogni altro file del vault, byte per byte

La seconda e' la piu' importante e la piu' trascurata. Una skill che scrive
sbaglia in due modi: non fa quello che deve — e ci si accorge subito — oppure
fa anche qualcos'altro. Il secondo caso e' silenzioso: la nota richiesta viene
scritta correttamente, e nel frattempo una riga di un'altra pagina cambia. Con
un vault sotto git lo si scopre al diff successivo, se qualcuno lo legge.
Qui lo si scopre subito, confrontando gli hash con il fixture di partenza.

Solo stdlib.
"""

import hashlib
import os
import re

from checks import _r, norm, read_frontmatter_text

SENTINELS = {"CHANGED", "UNCHANGED", "NONEMPTY", "EMPTY"}


def _walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".claude")]
        for name in filenames:
            full = os.path.join(dirpath, name)
            yield os.path.relpath(full, root), full


def _digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def snapshot(root):
    """{percorso relativo: sha256} di tutto il vault."""
    return {rel: _digest(full) for rel, full in _walk(root)}


def _read(root, rel):
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _log_entries(text):
    """[(data, testo)] delle voci `## YYYY-MM-DD ...`, nell'ordine del file."""
    if not text:
        return []
    body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    parts = re.split(r"(?m)^##\s+", body)[1:]
    out = []
    for part in parts:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", part.strip())
        out.append((m.group(1) if m else "", part))
    return out


def check_state(pristine, result, spec):
    """Confronta il vault dopo l'esecuzione con il fixture di partenza."""
    out = []
    before, after = snapshot(pristine), snapshot(result)
    st = spec.get("state", {})

    # --- cio' che deve esistere ------------------------------------------
    for rel in st.get("files_created", []):
        out.append(_r("state", f"creato {rel}", rel in after and rel not in before,
                      "creato" if rel in after and rel not in before
                      else ("gia' esisteva" if rel in before else "non creato")))

    for rel in st.get("files_modified", []):
        ok = rel in after and rel in before and before[rel] != after[rel]
        out.append(_r("state", f"modificato {rel}", ok,
                      "modificato" if ok else "invariato o assente"))

    # --- cio' che non deve cambiare --------------------------------------
    # L'asserzione piu' importante del file. Senza, una skill che scrive puo'
    # toccare mezzo vault e passare comunque, perche' ha fatto anche la cosa
    # giusta.
    protected = st.get("files_untouched", [])
    if protected == "*":
        allowed = set(st.get("files_created", [])) | set(st.get("files_modified", []))
        protected = [rel for rel in before if rel not in allowed]
    touched = [rel for rel in protected
               if rel not in after or before.get(rel) != after.get(rel)]
    if protected:
        out.append(_r("state", f"intatti gli altri {len(protected)} file", not touched,
                      "nessun file collaterale toccato" if not touched
                      else f"modificati senza motivo: {', '.join(sorted(touched)[:6])}"))

    # --- frontmatter ------------------------------------------------------
    for rel, fields in (st.get("frontmatter") or {}).items():
        text_before, text_after = _read(pristine, rel), _read(result, rel)
        if text_after is None:
            out.append(_r("state", f"frontmatter {rel}", False, "file assente dopo l'esecuzione"))
            continue
        fm_b = read_frontmatter_text(text_before or "")
        fm_a = read_frontmatter_text(text_after)
        for key, expected in fields.items():
            got = (fm_a.get(key) or "").strip()
            old = (fm_b.get(key) or "").strip()
            if expected == "CHANGED":
                ok, detail = got != old, f"«{old}» -> «{got}»"
            elif expected == "UNCHANGED":
                ok, detail = got == old, f"«{old}» -> «{got}»"
            elif expected == "NONEMPTY":
                ok, detail = bool(got), f"«{got}»"
            elif expected == "EMPTY":
                ok, detail = not got, f"«{got}»"
            else:
                ok, detail = norm(expected) in norm(got), f"«{got}» (atteso ~«{expected}»)"
            out.append(_r("state", f"{rel}:{key} = {expected}", ok, detail))

    # --- contenuto --------------------------------------------------------
    for rel, needles in (st.get("contains") or {}).items():
        text = _read(result, rel) or ""
        for needle in needles:
            ok = norm(needle) in norm(text)
            out.append(_r("state", f"{rel} contiene «{needle}»", ok,
                          "presente" if ok else "assente"))

    # --- convenzioni del vault -------------------------------------------
    # log.md e' append-only con le voci nuove in CIMA. La prima versione di
    # questo controllo cercava una parola chiave nei primi 900 caratteri, e
    # selftest_state.py l'ha bocciata: l'account era gia' nominato in una voce
    # vecchia in testa al file, quindi la voce nuova poteva finire in fondo
    # senza che niente se ne accorgesse. Cercava una parola, non un ordine.
    #
    # La versione giusta legge le date delle voci: la prima del file deve
    # essere la piu' recente, e ne deve essere comparsa una nuova.
    top = st.get("log_top_mentions")
    if top:
        rel = st.get("log_file", "wiki/log.md")
        before_entries = _log_entries(_read(pristine, rel))
        after_entries = _log_entries(_read(result, rel))

        out.append(_r("state", "voce di log aggiunta",
                      len(after_entries) > len(before_entries),
                      f"{len(before_entries)} -> {len(after_entries)} voci"))

        if after_entries:
            dates = [d for d, _ in after_entries if d]
            first = after_entries[0][0]
            ordered = bool(first) and first == max(dates)
            out.append(_r("state", "voce di log in cima", ordered,
                          f"prima voce {first}, piu' recente {max(dates) if dates else '—'}"
                          + ("" if ordered else " — la voce nuova e' finita in fondo")))
            head = norm(after_entries[0][1])
            missing = [t for t in top if norm(t) not in head]
            out.append(_r("state", "la voce in cima e' quella giusta", not missing,
                          "menziona quanto atteso" if not missing
                          else f"la prima voce non menziona: {', '.join(missing)}"))
        else:
            out.append(_r("state", "voce di log in cima", False, "nessuna voce datata trovata"))

    # Una sezione cronologica va letta dal piu' recente: la voce nuova prima
    # di quelle vecchie.
    for rel, cfg in (st.get("newest_first") or {}).items():
        text = _read(result, rel) or ""
        i_new, i_old = norm(text).find(norm(cfg["newer"])), norm(text).find(norm(cfg["older"]))
        ok = i_new != -1 and (i_old == -1 or i_new < i_old)
        out.append(_r("state", f"{rel}: «{cfg['newer']}» prima di «{cfg['older']}»", ok,
                      f"posizioni {i_new} / {i_old}"))
    return out
