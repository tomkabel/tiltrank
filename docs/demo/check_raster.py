#!/usr/bin/env python3
"""Outside judge for the hero PNGs: can a machine read them at README size?

Downscales each PNG to the width GitHub shows (900 px) and to a phone
(400 CSS px at 2x = 800 device px; at 1x no hero is readable, the old one
included), re-enlarges 3x without adding detail, runs tesseract, and reports
per rubric line the character error rate of the best-matching OCR line.
Also reports file size and aspect ratio. Needs `magick` and `tesseract`
(with eng.traineddata, falling back to ~/.cache/tessdata); not run in CI.

    python3 docs/demo/check_raster.py [png ...]

Pass: at 900 px >= 98% of rubric lines at CER <= 2%; at phone width the band
verdict and the pick are readable; PNG <= 400 KB.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import HERE, ROOT, run  # noqa: E402


def norm(s: str) -> str:
    # tesseract reads the middle dot and dashes as "-": fold them on both
    # sides so the judge scores legibility, not tesseract's glyph set
    s = s.replace("·", "-").replace("—", "-").replace("…", "...")
    return re.sub(r"\s+", " ", s).strip()


def cer(ref: str, hyp: str) -> float:
    prev = list(range(len(hyp) + 1))
    for i, a in enumerate(ref, 1):
        cur = [i]
        for j, b in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a != b)))
        prev = cur
    return prev[-1] / max(len(ref), 1)


TESSDATA = Path.home() / ".cache" / "tessdata"  # eng.traineddata if the system lacks it
ENV = (
    {**os.environ, "TESSDATA_PREFIX": str(TESSDATA)}
    if "TESSDATA_PREFIX" not in os.environ and (TESSDATA / "eng.traineddata").exists()
    else None
)


def ocr(png: Path, width: int) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        small = Path(tmp) / "s.png"
        subprocess.run(
            ["magick", str(png), "-resize", f"{width}x", "-resize", "300%", str(small)],
            check=True,
        )
        out = subprocess.run(
            ["tesseract", str(small), "-", "--psm", "6"],
            capture_output=True,
            encoding="utf-8",
            check=True,
            env=ENV,
        ).stdout
    return [norm(line) for line in out.splitlines() if line.strip()]


def best(ref: str, lines: list[str]) -> float:
    # an OCR line may hold extra glyphs (rails, markers): score the closest
    # window of the OCR line, not the whole line
    scores = []
    for line in lines:
        for start in range(0, max(1, len(line) - len(ref)) + 1, 1):
            scores.append(cer(ref, line[start : start + len(ref)]))
            if scores[-1] == 0:
                return 0.0
    return min(scores, default=1.0)


def main(paths: list[str]) -> int:
    rubric = [
        norm(line)
        for payload in ("payload-undetermined.json", "payload.json")
        for line in run(HERE / payload)
        if line.strip() and not line.startswith("NOTE:")
    ]
    pngs = [Path(p) for p in paths] or [
        ROOT / "docs" / "demo.png",
        ROOT / "docs" / "demo-light.png",
    ]
    ok = True
    for png in pngs:
        w, h = (
            int(v)
            for v in subprocess.run(
                ["magick", "identify", "-format", "%w %h", str(png)],
                capture_output=True,
                encoding="utf-8",
                check=True,
            ).stdout.split()
        )
        kb = png.stat().st_size / 1024
        print(f"{png.name}: {w}x{h}, aspect {h / w:.2f}, {kb:.0f} KB")
        ok &= kb <= 400
        for width in (900, 800):
            lines = ocr(png, width)
            errs = [best(ref, lines) for ref in rubric]
            good = sum(e <= 0.02 for e in errs)
            print(
                f"  {width:>3} px: {good}/{len(rubric)} rubric lines at CER<=2% "
                f"({good / len(rubric):.0%}), mean CER {sum(errs) / len(errs):.1%}"
            )
            if width == 900:
                ok &= good / len(rubric) >= 0.98
                for ref, e in zip(rubric, errs):
                    if e > 0.02:
                        print(f"      CER {e:.0%}: {ref}")
            else:
                text = " ".join(lines)
                key = all(k in text for k in ("Separated", "Signed cookies"))
                print(f"      band verdict and pick readable: {key}")
                ok &= key
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
