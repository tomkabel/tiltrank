#!/usr/bin/env python3
"""The install page is a contract. These strings are the page.

A reader who runs the first command must not be handed a command this repo
has already watched fail. The forbidden list is the failure log, not a style
guide.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
README = (ROOT / "README.md").read_text(encoding="utf-8")
SKILL = (ROOT / ".claude/skills/tiltrank/SKILL.md").read_text(encoding="utf-8")
PORTING = (ROOT / "docs/porting-hermes-pi.md").read_text(encoding="utf-8")


def quickstart() -> str:
    start = README.index("## Quick start")
    rest = README[start + len("## Quick start") :]
    end = rest.find("\n## ")
    return rest[:end]


def test_primary_command_is_skills_add() -> None:
    section = quickstart()
    # The whole command, not its fragments: `"-g" in section` matched any
    # word containing -g anywhere in the section.
    install = "npx skills add tomkabel/tiltrank --skill tiltrank -g -a claude-code hermes-agent pi --copy -y"
    assert re.search(r"^" + re.escape(install) + r"$", section, re.M), install
    assert section.index("npx skills add") < section.index("git clone")


def test_removal_uses_the_same_global_scope() -> None:
    section = quickstart()
    remove = "npx skills remove tiltrank -g -a claude-code hermes-agent pi -y"
    pinned = (
        "npx skills@1.7.4 add tomkabel/tiltrank --skill tiltrank "
        "-g -a claude-code hermes-agent pi --copy -y"
    )
    assert remove in section
    assert pinned in section
    assert section.index("npx skills add") < section.index(remove)
    assert "DISABLE_TELEMETRY=1" in section


def test_known_bad_commands_are_gone() -> None:
    section = quickstart()
    forbidden = [
        "hermes config set skills.external_dirs",
        'ln -s "$PWD/.claude/skills/tiltrank" ~/.claude/skills/tiltrank',
        'pi install "$PWD"',
    ]
    for snippet in forbidden:
        assert snippet not in section, snippet
    # The three-segment link required by test_pi_relative_link_has_three_dots
    # contains this two-segment string after its first "../". Reject the
    # two-segment command only when it is not that continuation.
    bad_pi = "../../.agents/skills/tiltrank ~/.pi/agent/skills/tiltrank"
    assert re.search(r"(?<!\.\./)" + re.escape(bad_pi), section) is None, bad_pi


def test_pi_relative_link_has_three_dots() -> None:
    section = quickstart()
    assert "../../../.agents/skills/tiltrank ~/.pi/agent/skills/tiltrank" in section


def test_skill_does_not_hardcode_install_paths() -> None:
    assert "<category>" not in SKILL
    assert ".hermes}/skills/" not in SKILL
    assert ".pi/agent/skills/tiltrank/scripts/rubric.py" not in SKILL
    assert "skill_dir" in SKILL
    assert "CLAUDE_SKILL_DIR" in SKILL
    assert "Replace `<skill-dir>` with the directory this table names" in SKILL


def test_panel_is_not_sold_as_a_claude_command() -> None:
    section = quickstart()
    # Every mention of /panel must sit in a sentence about pi, the word: a
    # split on "pi" also matched "pip", "pinned" and "API".
    for sentence in re.split(r"(?<=[.!?])\s+|\n\n", section):
        if "/panel" in sentence:
            assert re.search(r"\bpi\b", sentence), sentence


def test_porting_doc_does_not_reintroduce_dead_pi_settings() -> None:
    assert (
        "skills[]` did **not** work" in PORTING or "skills[]` did not work" in PORTING
    )
    tail = PORTING.split("did not work", 1)[-1]
    assert "pi supports the equivalent: `settings.json` `skills[]`" not in tail


def test_readme_links_resolve() -> None:
    for match in re.findall(r"\]\(([^)]+)\)", README):
        if match.startswith("http"):
            continue
        path = match.split("#", 1)[0]
        if not path:
            continue
        assert (ROOT / path).exists(), path


def test_porting_doc_quotes_the_current_frontmatter() -> None:
    """The porting doc's frontmatter snippet must match SKILL.md, not an old release."""

    def field(text: str, key: str) -> str:
        m = re.search(rf"^\s*{key}: (.+)$", text, re.M)
        assert m, key
        return m.group(1).strip()

    for key in ("version", "description", "allowed-tools"):
        assert field(PORTING, key) == field(SKILL, key), key


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 — report every contract break
                failed += 1
                print(f"FAIL {name}: {exc}")
    sys.exit(1 if failed else 0)
