---
name: battito
description: Il brief settimanale del vault ("battito" = heartbeat) — cosa è cambiato, cosa scade adesso, cosa è rimasto in silenzio, con una proposta di azione concreta per ciascuna voce. È il trigger che toglie all'owner il "ricordarsi di guardare". Fire on "BATTITO", "battito del vault", "cosa mi sono perso", "com'è messo il vault", "brief del lunedì", "weekly brief". Legge il vault e lancia tools/heartbeat/heartbeat.py; scrive nel vault solo su istruzione esplicita e solo tre campi.
---

# BATTITO

Il brief settimanale. Nasce da una diagnosi ricorrente nei vault mantenuti a mano: niente
è rotto, ma tutto ciò che richiede di ricordarsi di guardare — deal ferme da settimane,
chiusure attese già passate, un correction log che nessuno aggiorna — decade in silenzio.

Questa skill non aggiunge un altro report da leggere. Trasforma un elenco meccanico in
**cinque cose da decidere**, ognuna con una proposta già scritta da approvare o buttare.

## Come si esegue

1. **Lancia il battito meccanico** e leggi il suo output:

   ```bash
   python3 tools/heartbeat/heartbeat.py
   ```

   Scrive `wiki/meta/heartbeat.md` e aggiorna lo snapshot in `tools/heartbeat/state.json`.
   Se l'utente sta solo provando, usa `--no-state`: senza snapshot aggiornato il confronto
   della settimana prossima resta valido.

2. **Leggi `wiki/meta/heartbeat.md`** — è la fonte dei fatti. Non ricontarli a mano e non
   ricalcolare gli importi: sono già giusti, e rifarli a occhio è esattamente il modo in
   cui un output plausibile diventa falso.

3. **Per ogni voce che porti nel brief, apri la pagina account o la deal note** e leggi
   cosa dice davvero prima di proporre un'azione. Una proposta che non poggia su una riga
   scritta nel vault non si scrive.

## Cosa produci

**Massimo cinque voci.** Non sei un report: sei la persona che ha già letto il report.
Se il battito ne elenca ventinove, il tuo lavoro è scegliere le cinque che contano — per
valore a rischio, per quanto sono ferme, e per quanto è vicina la scadenza.

Per ciascuna, tre righe e non di più:

- **Il fatto**, con il numero: `€90.000 · P-005 Orbit Logistics — close atteso passato da 26 giorni`
- **Cosa dice il vault** — una riga da una fonte reale, con il link alla pagina. Se la
  pagina non dice niente di utile, scrivi *"la pagina non dice perché"*: è un'informazione,
  non un buco da riempire.
- **La proposta** — una azione concreta e una data. Se serve una mail o un messaggio,
  scrivine la bozza (corta), ma **non inviare niente**.

Chiudi con due righe secche:

- **Movimento**: cosa è cambiato dall'ultimo battito. Se non è cambiato niente, dillo —
  una settimana senza un solo movimento su una pipeline aperta è di per sé il dato.
- **Cosa non ho guardato**: i secchi che hai lasciato fuori e quante voci contengono.

## Applicare le proposte

Su istruzione esplicita dell'utente (*"applica 1, 3 e 4"*), puoi scrivere nel vault —
e **solo** così:

- solo i campi `next_action`, `next_action_date`, `risk_flag`;
- solo sulle deal che compaiono nel brief che hai appena prodotto;
- una riga in `wiki/log.md` (in cima) con cosa hai toccato e perché;
- `updated` e `last_update` al giorno corrente sulle deal modificate.

Tutto il resto resta com'è. Non cambiare `stage`, `amount_eur`, `forecast_cat` o
`expected_close`: quelli sono giudizio commerciale dell'owner e cambiarli per far
sparire un alert è esattamente il modo di rendere il vault inutile.

## Guardrail

- **Non mandi niente.** Mai. Le bozze restano bozze finché non le manda l'owner.
- **Non inventi una prossima azione** per far sparire un warning. Se non c'è materiale per
  proporla, la voce corretta è *"serve una tua decisione: non c'è niente nel vault su cui
  basare il prossimo passo"*.
- **Non tocchi lo stage né il forecast.** Se pensi che una deal vada chiusa persa, lo
  proponi a parole.
- Se `heartbeat.py` fallisce, dillo e fermati. Non ricostruire i numeri leggendo le note a
  mano: il punto della suite meccanica è che non allucina, e aggirarla perde la garanzia.

## Confini con gli altri strumenti

| Strumento | Domanda a cui risponde |
|---|---|
| `tools/lint/vault.py` → [[lint-report]] | Il vault è **integro**? (frontmatter, link, totali) — blocca i commit |
| `tools/heartbeat/heartbeat.py` → [[heartbeat]] | Cosa si è **mosso** e cosa è rimasto fermo? |
| `battito` (questa skill) | Quindi **cosa faccio lunedì mattina**? |
| `pipeline-summary` | Come sta il **forecast** rispetto alla quota? |

`pipeline-summary` guarda in avanti (forecast vs quota, coverage). Il battito guarda
indietro di una settimana e verso il basso, nei dettagli che decadono. Non si sovrappongono.
