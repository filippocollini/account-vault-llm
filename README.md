# account-vault-llm

**An LLM-maintained second brain for key-account work — and a way to tell whether it is lying.**

This repository is a public, fully synthetic version of a system I use at work: a git-versioned
[Obsidian](https://obsidian.md) vault that [Claude Code](https://claude.com/claude-code) reads and
writes, a set of skills that turn it into sales briefings, and — the part this repo is really
about — the tooling that checks the vault and measures the skills.

> Every account, person, amount, vendor, product and competitor in this repository is invented.
> The original vault holds real customer data and stays private. See [Data](#data).

---

## The problem

A key account manager's knowledge is scattered across email, chat, CRM fields, call notes and
memory. An LLM agent can keep it organised: read a meeting note, update the account page, the
deal, the log. It can then answer "where are we with this account?" in seconds.

Two things make that dangerous.

1. **The output is always plausible.** A deal review that invents an Economic Buyer, or a
   pipeline readout whose total is off by 12%, looks exactly like a correct one. There is no red
   error. There is a tidy, complete, wrong table.
2. **A system that writes can quietly break things.** The note you asked for is recorded
   correctly, and meanwhile a line on another account's page changes. Nobody rereads that page
   until the pipeline is already stale.

The usual test — "I tried it on a couple of accounts, it looks good" — covers the easy cases,
cannot be repeated when a skill changes, and depends on the impression of someone who already
knows the answer. This repo replaces the impression with measurement.

---

## Architecture

```
            .raw/  (immutable sources: call notes, meeting notes, exports)
              │  ingest — the agent reads, the human curates
              ▼
   wiki/  ── stakeholders/ ── pipeline/ ── decisions/ ── deliverables/ ── intel/ ── comms/
     │        index.md (catalog) · log.md (append-only) · hot.md (recent context)
     │
     ├──►  skills (.claude/skills)        read the vault, answer in chat; one of them writes
     │       snapshot · deal-review · pipeline-summary · battlecard · account-note · battito
     │
     ├──►  tools/lint/vault.py            is the vault INTACT?  deterministic, gates commits
     ├──►  tools/heartbeat/heartbeat.py   what MOVED, what is stuck?  weekly, never blocks
     └──►  tools/eval/                    do the SKILLS do their job?  record / replay
```

### The vault

Plain Markdown with flat YAML frontmatter, one folder per note type. Deal notes carry
machine-readable state (`stage`, `stage_pct`, `amount_eur`, `forecast_cat`, `expected_close`,
eight `meddpicc_*` fields); account pages carry the rollup and a dated `## Interazioni` log.
Three root files keep an agent oriented without rereading everything: `index.md` (catalog),
`hot.md` (≈500 words of recent context, overwritten), `log.md` (append-only, newest first).

The demo vault has ten accounts, a partner and eleven deals, and is **seeded with known
defects** — a slipped close date, an inconsistent weighted value, a missing close date, a
rollup that does not reconcile, forecast categories the rules don't support, a source never
ingested — so the tools have something real to find. They are listed in
[`wiki/meta/vault-usage-guide.md`](wiki/meta/vault-usage-guide.md).

### The skills

| Skill | What it does | Writes? |
|---|---|---|
| `snapshot` | account recap before a call; `CEO` scope adds an executive block | no |
| `deal-review` | MEDDPICC table, ranked gaps, one owned action per gap | no |
| `pipeline-summary` | forecast vs quota, in-quarter coverage, slips, risk, breakdown | no |
| `battlecard` | when we lose / win, proof points, trap question, positioning | no |
| `account-note` | distils a raw call note into the account page, deal note, log and hot cache | **yes** |
| `battito` | weekly brief: picks five items from the heartbeat and proposes one action each | only 3 fields, on request |

Shared guardrails: nothing is ever sent externally, empty fields are reported as gaps rather
than filled, and nothing in development is presented as available.

### Lint — is the vault intact?

[`tools/lint/vault.py`](tools/lint/vault.py) (stdlib only, no network) checks what can be
checked mechanically: frontmatter against a schema that lives in the code and is published from
it, dead and ambiguous wikilinks, orphans, index drift, templates against the schema,
provenance (`sources:` must point to a file that exists in `.raw/`), pipeline hygiene, forecast
categories against the stage/MEDDPICC/quarter rules, and **reconciliation** between the sum of
open deals and each account's rollup.

It is wired in three places through one wrapper (`tools/lint/run.sh`): a git pre-commit hook, a
Claude Code `Stop` hook, and the `/lint` slash command. The hook is a **ratchet, not a wall**: it
blocks a commit only if the ERROR count rises above `tools/lint/error-baseline.txt`. Existing
debt does not stop you working; adding new debt does. Lowering the baseline is progress, in git.

### Heartbeat — what moved?

The lint measures state; [`tools/heartbeat/heartbeat.py`](tools/heartbeat/heartbeat.py)
measures movement. It exists because of a diagnosis on the real vault: nothing was broken, but
everything that required someone to *remember to look* had decayed. It sorts the vault into six
buckets — due this week, overdue (by value), silent, moved since last run (diffed against a
committed snapshot), stuck decisions/deliverables, un-ingested sources — and reuses the lint's
parser so the two views cannot drift. The `battito` skill reads its report and turns it into
five decisions.

---

## Evaluation method

The design rule, shared by the lint and the eval suite:

> **What can be checked mechanically is never handed to a model.**

Every assertion falls into one class, in increasing cost and decreasing reliability:

| Class | Verifies | How | Cost |
|---|---|---|---|
| **Structure** | the promised format is all there | parsing | zero |
| **Grounding** | cited facts are in the source, invented ones are not | text comparison | zero |
| **Oracle** | the numbers are the ones the data produces | independent recomputation | zero |
| **State** | the vault after a write is the right one | file hashes, frontmatter diff | zero |
| **Judgment** | the reasoning is right | a second model votes | high, partial |

Most of what matters lives in the first four. "Missing actions", "cited an amount that does not
exist", "filled a cell the source leaves empty", "touched a page it had no reason to touch" sound
like judgment calls; they are parsing.

**Eleven cases, each built around a way of failing, not a feature.** Among them: a €780k deal
whose signer nobody has met (does the model promote the technical contact to champion?), an
almost empty account (does it invent?), a **negative control** where the right answer is
"this deal is fine" (does it manufacture problems?), two accounts with similar names (does it
silently pick one?), a pipeline with four inconsistent deals (does it launder them into a clean
total?), a blocker buried in prose (does the snapshot omit it?), and a write case whose raw note
mentions a second account in passing — that page must not change by a single byte.

**Oracle.** For `pipeline-summary` the expected numbers are not written by hand.
[`oracle.py`](tools/eval/oracle.py) is a second, independent implementation of the same
arithmetic that recomputes totals, weighted value, Commit/Best Case, in-quarter coverage, slips
and data inconsistencies from the fixture. If the fixture changes, the expectation follows.

**State.** `account-note` is judged on the diff it leaves, not on its prose:
[`statecheck.py`](tools/eval/statecheck.py) checks what must change and — the neglected half —
that every other file is byte-identical to the fixture.

**Judgment**, in [`judge.py`](tools/eval/judge.py), sees the rubric and the output but never
the expected answer, votes three times, reports agreement, and **never fails the build**.

**Record / replay.** `--record` runs the real skill through the `claude` CLI on an isolated copy
of the fixture and saves the output (and, for the write case, the resulting vault). The default
replay mode re-checks the saved outputs offline, in about a second, deterministically — so it
can run in CI and spending tokens becomes an explicit decision. A case with no recording fails
the run: CI must not go green by checking nothing.

**Who checks the checks.** [`selftest.py`](tools/eval/selftest.py) takes hand-written correct
outputs, breaks them twenty different ways — one per failure the suite claims to catch — and
verifies that each mutation trips the right assertion, while the correct output trips none. It
calls no model. During development it caught real bugs in the assertions, each of which would
have produced a green suite on a broken system:

1. the "no gaps" filter discarded any bullet starting with *nessun*, so *"Nessun champion: …"* —
   a serious gap — was read as the absence of gaps;
2. the log-order check looked for a keyword near the top of `log.md`, which an older entry
   already contained, so a new entry appended at the bottom passed;
3. a deal id counted as "listed" if it appeared anywhere, so a deal removed from the at-risk list
   but still mentioned in a data-quality note passed — now the id must appear with its amount;
4. number matching was substring-based, so a coverage of 1.9 was "found" inside 1.331.900.

### Results

Recorded on 2026-09-30 with `claude-sonnet-5`, one sample per case, deterministic classes only
(the judgment class was not run). **Selftest: green** — 20/20 mutations caught, oracle agrees
with hand-computed values, reference vault passes 24/24. **Skills: 8 of 11 cases pass.** The
three failures are kept as recorded, because they are the point:

| Case | Result | What happened |
|---|---|---|
| 01–04 `deal-review` | pass | no filled gaps, no invention, no manufactured problems on the healthy deal, asks when the name is ambiguous |
| 05 `pipeline-summary` | **15/20** | Weighted pipeline off by €20,000: the stored, inconsistent `weighted_eur` of one deal was used instead of recomputed — and that deal was not flagged as inconsistent. Same defect as the first measurement on the original vault. Two further misses (Best Case total, in-quarter coverage) are partly a **spec/check ambiguity**: the skill asks for cumulative figures while the oracle checks per-category totals, and the model excluded a slipped deal from coverage that the oracle counts. Open item: make the rule explicit in both places. |
| 06 `pipeline-summary`, "at risk" slice | **4/5** | Scope leak: the model ignored the date given in the prompt, used the system date, found more "risky" deals and listed the Commit deals the slice should exclude. |
| 07–08 `snapshot` | pass | the buried blocker surfaces; the CEO scope adds the executive block |
| 09–10 `battlecard` | pass | honest "when we lose", in-development product always qualified, unknown competitor flagged as best-effort |
| 11 `account-note` | **25/26** | Over-inference: wrote "investment committee" into `economic_buyer` although the call names no signer. Everything else held — including the account mentioned in passing, untouched byte for byte. |

Re-recording also surfaced a harness bug: `--record` did not pass a case's reference date to the
model, so the oracle (computing at the case date) and the model (reading the system clock)
could measure two different worlds. It went unnoticed in the original because the first
recording happened on the case date. It is fixed; case 06 shows the model can still ignore it.

```bash
python3 tools/eval/selftest.py        # do the assertions still tell right from wrong?
python3 tools/eval/run.py             # replay: re-check the recorded outputs (offline)
python3 tools/eval/run.py --record    # re-run the skills through the claude CLI (costs tokens)
python3 tools/eval/run.py --judge     # add the judgment class (costs tokens)
sh tools/lint/run.sh                  # lint the demo vault → wiki/meta/lint-report.md
python3 tools/heartbeat/heartbeat.py  # heartbeat → wiki/meta/heartbeat.md
```

Python 3.9+ and the standard library only. Recording needs an authenticated
[Claude Code](https://claude.com/claude-code) CLI. Install the gate with
`cp tools/githooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit`.
The demo vault pins its date in `.vault-today` (2026-09-10) so every run is reproducible;
delete that file to use the vault against the real calendar.

---

## Known limitations

- **Eleven cases are not coverage.** They are eleven failure modes chosen because I observed or
  expected them. There are others.
- **It does not measure writing quality.** A correct, unpleasant output passes.
- **Judgment stays an opinion.** It is reported separately and never changes the exit code.
- **The oracle can be wrong too.** It is independent, not infallible; `selftest_numbers.py`
  compares it with sums done by hand, which is all one can do.
- **Recordings are single samples.** The skills are non-deterministic; one recording per case
  says what happened once, not how often. Repeated sampling is not implemented.
- **Synthetic fixtures are cleaner than real data.** That is the price of publishing them.
- **`battito` is not evaluated yet**, and the lint's staleness check still relies partly on the
  self-declared `updated` field.
- **Language.** The vault content, skill output formats and code comments are in Italian, the
  working language of the original project. This README is the English entry point.

---

## How I built this with Claude Code

I want to be precise about who did what, because "built with AI" can mean anything.

**Mine: the problem, the design, and the decisions.** I use this vault every day on real
accounts, and most design choices here came out of something going wrong in that use: the
rule that anything mechanical goes to a script and not a model; the four-class split of
assertions; building each eval case around a failure mode instead of a feature; the negative
control; the oracle instead of hand-written expectations; asserting what must *not* change after
a write; the ratchet instead of a hard gate; the heartbeat after noticing that everything that
depended on my memory had decayed; and the guardrails — nothing sent externally, empty fields
reported as gaps, commercial judgment (stage, amount, forecast) never touched by the agent. I
decided what to measure and what counts as passing, and I reviewed every change.

**Paired with the agent: the code.** Most of the Python and the skill definitions were written
in pair with Claude Code: I described the behaviour and the failure I was worried about, the
agent proposed an implementation, I read it, pushed back, and we iterated. The commit history of
the original project carries a `Co-Authored-By` line on this work for that reason. Several of
the agent's first versions were wrong in instructive ways — the assertion bugs listed above were
caught by the mutation selftest rather than by either of us reading the code, which is the
strongest argument I have for writing the selftest in the first place.

**This public version** was also produced with Claude Code: it extracted the tooling from the
private repository, replaced every real name, number and product reference with synthetic ones,
wrote the demo vault from the eval fixtures, and re-recorded all eleven cases against the
de-branded skills, so the recordings in this repo were produced by exactly the code in this repo.

---

## Data

This is a derived, synthetic version of a private work repository. What was removed: all
customer, partner and colleague names, amounts and commercial details; the employer's brand,
templates and product names; internal roadmap information; the original commit history. Vendor
("Quillgate"), products and competitors are invented; any resemblance to real companies is
unintended. Third-party Obsidian skills used in the original are not redistributed here.
