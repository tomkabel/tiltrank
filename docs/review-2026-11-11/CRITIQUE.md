# External critique, 2026-11-11

Critique of the README hero demo (`docs/demo.svg`) as recorded on 2026-11-11, kept
as the input to `PLAN.md` and not edited since.

**The record may be incomplete.** `PLAN.md` revision 1 answered points that are
not below: `1d`, a summary list `S1`–`S4`, and a quoted "let trade-offs be
trade-offs". The full original is not in the repo. Revision 2 answers only what
is recorded here. The screenshot the critic reviewed was the committed
`docs/demo.svg` (`06e2dce`), whose text matches every quote below.

---

Here is a blunt, senior-level critique of **tiltrank** based on this screenshot.

At a glance, the visual polish of the terminal UI is clean. However, once you look past the aesthetics, the tool exhibits **quantification theater**, **flawed systems-engineering fundamentals**, and **redundant UX**.

### 1. "Quantification Theater" (Math-Washing LLM Vibes)

```text
Bash(python3 scripts/rubric.py)
  1. Redis          score 81  (evidence 90)
  2. File-based     score 49  (evidence 60)
  3. In-memory LRU  score 41  (evidence 60)
```

* **Where do these numbers come from?** `rubric.py` is invoked with **zero arguments**. That means the LLM either wrote hardcoded numbers into a script just to print them back out, or passed subjective weights via a hidden temp file to make a basic arithmetic script spit out `81` and `49`.
* **False Precision:** What does `score 81` vs. `score 49` actually mean? Why `81` and not `80`? What is `evidence 90` when the user prompt is a single sentence containing **zero metrics** (no QPS, no payload size, no TTL requirements, no read/write ratio, no latency SLA)?
* **The Danger:** Dressing up ungrounded LLM heuristics as deterministic telemetry (`evidence 90`, `band: Separated — a recommendation is defensible`) lulls developers into a false sense of rigor. If the inputs are vibes, the output is vibes—putting a two-digit integer next to it doesn't make it data science.

### 2. Fundamentally Flawed Architectural Reasoning

* **"Proven at this shape" — What shape?** The subtext says: *"which matters more if this stays a single box."* This implies the project is currently running on a **single node**. If an API is running on a single box with unknown traffic, recommending that the team provision, secure, monitor, and maintain a separate stateful Redis instance (`score 81`) over a 5-line in-memory LRU (`score 41`) is classic **resume-driven over-engineering (YAGNI)**.
* **Ranking File-based (49) over In-memory LRU (41) is absurd:** In almost no modern API architecture is a raw file-based cache superior to an in-memory LRU on a single box: both require "zero new infra" and are local to the box; file-based caching introduces disk I/O bottlenecks, inode exhaustion, file-locking race conditions under concurrent requests, and requires writing custom background reaper/eviction logic; in-memory LRU handles eviction automatically in nanoseconds and is thread/async-safe out of the box.
* **Misunderstanding what a cache is:** Dismissing an In-memory LRU as *"Weak — the cache is lost on every restart"* misunderstands the definition of a cache. **A cache is ephemeral by design.** If your system cannot tolerate a cold cache on deploy/restart without falling over, you don't have a caching problem—you have a database or state-persistence problem.

### 3. When a Recommendation is *Not* Defensible

```text
band: Separated — a recommendation is defensible
```

No, it isn't. When a developer asks *"Which cache should the API use?"* without specifying (1) how many application instances/workers are running, (2) how big the cached objects are, (3) what the eviction/invalidation strategy looks like, a senior tool **refuses to rank them yet**: *"Band: Undetermined — Missing critical constraints. Answer these 2 questions before ranking."*

### 4. Redundant UX & Information Duplication

The raw `Bash(...)` stdout prints the numbered list, the excluded item, and the band; immediately below it, the interactive TUI box repeats the same list, the excluded item verbatim, and the conclusion. Either `rubric.py` output should be hidden/collapsed in favour of the TUI box, or the TUI box shouldn't repeat it.

### 5. `.decisions.log` is an Anti-Pattern

Hidden dotfiles are where context goes to die. No one cares *that* you picked Redis; they care *why*. A single line is useless unless it captures the constraints, rejected alternatives, and trade-offs at the time of the decision. Mature teams use ADRs in a visible, version-controlled directory (e.g. `docs/decisions/004-api-caching.md`).

### Summary

1. Kill the fake 0–100 numbers; replace with constraint checklists.
2. Gate rankings behind missing context.
3. Fix the domain logic.
4. Hide the raw script stdout.
5. Write human-readable ADRs, not hidden logs.
