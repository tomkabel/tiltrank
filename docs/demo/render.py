#!/usr/bin/env python3
"""Generate the README hero from the committed payloads. Stdlib only.

Every rubric output line in the image is the real output of rubric.py on
docs/demo/payload-undetermined.json and docs/demo/payload.json; each one is a
`<text class="out1">` / `<text class="out2">` whose joined text (tspans
included) test_demo_contract.py checks verbatim. Colour is added per token,
never by changing the text. The prompts, ask cards and ADR excerpt are the
composed parts of the session.

    python3 docs/demo/render.py            # docs/demo.svg + docs/demo-light.svg
    python3 docs/demo/render.py --png      # ...and rasterize both (needs Chromium)
    python3 docs/demo/render.py --theme rose-pine-moon --out /tmp/x.svg --png

The PNGs are rasterized by headless Chromium, which honours the embedded
@font-face (rsvg-convert does not). Design notes: docs/demo/REDESIGN.md.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RUBRIC = ROOT / ".claude" / "skills" / "tiltrank" / "scripts" / "rubric.py"
FONTS = HERE / "fonts"

# Semantic roles; every colour in the image comes from one of these.
THEMES: dict[str, dict[str, str]] = {
    "vesper": {
        "backdrop0": "#2a2019",
        "backdrop1": "#0b0b0b",
        "bg": "#101010",
        "raised": "#181818",
        "border": "#2a2a2a",
        "dots": "#363636",
        "text": "#ededed",
        "dim": "#a0a0a0",
        "muted": "#7e7e7e",
        "accent": "#ffc799",
        "ok": "#99ffe4",
        "warn": "#ffc799",
        "bad": "#ff8080",
        "med": "#a0a0a0",
        "shadow": "0.6",
    },
    "vesper-light": {
        "backdrop0": "#f1e3d6",
        "backdrop1": "#e4e1dc",
        "bg": "#fcfbf9",
        "raised": "#f3f1ed",
        "border": "#dfdbd4",
        "dots": "#d4d0c9",
        "text": "#1c1b1a",
        "dim": "#55524e",
        "muted": "#6f6a64",
        "accent": "#a14d14",
        "ok": "#0b7059",
        "warn": "#a14d14",
        "bad": "#b02828",
        "med": "#55524e",
        "shadow": "0.18",
    },
    "rose-pine-moon": {
        "backdrop0": "#2f2b48",
        "backdrop1": "#161420",
        "bg": "#232136",
        "raised": "#2a273f",
        "border": "#44415a",
        "dots": "#44415a",
        "text": "#e0def4",
        "dim": "#9793b1",
        "muted": "#858099",
        "accent": "#c4a7e7",
        "ok": "#9ccfd8",
        "warn": "#f6c177",
        "bad": "#eb6f92",
        "med": "#f6c177",
        "shadow": "0.55",
    },
    "tokyo-night-storm": {
        "backdrop0": "#2f354f",
        "backdrop1": "#16161e",
        "bg": "#24283b",
        "raised": "#292e42",
        "border": "#3b4261",
        "dots": "#3b4261",
        "text": "#c0caf5",
        "dim": "#a9b1d6",
        "muted": "#8189b0",
        "accent": "#7aa2f7",
        "ok": "#9ece6a",
        "warn": "#e0af68",
        "bad": "#f7768e",
        "med": "#e0af68",
        "shadow": "0.55",
    },
}
TEXT_ROLES = ("text", "dim", "accent", "ok", "warn", "bad", "med")
SHIPPED = {"demo.svg": "vesper", "demo-light.svg": "vesper-light"}

FS, CW, LH = 14, 8.4, 22  # font size, JetBrains Mono advance (0.6 em), line height
PAD, IX, TB, GAP = 44, 30, 42, 16  # backdrop, window inset, title bar, block gap
OUT = 22  # tool output indent (right of the rail)


def run(payload: Path) -> list[str]:
    proc = subprocess.run(
        [sys.executable, str(RUBRIC)],
        input=payload.read_text(encoding="utf-8"),
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return proc.stdout.rstrip("\n").split("\n")


# --- rubric line tokens -------------------------------------------------------

WORD_ROLE = {
    "high": "ok",
    "med": "med",
    "low": "bad",
    "EXCLUDED": "bad",
    "Separated": "ok",
    "robust": "ok",
    "yes": "ok",
    "Undetermined": "warn",
    "ESCALATE": "warn",
    "missing-context": "warn",
}
CRITERIA = {"fit", "reversibility", "precedent", "evidence"}
BOLD = {"tiltrank:", "Separated", "Undetermined", "ESCALATE"}

Seg = tuple[str, str, bool]  # text, role, bold


def tokens(line: str) -> list[Seg]:
    """Colour a rubric line word by word; the joined text is the line itself."""
    base = "muted" if "EXCLUDED" in line else "text"
    segs: list[Seg] = []
    for tok in re.split(r"(\s+)", line):
        if not tok:
            continue
        if tok.isspace():
            role, bold = (segs[-1][1], segs[-1][2]) if segs else (base, False)
        else:
            if tok in WORD_ROLE:
                role = WORD_ROLE[tok]
            elif tok in CRITERIA or (tok.endswith(":") and tok != "tiltrank:"):
                role = "dim"
            elif tok in {"·", "—", "-", "--."} or re.fullmatch(r"\d+\.", tok):
                role = "muted"
            else:
                role = base
            bold = tok in BOLD
            if tok == "—":
                base = "dim"  # the rest is an explanation
        if segs and segs[-1][1:] == (role, bold):
            segs[-1] = (segs[-1][0] + tok, role, bold)
        else:
            segs.append((tok, role, bold))
    return segs


# --- svg primitives -----------------------------------------------------------


def text(t: dict, x: float, y: float, segs: list[Seg], cls: str = "", size=FS) -> str:
    """One line at baseline y. Spans are written back to back: no stray text."""
    attr = f' class="{cls}"' if cls else ""
    size_attr = f' font-size="{size}"' if size != FS else ""
    spans = []
    for s, role, bold in segs:
        weight = ' font-weight="600"' if bold else ""
        spans.append(f'<tspan fill="{t[role]}"{weight}>{escape(s)}</tspan>')
    return f'<text x="{x:g}" y="{y:g}"{attr}{size_attr}>{"".join(spans)}</text>'


def rect(x, y, w, h, rx, fill, stroke="", extra="") -> str:
    s = f' stroke="{stroke}"' if stroke else ""
    return (
        f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx:g}" '
        f'fill="{fill}"{s}{extra}/>'
    )


def width(s: str) -> float:
    return len(s) * CW


def base(y: float, h: float = LH) -> float:
    """Baseline that centres a FS line in a row of height h starting at y."""
    return round(y + h / 2 + FS * 0.36, 1)


# --- blocks: each returns (svg parts, height) ---------------------------------


def prompt(t, x, y, w, lines: list[str]):
    h = LH * len(lines) + 14
    parts = [rect(x - 12, y, w + 24, h, 8, t["raised"])]
    for i, line in enumerate(lines):
        by = base(y + 7 + LH * i)
        if i == 0:
            parts.append(text(t, x, by, [(">", "accent", True)], "user"))
        parts.append(text(t, x + 2 * CW, by, [(line, "text", False)], "user"))
    return parts, h


def tool(t, x, y, name: str, arg: str):
    parts = [
        f'<circle cx="{x + 4:g}" cy="{y + LH / 2:g}" r="4" fill="{t["ok"]}"/>',
        text(
            t,
            x + 18,
            base(y),
            [(name, "text", True), (f"({arg})", "dim", False)],
            "tool",
        ),
    ]
    return parts, LH


def output(t, x, y, cls: str, lines: list[str]):
    parts, cy = [], y + 4
    for line in lines:
        if not line:
            cy += LH // 2
            continue
        parts.append(text(t, x + OUT, base(cy), tokens(line), cls))
        cy += LH
    h = cy - y
    rail = (
        f'<path d="M{x + 4:g} {y - 4:g} V{y + h - 10:g}" stroke="{t["border"]}" '
        'stroke-width="2" stroke-linecap="round"/>'
    )
    return [rail, *parts], h


def call(t, x, y, name: str, arg: str, cls: str, lines: list[str]):
    """A tool call with its output hanging off the rail below it."""
    head, h1 = tool(t, x, y, name, arg)
    body, h2 = output(t, x, y + h1 + 2, cls, lines)
    return head + body, h1 + 2 + h2


def card_frame(t, x, y, w, h):
    return rect(x, y, w, h, 10, t["raised"], t["border"])


def ask_questions(t, x, y, w, title: list[Seg], questions):
    p = 16
    parts, cy = [], y + p
    parts.append(text(t, x + p, base(cy), title, "composed"))
    cy += LH + 8
    for q, options in questions:
        parts.append(text(t, x + p, base(cy), [(q, "text", False)], "composed"))
        cy += LH + 4
        cx = x + p
        for opt in options:
            cw = 30 + width(opt) + 14
            parts.append(rect(cx, cy, cw, 28, 14, t["bg"], t["border"]))
            parts.append(
                f'<circle cx="{cx + 16:g}" cy="{cy + 14:g}" r="4.5" fill="none" '
                f'stroke="{t["muted"]}" stroke-width="1.5"/>'
            )
            parts.append(
                text(t, cx + 30, base(cy, 28), [(opt, "dim", False)], "composed")
            )
            cx += cw + 8
        cy += 28 + 12
    h = cy - y + p - 12
    return [card_frame(t, x, y, w, h), *parts], h


def ask_pick(t, x, y, w, title: list[Seg], note: list[Seg], options):
    """options: (label, description, recommended)."""
    p, row = 16, 32
    pill = "Recommended"
    pill_w = width(pill) * 11 / FS + 16
    label_w = max(width(lbl) + (pill_w + 10 if rec else 0) for lbl, _, rec in options)
    desc_x = x + p + 28 + label_w + 28
    parts, cy = [], y + p
    parts.append(text(t, x + p, base(cy), title, "composed"))
    cy += LH
    parts.append(text(t, x + p, base(cy), note, "composed"))
    cy += LH + 8
    for label, desc, rec in options:
        mx = x + p + 10
        if rec:
            parts.append(
                rect(
                    x + 6, cy, w - 12, row, 7, t["accent"], extra=' fill-opacity="0.09"'
                )
            )
            parts.append(rect(x + 6, cy + 6, 3, row - 12, 1.5, t["accent"]))
            parts.append(
                f'<circle cx="{mx:g}" cy="{cy + row / 2:g}" r="5" fill="{t["accent"]}"/>'
            )
        else:
            parts.append(
                f'<circle cx="{mx:g}" cy="{cy + row / 2:g}" r="4.5" fill="none" '
                f'stroke="{t["muted"]}" stroke-width="1.5"/>'
            )
        lx = x + p + 28
        role = "accent" if rec else ("text" if desc else "dim")
        parts.append(text(t, lx, base(cy, row), [(label, role, rec)], "composed"))
        if rec:
            px = lx + width(label) + 10
            parts.append(
                rect(px, cy + 7, pill_w, row - 14, (row - 14) / 2, "none", t["accent"])
            )
            parts.append(
                text(
                    t,
                    px + 8,
                    base(cy, row) - 1,
                    [(pill, "accent", False)],
                    "composed",
                    size=11,
                )
            )
        if desc:
            parts.append(
                text(t, desc_x, base(cy, row), [(desc, "dim", False)], "composed")
            )
        cy += row
    h = cy - y + p - 4
    return [card_frame(t, x, y, w, h), *parts], h


def document(t, x, y, w, lines: list[str]):
    p = 16
    parts, cy = [], y + p - 2
    for line in lines:
        if line.startswith("## "):
            if cy > y + p:
                cy += 6
            segs = [("## ", "muted", False), (line[3:], "accent", True)]
        else:
            segs = []
            for chunk in re.split(r'("[^"]*")', line):
                if chunk:
                    segs.append(
                        (chunk, "ok" if chunk.startswith('"') else "text", False)
                    )
        parts.append(text(t, x + p, base(cy), segs, "composed"))
        cy += LH
    h = cy - y + p - 2
    return [card_frame(t, x, y, w, h), *parts], h


# --- the session --------------------------------------------------------------


def font_face() -> str:
    faces = []
    for weight, name in ((400, "Regular"), (600, "SemiBold")):
        data = (FONTS / f"JetBrainsMono-{name}.subset.woff2").read_bytes()
        faces.append(
            "@font-face{font-family:'TR Mono';font-weight:%d;"
            "src:url(data:font/woff2;base64,%s) format('woff2')}"
            % (weight, base64.b64encode(data).decode("ascii"))
        )
    return "".join(faces)


def build(t: dict) -> str:
    q = json.loads((HERE / "payload.json").read_text(encoding="utf-8"))["question"]
    out1 = [
        ln
        for ln in run(HERE / "payload-undetermined.json")
        if not ln.startswith("NOTE:")
    ]
    out2 = [ln for ln in run(HERE / "payload.json") if not ln.startswith("NOTE:")]
    rubric_call = "python3 ${CLAUDE_SKILL_DIR}/scripts/rubric.py <<'JSON' …"

    longest = max(width(ln) for ln in out1 + out2) + OUT
    inner = max(longest, 760)
    win_w = inner + 2 * IX
    canvas_w = win_w + 2 * PAD
    x = PAD + IX
    y = PAD + TB + 22

    blocks = [
        lambda y: prompt(
            t,
            x,
            y,
            inner,
            [q, "Candidates: Signed cookies, Postgres table, Redis, Managed auth SaaS"],
        ),
        lambda y: call(t, x, y, "Bash", rubric_call, "out1", out1),
        lambda y: ask_questions(
            t,
            x,
            y,
            inner,
            [
                ("Can't rank these yet.", "text", True),
                (" Two questions first.", "dim", False),
            ],
            [
                (
                    "How many instances of the admin tool run?",
                    ["One instance", "Several replicas", "Don't know yet"],
                ),
                (
                    "Is a logout for everyone on each deploy acceptable?",
                    ["Logout on deploy is fine", "Sessions must survive deploys"],
                ),
            ],
        ),
        lambda y: prompt(t, x, y, inner, ["One instance. Logout on deploy is fine."]),
        lambda y: call(t, x, y, "Bash", rubric_call, "out2", out2),
        lambda y: ask_pick(
            t,
            x,
            y,
            inner,
            [
                ("Which session store?", "text", True),
                (" Lead holds on every single rating.", "dim", False),
            ],
            [
                ("Excluded:", "bad", False),
                (" Managed auth SaaS (must be self-hosted).", "dim", False),
            ],
            [
                ("Signed cookies", "nothing to operate; cookie size cap", True),
                ("Redis", "shared store you do not need yet", False),
                ("Postgres table", "a table plus a reaper job", False),
                ("Other", "", False),
            ],
        ),
        lambda y: prompt(t, x, y, inner, ["Signed cookies"]),
        lambda y: tool(t, x, y, "Write", "docs/decisions/0001-admin-session-store.md"),
        lambda y: document(
            t,
            x,
            y,
            inner,
            [
                "## Decision",
                "Signed cookies, as recommended. Requirements quoted from the user:",
                '"It has to be self-hosted", "One instance", "Logout on deploy is fine".',
                "## What would make this wrong",
                "A second instance that must share sessions, or a session larger than 4 KB.",
            ],
        ),
    ]
    body: list[str] = []
    for i, block in enumerate(blocks):
        parts, h = block(y)
        body += parts
        y += h + (GAP if i + 1 < len(blocks) else 0)

    win_h = y + 26 - PAD
    canvas_h = win_h + 2 * PAD
    wx, wy = PAD, PAD
    title = "admin-tool — claude"
    chrome = [
        rect(wx, wy, win_w, win_h, 12, t["bg"], t["border"], ' filter="url(#shadow)"'),
        *(
            f'<circle cx="{wx + 22 + 20 * i:g}" cy="{wy + TB / 2:g}" r="6" fill="{t["dots"]}"/>'
            for i in range(3)
        ),
        text(
            t,
            wx + win_w / 2 - width(title) * 12 / FS / 2,
            base(wy, TB) - 1,
            [(title, "dim", False)],
            size=12,
        ),
        f'<path d="M{wx:g} {wy + TB:g} H{wx + win_w:g}" stroke="{t["border"]}"/>',
    ]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w:g}" '
            f'height="{canvas_h:g}" viewBox="0 0 {canvas_w:g} {canvas_h:g}" '
            "font-family=\"'TR Mono', 'JetBrains Mono', ui-monospace, monospace\" "
            f'font-size="{FS}" xml:space="preserve">',
            f"<style>{font_face()}text{{white-space:pre}}</style>",
            "<defs>",
            '<linearGradient id="backdrop" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{t["backdrop0"]}"/>'
            f'<stop offset="1" stop-color="{t["backdrop1"]}"/></linearGradient>',
            '<filter id="shadow" x="-10%" y="-10%" width="120%" height="125%">'
            '<feDropShadow dx="0" dy="18" stdDeviation="22" flood-color="#000" '
            f'flood-opacity="{t["shadow"]}"/></filter>',
            "</defs>",
            rect(0, 0, canvas_w, canvas_h, 18, "url(#backdrop)"),
            *chrome,
            *body,
            "</svg>",
            "",
        ]
    )


def rasterize(svg: Path, png: Path) -> None:
    browser = next(
        (
            b
            for b in ("chromium", "chromium-browser", "google-chrome")
            if shutil.which(b)
        ),
        None,
    )
    if browser is None:
        sys.exit("--png needs Chromium on PATH")
    head = svg.read_text(encoding="utf-8")[:400]
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head)
    assert m, f"no viewBox in {svg}"
    w, h = float(m[1]), float(m[2])
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [
                browser,
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--user-data-dir={profile}",
                "--default-background-color=00000000",
                "--force-device-scale-factor=2",
                f"--window-size={round(w)},{round(h)}",
                f"--screenshot={png}",
                svg.resolve().as_uri(),
            ],
            check=True,
            capture_output=True,
        )
    # 256 colours, no dither: ~4x smaller at PSNR ~54 dB; banding only shows
    # in the backdrop under a 4x contrast stretch.
    if shutil.which("magick"):
        subprocess.run(
            ["magick", str(png), "-strip", "-dither", "None", "-colors", "256"]
            + ["-define", "png:compression-level=9", str(png)],
            check=True,
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the README hero.")
    ap.add_argument("--theme", choices=sorted(THEMES), help="render one theme")
    ap.add_argument("--out", type=Path, help="output path for --theme")
    ap.add_argument("--png", action="store_true", help="also rasterize at 2x")
    args = ap.parse_args()
    if args.theme:
        jobs = [(args.out or Path(f"/tmp/hero-{args.theme}.svg"), args.theme)]
    else:
        jobs = [(ROOT / "docs" / name, theme) for name, theme in SHIPPED.items()]
    for path, theme in jobs:
        path.write_text(build(THEMES[theme]), encoding="utf-8")
        print(f"wrote {path} ({theme})")
        if args.png:
            rasterize(path, path.with_suffix(".png"))
            print(f"wrote {path.with_suffix('.png')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
