# Plan: answering the 2026-11-11 critique

Input: [`CRITIQUE.md`](CRITIQUE.md), a review of the README hero demo (`docs/demo.svg`).
Target release: **0.4.0** (the payload contract changes, see Phase 2).

## Goal beyond the goal

The critique is about one screenshot, but the real goal is bigger: **tiltrank must be
unable to produce that screenshot.** That means no rendered number, no recommendation
when the inputs can't support one, no `evidence 90` without a check anyone can see,
and a decision record a reviewer can read six months later. Fixing the demo alone
would just hide the problem.

## What was verified before planning

Every claim below was reproduced against `main` @ `71ba7b7`. None of it is inferred
from the critique.

1. **The demo numbers are real arithmetic on badly chosen inputs.** With weights
   0.5/0.3/0.2 and levels 20/60/90, the three totals have exactly one input each:
   Redis `(fit 90, rev 60, prec 90)` = 81, File-based `(20, 90, 60)` = 49, In-memory
   LRU `(20, 90, 20)` = 41. The critic's "Why 81 and not 80?" has an exact answer
   (0.5·90 + 0.3·60 + 0.2·90). Three bands across three criteria, plus null, give
   **44 reachable totals**. That is the false resolution the critic saw: the inputs
   are coarse, but the displayed total looks precise.
2. **The demo violates the skill's own anchors.** LRU `precedent: 20` means "novel",
   but in-memory LRU is about as proven as caching gets. That one mis-score is the
   whole reason File-based ranks above LRU. Redis `evidence: 90` means "verified in
   this repo this session", yet the demo shows no tool call that could have
   verified it. `fit 90` means "satisfies every stated need", but the prompt states
   one need (self-hosted), and every survivor meets it.
3. **The demo's domain prose comes from SKILL.md.** The shape template at
   `SKILL.md:318-324` contains "if this stays a single box", "proven at this
   shape" and "the cache dies on every restart". Every real run reads that
   template, so the skill pushes cache-flavoured reasoning into unrelated
   decisions. This is the root cause of critique §2. The engine has no domain
   logic.
4. **The demo was hand-edited.** The real table prints `separation: robust`,
   `band: Separated`, `separated: yes — a recommendation is defensible` and a
   `NOTE:` line. The demo merges these into one line that the script never emits.
5. **Fed honestly, the existing engine already refuses.** The same three options
   scored with no stated context (fit 60 each, evidence 20, LRU precedent 90) come
   out **Contested, `ESCALATE — not-separable, unverified-evidence`, In-memory LRU
   on top**. The math was not the main defect. The defect is that **nothing forces
   honest input**: the script accepts `fit 90` with zero stated requirements and
   `evidence 90` with no reference.
6. **"Never show the user a number" is broken by design on Claude Code.** SKILL.md
   says the score is an internal sort key, but the default table prints `score 81`
   to stdout, and Claude Code renders Bash output to the user. The rule holds for
   the ask and fails for the transcript.
7. **The decision log has almost no calibration signal yet.** `.decisions.log` holds
   39 records: 35 decisions, 30 of them `timed_out` (headless eval), and 2
   `diverged`. The JSONL exists to measure whether recommendations are any good,
   and so far it cannot.

## Verdict on each critique point

| # | Point | Verdict | What we do |
|---|---|---|---|
| 1a | `rubric.py` called with zero arguments, so the numbers are hardcoded | **Invalid as stated.** The payload arrives on stdin (heredoc); the demo truncated it. **Valid underneath:** the inputs are invisible to a reviewer | Phase 4 puts the inputs and reasons in a readable record |
| 1b | False precision, `81` vs `80` | **Valid** (finding 1) | Phase 1: no totals anywhere a person reads; ordinal words in and out |
| 1c | `evidence 90` with no metrics | **Valid** (finding 2) | Phase 3: evidence needs a reference anyone can check |
| 1d | Collapse to a scalar hides trade-offs | **Partly valid.** A sort key is needed to recommend at all, and stability resampling already tests it. Showing only the scalar is the defect | Phase 1: per-criterion profile and a computed trade-off line. Phase 2: constraint checklist |
| 2a | Redis over LRU on a single box is YAGNI | **Valid about the demo; the engine has no cache logic to fix** (findings 3, 5) | Phase 0: de-prime the template, rescore the demo. Phase 5: a benchmark checks domain judgement |
| 2b | File-based above LRU is absurd | **Valid**, caused by the LRU `precedent 20` mis-score | Phase 0 and Phase 5 |
| 2c | A cache is ephemeral by design | **Valid**, and the wording comes from SKILL.md's template | Phase 0 |
| 3 | No recommendation without the critical context | **Valid**, and the most important point | Phase 2: `Undetermined` band, decisive open questions, clarify first |
| 4 | The raw stdout duplicates the ask box | **Valid on Claude Code.** On Hermes/pi the tool output is less prominent, so the ask body must still carry exclusions | Phase 1: a short, number-free default output; the full table moves behind `--table` |
| 5a | A hidden dotfile is where context dies | **Partly valid.** The JSONL is a machine dataset (override rate), not documentation, and should stay. It is the wrong artefact for humans | Phase 4: generate ADRs from the same record |
| 5b | Records the *that*, not the *why* | **Valid.** No question, requirements, assumptions or trade-off reasons are logged | Phase 4: enrich the record |
| S3 | "Stop treating a distributed store as the default" | **Rejected as a code change.** Hard-coding cache priors into a general decision tool trades one bias for another | Covered by Phase 2's context gate plus Phase 5's benchmark, which measures judgement without encoding it |
| S4 | Collapse the script into a spinner | **Partly out of reach.** A skill cannot hide a harness's tool output | Phase 1 makes that output one line with no numbers. The pi extension already owns its rendering |

## Phases

Every phase follows the house rules: SKILL.md, `rubric.py` and `check_trace.py`
change together; each new protocol rule gets a `check_trace.RULES` entry quoting
the exact SKILL.md sentence; each rule gets a good fixture and a deliberately
broken one that must go red; and CI (3.10/3.13, Linux and Windows) stays green.
One PR per phase.

### Phase 0: Stop the skill from teaching bad reasoning (small, ships first)

Root cause of §2. Without this fix, every later phase is still fed primed prose.

- `SKILL.md:318-324`: rewrite the composed-shape template with abstract placeholders
  and no domain claims, matching the payload example's `Option A/B` convention
  (e.g. "Runner-up case: {the single strongest reason to pick #2}").
  `test_skill_contract.py` gets a check that the template contains no option
  label or domain noun from `scenarios.json`. That keeps it from re-acquiring
  cache wording.
- Rebuild the hero demo from a **committed payload** (`docs/demo/payload.json`) and
  real output. `test_install_contract.py` (or a new `test_demo_contract.py`) runs
  `rubric.py` on the payload and asserts that every line of rubric output shown in
  `demo.svg` appears verbatim in the real output. A hand-edited demo then fails CI.
- New demo content: show the Phase 2 behaviour (an underspecified question gets an
  `Undetermined` answer and two clarifying questions, then a ranking after the
  answers), not a confident pick. The demo is the product's main claim, so it
  should show the behaviour the critic asked for.
- Until Phases 1–2 land, replace the hero image with a correctly scored run (LRU
  `precedent 90`, honest `evidence`, no `fit 90`). Even that version will escalate,
  which is the honest picture.

**Exit / judge:** CI fails if `demo.svg` shows text that `rubric.py` does not
produce on the committed payload, and if the template contains a domain noun.

### Phase 1: No number reaches a human (critique §1b, §1d, §4)

- **Ordinal input.** `scores`/`evidence` accept `"low" | "med" | "high" | null`.
  `20/60/90` stay accepted for one minor version with a deprecation note on
  stderr, then go away. The arithmetic keeps its internal encoding; only the
  interface changes. SKILL.md anchors are rewritten to the words.
- **Default output is agent-facing and number-free:**
  `tiltrank: 3 ranked · 1 excluded (Managed SaaS: self-hosted) · Contested · ESCALATE not-separable`
  on the first line, then one line per option with the **per-criterion profile**
  (`fit high · reversibility med · precedent high · evidence: verified`). Claude Code
  collapses long Bash output after a few lines, so the first line must stand
  alone. The current table moves behind `--table`, and exact numbers stay in
  `--json` only.
- **Computed trade-off.** For the top two, the script prints the criteria the
  runner-up wins on (`trade-off: In-memory LRU beats Redis on reversibility`), or
  `dominates` when it wins on none. The steelman in step 4 must quote this
  line, so it is derived, not narrated. That covers the critic's "let trade-offs be
  trade-offs" without dropping the recommendation.
- **The ask stops repeating the transcript.** The ask body keeps the exclusion
  (Hermes/pi users may not see tool output) but drops nothing else it needs.
  SKILL.md step 4 gets one sentence: the description is the profile difference,
  not the band restated.
- `check_trace`: extend `NO_PERCENT` to the **tool output a live run captures**,
  not only the ask, plus a new rule `NO_SCORE_IN_TRANSCRIPT` for rendered
  `score \d+`. Fixtures: the demo's current output (red) and the new format
  (green).
- `extensions/tiltrank.ts`: no scoring logic. It only accepts a `profile` string
  per option, if the ask passes one.

**Exit / judge:** `rubric.py` default stdout contains no digit outside labels
(unit test with a regex over every fixture payload), and the live eval on all 15
scenarios shows zero `NO_PERCENT`/`NO_SCORE_IN_TRANSCRIPT` hits at `--repeat 3`.

### Phase 2: Gate the ranking behind missing context (critique §3, S1, S2)

The highest-value phase. The skill already says "A fork whose real discriminator is
unstated user intent is not a scorable option set" (SKILL.md:460), but nothing
enforces it.

- **Payload additions** (0.4.0, breaking where marked):
  - `requirements: [{"id": "self-hosted", "text": "...", "source": "user"|"repo"}]`:
    what was actually stated, quoted. **Breaking:** `fit_to_constraints: high` is
    rejected when `requirements` is empty ("satisfies every stated need" is
    vacuous with zero stated needs).
  - Per option `constraints: {"self-hosted": "pass"|"fail"|"unknown"}`, keyed by
    requirement id. This is the critic's **constraint checklist**, done as gating:
    `fail` excludes the option, and its note is generated from the requirement
    text (replacing the free-text `note`). `unknown` on a hard requirement makes
    the option unrankable until it is answered. `feasible: false` stays as a
    shorthand for one minor version.
  - `open_questions: [{"id", "text", "decisive": bool, "flips": ["<label>", ...]}]`:
    questions whose answer would change the ranking, each naming the options it
    would favour. A decisive question must name at least two different outcomes,
    so a decorative question cannot pass as decisive.
- **New band `Undetermined`, reason `missing-context`:** raised when any decisive
  question is open or any surviving option has an `unknown` hard constraint. In
  that state `recommended` is `null`, the output prints the decisive questions
  (at most 3, ranked by how many options they move) and **no ranking order**.
- **SKILL.md step 1 becomes "Frame, then clarify":** when the band is
  `Undetermined`, the ask is the clarifying questions (choices where they are
  closed, e.g. "One instance / Several replicas / Don't know yet"), not the
  option menu. The answers become `requirements` with `source: "user"`, then the
  script is re-run. A "Don't know yet" answer is recorded as an assumption, and
  the run continues with that assumption named in the ask body.
- **Anti-ceremony guard** (SKILL.md "When NOT to use" already warns about
  four-round interrogations): at most one clarify round per decision. A second
  `Undetermined` result goes to the user as "can't rank without X". The script
  does not loop.
- `check_trace` rules:
  - `NO_RECOMMEND_WHEN_UNDETERMINED`: an ask built after an `Undetermined` verdict
    has no `(Recommended)` and no option menu.
  - `CLARIFY_BEFORE_RANK`: the first ask after an `Undetermined` verdict carries
    the decisive questions.
  - `ASSUMPTION_DISCLOSED`: a requirement with `source: "assumed"` appears in the
    ask body.

  Each rule gets a good and a broken fixture.
- New scenarios in `scenarios.json`: `underspecified-cache` (the critic's exact
  prompt; expected: `Undetermined`), `cache-single-box-stated` (one instance,
  restart-tolerant, small working set; expected: In-memory LRU is top or
  co-top), and `cache-multi-replica-stated` (expected: a shared store is top).

**Exit / judge:** on `--live --repeat 5` with the Claude driver,
`underspecified-cache` yields `Undetermined` in ≥ 90% of runs (Wilson lower bound
reported), and the two stated variants never yield `Undetermined`.

### Phase 3: Evidence you can check (critique §1c)

- Per option `evidence_ref`: required for `med` and `high`. `high` needs a
  this-session reference (`cmd:` the command run, or `path:line`); `med` accepts
  an `url:` or `doc:`. The script rejects `high` without a this-session ref, and it
  rejects a ref whose kind does not match the level.
- On a live run, `check_trace` checks that each `cmd:` ref appears among the
  transcript's actual tool calls, the same way the injection check already
  trusts the log over the narration. New rule `EVIDENCE_REF_REAL`. A fixture
  that claims `cmd:redis-cli ping` with no such call must go red.
- The `unverified-evidence` escalation keeps its semantics. It now runs on a
  value that can no longer be typed in without doing the work.

**Exit / judge:** `EVIDENCE_REF_REAL` is green on all live scenarios at
`--repeat 3`; the broken fixture is red. The demo's `evidence 90` becomes
unrepresentable without a visible tool call.

### Phase 4: Records people read (critique §1a, §5)

- **Enrich the JSONL record** (still the calibration dataset): `question`,
  `requirements` (with sources), `open_questions` and their answers, assumptions,
  `constraints` per option, `evidence_ref`, the computed trade-off line, and the
  escalation probe that ran (command or file). Nothing new is free text the script
  cannot validate, except one `rationale` clause per option, capped at 200 chars
  and sanitised like labels.
- **`--adr DIR`** renders a MADR-format Markdown file (`NNNN-<slug>.md`: Context,
  Decision drivers = requirements, Considered options, Decision outcome with the
  user's pick and whether it diverged, Pros/cons from the profile and trade-off,
  Assumptions, Open risks). It is written from the same record, so the ADR and
  the log cannot drift. Never overwrite; number from the highest existing ADR
  in `DIR`; use the same path-confinement rules as `--log`. Stdlib only: string
  templating, no YAML/Jinja.
- **SKILL.md step 5:** write an ADR when the decision is architecture-level, the
  blast-radius criteria in step 3 hold, or the user asks. The JSONL is always
  written. Small decisions (tabs vs spaces) get no ADR, since a directory full of
  trivial ADRs is its own context graveyard.
- Default log location stays configurable. Do **not** move it into `docs/` by
  default: it is machine data and would churn diffs. The ADR is the visible
  artefact.
- Tests: golden-file test of the ADR renderer over every decision fixture, a
  no-overwrite test, and a path-escape test mirroring the `--log` ones.

**Exit / judge:** for each fixture decision, the generated ADR contains the
question, every requirement, every considered option with its exclusion reason
or trade-off, and the pick. A reviewer reading only the ADR can answer "why
Redis, and what would make it wrong" (spot-checked in the PR by someone other
than the author).

### Phase 5: An outside judge for judgement (critique §2, and the calibration gap)

Phases 0–4 make bad output structurally hard. This phase measures whether the
recommendations are *good*, which nothing in the repo measures today
(finding 7).

- **Decision benchmark** `eval/benchmark.json`: about 12 engineering decisions
  across domains (cache, queue, auth session store, DB migration strategy, build
  tool, retry policy). Each has a stated context and an **accepted answer set**
  written down before any run, including `Undetermined` as the correct answer
  for the underspecified variants. Each case gets a one-line justification that
  cites a primary source (vendor docs, an RFC, a well-known postmortem), so the
  answer key is checkable rather than this repo's opinion. A second engineer
  reviews the key before it is frozen.
- Runner: `check_trace.py --live --benchmark` reuses the existing driver, Wilson
  interval and `--repeat` machinery. It reports per-case agreement with the key
  and self-agreement across repeats.
- **Calibration report** `rubric.py --stats LOG`: over non-timed-out decisions,
  the override (`diverged`) rate per band and per escalation reason. If
  `Separated` picks are overridden as often as `Contested` ones, the bands are
  not carrying information, and the report says so.

**Exit / judge (hard target):** on `--repeat 5` with the Claude driver,
Undetermined cases are ≥ 90% `Undetermined`, specified cases are ≥ 80% inside
the accepted set, and the demo-style failure (a shared remote store recommended
for a stated single-instance, restart-tolerant case) occurs **0 times**. A miss
is reported with the real numbers in the PR and in `CHANGELOG.md`, not re-run
until it passes.

## Order and sizing

| Phase | Depends on | Size | Breaking |
|---|---|---|---|
| 0: de-prime and honest demo | none | S | no |
| 1: number-free output | 0 | M | output format (agent-facing only) |
| 2: context gate | 1 | L | yes: `requirements` needed for `fit high` |
| 3: checkable evidence | 1 | M | yes: `evidence_ref` needed for `med`/`high` |
| 4: ADRs and enriched record | 2, 3 | M | log schema additive |
| 5: benchmark and calibration | 2 | M | no |

Phases 2 and 3 ship together as 0.4.0, with a payload migration note in
`CHANGELOG.md` and the `porting-hermes-pi.md` examples updated. Phase 5's key is
written during Phase 2, before any Phase 2 live run, so the benchmark is never
tuned to the implementation.

## What this plan deliberately does not do

- **No domain rules in the engine** ("prefer in-process caches on one node").
  Context gating and an external benchmark fix the critic's §2 without
  hard-coding a new prior.
- **No second scoring method** (ELECTRE/AHP). The ordinal weighted sum plus
  stability resampling plus a visible trade-off line meets the critique; a
  heavier MCDA method would add complexity the benchmark has not shown is
  needed.
- **No custom renderer to hide tool output on Claude Code.** Not possible from a
  skill, and the one-line output makes it moot.

## Needs

- Present: the repo and CI, all three live drivers (`claude`, `hermes`, `pi`), and
  `.decisions.log` with 39 real records.
- Missing: a second engineer to review the Phase 5 answer key, and live-eval token
  budget (about 15 scenarios × 5 repeats × 3 drivers per phase gate).
