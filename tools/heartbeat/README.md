# Battito — cosa si è mosso e cosa è rimasto fermo

```bash
python3 tools/heartbeat/heartbeat.py              # aggiorna snapshot + wiki/meta/heartbeat.md
python3 tools/heartbeat/heartbeat.py --no-state   # prova senza consumare il confronto
python3 tools/heartbeat/heartbeat.py --today 2026-10-01
```

## Perché esiste

Diagnosi fatta sul vault originale (dati reali, non pubblicati qui): **quasi tutte le deal
aperte non toccate da oltre 30 giorni**, **la maggior parte del valore aperto con
`expected_close` già passata**, la cadenza del log dimezzata in due mesi, il correction
log fermo da settimane, la forecast accuracy mai misurata.

Nello stesso periodo il vault ha prodotto diversi deliverable. Quindi non era rotto: era che
**tutto quello che richiedeva all'owner di ricordarsi di guardare è decaduto**, mentre
tutto quello che gli veniva chiesto funzionava benissimo. Il battito toglie il
"ricordarsi".

## Non è un secondo lint

| | Domanda | Quando gira |
|---|---|---|
| `tools/lint/vault.py` | Il vault è **integro**? frontmatter, link, totali | a ogni commit (hook) |
| `tools/heartbeat/heartbeat.py` | Cosa si è **mosso**, cosa è fermo, cosa scade | settimanale |

Il lint misura lo **stato** e blocca i commit. Il battito misura il **movimento** e non
blocca niente. Il parsing è importato da `tools/lint/vault.py` — `parse_frontmatter`,
`as_date`, `last_interaction`, `fmt_eur` — così le due viste non derivano: se cambia la
definizione di "stale", cambia in un posto solo.

## I sei secchi

1. **Questa settimana** — `next_action_date` entro 7 giorni. L'unica parte proattiva, e
   l'unica che nessun altro strumento produce.
2. **Scaduto** — data passata e stato che non l'ha seguita. Ordinato per valore.
3. **Silenzio** — quello che non si muove *pur non avendo scadenze sfondate*. Le deal già
   elencate fra le scadute sono escluse: due secchi che dicono la stessa cosa sono un secchio.
4. **Movimento** — il diff con lo snapshot precedente. È la ragione per cui si chiama battito.
5. **Fermo** — decisioni e deliverable nello stesso stato da oltre 30 giorni.
6. **Da ingerire** — file in `.raw/` che nessuna nota cita.

## Lo snapshot

`state.json` è committato di proposito: è ciò che rende possibile il confronto settimana
su settimana, e git ne tiene la storia gratis. `--no-state` serve per provare senza
bruciare il confronto successivo.

La base della misura è **dichiarata in ogni riga** (`last_update` o `updated`,
`ultima interazione` o `updated`) — senza, due strumenti danno numeri diversi sulla
stessa deal e nessuno dei due è credibile.

## Cosa non fa

Non scrive nel vault a parte il proprio report, non manda niente, non decide niente.
Il giudizio e le bozze li mette la skill `battito`, che legge questo report; l'invio
resta sempre umano.
