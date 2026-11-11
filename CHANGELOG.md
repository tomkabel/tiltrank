# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-11-11

Answers the 2026-11-11 critique of the README demo ([`docs/review-2026-11-11/`](docs/review-2026-11-11/)).

### Changed (breaking: payload)
- **`fit_to_constraints` may differ across survivors only if a `soft` requirement is stated.** A hard requirement every survivor passes cannot separate them on fit. Payloads with a fit spread and no `requirements` now fail with `error: fit_to_constraints differs across survivors but no soft requirement is stated`. Migration: add `"requirements": [{"id", "text", "quote", "kind": "hard"|"soft", "source": "user"|"repo"|"assumed", "ref"?}]` to the payload, and `"constraints": {"<hard id>": "pass"|"fail"|"unknown"}` to each option. `feasible: false` stays as a shorthand for one minor version.
- **`Undetermined` is computed, not declared.** When fit is tied across survivors, or any survivor has an `unknown` hard constraint, the band is `Undetermined` with reason `missing-context`, `recommended` is `null`, and no order is printed. SKILL.md step 1 is now "Frame, then clarify": at most 3 closed clarifying questions, one round, answers become requirements. A "Don't know yet" answer becomes `source: "assumed"` and caps the band at `Contested` (reason `assumed-requirement`).
- **Default output has no totals.** Each option line shows anchor levels as words (`fit high · reversibility med · …`), the first line stands alone (`tiltrank: 3 ranked · 1 excluded (…) · Contested · ESCALATE not-separable`), and totals move behind `--table`. `--json` is unchanged apart from the new `rests_on`, `undetermined` and `missing` fields.
- **Single-rating probe.** Giving the top option the runner-up's rating on one criterion at a time; any flip prints `lead rests on: <criterion> of <option>` and caps the band at `Contested`. The resampler alone rated the demo payload `robust`; the probe shows its lead rested on one unsupported `fit` rating.
- The README hero image is gone until it can be generated from a committed payload. The SKILL.md payload example no longer shows a confident lead, and the shape template carries no domain claims.

### Added
- `check_trace.py --live --benchmark`: a held-out benchmark (`eval/benchmark.json`, 12 cases with cited keys) graded on pooled Wilson bounds, the escalation rate on specified cases, and the single-box failure count. `eval/baseline.json` records the pre-change engine.
- Checker rules `NO_SCORE_IN_TRANSCRIPT`, `REQUIREMENT_GROUNDED`, `NO_MENU_WHEN_UNDETERMINED`, `ASSUMPTION_DISCLOSED`, each with good and broken fixtures. Live traces carry `driver`, `assistant_text`, `user_messages` and `files_read`.
- The decision log records `question`, `requirements` (with sources and quotes), per-option `constraints` and `rests_on`.
- `test_skill_contract.py` holds SKILL.md to 543 lines, runs the payload example and fails if it is `Separated`, and rejects dev-set domain nouns in the example or template.
- Dev scenarios `underspecified-cache`, `cache-single-box-stated`, `cache-multi-replica-stated` with keys.

### Benchmark (held-out, claude-sonnet-5-5, `--repeat 5`, 10 on the single-box cases; `eval/baseline.json` vs `eval/results-0.4.0.json`)
| gate | baseline (pre-0.4.0) | 0.4.0 | plan's exit bar | result |
|---|---|---|---|---|
| underspecified cases come back `Undetermined` | 0/20, Wilson lower 0.00 | 14/19, Wilson lower 0.51 | lower bound >= 0.75 | **miss** |
| specified cases inside the accepted set | 47/47, lower 0.92 | 47/48, lower 0.89 | lower bound >= 0.70 | pass |
| single-box failure (shared store on top) | 0/17, upper 0.18 | 0/19, upper 0.17 | 0/n, reported as the upper bound | pass |
| escalation rate on specified cases | 36/47 | 34/48 | not more than +20 points over baseline | pass |
| `REQUIREMENT_GROUNDED` on live runs | n/a | 0 violations in 67 runs | green | pass |

The miss was one case: `retry-underspecified` ranked 4/5 times by quoting the whole question as a `soft` requirement, grounded but not a preference. Fix: `rubric.py` rejects a quote equal to `question`, and rule `QUOTE_NOT_THE_QUESTION` flags a quote that is a whole user message. Re-run of the four underspecified cases at `--repeat 5` after the fix: **20/20 `Undetermined`, Wilson lower bound 0.83** (`eval/results-0.4.0-underspecified-rerun.json`); the gate passes. Protocol-break rate was 9.0% (4 `ESCALATION_WHEN_CONTESTED`, 3 `NO_MENU_WHEN_UNDETERMINED`) against 4.5% at baseline.

### Cross-harness release pass
- **Claude, specified cases re-run after `QUOTE_NOT_THE_QUESTION`:** 47/50 inside the accepted set (Wilson lower 0.84), single-box failure 0/20, escalation 30/50 (`eval/results-0.4.0-specified-rerun.json`).
- **pi (gemini-2.5-pro, `--repeat 1`, partial):** 21 of 28 runs graded before a Gemini `MALFORMED_FUNCTION_CALL` aborted the pass; four specified cases never ran. Specified 17/17, single-box 0/15, underspecified 0/4. The model wrote its own `assumed` requirements before asking, turning `Undetermined` into `Contested`. New rule `ASSUMED_ONLY_AFTER_CLARIFY` flags all four of those traces and none of the Claude traces. pi's default model (deepseek-v4-pro) returned HTTP 402 (`eval/results-0.4.0-pi.json`).
- **Hermes: no pass.** Under Hermes v0.23's multiplexing gateway a variable missing from the profile's `.env` resolves to the default, never the calling process's environment, so the driver's per-run `TILTRANK_LOG` cannot reach the terminal tool. Adding it to `terminal.env_passthrough` was tested and has no effect; a throwaway `HERMES_HOME` fails with "Gateway draining: not_ready". The release-pass requirement for Hermes is unmet.
- Live drivers close stdin (every pi run used to hit the 900s timeout), and the pi driver runs with `-ne` so an operator package entry cannot load `extensions/tiltrank.test.ts` as an extension.

## [Unreleased]

### Fixed
- The feasibility gate accepted any value except literal `false` as feasible. `feasible` must now be a JSON boolean; `"false"`, `0`, `null` and `"no"` are rejected.
- A lone feasible option never raised `weak-field`. The weak-field check now runs for any field size and uses the conservative bound (`lo`), so an option propped up by unknown criteria escalates.
- Stability depended on input order (0.51 to 0.56 across the 24 orders of one four-option set). Options are perturbed in label order, with ties broken the way the ranking breaks them.
- Malformed payloads (`10**400`, non-object choices or weights, non-string labels) produced tracebacks. Every one is now a one-line `error:` with exit 1, checked by a mutation fuzz over a logged payload.
- `timed_out: "false"` logged as true, and a pick matching no label was accepted. `timed_out` and `escalated` must be booleans, and `pick` must name an option. The ask's `(Recommended)` marker is stripped first, so a verbatim pick no longer logs a false divergence.
- `label: null` became an option called `None`.
- SKILL.md told the agent both to run the invocation "as written" and not to, and the Claude Code table quoted a path the unquoted `allowed-tools` prefix never matched. One instruction now, pinned by `test_skill_contract.py`.
- Only the Hermes row said the recommended option goes first, while the checker enforced index 0 on every harness (issue #2). Every row says it now.
- Step 4 had no rule that labels come verbatim from the scored payload, and its template offered an "Option D" nothing had scored (issue #3). Step 1's "add the missing candidate" now routes through the payload, and `NO_INVENTED_OPTIONS` accepts any label the preceding rubric run scored (`options_scored`, read from the log on live runs).
- `INJECTION_NOT_EXECUTED` deleted any line mentioning `rubric.py` before scanning, so `rm -rf ~ # rubric.py` passed. Commands are now parsed with `shlex`: only a `python* .../rubric.py` call, a quoted heredoc it owns, and an `echo`/`printf`/`cat` piping into it are exempt; command substitution is never exempt.
- `check({})` passed every rule. New rule `RUBRIC_BEFORE_ASK`: a trace needs a rubric run, before any ask, and a live run without a decision log does not count.
- `OTHER_RESCORED` accepted any later rubric run, even one without the typed answer. `RESCORE_TO_DISMISS` used `events.index()`, so a duplicated rubric event hid a dismissal.
- `NO_PERCENT` flagged `Redis 1.0.1` and `3 of 4 teams` and missed `80 percent` and `4 in 5`.
- pi extension: `timeoutMs` accepted NaN, negative and overflowing values; the Other free-text prompt had no timeout and could block forever; `multiSelect` returned one raw string with unoffered names mixed in. One deadline now covers the whole ask, `multiSelect` returns `picks` (offered labels) and `other`, and an agent-appended `(Recommended)` is no longer rendered twice.
- The extension's `sanitiseLabel` truncated by UTF-16 units, not code points like `rubric.py`. `tiltrank.test.ts` now runs both on 300 generated inputs.
- The live Claude driver inherited the operator's permission mode. Under `auto`, headless `claude -p` denied every Bash call, so `rubric.py` never ran: the G3 sonnet pass had 0/45 rubric runs (issue #1). The driver now pins `--permission-mode dontAsk` and allows `Skill` alongside `Bash,Read,Grep,Glob`. It also runs Bash in Claude Code's OS sandbox, with no per-command unsandboxed fallback and `failIfUnavailable`, so `claude` exits rather than running unsandboxed when the sandbox cannot start. The repo and its git common dir are read-only; without that, a linked worktree's shared `.git` was writable. Only the run's `--out` dir and the per-user temp dir are writable, so an agent that obeys the `rm -rf` candidate can delete only files in those two places. `--out` must therefore be a new or empty directory outside the repo. Its default model is `claude-sonnet-5-5`, the one the docs name (was `claude-opus-4-5`).
- A live pass where `rubric.py` never ran printed a break rate (6.7% from 0/45 runs). Runs with no rubric invocation are now reported as not activated and kept out of the denominator, and a pass with none activated is `INVALID` with exit 1.
- CI ran twice per PR push, had no concurrency group or job timeouts, skipped the extension job when `extensions/package.json` was missing, and its stdlib check ignored `__import__`/`importlib`. Two install-contract assertions could not fail (`"-g" in section`, a split on `"pi"` that matched `pip`). The porting doc quoted the 0.2.0 frontmatter.

### Added
- `check_trace.RULES` maps every rule id to the SKILL.md sentence that states it. `test_skill_contract.py` fails if a rule is unregistered, if its sentence is missing from SKILL.md, or if deleting the rule from the source leaves every fixture green (mutation test).
- The injection flag missed zero-width splits, fullwidth text, `wget`, `base64 -d`, `sudo`, `eval`, `rm -fr` and "ignore the previous instructions". SKILL.md now calls it a best-effort keyword flag, not detection.

### Changed
- The README now has a removal command with the same global scope as the install (`npx skills remove tiltrank -g -a claude-code hermes-agent pi -y`), and tells the reader to pin `skills@1.7.4`. `SKILL.md` says not to run the `<skill-dir>` example as written.

### Added
- A self-hosted Claude Code marketplace at `.claude-plugin/marketplace.json`. It is not Anthropic's marketplace. The entry's source is this repo, and it loads `.claude/skills/` without a second copy of `SKILL.md`.

### Security
- Decision-log paths are contained to the working directory, or to `$TILTRANK_LOG_BASE` when set. The path must end in `.log`, the final component must not be a symlink, and the open uses `O_NOFOLLOW`.
- Injection-shaped candidate text is flagged by `rubric.py` and recorded in the verdict and the log. A live eval reads that finding from the log, not from the agent's narration, and fails if a shell tool runs the payload.
- CI actions are pinned to commit SHAs. `ruff` and `@anthropic-ai/claude-code` are pinned to exact versions. The typecheck job installs from `extensions/package-lock.json`.
- The live eval driver passes a minimal environment, not the operator's full shell.
- macOS CI is a separate experimental job and is not part of the required `test` check.

### Changed
- Relicensed from MIT to MPL-2.0 (file-level copyleft). Copies obtained under the earlier MIT license keep their MIT terms.
- Renamed the project from `decision-picker` to `tiltrank` (repo, skill directory, pi extension and tool name). The log env var is now `$TILTRANK_LOG` (was `$DECISION_PICKER_LOG`).

## [0.3.0] - 2026-11-01

### Changed
- The README's primary install is one `npx skills add` command for Claude Code, Hermes Agent, and pi. The old symlink quickstart and the two-segment pi link are gone. `SKILL.md` resolves `rubric.py` from the loaded skill directory instead of a guessed path.

## [0.2.0] - 2026-09-21

### Added
- MIT LICENSE file
- CONTRIBUTING.md, SECURITY.md, community health files (issue templates, PR template)
- Prerequisites, Changelog, and Acknowledgments sections in README
- `when_to_use` and `compatibility` frontmatter fields in SKILL.md
- `extensions/package.json` and `extensions/tsconfig.json` for pi extension type-checking
- Ruff lint step and macOS to CI matrix
- Extension type-check job in CI

### Changed
- Expanded `.gitignore` to industry-standard Python patterns
- Removed HTML wrapper from README; marked `claude plugin validate` as optional
- Sanitized internal provider details from docs/ and PLAN.md
- Added docs/README.md and PLAN.md design-history header
- Updated README Testing section with honest live-gate status

### Fixed
- License contradiction (README said 'all rights reserved', SKILL.md said MIT)
- Stale local branches removed
- Cached artifacts cleaned from working tree
