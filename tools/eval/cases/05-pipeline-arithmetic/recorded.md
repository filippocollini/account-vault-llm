# Pipeline Summary — as of 2026‑09‑10

**Nota sulla data:** ho usato il **2026‑09‑10** come data di riferimento (indicata esplicitamente per questa esecuzione), non il 2026‑09‑30 di sistema — la differenza è rilevante: con la data di sistema, 3 deal Commit/Best‑Case risulterebbero già scadute senza chiusura registrata. Segnalo comunque sotto dove l'assunzione cambia il quadro.

Fonte: 9 deal note in `wiki/pipeline/`, tutte di **Alex** (owner unico), tutte New Business.

## 1 — Forecast vs quota (Q3 2026, quota €850k)

| Bucket | € (valore pieno) | vs quota | Stato |
|---|---|---|---|
| Closed (won, Q3) | €300.000 (Ferro Group) | 35% | — |
| + Commit valido | €1.190.000 (Northwind €780k + Verta €410k) | **175%** cumulato | 🟢 GREEN |
| + Best Case valido | +€160.000 (Kestrel) | **194%** cumulato | 🟢 |

**"Valido" = rispetta i criteri di config** (Commit: L5+, MEDDPICC≥7, close in trimestre; Best Case: L4+, MEDDPICC≥6, close in trimestre). Ho dovuto **scartare 3 deal etichettate Commit/Best Case che non passano i criteri**:

- **P-007 Marrow Water (€120k, "Commit")** — MEDDPICC fermo a 5 (serve ≥7), Paper Process e Decision Process mancanti. È l'owner stesso a segnalarlo in nota. Non qualifica né come Commit né come Best Case (serve ≥6).
- **P-005 Orbit Logistics (€90k, "Best Case")** — MEDDPICC 5 (serve ≥6) **e** data di chiusura già scaduta (15/08) senza nuova data confermata.
- **P-008 Brenner Mobility (€45k, "Best Case")** — `expected_close` **mancante**: senza data non si può verificare "close in trimestre".

Se si contassero le etichette *as-stated* invece dei criteri, Commit salirebbe a €1.310k e Best Case a €295k — un quadro falsamente più pulito. I numeri sopra sono quelli rigorosi.

## 2 — Coverage & slip

- **Coverage Q3** = weighted pipeline chiudibile nel trimestre (Northwind €624k + Verta €328k + Kestrel €96k + Marrow €96k = €1.144k) ÷ quota residua (€850k − €300k closed = €550k) = **2,08×**. Sano, ma quasi tutto (86%) sta in due deal.
- **Slittate** (close date passata, ancora open): **1 deal** — P-005 Orbit Logistics, €90.000 (€54k weighted), doveva chiudere il 15/08, nessuna nuova data dal cliente.

## 3 — Deal a rischio (`risk_flag: AT RISK`)

**2 deal, €340.000 totali:**

| Deal | Valore | Motivo |
|---|---|---|
| Talvik Steel | €250.000 | Budget congelato in attesa capex 2027; contatto chiave in maternità fino a novembre |
| Orbit Logistics | €90.000 | Slittata da agosto, partner non ha fissato la call tecnica |

## 4 — Breakdown (pipeline open, €1.878.000 totali / €1.349.600 weighted)

**Per verticale:** Shipbuilding €780k · OEM €410k · Manufacturing €250k · Life Sciences €160k · Energy & Utilities €143k (Halden+Marrow) · Logistics €90k · Transport €45k

**Per paese:** IT €1.310k (70%) · SE €250k · DE €160k · ES €90k · AT €45k · NO €23k

**Per canale:** Direct €1.720k (91%) · Channel €158k (9%)

## 5 — Narrativa

**Sì, il numero si fa — ma è concentrato in due deal.** Northwind Marine (€780k) e Verta Robotics (€410k) da sole coprono il 175% della quota Q3 e rappresentano il 63% di tutta la pipeline aperta; se chiudono entro il 25 e 30 settembre come da MEDDPICC pulito (7 e 8), il trimestre è ampiamente coperto. **La leva/rischio principale è lì**: nessun'altra rete di sicurezza — tolte queste due, resta solo Kestrel (€160k) valida contro una quota residua di €550k, ben sotto copertura. In più, Marrow Water (€120k) è etichettata Commit ma non lo è (MEDDPICC 5, lo ammette la nota stessa) — va trattata come rischio, non come cuscinetto.
