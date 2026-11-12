# Plan: answering the 2026-11-11 critique

Input: [`CRITIQUE.md`](CRITIQUE.md), a review of the README hero demo (`docs/demo.svg`).
Target release: **0.4.0** (Phase 3 changes the payload contract).

**Revision 2.** Revision 1 (`ba9ec9f`) found the right problems but answered them
with six phases, two breaking changes and a larger SKILL.md, and its central gate
still relied on the model's honesty. It also missed the most damaging finding: the
engine's own stability check rated the mis-scored demo `robust`. This revision:

- adds findings 8–10;
- measures a baseline before building anything;
- makes `Undetermined` computed instead of declared;
- cuts the ordinal rename, `evidence_ref` and the ADR renderer (each is listed
  under Deferred with the measurement that would bring it back);
- replaces exit criteria that couldn't be run or meant nothing statistically.

## Goal beyond the goal

The critique is about one screenshot, but the real goal is bigger: **tiltrank
must be unable to produce that screenshot.** That means:

- no total shown to a person;
- no recommendation when nothing the user stated separates the options;
- no `Separated` verdict when the lead rests on a single rating;
- a decision record a reviewer can read six months later.

Fixing the demo alone would just hide the problem.

## What was verified before planning

Everything below was reproduced against `main` @ `71ba7b7`. Nothing is inferred
from the critique.

1. **The demo numbers are real arithmetic on badly chosen inputs.** With weights
   0.5/0.3/0.2 and levels 20/60/90, each total has exactly one input:
   - Redis `(fit 90, rev 60, prec 90)` = 81
   - File-based `(20, 90, 60)` = 49
   - In-memory LRU `(20, 90, 20)` = 41

   Three levels on three criteria, plus null, give **44 reachable totals**. The
   inputs are coarse, but the displayed total looks precise.
2. **The demo violates the skill's own anchors.**
   - LRU `precedent: 20` means "novel", yet in-memory LRU is about as proven as
     caching gets.
   - Redis `evidence: 90` means "verified in this repo this session", but the
     demo shows no tool call that could have verified it.
   - `fit 90` means "satisfies every stated need", but the prompt states one need
     (self-hosted), and every survivor meets it.
3. **SKILL.md teaches the demo, in two places.**
   - Prose: the shape template at `SKILL.md:318-324` contains "if this stays a
     single box", "proven at this shape" and "the cache dies on every restart".
   - Numbers: the payload example at `SKILL.md:172-173` is the demo's vectors
     exactly. `Option A` is `90/60/90, evidence 90` (the demo's Redis) and
     `Option B` is `20/90/20` (the demo's LRU).

   Every run reads both. The engine has no domain logic. The skill's own examples
   push cache reasoning, and a confident lead shaped like the demo's, into every
   decision.
4. **The demo was hand-edited.** The real output prints `score 81`,
   `separation: robust`, `band: Separated`, `separated: yes — a recommendation is
   defensible`, then a `NOTE:` line. The demo merged these into one line the
   script never emits, and it shows `Bash(python3 scripts/rubric.py)` without the
   heredoc. The critic read exactly what the project published.
5. **With no context, the ranking comes from the default priors alone.** Revision
   1 called a rescore "honest": fit 60 for every option (nothing separates them),
   evidence 20, LRU `precedent 90`. It gives `Contested`, `ESCALATE —
   not-separable, unverified-evidence`, and the order LRU 75 > File-based 69 >
   Redis 66. That rescore is just as authored as the original. With fit tied, the
   order is decided only by the generic `reversibility` and `precedent` weights,
   so it still ranks file-based above Redis on priors. This supports the
   critique's §3: in this state the right output is not a ranking.
6. **"Never show the user a number" is broken by design on Claude Code.** SKILL.md
   calls the score an internal sort key, but the default table prints `score 81`
   to stdout, and Claude Code shows Bash output to the user. The `NOTE:` line
   saying "never the number" sits directly under the number.
7. **No calibration data exists.** The only `.decisions.log` is a gitignored file
   on one machine: 39 records, 30 `timed_out` (left over from headless runs from
   before the live eval used per-run logs, `check_trace.py:1007`), 9 real. It
   says nothing about recommendation quality and cannot be reproduced. Nothing
   in this plan is gated on it.
8. **The stability check certified the wrong answer.** It is not just that the
   demo was edited: the engine itself rates the demo payload `robust` /
   `Separated`. Resampling flips each rating by one band *independently*
   (p=0.25), so it cannot see a *systematic* error, such as one option
   mis-scored on one criterion, which is exactly what happened. A deterministic
   probe shows the real fragility. Give Redis the runner-up's `fit` (20) and
   Redis drops to 46, below File-based's 49. **The lead rests on one rating, and
   it is the one finding 2 shows is unsupported.**
9. **The recorded critique does not cover everything revision 1 answered.**
   Revision 1 had verdict rows for points `1d`, `S1`–`S4` and a quoted "let
   trade-offs be trade-offs". None of those appear in `CRITIQUE.md`. The full
   original is not in the repo, so those rows are removed and `CRITIQUE.md` notes
   the gap.
10. **SKILL.md is 543 lines and only grows.** Revision 1 added prose in every
    phase and removed none. The skill is the product, and longer skills are
    followed less reliably. That cost was not counted.

## Verdict on each critique point

| # | Point | Verdict | What we do |
|---|---|---|---|
| 1 | `rubric.py` called with zero arguments, so the numbers are hardcoded | **Valid as read.** The payload goes in on stdin, but the project's own hand-made demo hid it (finding 4) | Phase 0 removes the demo. Phase 4 puts the inputs in a readable record |
| 1 | False precision, `81` vs `80` | **Valid** (finding 1) | Phase 2: no totals in default output |
| 1 | `evidence 90` with no metrics | **Valid** (finding 2). It does not affect the ranking, because evidence is not weighted, but it lets an unverified lead skip escalation | Phase 3's requirement grounding removes the context-free lead. `evidence_ref` is deferred (see below) |
| 1 | Ungrounded heuristics dressed as deterministic telemetry | **Valid, and worse than stated** (finding 8): the stability band itself is part of the problem | Phase 2: single-rating probe |
| 2a | Redis over LRU on a single box is YAGNI | **Valid about the demo.** The engine has no cache logic to fix (findings 3, 5) | Phase 0 removes the priming. Phase 1 benchmark measures it |
| 2b | File-based above LRU is absurd | **Valid.** Caused by the LRU `precedent 20` mis-score, and it survives an honest rescore on priors alone (finding 5) | Phase 3: with no separating requirement, there is no ranking |
| 2c | A cache is ephemeral by design | **Valid.** The wording comes from SKILL.md's template | Phase 0 |
| 3 | No recommendation without the critical context | **Valid, and the most important point** | Phase 3: computed `Undetermined` band |
| 4 | Raw stdout duplicates the ask box | **Valid on Claude Code.** On Hermes/pi the tool output is less prominent, so the ask body must still carry exclusions | Phase 2: number-free default output |
| 5a | A hidden dotfile is where context dies | **Partly valid.** The JSONL is machine data and stays. It is the wrong artefact for people | Phase 4: agent-written ADR |
| 5b | Records the *that*, not the *why* | **Valid** | Phase 4: the record gains the question and requirements |

## Rules every phase follows

- SKILL.md, `rubric.py` and `check_trace.py` change together.
- Each new protocol rule gets a `check_trace.RULES` entry quoting the exact
  SKILL.md sentence, plus a good fixture and a deliberately broken one that must
  go red.
- CI (3.10/3.13, Linux and Windows) stays green. One PR per phase.
- **SKILL.md line budget:** `test_skill_contract.py` asserts SKILL.md is at most
  543 lines. A phase that adds prose removes at least as much.
- **Benchmark after every phase:** each phase from 2 on re-runs the Phase 1
  benchmark and reports the change against the baseline in its PR (see
  Measurement).

## Measurement

All live gates use the Claude driver at `--repeat 5` unless stated. Hermes and pi
run once per release, not per phase, to save tokens.

- **Rates are gated on the Wilson 95% lower bound, not on the point estimate.**
  At `--repeat 5` a single case can never clear a meaningful bar: 5/5 has a
  lower bound of 0.57. So gates pool runs across cases. Runs within a case are
  correlated, so the pooled bound is optimistic. Per-case results are always
  reported next to it.
- **"Never" means a reported upper bound.** Zero failures in n runs is reported as
  "0/n, 95% upper bound x", for example 0/20 → ≤ 0.16.
- **Escalation budget.** Each phase reports the escalation rate on *specified*
  benchmark cases. A phase that raises it by more than 20 points over baseline,
  without raising agreement with the key, is reworked before merge. Escalating
  everything stops carrying information.
- **Dev set and held-out set stay apart.** `scenarios.json` (including the
  critic's exact prompt) is the dev set that SKILL.md wording is iterated
  against. `eval/benchmark.json` is held out: no case shares a domain noun with
  the dev set's cache scenarios, and nobody tunes against it.

## Phases

### Phase 0: Stop teaching the demo (S, ships first, not breaking)

- **Remove the hero image** from the README now. Every interim replacement,
  including a correctly scored run, would still print `score N`. The hero comes
  back after Phase 3, generated from a committed payload (`docs/demo/payload.json`),
  together with a `test_demo_contract.py` that asserts every line of rubric
  output in the image appears verbatim in real output.
- **Remove the prose priming:** rewrite `SKILL.md:318-324` with abstract
  placeholders and no domain claims ("Runner-up case: {the line `rubric.py`
  prints for the lead}").
- **Remove the number priming:** change the payload example at `SKILL.md:172-173`
  to show a tied `fit`, a `null`, and the escalation it causes, not a confident
  lead. `test_skill_contract.py` runs `rubric.py` on the example extracted from
  SKILL.md and fails if it comes back `Separated`. It also checks that neither
  the example nor the template contains a domain noun from `scenarios.json`.
- Add the SKILL.md line-budget assertion.

**Exit:** README has no hero image. Both contract checks are green, and each goes
red on a reverted copy of today's SKILL.md.

### Phase 1: Baseline before building (M, no code change to the engine)

- `eval/benchmark.json` has 12 engineering decisions across domains (queue, auth
  session store, DB migration strategy, build tool, retry policy, cache, and
  others):
  - **4 underspecified**: the key is `Undetermined`;
  - **8 specified**: the key is an accepted answer set;
  - **2 of the specified** are single-instance and restart-tolerant, where a
    shared remote store is a defined failure (the demo's error, in two domains).

  Each key entry has a one-line justification citing a primary source (vendor
  docs, an RFC, a public postmortem). The key is frozen by commit **before any
  run**. Any later change to it needs a CHANGELOG entry and a baseline re-run.
- Runner: `check_trace.py --live --benchmark` reuses the existing driver, the
  Wilson interval and `--repeat`.
- Run it on the current engine and commit the results as `eval/baseline.json`.
  Two runs: `--repeat 5` everywhere, plus `--repeat 10` on the two single-box
  cases.

**Exit:** the key and baseline are committed, with the baseline's real numbers,
however bad, in the PR description. There is no pass/fail: this is the number
every later phase must beat.

### Phase 2: Engine honesty (M, output format only, not breaking for payloads)

- **Default output has no totals.** Drop `score N` and `(evidence N)` from the
  default table. Each option line shows its per-criterion levels as words
  (`fit high · reversibility med · precedent high · evidence low`). This is an
  output-only rename; the input stays `20/60/90`. The full table moves behind
  `--table`, and exact numbers stay in `--json`.
  - The first line stands alone, because Claude Code collapses long Bash output:
    `tiltrank: 3 ranked · 1 excluded (Managed SaaS) · Contested · ESCALATE not-separable`.
  - Unit test: for every fixture payload, no total from `--json` appears as a
    token in default stdout. (Testing for "no digit" would fail on `3 ranked`.)
- **Single-rating probe** (finding 8). For each criterion, substitute the
  runner-up's rating into the top option. If any single substitution flips the
  order, print `lead rests on: fit_to_constraints of Redis`, and the result
  cannot be `Separated` (it escalates `not-separable`). If none flips, print
  `lead holds on every single rating`.
  - The probe is deterministic and adds no new randomness, so the fixed `SEED`
    behaviour is unchanged.
  - The printed line *is* the runner-up case: SKILL.md step 4 tells the agent to
    quote it rather than narrate a steelman. This replaces revision 1's separate
    "trade-off" line.
  - Fixture: the demo payload must come out `Contested`.
  - Fallback if the escalation budget is exceeded: the probe flips only on two
    substitutions. Report both variants against the baseline before choosing.
- **The ask stops repeating the transcript.** SKILL.md step 4: the ask body keeps
  exclusions (Hermes and pi users may not see tool output) and the
  `lead rests on` line, and does not restate the band.
- `check_trace` rule `NO_SCORE_IN_TRANSCRIPT`, using the log as ground truth like
  the injection check:
  - flags a `--json` rubric call in a live Claude Code transcript, since Claude
    Code shows that output to the user;
  - flags any assistant text containing a total recomputed from the logged
    payload.

  Fixtures: the demo's output (red), the new format (green).
- `extensions/tiltrank.ts`: unchanged. It renders whatever description the ask
  passes.

**Exit:**
- the unit test and the rule are green, and their broken fixtures are red;
- the demo payload is `Contested`;
- benchmark agreement is not below baseline;
- the escalation budget holds.

### Phase 3: Computed context gate (L, **breaking**, 0.4.0)

The highest-value phase. Revision 1 had the model *declare* decisive open
questions, and a model that wants to recommend simply declares none. Here
`Undetermined` is *computed* from inputs that `check_trace` can verify against
the transcript.

- **Payload additions:**
  - `requirements: [{"id", "text", "quote", "kind": "hard"|"soft", "source": "user"|"repo"|"assumed", "ref"?}]`.
    `quote` is the stated words. `source: "repo"` needs a `ref` of the form
    `path:line`.
  - Per option `constraints: {"<hard id>": "pass"|"fail"|"unknown"}`. `fail`
    excludes the option, with the note generated from the requirement text.
    `feasible: false` stays as a shorthand for one minor version.
- **Breaking validation: `fit_to_constraints` must be equal (or null) across all
  survivors unless at least one `soft` requirement exists.** Revision 1's rule
  ("reject `fit high` when `requirements` is empty") did not block the demo: the
  critic's prompt states one requirement, every survivor passes it, and `fit 90`
  stayed legal. This rule does block it. A hard requirement that every survivor
  passes cannot separate them on fit.
- **`Undetermined` (reason `missing-context`) is raised by the script, not
  declared** when either:
  1. any survivor has an `unknown` hard constraint; or
  2. `fit_to_constraints` is tied across survivors, so only the generic priors
     would order them (finding 5).

  In that state `recommended` is `null`, no ranking order is printed, and the
  output says `no stated requirement separates these options`. The model can
  only get around the gate by inventing a requirement, which the next rule
  catches.
- **SKILL.md step 1 becomes "Frame, then clarify":**
  - On `Undetermined`, the ask is at most 3 closed clarifying questions (e.g.
    "One instance / Several replicas / Don't know yet"), not the option menu.
  - Answers become requirements with `source: "user"`, then the script is re-run.
  - A "Don't know yet" answer becomes a `source: "assumed"` requirement. A
    ranking that rests on an assumed requirement is capped at `Contested` and
    can never be `Separated`.
  - At most one clarify round per decision. A second `Undetermined` result goes
    to the user as "can't rank without X"; the script never loops.

  The prose replaces the "unstated user intent" anti-pattern paragraph
  (`SKILL.md:460`), so the line budget holds.
- `check_trace` rules, each with a good and a broken fixture:
  - `REQUIREMENT_GROUNDED`: every `source: "user"` quote is a whitespace-normalised
    substring of a user message in the transcript, and every `source: "repo"`
    `ref` points at a file the transcript actually read.
  - `NO_MENU_WHEN_UNDETERMINED`: the first ask after an `Undetermined` verdict has
    no `(Recommended)` and is not the option menu.
  - `ASSUMPTION_DISCLOSED`: every `source: "assumed"` requirement appears in the
    ask body.
- Dev-set scenarios added to `scenarios.json`:
  - `underspecified-cache` (the critic's exact prompt): expected `Undetermined`;
  - `cache-single-box-stated`: expected in-memory LRU is top or co-top;
  - `cache-multi-replica-stated`: expected a shared store is top.

**Exit (held-out benchmark, pooled):**
- underspecified cases: `Undetermined` with a Wilson lower bound ≥ 0.75, which
  needs at least 19/20;
- specified cases: inside the accepted set with a lower bound ≥ 0.70, which needs
  at least 34/40;
- single-box failure: 0/20 (the two single-box cases at `--repeat 10`), reported
  as "≤ 0.16";
- the escalation budget holds;
- `REQUIREMENT_GROUNDED` is green on every live run.

A miss is reported with the real numbers in the PR and in `CHANGELOG.md`. It is
not re-run until it passes.

### Phase 4: Records people read (S, additive)

- **The JSONL record gains `question`, `requirements` (with sources and quotes)
  and the `lead rests on` line.** All of these are already in the payload or
  computed, so they are not new free text. The log stays the machine dataset.
- **The ADR is agent-written, not rendered.** SKILL.md step 5 says: for decisions
  that meet step 3's blast-radius criteria, or when the user asks, write
  `docs/decisions/NNNN-<slug>.md` with your file tool, under these headings:
  - Context
  - Requirements (quoted)
  - Options considered (exclusion reason or `lead rests on` line)
  - Decision (the user's pick, and whether it diverged)
  - Assumptions
  - What would make this wrong

  Use the next free number. Never overwrite. Small decisions get no ADR, because a
  directory of trivial ADRs is its own graveyard. Writing prose is the one thing
  the agent already does well; a stdlib template engine in `rubric.py` would
  duplicate it.
- `check_trace` rule `ADR_MATCHES_PICK`: if a live run writes an ADR, its Decision
  section names the user's pick and every excluded option appears. Good and broken
  fixtures.
- Re-add the README hero (see Phase 0), showing the underspecified prompt →
  clarifying questions → ranking → ADR.

**Exit:** the rule is green and its broken fixture is red; the demo contract test
is green; the line budget holds.

## Deferred, with what would bring each back

- **Ordinal input (`low|med|high`).** Renaming `20/60/90` keeps the same
  arithmetic and the same 44 totals, and costs a deprecation cycle across three
  harnesses. Phase 2 already shows the levels as words. *Bring back:* never on
  its own; only if the payload is redesigned for another reason.
- **`evidence_ref` (`cmd:` / `path:line` / `url:`).** Evidence is not weighted, so
  this only affects `unverified-evidence` escalation. A `cmd:` ref is easy to game
  (`redis-cli ping` proves Redis exists, not that it fits). `url:` refs are not
  checked and can be invented. Requiring refs would push most runs to escalate.
  *Bring back:* if the Phase 3 benchmark shows wrong picks concentrated in runs
  whose top option claimed `evidence ≥ 60`.
- **`--adr` renderer and `--stats` calibration report.** Phase 4's agent-written
  ADR covers the human artefact. A per-band override rate needs data that doesn't
  exist (finding 7). *Bring back `--stats`:* once there are ≥ 200 real, non-eval,
  not-timed-out decisions in one log.

## What this plan deliberately does not do

- **No domain rules in the engine** ("prefer in-process caches on one node").
  Context gating and a held-out benchmark address the critique's §2 without
  hard-coding a new prior.
- **No second scoring method** (ELECTRE/AHP). Its value would have to be shown on
  the benchmark first.
- **No custom renderer to hide tool output on Claude Code.** A skill can't do it,
  and the number-free first line makes it moot.

## Order and sizing

| Phase | Depends on | Size | Breaking |
|---|---|---|---|
| 0: stop teaching the demo | none | S | no |
| 1: benchmark baseline | 0 | M | no |
| 2: engine honesty | 1 | M | output format only (agent-facing) |
| 3: computed context gate | 2 | L | yes: `fit` spread needs a soft requirement |
| 4: records people read | 3 | S | log schema additive |

Phase 3 ships as 0.4.0, with a payload migration note in `CHANGELOG.md` and the
`porting-hermes-pi.md` examples updated.

## Needs

- **Present:** the repo and CI, and all three live drivers (`claude`, `hermes`,
  `pi`).
- **Token budget:**
  - baseline: about 80 benchmark runs;
  - Phases 2 and 3: about 80 each, plus the dev scenarios;
  - one Hermes and one pi pass at release.

  That is roughly 400 headless runs in total, down from revision 1's 225 per
  phase gate.
- **Nice to have, not a gate:** an outside engineer reviewing the benchmark key
  before it is frozen. The primary-source citations make the key checkable without
  one. Revision 1 made two gates depend on a reviewer the project doesn't have.
