# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A portable agent skill (Claude Code, Hermes Agent, pi) that scores a list of options with a weighted rubric, gates out infeasible ones, measures how stable the ranking is, and hands the pick to the user through the harness's native ask tool. **`SKILL.md` is the product**; the Python is a validator, feasibility gate, and the single source of truth for weights.

## Commands

All Python is stdlib-only, >= 3.10. No venv, no install step.

```bash
S=.claude/skills/tiltrank/scripts
python3 $S/test_rubric.py                  # unit tests (no framework; runs every test_* function)
python3 $S/eval/check_trace.py             # offline protocol assertions over fixtures.json
python3 $S/test_skill_contract.py          # SKILL.md wording <-> check_trace RULES, plus the rule mutation test
python3 $S/test_install_contract.py        # README install commands
python3 .github/scripts/stdlib_only.py     # no import outside the stdlib, dynamic imports included
python3 .github/scripts/test_stdlib_only.py   # the import checker itself catches every shape
ruff check --select E4,E7,E9,F $S .github/scripts   # lint, same rule set as CI
ruff format --check $S .github/scripts             # formatting, CI pins ruff==0.17.3 (`uvx ruff@0.17.3 ...` if not installed)
claude plugin validate .claude/skills      # SKILL.md frontmatter check (CI)
cd extensions && npm ci && npx tsc --noEmit         # pi extension typecheck (CI)
node --experimental-strip-types --test --test-force-exit extensions/tiltrank.test.ts  # extension + sanitiser parity

# single test: import the module and call the function
cd $S && python3 -c "import test_rubric as t; t.test_custom_weights()"

# run the rubric directly: JSON on stdin; --json for machine output, --log / $TILTRANK_LOG to append a record
python3 $S/rubric.py --json < input.json

# live eval (real headless sessions, costs tokens, non-deterministic)
python3 $S/eval/check_trace.py --live --driver claude|hermes|pi [--only <scenario-id>] [--repeat N] [--model M]
```

CI (`.github/workflows/test.yml`) runs on Python 3.10 and 3.13, on Linux and Windows (both required; macOS is experimental), and fails on any import outside the stdlib (`.github/scripts/stdlib_only.py`, which also catches `__import__`/`importlib`).

## Architecture

- `.claude/skills/tiltrank/SKILL.md` — the 5-step workflow the agent follows (frame → score → escalate → ask → act/record), plus anti-patterns. Scripts are addressed via `${CLAUDE_SKILL_DIR}`, so the directory must stay self-contained.
- `scripts/rubric.py` — validates sub-scores (must be anchor band values from `LEVELS`, or `null`; free numbers are rejected), excludes `feasible: false` options before any arithmetic, ranks on the conservative bound (unknowns contribute nothing), resamples weights + jitters ratings with a fixed `SEED` to compute stability/band, emits escalation `reasons`, and appends to `.decisions.log` (JSONL, gitignored). `evidence` is deliberately **not** a weighted criterion — it only drives escalation.
- `scripts/eval/check_trace.py` — `check(trace)` holds the protocol assertions (≤4 options, `(Recommended)` first, no percentages shown to the user, no re-scoring to dismiss an escalation reason, injection-shaped `Other` answers never executed, final action matches the user's pick). Offline mode runs `fixtures.json`; `--live` drives a harness CLI per `scenarios.json` and captures the rubric log via `$TILTRANK_LOG` as ground truth (ask-tool arguments are only self-reported — `AskUserQuestion` doesn't exist in headless `claude -p`).
- `extensions/tiltrank.ts` — pi extension providing the `tiltrank` ask tool (AskUserQuestion-shaped) and `/panel`. Rendering and returning the pick only; never duplicate scoring/gating logic there.

## House rules

- **New behaviour needs a fixture**: any protocol-rule change gets a labelled trace in `fixtures.json`, including a deliberately broken variant that must go red.
- **A new check_trace rule** goes in `check_trace.RULES` with the exact SKILL.md sentence that states it. `test_skill_contract.py` fails otherwise, and also fails if no fixture goes red when the rule's `bad.append` is deleted.
- **No dependencies**: no `requirements.txt`, `pyproject.toml`, or vendored packages.
- Changing scoring/protocol semantics usually means touching `SKILL.md`, `rubric.py`, and `check_trace.py` together — a rule only in prose isn't enforced, a rule only in code isn't followed.
- Harness install quirks (Hermes and pi don't follow symlinked skill dirs for discovery) are documented in `README.md` under Quick start and in `docs/porting-hermes-pi.md`. `PLAN.md` is design history, not a task list.
