# Eval — misurare se le skill del vault fanno davvero il loro lavoro

Questa cartella risponde a una domanda che di solito resta senza risposta:
**come si fa a sapere se una skill basata su un modello linguistico funziona?**

Non è retorica. Le skill di questo vault producono una qualificazione di
trattativa, un riepilogo di pipeline, una scheda competitiva, un recap prima di
una call — e una di loro scrive dentro il vault. Il testo che producono è sempre
plausibile. È scritto bene anche quando è sbagliato. Non c'è un errore rosso che
avvisa quando il modello ha inventato un Economic Buyer o sbagliato un totale del
12%: c'è una tabella ordinata, completa, e falsa.

Il collaudo abituale — "l'ho provata su un paio di account, mi sembra buona" —
non regge. Copre i casi facili invece dei modi in cui il sistema fallisce
davvero, non si può ripetere quando la skill cambia, e dipende dall'impressione
di chi guarda, che sa già cosa dovrebbe uscire.

Questa suite sostituisce l'impressione con una misura.

**Copertura attuale: 5 skill, 11 casi.**

---

## Il principio: quattro classi di controllo

È la decisione di progetto più importante, ed è la stessa che regge
`tools/lint/vault.py`:

> **Quello che si può verificare meccanicamente non si fa verificare a un modello.**

Ogni asserzione ricade in una classe, in ordine crescente di costo e
decrescente di affidabilità:

| Classe | Cosa verifica | Come | Costo | Affidabilità |
|---|---|---|---|---|
| **Struttura** | il formato promesso c'è tutto | parsing | zero | totale |
| **Grounding** | i fatti citati stanno nella fonte, e quelli inventati no | confronto testuale | zero | totale |
| **Oracolo** | i numeri sono quelli che escono dai dati | ricalcolo indipendente | zero | totale |
| **Stato** | il vault dopo l'esecuzione è quello giusto | confronto di file e hash | zero | totale |
| **Giudizio** | il ragionamento è quello giusto | un secondo modello valuta | alto | parziale |

Il punto pratico: **quasi tutto ciò che conta sta nelle prime quattro.**
"Mancano le azioni", "ha scritto un importo che non esiste", "ha riempito una
casella che la fonte lascia vuota", "ha toccato una pagina che non c'entrava" —
sembrano giudizi, e sono parsing.

La quinta è ridotta al minimo, perché un modello che valuta è a sua volta non
deterministico. Le resta solo ciò che dipende dal merito del caso: *"il gap
messo al primo posto è quello giusto?"*. Per questo il giudizio, in `judge.py`,
vota tre volte e riporta il grado di accordo — se un'asserzione fa
sistematicamente 2 a 1, il problema è la domanda, non il sistema — e **non fa
mai fallire la suite**: si riporta, non blocca.

### L'oracolo

Per `pipeline-summary` c'è una verifica più forte del confronto con valori
attesi: **una seconda implementazione, indipendente, della stessa aritmetica.**
`oracle.py` legge il frontmatter dei deal del fixture e ricalcola totali,
pesato, copertura, Commit e Best Case, slittamenti e incoerenze.

Perché non scrivere i numeri attesi a mano in `case.json`:

1. Se il fixture cambia, l'atteso si aggiorna da solo. Un numero copiato
   invecchia in silenzio e la suite comincia a misurare il passato.
2. Costringe a esprimere le regole (*Commit = L5+ & MEDDPICC ≥7 & chiusura in
   trimestre*) come codice eseguibile invece che come prosa in un prompt. Se le
   due implementazioni divergono, una ha torto ed è bene scoprirlo.
3. Rende falsificabile "il modello ha sbagliato la somma": si sa di quanto.

L'oracolo non è la verità assoluta. È una seconda opinione scritta in un
linguaggio che non allucina.

### Lo stato

`account-note` è l'unica skill che scrive, e valutarne la prosa non serve a
niente: il suo prodotto è la differenza tra il vault prima e dopo.
`statecheck.py` verifica due cose, e la seconda è quella trascurata:

- **cosa deve cambiare** — un campo aggiornato, una sezione creata, la voce di
  log in cima;
- **cosa non deve cambiare** — ogni altro file del vault, byte per byte.

Una skill che scrive sbaglia in due modi. Non fa quello che deve, e ci si
accorge subito. Oppure fa *anche qualcos'altro*: la nota richiesta viene scritta
correttamente e nel frattempo una riga di un'altra pagina cambia. Il secondo
caso è silenzioso.

---

## Gli undici casi

Ogni caso è un vault sintetico in miniatura — account inventati, nessun dato
reale — costruito attorno a **un modo specifico di sbagliare**. Non attorno a
una funzionalità: attorno a un fallimento.

### `deal-review`

| Caso | Situazione | Il fallimento che misura |
|---|---|---|
| 01 | deal €780k, chi firma mai incontrato | **riempire un buco** — promuovere il referente tecnico a champion perché una tabella piena sembra un lavoro migliore |
| 02 | una sola call, sei dimensioni vuote | **inventare** — plausibilità al posto di fatti quando la fonte tace |
| 03 | trattativa sana, otto su otto | **fabbricare problemi** — il controllo negativo |
| 04 | due account con nome simile | **risolvere in silenzio l'entità sbagliata** |

### `pipeline-summary`

| Caso | Situazione | Il fallimento che misura |
|---|---|---|
| 05 | 9 deal, di cui 4 con dati incoerenti | **sbagliare un numero in modo invisibile**, e **lavare i dati sporchi** in un totale pulito |
| 06 | richiesta ristretta ai soli deal a rischio | **fuga di scope** — rispondere con tutto quello che si sa |

### `snapshot`

| Caso | Situazione | Il fallimento che misura |
|---|---|---|
| 07 | bloccante vero sepolto nella prosa | **l'omissione** — chi legge assume che sia completo, e ciò che manca non viene cercato altrove |
| 08 | stesso account, scope CEO | **cambiare etichetta senza cambiare altitudine** |

### `battlecard`

| Caso | Situazione | Il fallimento che misura |
|---|---|---|
| 09 | concorrente coperto dall'intel | **onestà difensiva** — «perdiamo solo se il cliente sbaglia» — e **promettere funzioni non disponibili** |
| 10 | concorrente fuori elenco | **sicurezza non dovuta** — una scheda di congetture identica in forma a una fondata |

### `account-note`

| Caso | Situazione | Il fallimento che misura |
|---|---|---|
| 11 | call che non giustifica avanzamenti e nomina di sfuggita un altro account | **danno collaterale**, **dedurre troppo**, **convenzioni saltate** |

Tre casi meritano una nota.

**Il 03 è il controllo negativo**: la risposta giusta è "va tutto bene". Quasi
nessuna suite ne contiene uno, ed è il motivo per cui molti sistemi sembrano
funzionare finché non li si guarda — si verifica sempre che trovino qualcosa,
mai che si fermino quando non c'è niente da trovare. Un sistema che segnala
sempre un problema non è cauto, è rumore.

**Il 04 misura il fallimento più pericoloso**, perché è l'unico completamente
invisibile: tabella piena, numeri coerenti fra loro, azienda sbagliata. Nessun
controllo di formato lo intercetta.

**L'11 è l'unico in cui l'oggetto della misura non è il testo.** Il caso è
costruito perché il testo grezzo nomini di sfuggita un secondo account: quella
pagina non deve muoversi di un byte.

---

## Registra e ricontrolla

Due modalità, e la separazione è deliberata:

- **replay** (predefinita) — ricontrolla gli output già salvati in
  `cases/*/recorded.md` (e, per i casi che scrivono, `cases/*/recorded-vault/`).
  Gratis, offline, sempre uguale, si mette in CI.
- **record** (`--record`) — chiama davvero il modello e riscrive gli output.
  Costa, e si fa quando cambia la skill.

Senza la separazione ogni verifica richiederebbe una chiamata al modello: la
suite sarebbe lenta, costosa e instabile, e nessuno la eseguirebbe. Così quasi
tutti i controlli girano in un secondo e la spesa diventa una decisione
esplicita invece di un effetto collaterale.

I fixture sono dati, i casi sono domande su quei dati: con `vault_from` un caso
riusa il vault di un altro invece di duplicarlo (il 06 riusa il 05, il 08 il 07,
il 10 il 09). Duplicare un fixture significa doverlo aggiornare in due punti,
e la seconda copia diverge.

---

## Chi controlla i controlli

`selftest.py` è la parte a cui tengo di più.

Una suite di eval ha un modo silenzioso di essere inutile: **passare sempre.**
Se le asserzioni sono scritte larghe, il report è verde qualunque cosa esca — e
dà fiducia, il che è peggio di non avere niente.

Il selftest lo esclude. Prende un output corretto scritto a mano, lo rompe in
venti modi diversi — uno per ciascun fallimento che la suite dovrebbe vedere — e
verifica che ogni rottura accenda il controllo giusto. Se una mutazione passa
inosservata, l'asserzione corrispondente non serve a niente e va riscritta.

Non chiama nessun modello, gira in un secondo, e **ha già trovato tre difetti
reali nei controlli**:

1. **Il filtro dei gap era troppo largo.** Scartava qualunque riga iniziasse per
   «nessun», quindi trattava *«Nessun champion: Sollner non porta il caso»* — un
   gap grave — come la dichiarazione che non ci sono gap. Il caso del deal sano
   sarebbe stato verde per il motivo sbagliato.
2. **Il controllo sull'ordine del log misurava la cosa sbagliata.** Cercava una
   parola chiave nei primi 900 caratteri di `log.md`, ma l'account era già
   nominato in una voce vecchia in testa: la voce nuova poteva finire in fondo
   senza che niente se ne accorgesse. Ora legge le date e verifica che la prima
   voce sia la più recente.
3. **`must_list_ids` accettava una menzione qualsiasi.** Un deal rimosso
   dall'elenco di quelli a rischio restava citato in una nota sui dati
   incoerenti, e il controllo passava. Ora l'identificativo deve comparire
   *insieme al proprio importo*, che è il modo in cui un deal viene davvero
   elencato.

Ognuno dei tre avrebbe prodotto una suite verde su un sistema rotto. Le
correzioni, e la riga che le ha causate, sono nei commenti del codice.

---

## Come si usa

```bash
python3 tools/eval/selftest.py         # le asserzioni sono ancora valide? (3 suite)
python3 tools/eval/run.py              # replay: ricontrolla gli output salvati
python3 tools/eval/run.py --record     # rigenera gli output (chiama il modello)
python3 tools/eval/run.py --judge      # aggiunge la classe giudizio
python3 tools/eval/run.py --case 05    # un caso solo
python3 tools/eval/oracle.py cases/05-pipeline-arithmetic/vault 2026-09-10
```

Exit code 1 se fallisce un'asserzione deterministica **o se un caso non ha
output registrato**: una CI non deve diventare verde per non aver controllato
niente. Il report finisce in `runs/latest.md`.

```
tools/eval/
├── run.py                orchestrazione, record/replay, report
├── checks.py             struttura, grounding, oracolo — deterministici
├── statecheck.py         stato del vault per la skill che scrive
├── oracle.py             ricalcolo indipendente dell'aritmetica pipeline
├── judge.py              giudizio — isolato di proposito
├── selftest.py           punto di ingresso: esegue le tre suite di autoverifica
├── selftest_numbers.py   verifica oracolo, sezioni, qualifica
├── selftest_state.py     verifica i controlli di stato
└── cases/
    ├── _shared/                metodologia MEDDPICC condivisa
    └── NN-nome/
        ├── case.json           prompt + asserzioni + fallimento sotto test
        ├── vault/              vault sintetico (o `vault_from` per riusarne uno)
        ├── recorded.md         ultimo output registrato
        └── recorded-vault/     stato del vault dopo l'esecuzione (casi che scrivono)
```

Aggiungere un caso vuol dire creare una cartella con `case.json` e un vault.
Nessun codice da toccare.

---

## Cosa non fa

Detto esplicitamente, perché una suite che si presenta come completa è peggio
di nessuna suite:

- **Non misura la qualità della scrittura.** Misura correttezza, ancoraggio alla
  fonte, completezza strutturale ed effetti sul vault. Un output corretto e
  sgradevole passa.
- **Undici casi non sono una copertura.** Sono undici modi di fallire scelti
  perché osservati o attesi. Ce ne sono altri.
- **Il giudizio resta un'opinione.** Per questo è separato nel report e non alza
  mai l'exit code.
- **L'oracolo può sbagliare come il modello.** È indipendente, non infallibile:
  `selftest_numbers.py` lo confronta con conti fatti a mano, ed è tutto quello
  che si può fare.
- **I fixture sono sintetici.** Nessun dato di cliente reale, per poter
  pubblicare la cartella. Il rovescio è che sono più puliti del vault vero.

---

## Stato

- **Selftest: verde.** 20 rotture su 20 intercettate; oracolo concorde su 11/11
  valori calcolati a mano e 4/4 deal incoerenti; vault di riferimento 24/24.
- **Registrazione del 2026-09-30** (`claude-sonnet-5`, un campione per caso, senza
  giudizio): **8 casi su 11 verdi.** I tre rossi sono risultati veri e restano
  registrati così come sono:
  - **05** — il pesato usa il `weighted_eur` incoerente di P-006 invece di
    ricalcolarlo, e P-006 non viene segnalato. Best Case e copertura mancano in
    parte per un'ambiguità fra spec e controllo (la skill chiede i cumulati,
    l'oracolo i totali per categoria; il modello esclude dalla copertura la deal
    slittata, l'oracolo la conta): da rendere esplicita in entrambi i posti.
  - **06** — fuga di scope: il modello ignora la data del caso, usa quella di
    sistema ed elenca anche i deal Commit.
  - **11** — deduce troppo: scrive il «comitato investimenti» come Economic Buyer.
    La pagina dell'altro account nominato di sfuggita resta intatta.
- La ri-registrazione ha trovato un difetto dell'harness: `--record` non passava
  al modello la data del caso, quindi oracolo e modello potevano misurare due
  giorni diversi. Corretto in `run.py`.
