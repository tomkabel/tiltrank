# Contributing to tiltrank

Issues and PRs welcome. This skill ships in three harnesses (Claude Code,
Hermes Agent, pi) from one codebase, so a few small rules keep it portable.

## Run tests locally

Both suites are stdlib-only Python — no virtualenv needed.

```bash
# unit tests: validation, gating, ranking, stability
python3 .claude/skills/tiltrank/scripts/test_rubric.py

# protocol-trace assertions + fixture regressions
python3 .claude/skills/tiltrank/scripts/eval/check_trace.py

# install-page contract (forbidden commands, relative links, skill paths)
python3 .claude/skills/tiltrank/scripts/test_install_contract.py
```

CI runs the unit tests, the protocol assertions, and the install contract on **Python 3.10 and 3.13**.

## House rules

1. **New behaviour needs a fixture.** Any change to protocol rules gets a
   labelled trace in
   `.claude/skills/tiltrank/scripts/eval/fixtures.json` — including a
   deliberately broken variant that must go red. If a rule isn't asserted, it
   isn't real.
2. **No dependencies.** CI fails on any import outside the Python standard
   library. The skill is intentionally copy-paste portable; don't add a
   `requirements.txt`, a `pyproject.toml`, or a vendored package.

## Branch & PR workflow

- Create a branch off `main` (`git checkout -b my-fix`); never push directly
  to `main`.
- Open a pull request against `main`. Keep one concern per PR.
- Before opening a PR, run locally:

  ```bash
  claude plugin validate .claude/skills
  ```

  (requires [Claude Code](https://docs.claude.com/en/docs/claude-code)
  installed). This catches SKILL.md / frontmatter problems CI can't see from
  the Python side.

## Adding live-eval scenarios

The `--live` harness draws scenarios from
`.claude/skills/tiltrank/scripts/eval/scenarios.json`. To add one:

1. Append a scenario object (prompt, options, any expected reasons).
2. Re-run `check_trace.py` — it picks up new scenarios automatically.
3. If the scenario is meant to exercise a new rule, add a matching fixture in
   `fixtures.json` so the offline suite covers it too.

Live runs call a real model and are non-deterministic; the fixtures are the
deterministic contract.
