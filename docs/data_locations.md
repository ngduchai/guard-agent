# Where the Experiment Data Lives — A Reader's Guide

A complete map of every metric the orchestrator collects, where it lives on
disk, what shape it has, and how to read it.  Written for the analysis agent;
useful for any later reader.

> All paths are relative to the repo root `/home/ndhai/diaspora/guard-agent/`
> unless an absolute path is shown.

---

## 1. Data sources at-a-glance

| What you want | File / dir | Format | One-line extraction |
|---|---|---|---|
| Final outcome of the LLM iter loop per app | `build/iterative_logs/<APP>_baseline/result.json` | JSON | `json.load(open(p))['passed']` (also: `iterations`, `wall_elapsed_s`, `total_tokens`) |
| Per-iteration LLM trace (intent, edits, tools called) | `build/iterative_logs/<APP>_baseline/iter_<N>/opencode_stdout.txt` | text | `tail -200` for the LLM's own summary |
| Per-iteration validation outcome (FATAL or PASS) | `build/iterative_logs/<APP>_baseline/iter_<N>/validate_stderr.txt` + `validate_stdout.txt` | text | `grep "FATAL\|Validation B"` |
| Per-iteration LLM token + tool-call breakdown | `build/iterative_logs/<APP>_baseline/iter_<N>/inspection.json` | JSON | `d['tokens']`, `d['tool_calls']`, `d['file_changes']` |
| Per-iteration prompt the LLM saw | `build/iterative_logs/<APP>_baseline/iter_<N>/prompt.txt` | text | direct read |
| Resilient binary's own stdout/stderr (the actual mpirun output) | `build/validation_output/<APP>_baseline/correctness/{resilient,resilient_clean}/{stdout,stderr}.txt` and `attempt_<N>/{stdout,stderr}.txt` | text | grep VeloC INFO/FATAL lines |
| Build log for the LLM-modified resilient binary | `build/iterative_logs/<APP>_baseline/iter_<N>/build_output.txt` | text | usually empty if build succeeded |
| Vanilla failure-free baseline timing | `build/baseline_cache/<APP>/ground_truth_meta.json` | JSON | `json.load(open(p))['elapsed_s']` |
| Vanilla audit verdict (resilience-strip verification) | `build/audit_output/_logs/<APP>.log` | text | tail; look for "All stages completed successfully" |
| Vanilla audit aggregated summary | `build/audit_output/audit_summary.json` | JSON | `json.load(open(p))` |
| Per-cell perf for upstream reference (`<APP>_reference`) | `build/validation_output/<APP>_reference/benchmarks/raw_metrics.json` | JSON | see §3.3 schema |
| Per-cell perf for LLM-modified (`<APP>_baseline`) | `build/validation_output/<APP>_baseline/benchmarks/raw_metrics.json` | JSON | see §3.3 schema |
| Per-run mpirun stdout (under each cell) | `build/validation_output/<APP>_{reference,baseline}/benchmarks/{original,resilient}/<size-freq>/run_<N>/stdout.txt` (also `attempt_<N>/stdout.txt` for failure-injected) | text | direct read |
| Vanilla source (resilience-stripped — what the LLM is given) | `tests/apps/vanillas/<APP>/` | source tree | direct read |
| Reference checkpointed source (upstream's own resilient impl) | `tests/apps/checkpointed/<APP>/` | source tree | **READ-ONLY per `AGENTS.md`** |
| LLM-modified source (final state after iter loop) | `build/tests_baseline/<APP>/` | source tree | `diff -rq tests/apps/vanillas/<APP>/ build/tests_baseline/<APP>/` for the delta |
| Per-app workload + comparison config | `tests/apps/configs/<APP>.yaml` | YAML | size/freq cell args, MPI ranks, comparison method, tolerance |
| Failure-injection cadence definitions | `tests/apps/configs/_frequencies.yaml` | YAML | `nofail`/`once`/`multi`/`burst` parameters |
| Reference input file overlays (for upstream that needs special inputs) | `tests/apps/patches/<APP>/<input_subdir>/...` | files | overlay on top of vanilla source for the upstream build |
| Generated bench scenarios (consumed by metrics_collector) | `validation/veloc/benchmark_configs/<APP>.json` | JSON | `scenarios[*].{name,app_args,num_runs,injection_delay,...}` |
| Orchestrator stage transitions | `build/run_logs/_orchestrator.log` | text | grep `TIER\|TIER COMPLETE\|<stage> (starting\|done)` |
| Per-stage logs | `build/run_logs/{audit,bench_reference,iter,bench_baseline}_<tier>.log` | text | direct tail |
| Stall-watch events (when watcher flagged/killed opencode) | `build/iterative_logs/<APP>_baseline/iter_<N>/stall_watch.log` (per-iter) and `build/run_logs/_stall_investigations.log` (global) | text | direct read |

---

## 2. Tier and app composition

Tier files (whitespace + comments stripped):

| Tier | File | Apps |
|---|---|---|
| fast | `validation/veloc/apps_fast.txt` | CoMD, HPCG, SPARTA, Athena++, CLAMR, PRK_Stencil |
| mid  | `validation/veloc/apps_mid.txt`  | MMSP, HyPar, OpenLB, LAMMPS, SAMRAI, ROSS |
| slow | `validation/veloc/apps_slow.txt` | SPPARKS, SW4lite, QMCPACK, Smilei, Nyx, WarpX |

The unified config (`tests/apps/configs/<APP>.yaml`) has a `category` field
classifying the workload:

| Category | Apps |
|---|---|
| iterative_fixed | CoMD, HPCG, MMSP, HyPar, SPPARKS, SW4lite, QMCPACK |
| iterative_variable | SPARTA, LAMMPS, Smilei |
| iterative_adaptive | Athena++, CLAMR, OpenLB, SAMRAI, Nyx, WarpX |
| asynchronous | PRK_Stencil, ROSS |

(Used as the colour grouping in `docs/figs/fast_tier_iter_*.png`.)

---

## 3. Schemas of the key JSON files

### 3.1 `build/iterative_logs/<APP>_baseline/result.json`

```json
{
  "app_name": "CoMD",
  "mode": "baseline",
  "passed": true,
  "iterations": 2,             // number of iters used (1..max_iters)
  "max_iters": 10,
  "total_elapsed_s": 1339.87,  // sum of opencode + validation across all iters
  "wall_elapsed_s": 1340.19,
  "total_input_tokens": 270898,
  "total_output_tokens": 4328,
  "total_tokens": 275226,
  "per_iteration": [
    {
      "iter": 1,
      "opencode_elapsed_s": 650.31,
      "validation_elapsed_s": 302.37,
      "total_elapsed_s": 952.69,
      "validation_passed": false,
      "input_tokens": 20194, "output_tokens": 433, "total_tokens": 20627
    },
    { "iter": 2, "...": "..." }
  ]
}
```

Optional fields (present only when applicable):

- `_reconstructed: true` + `_reconstruction_note: "..."` — file was hand-built
  after the run_iterative.sh wrapper was killed mid-flight (see ISSUES.md
  #44).  Treat its numbers as best-effort from disk artefacts.
- `stall_aborted: true` + `stall_iteration: <N>` — the per-app loop was ended
  by the stall watcher; `passed` will be `false` and BENCH-BASELINE will be
  cache-skipped for this app.

### 3.2 `build/iterative_logs/<APP>_baseline/iter_<N>/inspection.json`

```json
{
  "iter_dir": ".../iter_1",
  "session": { /* opencode session metadata */ },
  "file_changes": {
    "files_added": [...], "files_modified": [...],
    "lines_added": 482, "lines_removed": 17
  },
  "tokens": {
    "input": 4219988, "output": 26867, "total": 4246855,
    "cache_read": 0, "cache_write": 0, "reasoning": 0
  },
  "tool_calls": [ /* ordered list of opencode tool invocations */ ],
  "errors": [ /* opencode-level errors if any */ ],
  "text_first": "...",  // first ~500 chars of LLM's stdout
  "text_last":  "...",  // last ~500 chars of LLM's stdout
  "step_count": 44,
  "warnings": [],
  "file_changes_db_summary": { /* short summary */ },
  "edited_source": true
}
```

`tokens.input/output/total` is more accurate than the values in
`result.json` (which are derived from a SQLite query that occasionally
under-counts mid-iter; see HyPar iter_1 where SQLite said ~20k while
inspection.json said 4.2M).

### 3.3 `build/validation_output/<APP>_{reference,baseline}/benchmarks/raw_metrics.json`

```json
{
  "scenarios": [                       // the cells that were measured
    {
      "name": "small-nofail",
      "_size": "small", "_frequency": "nofail",
      "num_procs": 4,
      "app_args": ["-x", "80", ...],
      "inject_failures": false,
      "num_runs": 3,
      "injection_delay": 0.0,
      "max_attempts": 1,
      "original_app_args": null,       // optional vanilla-only override
      "resilient_app_args": null       // optional upstream-only override
    },
    { "name": "small-once", "...": "..." }
  ],
  "runs": [                            // one entry per (scenario, codebase, run_index)
    {
      "scenario_name": "small-nofail",
      "codebase": "original" | "resilient",
      "run_index": 1,
      "elapsed_s": 124.06,
      "injected": false,               // true if failure was injected this run
      "num_attempts": 1,               // 1 = no retry, 2 = one kill+restart
      "checkpoint_size_bytes": 130417056,    // total bytes in ALL checkpoint dirs (see §4.4 caveat)
      "checkpoint_per_frame_bytes": 21736176,
      "checkpoint_frames_on_disk": 6,
      "checkpoint_files_count": 24,
      "recovery_time_s": null,         // parsed from VeloC stdout when present
      "peak_memory_bytes": 266887168,
      "memory_samples_bytes": [ /* sampled RSS over the run */ ]
    }
  ],
  "summary": {                         // pre-aggregated mean/std/min/max/n
    "small-nofail": {
      "original":  { "elapsed_s": { "mean": ..., "std": ..., ... }, ... },
      "resilient": { ... }
    },
    "small-once": { "resilient": { ... } }   // vanilla-once is synthetic, not run
  }
}
```

`codebase`:

- `"original"` — the vanilla app (resilience-stripped; what the LLM started
  from).  Only `nofail` cells are run; `once` is **synthesized in the
  comparison report** as `vanilla.nofail × (1 + delay_fraction)` (see issue
  history; we do NOT re-run vanilla under failure).
- `"resilient"` — for `*_reference/`, the upstream-checkpointed source.  For
  `*_baseline/`, the LLM-modified source.

### 3.4 `build/baseline_cache/<APP>/ground_truth_meta.json`

```json
{
  "schema_version": 1,
  "elapsed_s": 148.3,                  // failure-free vanilla wall-clock (validation size)
  "baseline_pass1_elapsed_s": 148.4,
  "baseline_pass2_elapsed_s": 148.3,
  "baseline_warmup_elapsed_s": 152.1,
  "cache_key": { /* num_procs, args, executable_name, app_input_subdir, build_cmd, ... */ },
  "cache_key_hash": "sha256:...",
  "vanilla_src_max_mtime": 1745692345.123,
  "vanilla_src_file_count": 87,
  "cached_at": "2026-04-28T15:29:18Z",
  "collector_host": "dev",
  "collector_version": 1
}
```

`elapsed_s` is the failure-free baseline used to compute the recovery-ratio
denominator (e.g., "1.04× of baseline").

### 3.5 `build/audit_output/audit_summary.json`

```json
{
  "started_at": "...",
  "results": [
    { "app": "MMSP", "status": "PASS",
      "detail": "Vanilla works failure-free, matches reference, and cannot recover (ratio 1.92x, checkpoint files=0)." },
    ...
  ],
  "by_status": { "PASS": 6 }
}
```

A vanilla PASS means: failure-free output matches reference, AND failure-injected
recovery proof FAILS as expected (vanilla can't recover because checkpoint code
was stripped).  This is the "vanilla is properly stripped" signal.

---

## 4. Caveats and known data-quality issues

### 4.1 Reference `checkpoint_size_bytes` can be null even though the run "passed"

For some apps, the upstream-checkpointed binary requires a CLI flag to
enable its native checkpointer (e.g., CLAMR's Crux needs `-c <interval>`;
without it, `crux_type = CRUX_NONE`).  Our generator does NOT emit
`resilient_app_args` containing such opt-in flags, so the upstream binary
runs without checkpointing.  In that case:

- `checkpoint_size_bytes`, `checkpoint_per_frame_bytes`,
  `checkpoint_frames_on_disk`, `checkpoint_files_count` will all be
  `None` / `null` / `0` for every resilient run of that app.
- The failure-injection scenario STILL "passes" because the bench
  framework retries from scratch (`num_attempts: 2`) and the rerun finishes
  to the same final output — but this is a **rerun, not a recovery**.
  Distinguish the two in your analysis.

Affected (as of 2026-04-29): **CLAMR**.  Other fast-tier apps either default
their checkpointer to "on" or use an env-var-based opt-in that the framework
sets via separate env handling.  See ISSUES.md for the running list.

### 4.2 `result.json` token counts vs `inspection.json` token counts

`result.json.total_tokens` comes from a SQLite query against opencode's
session DB and can under-count when the iter wrapper queries before all
records are flushed.  `inspection.json.tokens.total` is the authoritative
count (read directly from opencode's per-message records).  When the two
disagree, prefer inspection.json.

### 4.3 `_reconstructed: true` markers in result.json

When the `run_iterative.sh` wrapper is SIGKILL'd mid-validation, the
result.json is missing.  We hand-reconstruct from iter dir artefacts.
Reconstructed files have `_reconstructed: true` and a `_reconstruction_note`
field.  Their numbers are derived from file mtimes (timing) and
inspection.json (tokens) — accurate but not original.  Filter via
`json.load(p).get('_reconstructed', False)` if you want to exclude.

### 4.4 Vanilla-once is synthetic, not measured

For every `<APP>_reference` and `<APP>_baseline`, `runs[].codebase=='original'`
exists ONLY for `small-nofail` cells.  The vanilla-once metric we report
in comparison reports is computed as
`vanilla.nofail × (1 + frequency.delay_fraction)` — see
`tests/apps/configs/_frequencies.yaml` for the multipliers.  Never expect
to find an `original` row with `inject_failures: true` in raw_metrics.json.

### 4.5 Old vs new ITER feedback prompt

CoMD, HPCG, SPARTA passed under the **old** iter feedback prompt (which
only included the validator's stdout/stderr/build output, not the resilient
binary's own crash messages).  Athena++, CLAMR, PRK_Stencil passed under
the **new** prompt (which adds the resilient binary's stdout/stderr from
both failure-prone and failure-free runs).  When comparing token cost or
iteration count across the fast tier, group by feedback variant:

```python
OLD_FB = {"CoMD", "HPCG", "SPARTA"}
NEW_FB = {"Athena++", "CLAMR", "PRK_Stencil"}
```

A queued rerun script (`build/run_logs/_rerun_passed_apps_with_new_feedback.sh`)
will re-measure the OLD_FB three under the new prompt after `ALL TIERS COMPLETE`,
producing a clean apples-to-apples comparison.  Until then, a head-to-head
"feedback impact" plot needs to flag the variant per bar.

### 4.6 Some attempt dirs have no stdout/stderr

The `attempt_*/stdout.txt` files come from the validate.py runner's
captures of mpirun.  When mpirun crashes very early (e.g. exit=255 in <1s)
the captured output may be empty.  In that case, look at the runner's own
log line in `validate_stdout.txt` (e.g.
`[runner] checkpoint-observed: NO CHECKPOINT detected (kill_attempt elapsed=2s, exit=255)`).

---

## 5. Common queries — copy-pasteable Python

### 5.1 Per-app convergence summary

```python
import json
from pathlib import Path
ROOT = Path("/home/ndhai/diaspora/guard-agent")

def load_result(app: str) -> dict | None:
    p = ROOT / f"build/iterative_logs/{app}_baseline/result.json"
    return json.loads(p.read_text()) if p.exists() else None

for app in ["CoMD", "HPCG", "SPARTA", "Athena++", "CLAMR", "PRK_Stencil"]:
    r = load_result(app)
    if r:
        verdict = "PASS" if r["passed"] else "FAIL"
        recon = " [reconstructed]" if r.get("_reconstructed") else ""
        print(f"{app:14}  {verdict}  iters={r['iterations']:2}  "
              f"wall={r['wall_elapsed_s']/60:5.1f}m  tokens={r['total_tokens']:>10,d}{recon}")
```

### 5.2 Per-iter token + tool-call breakdown

```python
def load_inspection(app: str, iter_n: int) -> dict:
    p = ROOT / f"build/iterative_logs/{app}_baseline/iter_{iter_n}/inspection.json"
    return json.loads(p.read_text())

insp = load_inspection("Athena++", 4)
print(f"tokens: {insp['tokens']}")
print(f"tool calls: {len(insp['tool_calls'])}")
print(f"file changes: {insp['file_changes']}")
```

### 5.3 Per-cell perf comparison (LLM vs reference)

```python
def cell_summary(app: str, which: str, scen: str, codebase: str) -> dict:
    """which is 'reference' or 'baseline'"""
    p = ROOT / f"build/validation_output/{app}_{which}/benchmarks/raw_metrics.json"
    d = json.loads(p.read_text())
    return d["summary"][scen][codebase]   # mean/std/min/max/n per metric

ref  = cell_summary("CoMD", "reference", "small-nofail", "resilient")
llm  = cell_summary("CoMD", "baseline",  "small-nofail", "resilient")
print(f"CoMD nofail elapsed: ref={ref['elapsed_s']['mean']:.1f}s  llm={llm['elapsed_s']['mean']:.1f}s")
print(f"CoMD per-frame ckpt: ref={ref['checkpoint_per_frame_bytes']['mean']/1e6:.1f}M  "
      f"llm={llm['checkpoint_per_frame_bytes']['mean']/1e6:.1f}M")
```

### 5.4 Recovery ratio (kill+recovery / failure-free baseline)

```python
def recovery_ratio(app: str, which: str) -> float:
    p = ROOT / f"build/validation_output/{app}_{which}/benchmarks/raw_metrics.json"
    d = json.loads(p.read_text())
    free = d["summary"]["small-nofail"]["resilient"]["elapsed_s"]["mean"]
    inj  = d["summary"]["small-once"]["resilient"]["elapsed_s"]["mean"]
    return inj / free

for app in ["CoMD", "HPCG", "SPARTA", "Athena++", "CLAMR", "PRK_Stencil"]:
    try:
        r_llm = recovery_ratio(app, "baseline")
        r_ref = recovery_ratio(app, "reference")
        print(f"{app:14}  llm={r_llm:.3f}x  ref={r_ref:.3f}x  delta={r_llm-r_ref:+.3f}")
    except KeyError:
        pass
```

### 5.5 LLM source modifications per app

```python
import subprocess
def llm_diff(app: str) -> list[str]:
    out = subprocess.run(
        ["diff", "-rq",
         f"{ROOT}/tests/apps/vanillas/{app}",
         f"{ROOT}/build/tests_baseline/{app}"],
        capture_output=True, text=True
    )
    return out.stdout.splitlines()

for line in llm_diff("Athena++"):
    print(line)
```

### 5.6 Validation FATAL clustering

```python
import re
from collections import Counter
fatals = Counter()
for app_dir in (ROOT / "build/iterative_logs").iterdir():
    for iter_dir in app_dir.glob("iter_*"):
        stderr = iter_dir / "validate_stderr.txt"
        if not stderr.exists(): continue
        for m in re.finditer(r"FATAL: Correctness stage encountered a fatal error\.\s*(.+?)(?:\n\n|\n  Output)",
                             stderr.read_text(), re.DOTALL):
            # First sentence of the FATAL message — coarse cluster key
            key = m.group(1).strip().split(".")[0]
            fatals[key] += 1
for key, count in fatals.most_common(10):
    print(f"{count:3}  {key[:120]}")
```

---

## 6. Quick start for the analysis agent

Read these in order to orient yourself:

1. This file (you're here).
2. `docs/llm_resilience_report/CoMD.md` — the per-app report format target.
3. `docs/figs/_plot_fast_tier_iter_metrics.py` — the figure format target.
4. `docs/analysis_agent_briefing.md` — the broader project briefing.
5. `AGENTS.md` and `CLAUDE.md` — project rules.

Then ask the user which analysis (from the briefing's §5 list) to start.

---

## 7. Updates

If you (or a future agent) discover a metric source not catalogued here,
**update this file** rather than letting the next analyst rediscover it.
The `Last verified` table below is a sanity check that the catalogue has
not drifted from disk reality.

### Last verified

| Section | Date | Verified-against |
|---|---|---|
| §1, §3 | 2026-04-29 | fast tier complete; CoMD/HPCG/Athena++/CLAMR raw_metrics.json present and matching schema |
| §4.1 | 2026-04-29 | Confirmed by direct probe: CLAMR_reference small-once `checkpoint_size_bytes: null`, `num_attempts: 2`, attempt_2 stdout starts at `Iteration 0` (rerun, not recovery) |
| §4.3 | 2026-04-29 | HyPar result.json is the first reconstructed file in the run |
