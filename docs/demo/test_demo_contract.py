#!/usr/bin/env python3
"""The README hero must not be hand-edited again.

Every `class="out1"` / `class="out2"` line in docs/demo.svg and
docs/demo-light.svg must be rubric.py's real output on the committed payloads,
whitespace included, none may be missing, no total may appear anywhere, and
every theme colour must pass WCAG contrast. Re-render with `python3 docs/demo/render.py` after an engine change.

    python3 docs/demo/test_demo_contract.py
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render import HERE as DEMO_DIR  # noqa: E402
from render import ROOT, SHIPPED, TEXT_ROLES, THEMES, run  # noqa: E402

SVGS = [ROOT / "docs" / name for name in SHIPPED]
NS = "{http://www.w3.org/2000/svg}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
RUNS = (("out1", "payload-undetermined.json"), ("out2", "payload.json"))


def svg_lines(svg: Path, strip: bool = True) -> dict[str, list[str]]:
    """Joined text of every <text>, tspans included, grouped by class."""
    out: dict[str, list[str]] = {}
    for node in ET.parse(svg).iter(f"{NS}text"):
        joined = "".join(node.itertext())
        out.setdefault(node.get("class", ""), []).append(
            joined.strip() if strip else joined
        )
    return out


def real_visible(payload: str) -> list[str]:
    return [
        line
        for line in run(DEMO_DIR / payload)
        if line and not line.startswith("NOTE:")
    ]


def test_rubric_lines_in_the_image_are_real() -> None:
    for svg in SVGS:
        shown = svg_lines(svg)
        for cls, payload in RUNS:
            real = [line.strip() for line in run(DEMO_DIR / payload)]
            assert shown.get(cls), f"no {cls} lines in {svg}"
            for line in shown[cls]:
                assert line in real, (
                    f"{svg.name} {cls}: shows a line rubric.py never printed: {line!r}"
                )
            missing = [
                line.strip()
                for line in real_visible(payload)
                if line.strip() not in shown[cls]
            ]
            assert not missing, f"{svg.name} {cls}: rubric output missing: {missing}"


def test_rubric_whitespace_survives_verbatim() -> None:
    # rsvg ignores CSS white-space and Chromium ignores xml:space, so both are
    # needed, and the unstripped text must equal the rubric line byte for byte.
    for svg in SVGS:
        root = ET.parse(svg).getroot()
        assert root.get(XML_SPACE) == "preserve", f"{svg.name}: no xml:space"
        assert "white-space:pre" in svg.read_text(encoding="utf-8"), svg.name
        shown = svg_lines(svg, strip=False)
        for cls, payload in RUNS:
            assert shown[cls] == real_visible(payload), (
                f"{svg.name} {cls}: text differs from rubric.py output"
            )


def _luminance(hex_colour: str) -> float:
    rgb = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg: str, bg: str) -> float:
    hi, lo = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_every_text_colour_is_legible() -> None:
    # WCAG AA: 4.5:1 for text roles, 3:1 for separators and chrome text.
    bad = []
    for name, t in THEMES.items():
        for surface in ("bg", "raised"):
            for role in TEXT_ROLES:
                if contrast(t[role], t[surface]) < 4.5:
                    bad.append(
                        f"{name}.{role} on {surface}: {contrast(t[role], t[surface]):.2f}"
                    )
            if contrast(t["muted"], t[surface]) < 3:
                bad.append(
                    f"{name}.muted on {surface}: {contrast(t['muted'], t[surface]):.2f}"
                )
    assert not bad, "low contrast: " + "; ".join(bad)


def test_image_shows_no_total() -> None:
    for svg in SVGS:
        text = " ".join(line for lines in svg_lines(svg).values() for line in lines)
        assert not re.search(r"\bscore\s+\d", text), f"{svg.name}: shows a total"
        assert not re.search(r"\d\s*%|\d+/100\b", text), (
            f"{svg.name}: shows a percentage"
        )


def test_readme_embeds_the_generated_image() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if 'src="docs/demo.svg"' in readme:
        return
    # A raster hero is allowed only alongside the generated SVG it is
    # rasterized from, with the tie to render.py recorded in the README;
    # anything else is a hand-edited image again.
    assert 'src="docs/demo.png"' in readme, "README embeds no generated hero"
    assert "docs/demo.svg" in readme and "render.py" in readme, (
        "docs/demo.png must stay tied to the contract-checked docs/demo.svg"
    )
    # The light-mode variant, if offered, must be the other shipped raster.
    for src in re.findall(r'srcset="(docs/demo[^"]*)"', readme):
        assert Path(src).with_suffix(".svg").name in SHIPPED, f"untracked hero {src}"


def run_all() -> None:
    tests = [
        v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)
    ]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {type(exc).__name__}: {str(exc)[:300]}")
    if failed:
        print(f"demo contract: {len(failed)}/{len(tests)} tests failed")
        sys.exit(1)
    print(f"demo contract: {len(tests)} tests passed")


if __name__ == "__main__":
    run_all()
