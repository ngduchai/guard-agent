# LLM Resilience Engineering — Cross-App Summary

**Apps covered (post-strip)**:
- [`CoMD`](CoMD.md) — PASS in **2 iters**, 1238 s wall, **0.43 M tokens**
- [`HPCG`](HPCG.md) — PASS in **4 iters**, 2558 s wall, **5.32 M tokens**
- [`SPARTA`](SPARTA.md) — PASS in **3 iters**, 3153 s wall, **7.64 M tokens**
- [`PRK_Stencil`](PRK_Stencil.md) — PASS in **2 iters**, 616 s wall, **1.29 M tokens**

**Pipeline run**: 2026-04-27 (Phase 4 baseline iterative agent over post-strip vanillas; Athena++ runs in parallel and is excluded here).

**Iter logs**: [`build/iterative_logs/CoMD_baseline/`](../../build/iterative_logs/CoMD_baseline/), [`build/iterative_logs/HPCG_baseline/`](../../build/iterative_logs/HPCG_baseline/), [`build/iterative_logs/SPARTA_baseline/`](../../build/iterative_logs/SPARTA_baseline/), [`build/iterative_logs/PRK_Stencil_baseline/`](../../build/iterative_logs/PRK_Stencil_baseline/). **Benchmarks**: [`build/validation_output/CoMD_baseline/`](../../build/validation_output/CoMD_baseline/), [`build/validation_output/HPCG_baseline/`](../../build/validation_output/HPCG_baseline/), [`build/validation_output/SPARTA_baseline/`](../../build/validation_output/SPARTA_baseline/), [`build/validation_output/PRK_Stencil_baseline/`](../../build/validation_output/PRK_Stencil_baseline/).

---

## 1. Cross-cutting patterns

> **See also**: [`_state_coverage_matrix.md`](_state_coverage_matrix.md) — a cross-app
> matrix that normalises every per-app §1.4 *State coverage* table into one
> categorical view (15 state classes × 6 apps), with companion heatmap
> figure [`docs/figs/fast_tier_state_coverage.{pdf,png}`](../figs/fast_tier_state_coverage.png).
> Quantifies the fourth bullet below ("trust deterministic re-init") — LLM and
> reference agree on **5 of 15** universally-applicable rows; LLM-only saves
> account for **3** of the **8** divergent cells (harness-mirror buffer +
> defensive solver tunables), reference-only saves account for the other
> **5** (geometry / decomposition / species).

### 1.1 Common LLM behaviors observed

- **The "missing veloc.cfg at codebase root" trap** — every app failed iter 1 with the validator's `No VeloC checkpoint directories resolved from veloc.cfg` (CoMD is the exception — its iter 1 placed [`veloc.cfg`](../../build/tests_baseline/CoMD/veloc.cfg) at the project root because the run cwd is the project root, see [`CoMD/iter_1/opencode_stdout.txt:143-148`](../../build/iterative_logs/CoMD_baseline/iter_1/opencode_stdout.txt)). For HPCG, SPARTA, and PRK_Stencil the iter-2 fix was identical: copy `<run-dir>/veloc.cfg` to `<codebase-root>/veloc.cfg` byte-for-byte (see [`HPCG/iter_2`](../../build/iterative_logs/HPCG_baseline/iter_2/opencode_stdout.txt), [`SPARTA/iter_2`](../../build/iterative_logs/SPARTA_baseline/iter_2/opencode_stdout.txt), [`PRK_Stencil/iter_2`](../../build/iterative_logs/PRK_Stencil_baseline/iter_2/opencode_stdout.txt)). The validator's discovery path is pinned to two specific filesystem locations (`source_dir/veloc.cfg`, `build_dir/veloc.cfg`, see `runner.py:1487-1494`) and is documented in [`ISSUES.md`](../../ISSUES.md) #37, but the LLM still has to re-derive it from the FATAL message each time.
- **Single-phase recovery only** — every app uses the canonical `VELOC_Mem_protect → VELOC_Restart_test → VELOC_Restart_begin → VELOC_Recover_mem → VELOC_Restart_end` cycle. HPCG iter 1–3 attempted a two-phase variant (calling `VELOC_Restart_begin/end` twice on the same version, partitioned by `VELOC_Recover_selective` over ids {0,1} then {2,3}) and iter 4 rolled back to single-phase after the forensic insight that the failure-prone `40 B/file` checkpoint metric was caused by silent VeloC state corruption following the double-end (see [`HPCG/iter_4/opencode_stdout.txt:381-392`](../../build/iterative_logs/HPCG_baseline/iter_4/opencode_stdout.txt)).
- **Pre-grow + fixed ceiling for variable-size arrays** — both SPARTA (particle array) and HPCG iters 1–3 (residual array) initially struggled with VeloC's requirement that `Mem_protect` size match between checkpoint and recover. The solutions diverged: SPARTA pre-grew [`particle->particles`](../../build/tests_baseline/SPARTA/src/update.cpp) to `1.25 × nglobal_per_rank` so the pointer is stable across the run (see [`SPARTA/iter_1/opencode_stdout.txt`](../../build/iterative_logs/SPARTA_baseline/iter_1/opencode_stdout.txt) lines 113-150); HPCG iter 4 sidestepped the problem by storing only one `last_residual` double and reconstructing the array on restore (residuals are bit-identical because the CG problem is deterministic — see [`HPCG/iter_4/opencode_stdout.txt:393-418`](../../build/iterative_logs/HPCG_baseline/iter_4/opencode_stdout.txt)).
- **Trust deterministic re-init; checkpoint only the dynamic delta** — every app skips re-derivable state (geometry, decomposition, species, sparse matrix structure, multigrid hierarchy) and rebuilds it via the existing init paths on restart. Only what mutates inside the timed loop ends up in `Mem_protect`. Concrete examples: CoMD skips `Domain`/`LinkCell`/`SpeciesData` (see [`CoMD.md` § 1.4 state-coverage table](CoMD.md#state-coverage)); HPCG skips matrix `A` + multigrid hierarchy + `b/x/xexact` (see [`HPCG.md` § 1.4](HPCG.md#state-coverage)); SPARTA skips grid cells + RCB partition + mixture/computes/fixes (see [`SPARTA.md` § 1.4](SPARTA.md#state-coverage)).
- **Restart cadence selection by recovery-time math** — CoMD iter 2's fix (`COMD_CKPT_INTERVAL` 5 → 1, see [`build/tests_baseline/CoMD/src-mpi/CoMD.c#L215`](../../build/tests_baseline/CoMD/src-mpi/CoMD.c#L215)) and SPARTA's `veloc_ckpt_interval = 5000` ([`build/tests_baseline/SPARTA/src/update.cpp#L443`](../../build/tests_baseline/SPARTA/src/update.cpp#L443)) and HPCG's per-CG-set checkpoint are all driven by the 1.2× kill+recovery wall-time cap, not by I/O bandwidth concerns. CoMD's iter-2 reasoning is explicit in [`CoMD/iter_2/opencode_stdout.txt:23-50`](../../build/iterative_logs/CoMD_baseline/iter_2/opencode_stdout.txt): "kill at ~80s, recovery 99s → recovery redoes ~30s of work; reduce interval 5→1 so worst-case redo drops to ~10s".
- **No-Bash → static review only** — every iter-1 stdout contains a moment of *"I have no shell tool, so I'll do thorough static review"* followed by an N-point self-review checklist (CoMD: 12 points; HPCG: 9 points; SPARTA: 33 points; PRK_Stencil: 7 points). The LLM compensates by reading the full modified file end-to-end and cross-checking against in-repo VeloC references — except in PRK_Stencil iter 1, where the workspace contains NO VeloC reference at all and the LLM had to fall back to public-API training knowledge with explicit risk hedging (see [`PRK_Stencil/iter_1/opencode_stdout.txt:48-122`](../../build/iterative_logs/PRK_Stencil_baseline/iter_1/opencode_stdout.txt)).

### 1.2 Where the LLM consistently outperforms reference

- **Smaller per-frame payload** — by skipping immutable / re-derivable state, the LLM checkpoints are 1.3× (CoMD 149 MB vs ref 204 MB) to **12×** (HPCG 544 B vs ref 6 192 B) smaller per frame than the reference's full-state dumps. Numbers are sourced from [`build/validation_output/CoMD_baseline/benchmarks/raw_metrics.json`](../../build/validation_output/CoMD_baseline/benchmarks/raw_metrics.json) and [`build/validation_output/HPCG_baseline/benchmarks/raw_metrics.json`](../../build/validation_output/HPCG_baseline/benchmarks/raw_metrics.json) (`per_event_bytes_total`).
- **Lower recovery wall-time ratio when the harness contract is loose** — HPCG (0.56×) and PRK_Stencil (1.00×) beat the reference because the LLM's "shortcut to ReportResults / loop early-exit" (HPCG: [`main.cpp:518`](../../build/tests_baseline/HPCG/src/main.cpp#L518) sets `numberOfCgSets = cg_set_start`) exploits text-only validation contracts the reference doesn't optimise for. PRK_Stencil's keep_patterns are pure text (`Solution validates`, `Reference L1 norm`) so the validator extracts no numbers — see [`PRK_Stencil/iter_2/opencode_stdout.txt`](../../build/iterative_logs/PRK_Stencil_baseline/iter_2/opencode_stdout.txt).
- **Tighter checkpoint cadence under VeloC `mode=sync`** — CoMD's per-iter VeloC checkpoints (~10 s apart, [`CoMD.c#L215`](../../build/tests_baseline/CoMD/src-mpi/CoMD.c#L215)) are cheaper than reference's per-500-MD-step POSIX writes (~50 s apart, [`tests/apps/checkpointed/CoMD/src-mpi/CoMD.c#L140`](../../tests/apps/checkpointed/CoMD/src-mpi/CoMD.c#L140)), giving a smaller redo window and a 1.04× recovery ratio (vs reference's 1.16–1.32×).

### 1.3 Where the reference consistently outperforms LLM

- **Cumulative on-disk footprint when the reference uses overwrite semantics** — CoMD reference keeps **1 frame** (each rank overwrites [`CoMD_state-<rank>.txt`](../../tests/apps/checkpointed/CoMD/src-mpi/checkpoint.c#L208)) for a 204 MB total; LLM keeps 6 frames via VeloC's `max_versions=3` × 2 dirs for an 892 MB total — **4.4× larger**. Same shape for HPCG (1 vs 4 frames) and SPARTA (LLM is actually 3.4× smaller here because reference's `restart 2000` writes 82 retained files via [`write_restart.cpp`](../../tests/apps/checkpointed/SPARTA/src/write_restart.cpp)).
- **Output completeness for non-trivial validators** — reference implementations re-run the *full* loop on restart and produce complete benchmark reports (real GFLOP/s, full thermo history). The LLM's recovery shortcuts (HPCG `numberOfCgSets = cg_set_start` at [`main.cpp:518`](../../build/tests_baseline/HPCG/src/main.cpp#L518), SPARTA stdout-history replay at [`update.cpp:484`](../../build/tests_baseline/SPARTA/src/update.cpp#L484)) trade benchmark fidelity for staying under the 1.2× cap. A stricter validator that compared the full thermo timeline numerically would catch this.
- **Robustness to bigger problem sizes** — reference designs that walk the live data structure (CoMD's `nTotalBoxes` not `nLocalBoxes`, SPARTA's per-step `nlocal`) scale naturally; LLM's pre-grown ceilings (SPARTA 1.25× nglobal at [`update.cpp:484`](../../build/tests_baseline/SPARTA/src/update.cpp#L484)) waste memory and break if the steady-state `nlocal` exceeds the ceiling.

### 1.4 Token cost ladder (cheap → expensive bug categories)

1. **Cadence tuning** (~0.21 M tokens): change one constant. CoMD iter 2: `COMD_CKPT_INTERVAL_DEFAULT` 5 → 1 at [`CoMD.c#L215`](../../build/tests_baseline/CoMD/src-mpi/CoMD.c#L215) to shrink the redo window. Reasoning chain in [`CoMD/iter_2/opencode_stdout.txt:23-50`](../../build/iterative_logs/CoMD_baseline/iter_2/opencode_stdout.txt). Apps: **CoMD**.
2. **Validator-discovery cfg fix** (~0.17 M / 0.18 M / 0.54 M tokens for PRK_Stencil / HPCG / SPARTA): write a duplicate `veloc.cfg` at the codebase root. Same pattern across all 3 affected apps (see iter_2 logs above); cost varies because the LLM re-derives the rule each time. Apps: **HPCG, SPARTA, PRK_Stencil** iter 2.
3. **Loop-shape fix on a misdiagnosed root cause** (~1.04 M tokens, single iter): HPCG iter 3's `numberOfCgSets = cg_set_start` shortcut at [`main.cpp:504`](../../build/tests_baseline/HPCG/src/main.cpp#L504) — directionally correct but never triggered because the underlying checkpoints were broken (40 B/file vs expected 3464 B/file). Reasoning chain in [`HPCG/iter_3/opencode_stdout.txt:178-260`](../../build/iterative_logs/HPCG_baseline/iter_3/opencode_stdout.txt). Apps: **HPCG** iter 3.
4. **Variable-size array recovery** (~3.7 M / 6.8 M tokens for HPCG-iter-4 / SPARTA-iter-3): redesigning the protected-region layout to handle (a) drifting `numberOfCgSets` across restart-vs-original ([`HPCG/iter_4/opencode_stdout.txt:381-505`](../../build/iterative_logs/HPCG_baseline/iter_4/opencode_stdout.txt)) or (b) buffered stdout being lost on SIGKILL ([`SPARTA/iter_3/opencode_stdout.txt:80-225`](../../build/iterative_logs/SPARTA_baseline/iter_3/opencode_stdout.txt)). These are the single most expensive single-iter spends in the dataset and require deep cross-reading of validator + harness + library docs. Apps: **HPCG** iter 4, **SPARTA** iter 3.
5. **Greenfield integration with no Bash + no reference + no in-repo VeloC user** (~1.10 M tokens): PRK_Stencil iter 1 — the LLM had to derive the entire VeloC API surface from training-data knowledge of the public C header and document explicit risk hedges (e.g., `libveloc-client.so` vs `libveloc.so`, see [`PRK_Stencil/iter_1/opencode_stdout.txt:48-122`](../../build/iterative_logs/PRK_Stencil_baseline/iter_1/opencode_stdout.txt)). Apps: **PRK_Stencil** iter 1 (the only app where this happened — the others got to peek at in-repo VeloC examples via `task(explore)`).

## 2. Per-app summary table

| App | Iters | Wall | Tokens | LLM ckpt/frame | Ref ckpt/frame | LLM recovery | Ref recovery | One-line insight |
|---|---|---|---|---|---|---|---|---|
| [CoMD](CoMD.md) | 2 | 1238 s | 0.43 M | 149 MB | 204 MB | 1.04 × | 1.16 –1.32 × | Cadence-tuning is the cheapest fix mode in the dataset; LLM correctly identifies state on iter 1 and only mis-tunes one constant. |
| [HPCG](HPCG.md) | 4 | 2558 s | 5.32 M | 544 B | 6 192 B | 0.56 × | ~0.87 –0.90 × | Determinism insight (residuals are bit-identical across CG sets) compresses the checkpoint to 12 × smaller than reference, but only after diagnosing the 2-phase-recovery corruption bug in iter 4. |
| [SPARTA](SPARTA.md) | 3 | 3153 s | 7.64 M | 46 MB | 7.8 MB | 1.04 × | 1.06 × | Stdout-history mirror buffer (regions 4 & 5) is harness-induced state with no analogue in the reference; iter 3 spends 88 % of tokens diagnosing libc-buffered stdout loss on SIGKILL. |
| [PRK_Stencil](PRK_Stencil.md) | 2 | 616 s | 1.29 M | 652 MB | n/a — reference source exists, no benchmark run | 1.00 × | n/a — reference benchmark not collected | Smallest token spend of the four apps because the kernel is tiny (3 protected regions) and the validator extracts no numbers — text-only PASS. |

## 3. Index

Per-app reports (fast tier):
- [CoMD](CoMD.md)
- [HPCG](HPCG.md)
- [SPARTA](SPARTA.md)
- [Athena++](Athena++.md)
- [CLAMR](CLAMR.md)
- [PRK_Stencil](PRK_Stencil.md)

Cross-app analyses:
- [`_state_coverage_matrix.md`](_state_coverage_matrix.md) — normalised state-class × app matrix with heatmap
- Template: [_TEMPLATE.md](_TEMPLATE.md)
