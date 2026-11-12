#!/usr/bin/env python3
"""The README hero must not be hand-edited again.

Every `class="out1"` / `class="out2"` line in docs/demo.svg must appear
verbatim in rubric.py's real output on the committed payloads, no rubric
output line may be missing from the image, and no total may appear anywhere
in it. Re-render with `python3 docs/demo/render.py` after an engine change.

    python3 docs/demo/test_demo_contract.py
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render import HERE as DEMO_DIR, ROOT, run  # noqa: E402

SVG = ROOT / "docs" / "demo.svg"
NS = "{http://www.w3.org/2000/svg}"


def svg_lines() -> dict[str, list[str]]:
    tree = ET.parse(SVG)
    out: dict[str, list[str]] = {}
    for node in tree.iter(f"{NS}text"):
        out.setdefault(node.get("class", ""), []).append((node.text or "").strip())
    return out


def test_rubric_lines_in_the_image_are_real() -> None:
    shown = svg_lines()
    for cls, payload in (
        ("out1", "payload-undetermined.json"),
        ("out2", "payload.json"),
    ):
        real = [line.strip() for line in run(DEMO_DIR / payload)]
        real_visible = [line for line in real if line and not line.startswith("NOTE:")]
        assert shown.get(cls), f"no {cls} lines in {SVG}"
        for line in shown[cls]:
            assert line in real, (
                f"{cls}: image shows a line rubric.py never printed: {line!r}"
            )
        missing = [line for line in real_visible if line not in shown[cls]]
        assert not missing, f"{cls}: rubric output missing from the image: {missing}"


def test_image_shows_no_total() -> None:
    text = " ".join(line for lines in svg_lines().values() for line in lines)
    assert not re.search(r"\bscore\s+\d", text), "a total is shown in the hero"
    assert not re.search(r"\d\s*%|\d+/100\b", text), "a percentage is shown in the hero"


def test_readme_embeds_the_generated_image() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert 'src="docs/demo.svg"' in readme


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
