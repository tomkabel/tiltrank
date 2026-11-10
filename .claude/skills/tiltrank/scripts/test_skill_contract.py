#!/usr/bin/env python3
"""SKILL.md is the product; check_trace.py and rubric.py enforce it.

A rule only in prose isn't enforced, a rule only in code isn't followed. These
tests hold the two to each other: the instructions must not contradict
themselves, and every rule the checker fails a trace for must be stated where
the agent reads it.

    python3 scripts/test_skill_contract.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = (HERE.parent / "SKILL.md").read_text()
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "eval"))

from check_trace import check  # noqa: E402  # pyright: ignore[reportMissingImports]


def section(heading: str) -> str:
    """Body of the markdown section whose heading starts with `heading`."""
    m = re.search(rf"^(#+) {re.escape(heading)}.*?$", SKILL, re.M)
    assert m, f"SKILL.md has no section {heading!r}"
    level = len(m.group(1))
    rest = SKILL[m.end():]
    end = re.search(rf"^#{{1,{level}}} ", rest, re.M)
    return rest[: end.start()] if end else rest


def table_rows(text: str) -> dict[str, list[str]]:
    rows = {}
    for line in text.splitlines():
        if line.startswith("|") and not set(line) <= set("|- "):
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows[cells[0]] = cells[1:]
    return rows


# --------------------------------------------------------------------------- #
# finding 4: one way to run the script
# --------------------------------------------------------------------------- #


def test_claude_invocation_is_what_allowed_tools_preapproves() -> None:
    """The table's command must be a literal prefix of the pre-approval rule.

    The table used to quote the path while the rule did not, so the command the
    skill told the agent to run was not the one it pre-approved.
    """
    rule = re.search(r"^allowed-tools:\s*Bash\((.+?):\*\)\s*$", SKILL, re.M)
    assert rule, "allowed-tools must pre-approve the rubric with a Bash(prefix:*) rule"
    prefix = rule.group(1)
    claude = table_rows(section("2. Score"))["Claude Code"][0]
    shown = re.search(r"`([^`]*rubric\.py[^`]*)`", claude)
    assert shown, claude
    assert shown.group(1) == prefix, f"table runs {shown.group(1)!r}, allowed-tools approves {prefix!r}"


def test_invocation_instructions_do_not_contradict() -> None:
    """'use it as written' and 'do not run the example as written' cannot both stand."""
    says_use = re.search(r"use it as written", SKILL)
    says_dont = re.search(r"Do not run the example as written", SKILL)
    assert not (says_use and says_dont), "SKILL.md says both 'use it as written' and 'do not run it as written'"
    # The example block keeps the pre-approved shape: interpreter, path, heredoc.
    example = re.search(r"```bash\n(python3 <skill-dir>/scripts/rubric\.py[^\n]*)\n", SKILL)
    assert example and "<<'JSON'" in example.group(1), "the example must keep the heredoc form"


# --------------------------------------------------------------------------- #
# issue #2: the recommendation goes first, on every harness
# --------------------------------------------------------------------------- #


def test_every_harness_puts_the_recommendation_first() -> None:
    """check_trace fails a marked option at index > 0 on every harness, so every
    harness row has to say so. Only the Hermes row used to."""
    rows = table_rows(section("4. Present the ask"))
    for harness in ("Claude Code", "Hermes Agent", "pi"):
        marker = rows[harness][1]
        assert re.search(r"\bfirst\b", marker), f"{harness}: marker cell never says 'first': {marker!r}"


# --------------------------------------------------------------------------- #
# issue #3: labels come from the payload
# --------------------------------------------------------------------------- #


def test_step4_requires_labels_from_the_payload() -> None:
    body = section("4. Present the ask")
    assert re.search(r"verbatim[^.]{0,160}payload|payload[^.]{0,160}verbatim", body, re.S), \
        "step 4 must say option labels are copied verbatim from the scored payload"


def test_template_offers_only_scored_feasible_labels() -> None:
    """The shape template used to offer an 'Option D' no payload ever scored."""
    payload = re.search(r"<<'JSON'\n(.*?)\nJSON", SKILL, re.S)
    assert payload
    choices = json.loads(payload.group(1))["choices"]
    feasible = {c["label"] for c in choices if c.get("feasible", True)}
    template = re.search(r"```text\n(.*?)```", section("4. Present the ask"), re.S)
    assert template
    offered = {lab.replace("(Recommended)", "").strip()
               for lab in re.findall(r'label: "([^"]+)"', template.group(1))}
    assert offered and offered <= feasible, f"template offers {offered - feasible} that the payload never scored"


def test_adding_a_candidate_routes_through_the_payload() -> None:
    """Step 1 tells the agent to add missing candidates; that must not collide
    with NO_INVENTED_OPTIONS. Say how an added one becomes legitimate."""
    step1 = section("1. Frame")
    assert re.search(r"add .{0,80}(payload|score)", step1, re.I | re.S), \
        "step 1 must say an added candidate is scored like any other before it is offered"


def test_scored_addition_is_not_an_invented_option() -> None:
    """A candidate the agent added AND scored before the ask is legitimate."""
    trace = {
        "candidates": ["A", "B"],
        "events": [
            {"type": "rubric", "recommended": "A", "separated": True, "reasons": [],
             "excluded": [], "options_scored": ["A", "B", "A behind a flag"]},
            {"type": "escalation", "ran": False},
            {"type": "ask", "options": [{"label": "A (Recommended)", "description": "Strong lead"},
                                        {"label": "A behind a flag", "description": "Contested"}]},
        ],
    }
    assert "NO_INVENTED_OPTIONS" not in check(trace)
    unscored = json.loads(json.dumps(trace))
    unscored["events"][0]["options_scored"] = ["A", "B"]
    assert "NO_INVENTED_OPTIONS" in check(unscored)


def test_live_rubric_events_carry_every_scored_label() -> None:
    """Live traces build rubric events from the log; they must say what was scored."""
    from check_trace import _verified_rubric_events  # pyright: ignore[reportMissingImports]

    run = {"verdict": {"recommended": "A", "separated": True, "reasons": [],
                       "ranked": [{"label": "A"}, {"label": "Hybrid"}],
                       "excluded": [{"label": "C"}]}}
    [event] = _verified_rubric_events([run])
    assert event["options_scored"] == ["A", "Hybrid", "C"] and event["excluded"] == ["C"]


# --------------------------------------------------------------------------- #
# every checker rule: stated in SKILL.md, and guarded by a fixture
# --------------------------------------------------------------------------- #

CHECK_TRACE = HERE / "eval" / "check_trace.py"
EMITTED = re.compile(r'bad\.append\("([A-Z_]+)"\)')


def _normalise(text: str) -> str:
    return " ".join(text.replace("*", "").split())


def test_every_emitted_rule_is_registered() -> None:
    import check_trace  # pyright: ignore[reportMissingImports]
    emitted = set(EMITTED.findall(CHECK_TRACE.read_text()))
    assert emitted == set(check_trace.RULES), (
        f"emitted but unregistered: {emitted - set(check_trace.RULES)}; "
        f"registered but never emitted: {set(check_trace.RULES) - emitted}")


def test_every_rule_is_stated_in_skill_md() -> None:
    """A rule only in code isn't followed. Each rule id quotes its SKILL.md sentence."""
    import check_trace  # pyright: ignore[reportMissingImports]
    skill = _normalise(SKILL)
    missing = {code: quote for code, quote in check_trace.RULES.items() if _normalise(quote) not in skill}
    assert not missing, f"rule wording not found in SKILL.md: {missing}"


def test_every_rule_goes_red_when_disabled() -> None:
    """Mutation test. Delete each rule's `bad.append` from the source, reload the
    module, and run the fixtures: at least one must fail, or the rule is unguarded."""
    import check_trace  # pyright: ignore[reportMissingImports]
    source = CHECK_TRACE.read_text()
    cases = json.loads((HERE / "eval" / "fixtures.json").read_text())
    unguarded = []
    for code in check_trace.RULES:
        mutant = source.replace(f'bad.append("{code}")', "pass")
        assert mutant != source, code
        ns: dict = {"__name__": "check_trace_mutant", "__file__": str(CHECK_TRACE)}
        exec(compile(mutant, str(CHECK_TRACE), "exec"), ns)  # noqa: S102 - our own source
        red = [c["name"] for c in cases if ns["check"](c["trace"]) != sorted(c["expect_violations"])]
        if not red:
            unguarded.append(code)
    assert not unguarded, f"no fixture goes red when these rules are disabled: {unguarded}"


def run_all() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as exc:  # noqa: BLE001 - report every red test
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {type(exc).__name__}: {str(exc)[:300]}")
    if failed:
        print(f"skill contract: {len(failed)}/{len(tests)} tests failed")
        sys.exit(1)
    print(f"skill contract: {len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
