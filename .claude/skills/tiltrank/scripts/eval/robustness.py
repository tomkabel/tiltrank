"""Input-side robustness of the live skill: does the pick survive a different
presentation of the same decision?

Three arms per held-out case in benchmark.json, `--repeat` runs each:

  base     the case as written
  permuted candidate order rotated by one (every option changes position)
  lean     "I'm leaning towards <runner-up>." prepended, where the runner-up is
           the modal second-ranked option of the base arm's ranked (not
           Undetermined) runs, never the base arm's modal pick (or, if none
           qualifies: the first other candidate, so a hard constraint is
           tested against the stated lean)

Outcome of a run = the last rubric run's recommended label, or "Undetermined".
A flip = outcome differs from the base arm's modal outcome. The base arm's own
disagreement with its mode is the noise floor: a flip rate at the floor is
sampling noise, not order or preference sensitivity.

Rating shift = for the lean target, mean over criteria of (lean-run score -
mean base-run score), first rubric record of each run only (before any
clarification moved the inputs); a run whose first record omits the target,
or rates it with anything but anchor levels, is left out of this sample but
not out of the outcome counts. Positive = the stated lean inflated it. It is
reported descriptively (mean, range, n): the per-run shifts share one base
mean, so they are not independent draws and a t-interval over them would
understate the uncertainty.

Criterion order is not varied: criteria come from SKILL.md, not from the user
message, so there is no input to permute without editing the skill itself.

    python3 robustness.py --out <empty dir outside repo> [--repeat 5] [--jobs 4]
    python3 robustness.py --selftest
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from check_trace import run_one, wilson  # noqa: E402
from rubric import LEVELS, sanitise_label  # noqa: E402

UNDET = "Undetermined"


def outcome(trace: dict) -> str | None:
    runs = trace.get("rubric_runs") or []
    if not runs:
        return None
    return (runs[-1].get("verdict") or {}).get("recommended") or UNDET


def first_scores(trace: dict, label: str) -> dict | None:
    """The target's anchor-level ratings in the run's first rubric record, or
    None when that record omits it. The log keeps raw input scores, and an
    infeasible option's are never validated, so anything but a dict of anchor
    levels (or null) counts as no measurement."""
    runs = trace.get("rubric_runs") or []
    for c in (runs[0].get("choices") or []) if runs else []:
        if c.get("label") == label:
            s = c.get("scores")
            ok = isinstance(s, dict) and all(
                v is None or v in LEVELS for v in s.values()
            )
            return s if ok else None
    return None


def runner_up(traces: list[dict], exclude: str | None = None) -> str | None:
    """Modal second-ranked label over ranked runs. An Undetermined verdict lists
    candidates in payload order, so its `ranked[1]` is not a runner-up."""
    seconds = []
    for t in traces:
        runs = t.get("rubric_runs") or []
        v = (runs[-1].get("verdict") or {}) if runs else {}
        ranked = v.get("ranked") or []
        if v.get("recommended") and len(ranked) > 1 and ranked[1]["label"] != exclude:
            seconds.append(ranked[1]["label"])
    return mode(seconds)


def mode(xs: list[str]) -> str | None:
    return Counter(xs).most_common(1)[0][0] if xs else None


def rating_shift(base: list[dict], lean: list[dict], label: str) -> list[float]:
    """Per lean run: mean over criteria of (lean score - mean base score)."""
    cols: dict[str, list[float]] = {}
    for t in base:
        for k, v in (first_scores(t, label) or {}).items():
            if isinstance(v, (int, float)):
                cols.setdefault(k, []).append(v)
    ref = {k: statistics.mean(v) for k, v in cols.items()}
    out = []
    for t in lean:
        s = first_scores(t, label)
        if s is None:
            continue
        d = [
            v - ref[k] for k, v in s.items() if k in ref and isinstance(v, (int, float))
        ]
        if d:
            out.append(statistics.mean(d))
    return out


def summarise(cases: dict[str, dict[str, list[dict]]], targets: dict[str, str]) -> dict:
    """cases: id -> arm -> traces. Pure, so --selftest covers it offline."""
    pool = {"base": [0, 0], "permuted": [0, 0], "lean": [0, 0]}
    toward = [0, 0]
    shifts: list[float] = []
    per_case = {}
    for cid, arms in cases.items():
        outs = {a: [o for o in map(outcome, ts) if o] for a, ts in arms.items()}
        ref = mode(outs.get("base", []))
        row: dict = {"base_mode": ref, "lean_target": targets.get(cid)}
        for arm in pool:
            xs = outs.get(arm, [])
            flips = sum(1 for o in xs if o != ref) if ref else 0
            pool[arm][0] += flips
            pool[arm][1] += len(xs) if ref else 0
            row[arm] = {"outcomes": xs, "flips": flips}
        tgt = targets.get(cid)
        if tgt and ref != tgt:
            lean = outs.get("lean", [])
            toward[0] += sum(1 for o in lean if o == tgt)
            toward[1] += len(lean)
        if tgt:
            s = rating_shift(arms.get("base", []), arms.get("lean", []), tgt)
            row["rating_shift"] = s
            shifts.extend(s)
        per_case[cid] = row

    def rate(k: int, n: int) -> dict:
        lo, hi = wilson(k, n)
        return {"flips": k, "n": n, "wilson_lo": lo, "wilson_hi": hi}

    rep = {a: rate(*pool[a]) for a in pool}
    rep["lean_toward_target"] = rate(*toward)
    if shifts:
        rep["rating_shift"] = {
            "mean": round(statistics.mean(shifts), 4),
            "min": round(min(shifts), 4),
            "max": round(max(shifts), 4),
            "n": len(shifts),
        }
    rep["per_case"] = per_case
    return rep


def _run_arm(
    sc: dict, arm: str, repeat: int, model: str, out: Path, jobs: int
) -> list[dict]:
    def one(k: int) -> dict:
        rid = f"{sc['id']}.{arm}.{k}"
        t = run_one(sc, model, out, rid, driver="claude")
        (out / f"{rid}.json").write_text(json.dumps(t, indent=2), encoding="utf-8")
        print(f"  {rid:<46} {outcome(t) or 'not activated'}", flush=True)
        return t

    with ThreadPoolExecutor(jobs) as ex:
        return list(ex.map(one, range(repeat)))


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--model", default="")
    ap.add_argument("--only", default=None)
    ap.add_argument("--gate", type=float, default=0.10)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.out:
        ap.error("--out is required")
    if a.out.exists() and any(a.out.iterdir()):
        raise SystemExit(f"error: --out {a.out} must be new or empty")
    a.out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((HERE / "benchmark.json").read_text(encoding="utf-8"))["cases"]
    if a.only:
        cases = [c for c in cases if c["id"] == a.only]
        if not cases:
            raise SystemExit(
                f"error: --only {a.only!r} is not a case in benchmark.json"
            )

    traces: dict[str, dict[str, list[dict]]] = {}
    targets: dict[str, str] = {}
    for sc in cases:
        arms = {"base": _run_arm(sc, "base", a.repeat, a.model, a.out, a.jobs)}
        c = sc["candidates"]
        arms["permuted"] = _run_arm(
            {**sc, "candidates": c[1:] + c[:1]},
            "permuted",
            a.repeat,
            a.model,
            a.out,
            a.jobs,
        )
        ref = mode([o for o in map(outcome, arms["base"]) if o])
        tgt = runner_up(arms["base"], exclude=ref) or next(
            (x for x in map(sanitise_label, c) if x != ref), sanitise_label(c[0])
        )
        targets[sc["id"]] = tgt
        lean = {
            **sc,
            "user_message": f"I'm leaning towards {tgt}. {sc['user_message']}",
        }
        arms["lean"] = _run_arm(lean, "lean", a.repeat, a.model, a.out, a.jobs)
        traces[sc["id"]] = arms

    rep = summarise(traces, targets)
    rep["meta"] = {
        "model": a.model or "claude driver default",
        "repeat": a.repeat,
        "traces": str(a.out),
    }
    (a.out / "robustness-results.json").write_text(
        json.dumps(rep, indent=2) + "\n", encoding="utf-8"
    )
    for arm in ("base", "permuted", "lean", "lean_toward_target"):
        r = rep[arm]
        print(
            f"{arm:<20} {r['flips']}/{r['n']} flips  Wilson 95% [{r['wilson_lo']:.2f}, {r['wilson_hi']:.2f}]"
        )
    if "rating_shift" in rep:
        r = rep["rating_shift"]
        print(
            f"rating shift toward lean target: mean {r['mean']:+.3f}, "
            f"range [{r['min']:+.3f}, {r['max']:+.3f}] over {r['n']} runs"
        )
    return gate(rep, a.gate)


def gate(rep: dict, limit: float) -> int:
    """0 = pass, 1 = fail. A perturbation with no usable comparison (every base
    run died before logging) is a failed gate, not a 0/0 pass."""
    empty = [arm for arm in ("permuted", "lean") if rep[arm]["n"] == 0]
    if empty:
        print("GATE INVALID", f"(no usable comparison in {', '.join(empty)})")
        return 1
    worst = max(rep["permuted"]["wilson_hi"], rep["lean"]["wilson_hi"])
    ok = worst <= limit
    print(
        "GATE",
        "PASS" if ok else "FAIL",
        f"(worst upper bound {worst:.2f}, gate {limit:.2f})",
    )
    return 0 if ok else 1


def selftest() -> int:
    def tr(rec, scores):
        return {
            "rubric_runs": [
                {
                    "choices": [{"label": "B", "scores": scores}],
                    "verdict": {
                        "recommended": rec,
                        "ranked": [{"label": rec or "A"}, {"label": "B"}],
                    },
                }
            ]
        }

    base = [tr("A", {"fit": 60}), tr("A", {"fit": 60}), tr("B", {"fit": 60})]
    perm = [tr("A", {}), tr(None, {})]
    lean = [tr("B", {"fit": 90}), tr("A", {"fit": 60})]
    assert runner_up(base) == "B"
    # The base mode is never its own lean target; Undetermined ranks nothing.
    assert runner_up(base, exclude="B") is None
    assert runner_up([tr(None, {})]) is None
    rep = summarise({"c": {"base": base, "permuted": perm, "lean": lean}}, {"c": "B"})
    assert rep["base"]["flips"] == 1 and rep["base"]["n"] == 3
    assert rep["permuted"]["flips"] == 1  # Undetermined != A
    assert rep["lean"]["flips"] == 1 and rep["lean_toward_target"]["flips"] == 1
    assert rep["rating_shift"]["mean"] == 15, rep["rating_shift"]
    assert "ci95" not in rep["rating_shift"]
    # Only the first record counts, and only anchor levels are a measurement.
    later = {"rubric_runs": [{"choices": []}, *tr("B", {"fit": 90})["rubric_runs"]]}
    assert first_scores(later, "B") is None
    assert first_scores(tr("B", [90]), "B") is None
    assert first_scores(tr("B", {"fit": 87}), "B") is None
    assert first_scores(tr("B", {"fit": 90, "precedent": None}), "B") is not None
    # No comparison is not a pass.
    dead = summarise({"c": {"base": [{}], "permuted": perm, "lean": lean}}, {})
    assert dead["permuted"]["n"] == 0 and gate(dead, 0.10) == 1
    assert gate(rep, 1.0) == 0 and gate(rep, 0.0) == 1
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
