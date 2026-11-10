# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
