# sonnet46 pre-permfix archive

**Archived:** 2026-05-29 03:02:21 UTC (epoch 1780023705)

**Reason:** Snapshot of all sonnet46 LLM-iter artifacts taken BEFORE the
`run_iterative.sh` per-launch OpenCode config fix landed (commit be99a709a,
ISSUES.md #58). Captures the workspace pollution and stable-stuck-club
symptoms produced by the global `tests_baseline_*/**` read-deny that
blocked LLMs from reading their own workspaces. Preserved so the fresh
sonnet46 run can be compared against the pre-fix data without losing the
canonical examples (HyPar `!`-prefix overrides, SPPARKS library-intercept
substitution, etc.).

## Contents

- `iterative_logs/` — 16 per-app iter loop directories (45 MB total).
- `tests_baseline_sonnet46/` — 16 LLM-modified workspace trees (1.5 GB total).
- `validation_output/` — 16 per-app validator output dirs (41 GB total, mostly
  per-iter build artifacts + checkpoint bytes + benchmark raw_metrics).
- `orchestrator_logs/` — 4 `phase1_sonnet46_*` log files from the various
  orchestrator launches that fed into this snapshot.

## Verdict state at archive time

5 apps reached PASS in the pre-fix sweep:

| App | Verdict | Iter that passed |
|---|---|---|
| CoMD | TRUSTED | 1 |
| HPCG | TRUSTED | 2 |
| OpenLB | TRUSTED | 4 |
| SPARTA | TRUSTED | 6 |
| SPPARKS | CONDITIONAL_TRUSTED | 11 (library-intercept substitution, see _decisions.log 2026-05-29) |

Full forensic chain in `build/_experiment_state/_decisions.log` (kept live, not archived).

## Not archived (kept live in `build/`)

- `build/baseline_cache/<APP>/` — vanilla baseline metrics, cross-experiment paper-grade.
- `build/validation_output/<APP>_reference/` — upstream reference baseline output.
- `build/_experiment_state/_trust.json` + `_decisions.log` — trust state preserves history pointer to this archive.
