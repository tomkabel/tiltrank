# Hero redesign plan

Goal beyond the goal: a visitor who lands on the README understands in about
five seconds what tiltrank does (gate, rank, measure stability, ask, record).
They trust that the screenshot is real, and it looks like something a careful
tool would ship. The redesign starts from a new terminal theme and does not
restyle the current image.

## 1. What is wrong now (measured, not taste)

| Defect | Cause | Evidence |
|---|---|---|
| Ask-box right borders are ragged and the option columns collapse | `rsvg-convert` ignores CSS `white-space:pre`, so runs of spaces collapse to one | `docs/demo.png`: `│ How many instances … run? │` ends early. rubric.py prints `Signed cookies␣␣fit`, and the PNG shows a single space |
| The font is whatever fontconfig picks | `ui-monospace, SFMono-Regular, Menlo` doesn't exist on Linux, and no font is embedded | the PNG is in Noto Sans Mono, which nobody chose |
| One accent colour for everything "composed" | `colours` is a five-entry dict keyed by line class, with no per-token colour | box chrome, answers and the ADR are all `#7ee787` |
| No hierarchy between the four beats (run 1, ask, run 2, ask, record) | flat line list with blank-line separators | 50 lines, 1800×1844 px, nearly square, no landmarks |
| Box-drawing glyphs fake a UI | ASCII boxes stand in for the harness ask tool | they look like a mock, which undercuts "this is real" |
| No terminal chrome or framing | a bare `rect rx=8` | it reads as a pasted text dump, not a session |

## 2. Constraints the new design must keep

1. **Truth contract.** Every `out1`/`out2` line must stay verbatim rubric.py
   output, all of it must be shown, and no totals or percentages
   (`test_demo_contract.py`). Colour can be added per token, but no text may
   be changed or dropped.
2. **Stdlib-only `render.py`.** Fonts, rasterizing and QA run as external
   binaries through subprocess or as a documented manual step. Nothing gets
   imported.
3. **The PNG stays a derivative of the SVG.** The SVG is the checked source
   and the PNG is a byte-for-byte raster of it.
4. **It's displayed at 900 CSS px on GitHub** (`width="900"`) and at about
   350–400 px on mobile.

## 3. Design direction: new theme, from scratch

### 3.1 Theme template: pick by rendering, not by reading

Shortlist three established, well-tuned dark themes with different
personalities, and render the full hero in each:

| Candidate | Personality | Why it fits |
|---|---|---|
| **Vesper** (Rauno Freiberg) | near-black, grey-dominant, one warm peach accent | the most restrained of the three. Signals taste through restraint, and one accent maps to "the recommendation" |
| **Rosé Pine Moon** | muted violet base, soft pastels | warm and calm. Has distinct `love`/`gold`/`foam` hues for the excluded, med and high states |
| **Tokyo Night Storm** | blue-slate base, saturated accents | familiar to developers. The highest contrast of the three, and the safest when downscaled |

Recommendation: **Vesper-derived**. Other READMEs mostly use the GitHub-dark
palette, and the current hero does too. A greyscale UI with one accent is the
look that reads "polished". It also lets colour carry meaning (the pick, the
exclusion) instead of decoration.

Derive the final palette in **OKLCH**: one hue for the accent and a fixed
lightness ramp for text tiers (primary L≈0.93, secondary L≈0.72, muted
L≈0.55). Contrast is tuned on lightness, not by eye. Keep semantic roles in one
dict at the top of `render.py`, never inline hex:

```
bg, bg_raised, border, text, text_dim, text_muted,
accent (the pick / recommended), ok (high), warn (med), bad (excluded/low),
prompt (user ">"), tool (⏺ tool calls)
```

### 3.2 Typography

- **JetBrains Mono** (OFL, installed locally). 14 px, line-height 1.55
  (≈22 px), weight 400 for body text, 600 for the band verdict and the chosen
  option.
- **Embed a subset** of the font in the SVG as base64 WOFF2 in
  `@font-face`, so the SVG renders identically everywhere. Subsetting needs
  `pyftsubset` (fonttools). Run it **once as a manual step** and commit the
  subset as `docs/demo/font.woff2`. `render.py` only base64-reads the file
  (stdlib). Coverage: ASCII + `·—…⏺●○│┌└─✓✗`.
- `xml:space="preserve"` on every `<text>`. Unlike the CSS property, rsvg
  honours this attribute, and it fixes defect #1 at the root.

### 3.3 Composition: a story in four beats

The hero becomes a framed window on a soft backdrop, not a text dump.

```
 ┌─ backdrop: subtle radial gradient, 48 px padding ─────────────────────┐
 │  ╭─ window ─────────────────────────────────────────────────────╮     │
 │  │ ● ● ●           claude — ~/admin-tool                        │     │
 │  ├──────────────────────────────────────────────────────────────┤     │
 │  │ > Which session store …                                      │     │
 │  │ ⏺ rubric.py                                                  │     │
 │  │   tiltrank: 3 unranked · 1 excluded · Undetermined           │ ① gate
 │  │   …                                                          │     │
 │  │ ╭ ask card ─────────────────────────╮                        │ ② ask
 │  │ ╰───────────────────────────────────╯                        │     │
 │  │ ⏺ rubric.py                                                  │ ③ rank
 │  │ ╭ ask card (● Signed cookies  Recommended) ╮                 │ ④ pick
 │  │ ⏺ Write(docs/decisions/0001-…)                               │ ⑤ record
 │  ╰──────────────────────────────────────────────────────────────╯     │
 └───────────────────────────────────────────────────────────────────────┘
```

- **Window chrome**: three muted traffic-light dots and a centred title in
  `text_muted`, with a 1 px `border` hairline under the title bar. Corner
  radius 12, plus a soft drop shadow (`feDropShadow`, which rsvg supports).
- **Ask cards drawn as SVG shapes** (`rect rx=8`, `bg_raised` fill, 1 px
  border), not box-drawing glyphs. Options get a tab-stop column so their
  descriptions align. The recommended option gets an accent left bar and a
  `Recommended` pill, and the chosen answer gets a check. This mirrors how the
  harness ask tool actually looks, instead of faking it in ASCII.
- **Per-token colour in rubric lines** with `<tspan>`. The text is unchanged
  and the contract test is untouched:
  - `high`/`med`/`low` → ok/warn/bad hues (one lightness, three hues, so the
    colours stay distinct for colour-blind readers)
  - `EXCLUDED — fails: …` → `bad`, with the `--.` row dimmed to `text_muted`
  - `band: Separated` / `Undetermined` and `ESCALATE` → weight 600, accent or
    warn
  - criterion names → `text_dim`, values → `text`
- **Beat rail (optional, decide at review)**: small numbered markers in the
  right margin, outside the window: gate, ask, rank, pick, record. They do the
  work of a caption without adding prose to the README.
- **Vertical rhythm**: 12 px between beats instead of empty text rows, with
  the user prompts (`>`) in `prompt` colour and bold. A thin divider separates
  the two runs.

### 3.4 Size and legibility budget

- Canvas 1000 × ≤1100 user units, rasterized at 2× (2000 px wide). At 900 CSS
  px the body text renders at ≥12.5 px.
- Line count: the 50 rows today drop to about 42 visual rows once the boxes
  become cards and the spacer rows go. The longest rubric line
  (`separation: robust — …`, 98 chars) sets the window width. At 14 px
  JetBrains Mono (8.4 px advance) that's ≈825 units plus padding, so it fits
  in 1000.

### 3.5 Light mode

Ship `demo-dark.png` and `demo-light.png` behind `<picture>` with
`prefers-color-scheme`. The light palette comes from the same OKLCH roles with
lightness inverted, not a second hand-picked theme. `render.py --theme
light|dark`. Update `test_readme_embeds_the_generated_image` to accept the
`<picture>` form.

## 4. Implementation steps

1. **Theme bake-off.** Add a `THEMES` dict with the three candidates, all
   mapped onto the role names. `render.py --theme <name> --out <path>`
   renders each candidate to `/tmp/hero-<name>.svg/png`. Nothing gets
   committed.
2. **Fix the raster pipeline first, in the old style.** Add
   `xml:space="preserve"` and an explicit font family, then re-rasterize. This
   isolates the pipeline fix from the design change: the old design with
   correct spacing is the baseline the new one has to beat.
3. **Font**: subset JetBrains Mono to `docs/demo/font.woff2` (one-off
   `pyftsubset` via `uvx --from fonttools pyftsubset …`). Embed it with
   `base64` from the stdlib.
4. **Layout engine in `render.py`**: replace the flat `lines` list with a list
   of blocks (`prompt`, `tool`, `output(run)`, `ask(card)`, `write(adr)`),
   each of which returns its SVG fragment and height. Keep it to one file and
   plain functions, no classes.
5. **Tokenizer for rubric lines**: a regex that splits on ` · ` and the known
   keywords and wraps each token in a `<tspan>`. It is purely presentational.
6. **Contract test**: change `(node.text or "")` to `"".join(node.itertext())`
   so tspans don't hide text from the check. Add the new checks from §5.
7. **README**: switch to `<picture>` (dark/light), update the regenerate
   comment, and update the alt text if the story changes.
8. **Rasterize** both themes with `rsvg-convert -w 2000`. If rsvg mishandles
   the WOFF2 `@font-face`, rasterize with headless Chromium instead
   (`chromium --headless --screenshot --window-size=…
   --force-device-scale-factor=2`). Chromium is installed, and Playwright's
   chromium-1243 is cached.

## 5. Outside judges: what counts as a pass

Nothing here is graded by the author's eye alone.

| Judge | Pass |
|---|---|
| `test_demo_contract.py` (existing) | green. Every rubric line is still verbatim, with no totals or percentages |
| **Contrast check** (new test, stdlib WCAG relative-luminance maths over the theme dict) | every text role ≥ 4.5:1 against `bg` and `bg_raised`, `text_muted` ≥ 3:1. Both themes |
| **Whitespace fidelity** (new test) | for each `out*` `<text>`, `xml:space="preserve"` is set and the joined text equals the rubric line with internal double spaces intact |
| **OCR legibility at README scale** (`tesseract`, manual/CI-optional) | downscale the PNG to 900 px and to 400 px wide and OCR it. At 900 px, ≥ 98% of the rubric lines are recovered at character error rate ≤ 2%. At 400 px, the band verdict and the pick are recovered |
| **Alignment probe** (PIL/magick, manual) | the right edges of the ask cards are one straight column (they're shapes now, so this is trivially true), and the option-description column x-positions are equal |
| **Blind A/B** | the old (whitespace-fixed) baseline against the three theme candidates, unlabelled, in shuffled order, shown to the user and two or three other people. The winner has to beat the baseline by a majority |
| **Size budget** | PNG ≤ 400 KB (run `magick … -strip -define png:compression-level=9`) and height ≤ 1.15 × width |

## 6. What it needs

| Item | Status |
|---|---|
| `rsvg-convert`, `magick`, `tesseract`, Chromium (+ Playwright chromium-1243) | present |
| JetBrains Mono font | present locally (OFL, so it can be redistributed as a subset) |
| `pyftsubset` for the one-off subset | not installed. `uvx --from fonttools` works without polluting the repo |
| Human raters for the A/B | the user, plus whoever they nominate |

## 7. Skipped on purpose

- **Animated SVG/GIF (typing effect)**: it slows down reading a hero whose job
  is to be scanned. Revisit only if the A/B shows people missing the story.
- **Changing rubric.py output** (for example `--.` → `—`): this is an engine
  change with its own tests and eval surface, so it's out of scope here. File
  it separately if the dimmed row still looks wrong.
- **Third-party screenshot tools** (VHS, freeze, Carbon, ray.so): they
  produce images, and an image breaks the verbatim-text contract the
  SVG gives for free.

## 8. Rewritten prompt (for an implementing agent)

```
Redesign docs/demo.svg / docs/demo.png from scratch following
docs/demo/REDESIGN.md. Keep render.py stdlib-only and the SVG the checked
source. First land the whitespace fix (xml:space="preserve") in the old style
as the baseline. Then render the hero in Vesper, Rosé Pine Moon and Tokyo Night
Storm via `render.py --theme`, with JetBrains Mono embedded as a committed
WOFF2 subset, the ask boxes as SVG cards, and per-token tspan colour on rubric
lines. Ship dark and light PNGs behind <picture>. A pass means:
test_demo_contract.py is green with the new contrast and whitespace tests
added; tesseract recovers ≥98% of rubric lines at 900 px width (CER ≤2%); the
PNG is ≤400 KB; and the chosen theme beats the whitespace-fixed baseline in a
blind A/B with the user.
```
