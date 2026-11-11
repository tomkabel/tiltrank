#!/usr/bin/env python3
"""Generate docs/demo.svg from the committed payloads. Stdlib only.

Every rubric output line in the image is the real output of rubric.py on
docs/demo/payload-undetermined.json and docs/demo/payload.json; the lines are
tagged `class="out1"` / `class="out2"` so test_demo_contract.py can check them
verbatim. The ask boxes, the user's answers and the ADR excerpt are the
composed parts of the session and are tagged `class="composed"`.

    python3 docs/demo/render.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RUBRIC = ROOT / ".claude" / "skills" / "tiltrank" / "scripts" / "rubric.py"


def run(payload: Path) -> list[str]:
    proc = subprocess.run(
        [sys.executable, str(RUBRIC)],
        input=payload.read_text(encoding="utf-8"),
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return proc.stdout.rstrip("\n").split("\n")


def main() -> int:
    q = json.loads((HERE / "payload.json").read_text(encoding="utf-8"))["question"]
    out1 = run(HERE / "payload-undetermined.json")
    out2 = run(HERE / "payload.json")
    lines: list[tuple[str, str]] = [
        ("user", f"> {q}"),
        (
            "user",
            "  Candidates: Signed cookies, Postgres table, Redis, Managed auth SaaS",
        ),
        ("", ""),
        ("tool", "⏺ Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/rubric.py <<'JSON' …)"),
        *[("out1", f"  {line}") for line in out1 if not line.startswith("NOTE:")],
        ("", ""),
        (
            "composed",
            "┌ Can't rank these yet. Two questions first: ──────────────────────────┐",
        ),
        (
            "composed",
            "│ How many instances of the admin tool run?                             │",
        ),
        (
            "composed",
            "│   ○ One instance   ○ Several replicas   ○ Don't know yet              │",
        ),
        (
            "composed",
            "│ Is a logout for everyone on each deploy acceptable?                   │",
        ),
        (
            "composed",
            "│   ○ Logout on deploy is fine   ○ Sessions must survive deploys        │",
        ),
        (
            "composed",
            "└───────────────────────────────────────────────────────────────────────┘",
        ),
        ("user", "> One instance. Logout on deploy is fine."),
        ("", ""),
        ("tool", "⏺ Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/rubric.py <<'JSON' …)"),
        *[("out2", f"  {line}") for line in out2 if not line.startswith("NOTE:")],
        ("", ""),
        (
            "composed",
            "┌ Which session store? Lead holds on every single rating. ──────────────┐",
        ),
        (
            "composed",
            "│ Excluded: Managed auth SaaS (must be self-hosted).                    │",
        ),
        (
            "composed",
            "│ ● Signed cookies (Recommended)  nothing to operate; cookie size cap   │",
        ),
        (
            "composed",
            "│ ○ Redis                         shared store you do not need yet      │",
        ),
        (
            "composed",
            "│ ○ Postgres table                a table plus a reaper job             │",
        ),
        (
            "composed",
            "│ ○ Other                                                               │",
        ),
        (
            "composed",
            "└───────────────────────────────────────────────────────────────────────┘",
        ),
        ("user", "> Signed cookies"),
        ("", ""),
        ("tool", "⏺ Write(docs/decisions/0001-admin-session-store.md)"),
        ("composed", "  ## Decision"),
        (
            "composed",
            "  Signed cookies, as recommended. Requirements quoted from the user:",
        ),
        (
            "composed",
            '  "It has to be self-hosted", "One instance", "Logout on deploy is fine".',
        ),
        ("composed", "  ## What would make this wrong"),
        (
            "composed",
            "  A second instance that must share sessions, or a session larger than 4 KB.",
        ),
    ]
    colours = {
        "user": "#e6edf3",
        "tool": "#8b949e",
        "out1": "#c9d1d9",
        "out2": "#c9d1d9",
        "composed": "#7ee787",
    }
    line_h, pad, width = 18, 20, 900
    height = pad * 2 + line_h * len(lines)
    body = []
    for i, (cls, text) in enumerate(lines):
        y = pad + line_h * (i + 1)
        if not text:
            continue
        colour = colours.get(cls, "#c9d1d9")
        attr = f' class="{cls}"' if cls else ""
        body.append(
            f'<text x="{pad}" y="{y}" fill="{colour}"{attr}>{escape(text)}</text>'
        )
    svg = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" '
            'font-size="13">',
            f'<rect width="{width}" height="{height}" rx="8" fill="#0d1117"/>',
            "<style>text{white-space:pre}</style>",
            *body,
            "</svg>",
            "",
        ]
    )
    (ROOT / "docs" / "demo.svg").write_text(svg, encoding="utf-8")
    print(f"wrote docs/demo.svg ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
