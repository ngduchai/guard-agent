# `PRK_Stencil` — LLM Resilience Engineering Report

**App**: `PRK_Stencil` — Parallel Research Kernels barrier-free 2D star-stencil MPI proxy app (`COEFX·i + COEFY·j` initial field, RADIUS-1 stencil, accumulating output grid)
**Vanilla source**: [`tests/apps/vanillas/PRK_Stencil/`](../../tests/apps/vanillas/PRK_Stencil/)
**Reference source**: [`tests/apps/checkpointed/PRK_Stencil/`](../../tests/apps/checkpointed/PRK_Stencil/)
**LLM-generated source**: [`build/tests_baseline/PRK_Stencil/`](../../build/tests_baseline/PRK_Stencil/)
**Iteration outcome**: PASS in **2 iters** / **701 s** wall / **0.18 M tokens** (smallest token cost of the fast tier)

---

## 1. LLM Methodology

### 1.1 Overall reasoning process (text/table DAG)

A turn-by-turn record of LLM thought↔action across both iterations,
distilled from the long structured chain in
[`iter_1/opencode_stdout.txt`](../../build/iterative_logs/PRK_Stencil_baseline/iter_1/opencode_stdout.txt)
(7 distinct turns: layout → app/algorithm → state-evolution audit → VeloC location → design plan + corner-case enumeration → integration into stencil.c/Makefile/veloc.cfg → static self-review)
and the very short triage chain in
[`iter_2/opencode_stdout.txt`](../../build/iterative_logs/PRK_Stencil_baseline/iter_2/opencode_stdout.txt)
(3 turns: error grep → cfg search-path discovery → one-file copy). Iter 1 input was only **20k tokens** — the smallest first-pass cost of the fast-tier apps.

### Iter 1 — 428s — ❌ FAIL

| Turn | 🧠 Thought | 🔧 Action |
|:---:|---|---|
| **1.a** | What app is this and what does the comparator key on? | list [PRK_Stencil/](../../build/tests_baseline/PRK_Stencil/) + read [app.yaml](../../build/tests_baseline/PRK_Stencil/app.yaml) + [prompt.txt](../../build/tests_baseline/PRK_Stencil/prompt.txt) → PRK Stencil MPI1 (C, 4-rank `2×2`, 16500 iters × 4000² grid, ~120 s baseline); validates on `"Solution validates"` substring with `tolerance=0.001`. |
| **1.b** | Where is the timestep loop, what's the per-iteration mutable state? | read [stencil.c](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c) + [Makefile](../../build/tests_baseline/PRK_Stencil/Stencil/Makefile) + [common/make.common](../../build/tests_baseline/PRK_Stencil/common/make.common) → main loop is `for (iter=0; iter<=iterations; iter++)` at L330; *"out[] is **accumulated** across iterations (line 412–414 use `+=`), so it absolutely must be checkpointed. in[] is updated at line 420 (`IN(i,j) += 1.0`); also must be checkpointed. Halo buffers are overwritten before use → no need to checkpoint. All other state is deterministic from arguments and can be reconstructed."* |
| **1.c** | Where is VeloC installed and what API surface? | grep `VELOC_DIR\|veloc-client` across the repo → finds the Quicksilver reference Makefile/main.cc (`/home/ndhai/usr` install, `-lveloc-client`, `Init/Mem_protect/Restart_test/Restart_begin/Recover_mem/Restart_end/Checkpoint_begin/Checkpoint_mem/Checkpoint_end/Finalize`). Direct read of `/home/ndhai/usr/include/veloc.h` is denied by sandbox → API inferred from Quicksilver. |
| **1.d** | Design plan: 3 protect regions (`iter`, `in`, `out`); cadence `iterations/20` ≈ 825 iters ≈ 6 s apart, ≈20 frames over the run; save `iter+1` to avoid double-accumulation on resume; init `local_stencil_time` after restart so the post-loop reduce stays well-defined. | enumerate 17 corner cases verbatim in [`opencode_stdout.txt`](../../build/iterative_logs/PRK_Stencil_baseline/iter_1/opencode_stdout.txt) (no-checkpoint first run, restart at iter > 1 → timer init, restart at iter==0, restart at iter==iterations+1, init failure, recovery failure, halo staleness OK, name/ID uniqueness, MPI/VeloC ordering, etc.). |
| **1.e** | Wire VeloC into the build the canonical way (mirror Quicksilver). | edit [Stencil/Makefile](../../build/tests_baseline/PRK_Stencil/Stencil/Makefile) — add `VELOC_DIR ?= /home/ndhai/usr`, `-I$(VELOC_DIR)/include` into INCLUDEPATHS, `-L$(VELOC_DIR)/lib -Wl,-rpath,$(VELOC_DIR)/lib` into LIBPATHS, `-lveloc-client` into LIBS. |
| **1.f** | Integrate Init/protect/Restart/Checkpoint/Finalize into main; `#include <veloc.h>` + 3 protect IDs (`ITER=0`, `IN=1`, `OUT=2`); change `for (iter=0; …)` → `for (; …)` so the restored counter isn't overwritten. | edit [Stencil/stencil.c:73-81](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L73), [L156-172](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L156) (Init+abort), [L357-412](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L357) (3× Mem_protect + Restart probe), [L416-425](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L416) (cadence + post-restart timer init), [L519-547](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L519) (end-of-iter checkpoint with `iter+1` swap dance), [L602-603](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L602) (Finalize). |
| **1.g** | No Bash → static self-review (variable shadowing, mid-block decls under c99/c11, MPI↔VeloC ordering, `bail_out` collectivity, halo invariant, comparator semantics — concludes only `"Solution validates"` line is compared, no numbers extracted, so timing skew on rate is irrelevant). | write [Stencil/veloc.cfg](../../build/tests_baseline/PRK_Stencil/Stencil/veloc.cfg) (`mode=sync`, `scratch=/tmp/stencil_scratch`, `persistent=/tmp/stencil_persistent`, `max_versions=3`). |

> ❌ **RESULT**: validator fatal *before* MPI launch — `"No VeloC checkpoint directories resolved from veloc.cfg under /home/ndhai/diaspora/guard-agent/build/tests_baseline/PRK_Stencil"`. The cfg was written to `Stencil/veloc.cfg` but the harness probes `<source_dir>/veloc.cfg` (codebase root), not the run-cwd. Code edits all correct; deployment config misplaced.

→ **Feedback into iter 2**: `validate_stderr` quotes the exact "checkpoint-observed strategy needs scratch/persistent paths to poll. Either ship a valid veloc.cfg or use the legacy fixed-delay strategy."

### Iter 2 — 272s — ✅ PASS

| Turn | 🧠 Thought | 🔧 Action |
|:---:|---|---|
| **2.a** | Quote the exact error and form a hypothesis: validator looks for `veloc.cfg` somewhere it isn't. | read [iter_1/validate_stderr.txt](../../build/iterative_logs/PRK_Stencil_baseline/iter_1/validate_stderr.txt). |
| **2.b** | Find where the validator searches. | grep `"No VeloC checkpoint directories resolved"` in repo → `runner.py:1487-1494` only probes `<source_dir>/veloc.cfg` and `<build_dir>/veloc.cfg`; cfg was at `Stencil/veloc.cfg`, one level too deep. |
| **2.c** | One-file fix — copy the existing cfg byte-for-byte to the codebase root. The runtime `VELOC_Init("veloc.cfg")` still finds it at run-cwd `Stencil/`, AND the harness now resolves it from the source root. | write [PRK_Stencil/veloc.cfg](../../build/tests_baseline/PRK_Stencil/veloc.cfg) (identical content to `Stencil/veloc.cfg`). |

> ✅ **RESULT**: 24 ckpt files observed; kill+recovery `121.0 s / 121.8 s = 0.99 ×` (well under the 1.20 × cap); both failure-prone and failure-free outputs PASS (`No numbers to compare` since only `"Solution validates"` survives the keep-pattern filter).

**Sources** (clickable):
- Iter 1: [`opencode_stdout.txt`](../../build/iterative_logs/PRK_Stencil_baseline/iter_1/opencode_stdout.txt), [`inspection.json`](../../build/iterative_logs/PRK_Stencil_baseline/iter_1/inspection.json), [`validate_stderr.txt`](../../build/iterative_logs/PRK_Stencil_baseline/iter_1/validate_stderr.txt)
- Iter 2: [`opencode_stdout.txt`](../../build/iterative_logs/PRK_Stencil_baseline/iter_2/opencode_stdout.txt), [`inspection.json`](../../build/iterative_logs/PRK_Stencil_baseline/iter_2/inspection.json), [`validate_stdout.txt`](../../build/iterative_logs/PRK_Stencil_baseline/iter_2/validate_stdout.txt)

### 1.2 Critical state identification

| Question | Answer |
|---|---|
| Detection algorithm | Read [`stencil.c`](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c) end-to-end and traced the only loop ([L330](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L330) in the original / [L427](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L427) post-edit) field-by-field. Verbatim from [`iter_1/opencode_stdout.txt`](../../build/iterative_logs/PRK_Stencil_baseline/iter_1/opencode_stdout.txt): *"Per-iteration state that evolves: in[] (the grid with halo), out[] (output, accumulated with `+=`), and iter itself. Halo buffers (top_buf_*, etc.) are only valid during a single iteration's halo exchange and are overwritten before use → no need to checkpoint. All other state (weight, dimensions, neighbors, ranks) is deterministic from arguments and can be reconstructed."* |
| Source tools / queries the LLM used | `read` [`stencil.c`](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c), [`Stencil/Makefile`](../../build/tests_baseline/PRK_Stencil/Stencil/Makefile), [`common/make.common`](../../build/tests_baseline/PRK_Stencil/common/make.common), [`MPI.defs`](../../build/tests_baseline/PRK_Stencil/common/MPI.defs), [`make.defs`](../../build/tests_baseline/PRK_Stencil/common/make.defs), [`include/par-res-kern_general.h`](../../build/tests_baseline/PRK_Stencil/include/par-res-kern_general.h), [`include/par-res-kern_mpi.h`](../../build/tests_baseline/PRK_Stencil/include/par-res-kern_mpi.h), [`MPI_bail_out.c`](../../build/tests_baseline/PRK_Stencil/common/MPI_bail_out.c), [`app.yaml`](../../build/tests_baseline/PRK_Stencil/app.yaml); `grep "veloc\|VeloC\|VELOC"` across repo → Quicksilver reference; read [`Quicksilver/src/main.cc`](../../tests/ecp/ref-resilient/Quicksilver/src/main.cc) and [`Quicksilver/src/Makefile`](../../tests/ecp/ref-resilient/Quicksilver/src/Makefile) for canonical API/flags; read [`Quicksilver/veloc.cfg`](../../tests/ecp/ref-resilient/Quicksilver/veloc.cfg) for cfg format. Direct read of `/home/ndhai/usr/include/veloc.h` and globs outside `/home/ndhai/diaspora/guard-agent` were denied by sandbox. |
| State considered & rejected | (a) Halo communication buffers `top/bottom/right/left_buf_*` — *"refilled from neighbours at the top of every iteration before being read"*; (b) `weight[][]` array — *"computed once from RADIUS, never modified"*; (c) Decomposition geometry (`Num_procsx/y`, `my_IDx/y`, `istart/iend/jstart/jend`, `width`, `height`, neighbour ranks) — derived deterministically from CLI args + rank id; (d) CLI inputs (`iterations`, `n`) — re-parsed on restart from `argv`; (e) `local_stencil_time` — re-initialized after restart (see corner case in [stencil.c:423-425](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L423)). |
| State eventually protected | 3 regions registered with `VELOC_Mem_protect` ([stencil.c:370-376](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L370)): `iter` (4 B), `in` (`(width+2·RADIUS) × (height+2·RADIUS) × sizeof(DTYPE)`), `out` (`width × height × sizeof(DTYPE)`). Per-rank checkpoint payload **64.1 MiB** measured; per-frame total ≈ **244.6 MiB across 4 ranks**. |

(Source: [`iter_1/opencode_stdout.txt`](../../build/iterative_logs/PRK_Stencil_baseline/iter_1/opencode_stdout.txt) design-plan + corner-case sections.)

### 1.3 Protection + recovery algorithm

```pseudocode
ON STARTUP:
  1. MPI_Init(&argc, &argv)                                # stencil.c:152
     MPI_Comm_rank/size                                    # stencil.c:153-154
  2. cfg = getenv("VELOC_CFG") ?? "veloc.cfg"              # stencil.c:162
     IF VELOC_Init(MPI_COMM_WORLD, cfg) != SUCCESS:
        MPI_Abort(MPI_COMM_WORLD, 1)                       # stencil.c:170
  3. parse iterations, n; broadcast; compute decomposition
  4. allocate in[], out[], halo buffers (unchanged)
  5. iter = 0                                              # stencil.c:369
     VELOC_Mem_protect(0, &iter, 1, sizeof(int))           # stencil.c:370
     VELOC_Mem_protect(1, in,  (W+2R)*(H+2R), sizeof(DTYPE)) # stencil.c:371
     VELOC_Mem_protect(2, out, W*H,           sizeof(DTYPE)) # stencil.c:374
  6. v = VELOC_Restart_test("stencil", 0)                  # stencil.c:385
     IF v > 0:
        VELOC_Restart_begin → Recover_mem → Restart_end    # stencil.c:388-392
        IF !restart_ok: bail_out(1)                        # stencil.c:394-403
        # iter, in, out are now restored

DURING COMPUTATION:
  ckpt_interval = (iterations >= 20) ? iterations/20 : 1   # stencil.c:416
  IF iter > 1: local_stencil_time = wtime()                # stencil.c:423-425
  for (; iter <= iterations; iter++):                      # stencil.c:427
     halo-exchange (4 directions, Isend/Irecv/Wait)
     apply stencil → out[i,j] += weight·in[i+ii,j+jj]      # stencil.c:509-511
     in[i,j] += 1.0                                        # stencil.c:517
     IF (iter+1) % ckpt_interval == 0 OR iter == iterations:
        saved_iter = iter+1                                # stencil.c:530
        iter       = saved_iter   # so checkpoint sees resume-point
        VELOC_Checkpoint_begin/Checkpoint_mem/Checkpoint_end(saved_iter)
        iter       = prev_iter    # restore for the for-loop's iter++

ON SHUTDOWN:
  L1-norm reduction, "Solution validates" print
  VELOC_Finalize(1)                                        # stencil.c:603
  MPI_Finalize()
```

(Pseudocode reflects the LLM's actual implementation in [`build/tests_baseline/PRK_Stencil/Stencil/stencil.c`](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c).)

### 1.4 LLM vs reference comparison

#### State coverage

| Application state | LLM | Reference | Notes |
|---|:---:|:---:|---|
| `iter` (loop counter) | ☑ | ☑ | LLM saves `iter+1` (resume-point) via swap dance; reference saves `iter` and re-tests `iter % ckpt_every` post-restart, guarded by a `loaded` flag to suppress the immediate re-checkpoint. |
| `in[]` (input grid + halo) | ☑ | ☑ | Both save the full `(W+2R)·(H+2R)` slab. |
| `out[]` (accumulating output grid) | ☑ | ☑ | Both save the full `W·H` slab — required because of the `+=` accumulation. |
| Halo communication buffers | ☐ | ☐ | Both skip — refilled by `MPI_Isend/Irecv` at the top of every iteration. |
| `weight[2R+1][2R+1]` stencil weights | ☐ | ☐ | Both skip — computed once from `RADIUS` constant. |
| Decomposition (`Num_procsx/y`, `my_IDx/y`, `istart/iend`, neighbours, `width/height`) | ☐ | ☐ (header only) | LLM re-derives from CLI args + rank id; reference writes a `prk_ckpt_header` with `width/height/radius/Num_procs/iter` for restart-time validation but recomputes the geometry. |
| `local_stencil_time` (timer) | ☐ (re-init at restart) | ☐ (re-init at restart) | Both re-initialize via `wtime()` after a successful resume past `iter==1`. |

#### Checkpoint strategy

| Aspect | LLM | Reference |
|---|---|---|
| Where checkpoint is invoked (`file:func:line`) | [`Stencil/stencil.c:main:534`](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L534) (`VELOC_Checkpoint_begin/_mem/_end`) | [`Stencil/stencil.c:main:530`](../../tests/apps/checkpointed/PRK_Stencil/Stencil/stencil.c#L530) → `prk_ckpt_save()` (POSIX `write` to `CKPT_DIR/stencil_ckpt.<rank>.bin`) |
| Which process(es) invoke | All 4 MPI ranks (each writes its own VeloC per-rank file) | All 4 ranks (each writes its own per-rank `.bin`) |
| Cadence | `iterations/20` ≈ every 825 outer iters (≈20 frames over the 16500-iter run) — also forced on the final iter | Every 500 iters (`CKPT_EVERY` default; ≈33 events over 16500 iters), suppressed on the iteration immediately after a successful restart |
| Per-write storage (per-frame, all ranks) | **256 512 704 B (≈ 244.6 MiB)** | **256 512 624 B (≈ 244.6 MiB)** (delta = 80 B = 20 B header × 4 ranks; payload size identical) |
| Frames retained on disk | **6** (`max_versions=3` × 2 dirs scratch+persistent: 6 files / rank × 4 ranks = 24 files; 6 logical frames) | **1** (each rank overwrites the same `stencil_ckpt.<rank>.bin`) |
| Cumulative on disk at end | **1 539 076 224 B (≈ 1.43 GiB)** across 24 files | **256 512 624 B (≈ 244.6 MiB)** across 4 files |

(Per-frame metrics from [`build/validation_output/PRK_Stencil_baseline/benchmarks/raw_metrics.json`](../../build/validation_output/PRK_Stencil_baseline/benchmarks/raw_metrics.json) and [`build/validation_output/PRK_Stencil_reference/benchmarks/raw_metrics.json`](../../build/validation_output/PRK_Stencil_reference/benchmarks/raw_metrics.json).)

#### Recovery strategy

| Aspect | LLM | Reference |
|---|---|---|
| Where recovery is detected (`file:line`) | [`Stencil/stencil.c:385`](../../build/tests_baseline/PRK_Stencil/Stencil/stencil.c#L385) — `VELOC_Restart_test("stencil", 0)` returns latest version | [`Stencil/stencil.c:387`](../../tests/apps/checkpointed/PRK_Stencil/Stencil/stencil.c#L387) — `prk_ckpt_load()` opens per-rank file, validates magic + header, restores `iter/in/out` |
| What's done after restore | All 3 protected regions overwritten in place by `VELOC_Recover_mem`; loop resumes at restored `iter` (which is `saved_iter = old_iter+1`); next halo exchange refills buffers; if `iter > 1` the post-restart `wtime()` re-init keeps `local_stencil_time` finite | `loaded_iter`, `in[]`, `out[]` deserialized; `iter = loaded_iter`; `loaded=1` flag suppresses the checkpoint that would otherwise immediately re-trigger; loop resumes |
| Time to recover (kill+recovery / failure-free baseline) | **0.99 ×** (121.0 s / 121.8 s; iter-2 PASS) — well under the 1.2 × production cap | Reference benchmark `small-once` mean **719 s** vs `original` mean **120 s** (**~6.0 ×**) — reference pays a much larger overhead because `prk_ckpt_save` writes 33 frames × 244 MiB synchronously per run via blocking POSIX `write` without VeloC's overlap |
| Output correctness | `"Solution validates"` printed by both failure-prone and failure-free runs (numeric comparator: *"No numbers to compare"* → PASS) | `"Solution validates"` printed; reference run also passes correctness in benchmarks |

---

**Key observations**
- LLM converges in **2 iters / 0.18 M tokens** — the smallest token budget of the fast tier (< CoMD's 0.43 M). Iter 1 input was only 20 k tokens because the codebase is single-file with one obvious loop and three obvious mutable arrays.
- The iter-1 failure is **not a code defect**: all VeloC instrumentation, state coverage, cadence, and corner-case handling were correct on the first try. The fix in iter 2 was a pure deployment-config relocation (move `veloc.cfg` from `Stencil/` to the codebase root where the validator's harness probes for it). No source edits in iter 2.
- LLM's per-frame payload (~244.6 MiB) matches the reference almost exactly (same three arrays, same sizes); the only delta is a tiny 20 B/rank header overhead in the reference. Cumulative footprint is ~6 × larger because LLM keeps 6 retained versions vs reference's 1 — a tunable (`max_versions`).
- LLM achieves a dramatically **lower** kill+recovery ratio (0.99 ×) than the reference's failure-free overhead (~5.6 × over original) because VeloC under `mode=sync` overlaps writes far more efficiently than the reference's blocking POSIX `write` of the full 244 MiB snapshot, and because the LLM checkpoints less frequently (~20 frames vs 33).
- Simplest state to checkpoint of any fast-tier app: 3 contiguous `Mem_protect` regions, no halo zone bookkeeping, no MPI-buffer reconstruction, no force/velocity arrays, no link-cell data structure. That minimalism is what made convergence so cheap.
