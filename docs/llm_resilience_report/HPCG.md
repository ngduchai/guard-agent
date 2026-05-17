# `HPCG` — LLM Resilience Engineering Report

**App**: `HPCG` — High-Performance Conjugate Gradient benchmark (sparse SpMV + multigrid preconditioner; timed CG-sets phase is the dominant runtime loop)
**Vanilla source**: [`tests/apps/vanillas/HPCG/`](../../tests/apps/vanillas/HPCG/)
**Reference source**: [`tests/apps/checkpointed/HPCG/`](../../tests/apps/checkpointed/HPCG/)
**LLM-generated source**: [`build/tests_baseline/HPCG/`](../../build/tests_baseline/HPCG/)
**Iteration outcome**: PASS in **2 iters** / **847 s** wall / **0.35 M tokens**

---

## 1. LLM Methodology

### 1.1 Overall reasoning process (text/table DAG)

A turn-by-turn record of LLM thought↔action across both iterations,
distilled from the literal `Intent → Motivation → Expectation → Result`
chain in
[`iter_1/opencode_stdout.txt`](../../build/iterative_logs/HPCG_baseline/iter_1/opencode_stdout.txt)
(11 turns: layout → app.yaml + xhpcg_run wrapper → loop discovery → VeloC search → guide read → Quicksilver template read → design plan → Make.Linux_MPI edit → main.cpp edit → veloc.cfg + wrapper edit → static self-review with two-phase-restart → fixed-buffer refactor)
and the very short chain in
[`iter_2/opencode_stdout.txt`](../../build/iterative_logs/HPCG_baseline/iter_2/opencode_stdout.txt)
(3 turns: parse fatal validator error → grep validator probe paths → copy `veloc.cfg` to source root).

### Iter 1 — 526s — ❌ FAIL

| Turn | 🧠 Thought | 🔧 Action |
|:---:|---|---|
| **1.a** | What's the layout, what does validation key on, where does the binary actually run? | list [HPCG/](../../build/tests_baseline/HPCG/) + read [app.yaml](../../build/tests_baseline/HPCG/app.yaml) + [prompt.txt](../../build/tests_baseline/HPCG/prompt.txt) + [QUICKSTART](../../build/tests_baseline/HPCG/QUICKSTART) → 4-rank `mpirun … ./xhpcg_run --nx=32 --ny=32 --nz=32 --rt=120` from `bin/`; comparator keys on `HPCG_VALIDATION=` line written by the wrapper iff the report contains `"HPCG result is VALID"`. |
| **1.b** | Where is the timed loop and what state mutates inside it? | read [main.cpp](../../build/tests_baseline/HPCG/src/main.cpp) → outer loop is `for (int i=0; i<numberOfCgSets; ++i)` (the **Optimized CG Timing Phase**); each `CG()` call is independent (`ZeroVector(x)` first), so the only loop-carried state is the index `i`, accumulators `times[0..9]`, and the per-set residual array `testnorms_data.values[]`. |
| **1.c** | `xhpcg_run` is named in app.yaml but `Makefile` builds `xhpcg` — is it a wrapper? | read [bin/xhpcg_run](../../build/tests_baseline/HPCG/bin/xhpcg_run) → shell wrapper that execs `xhpcg`, then on rank 0 prints `HPCG_VALIDATION=PASSED/FAILED` based on grepping the report file. |
| **1.d** | Where is VeloC installed? | grep+glob across the workspace → VeloC at `/home/ndhai/usr` (header `include/veloc.h`, lib `lib/libveloc-client.so`); also discover sibling resilient app **Quicksilver** + canonical [`veloc_guide.md`](../../guard_agent/guides/veloc_guide.md). |
| **1.e** | What's the canonical pattern in this repo? | read VeloC guide + Quicksilver Makefile/main.cc → use `-DHAVE_VELOC -I…/include`, link `-Wl,-rpath,…/lib -lveloc-client`; canonical call sequence: `VELOC_Init` after `MPI_Init` → `Mem_protect` → `Restart_test` → `Restart` → `Checkpoint(name, version)` → `Finalize(1)`; `veloc.cfg` must be in PWD. |
| **1.f** | Design plan: protect everything that determines post-loop `TestNorms` + `ReportResults` outputs — `i`, `numberOfCgSets`, `optMaxIters`, `optNiters`, `optTolerance`, `opt_worst_time`, `err_count`, `tolerance_failures`, `global_failure`, `times[10]`, and the `numberOfCgSets`-sized residual array. Checkpoint **every iteration** because each CG set is multi-second and we need a recent frame before the 95% kill point. | (planning turn — no edit) |
| **1.g** | Edit the build system. | edit [setup/Make.Linux_MPI](../../build/tests_baseline/HPCG/setup/Make.Linux_MPI) — append `-DHAVE_VELOC -I/home/ndhai/usr/include` to compile flags, `-L/home/ndhai/usr/lib -Wl,-rpath,/home/ndhai/usr/lib -lveloc-client` to link flags. |
| **1.h** | Variable-size `testnorms_data.values[numberOfCgSets]` would force a two-phase restart (recover `numberOfCgSets` first, then allocate, then recover the array). That ordering against `VELOC_Restart_begin/Recover_selective/Restart_end` twice for the same version is **unverified** — flag risk in self-review. | (initial drafting of [main.cpp](../../build/tests_baseline/HPCG/src/main.cpp) edits) |
| **1.i** | Refactor: embed residuals as a fixed-size `double cg_residuals[MAX_CG_SETS=2048]` field inside the protected `VelocCkptHeader` struct → one contiguous region, single `VELOC_Mem_protect`, single-phase `VELOC_Restart`. 16 KB extra per rank is negligible. | edit [main.cpp:381-502](../../build/tests_baseline/HPCG/src/main.cpp#L381) — define struct, allocate on heap, register at id=0, `VELOC_Restart_test`/`VELOC_Restart` at L425-454, per-iteration `VELOC_Checkpoint("hpcgckpt", i+1)` at L483, and a final post-loop checkpoint at L497 covering a failure between the loop and `ReportResults`. |
| **1.j** | Need `veloc.cfg` accessible at runtime PWD (`bin/`); let the wrapper symlink it just like `hpcg.dat`. | write [bin/veloc.cfg](../../build/tests_baseline/HPCG/bin/veloc.cfg) (`mode=sync`, `scratch=/tmp/hpcg_veloc_scratch`, `persistent=/tmp/hpcg_veloc_persistent`, `max_versions=3`, `scratch_versions=3`); edit [bin/xhpcg_run](../../build/tests_baseline/HPCG/bin/xhpcg_run) to symlink `veloc.cfg` into PWD and `mkdir -p` the `/tmp` dirs. |
| **1.k** | Static review: 12-point checklist covering MPI ordering, `Mem_protect` ID uniqueness, struct layout, `delete ckpt_hdr` lifetime vs. `VELOC_Finalize`, fresh-vs-stale checkpoint behavior across independent test runs. All items resolved positively except for one architectural concern (cross-test isolation) which is delegated to the validation framework, matching Quicksilver's pattern. | (review only) |

> ❌ **RESULT**: validator aborted in the Correctness stage **before any LLM-modified code ran** — `[validate] FATAL: No VeloC checkpoint directories resolved from veloc.cfg under <source_dir> or <build_dir>`. The validator's checkpoint-observed injection strategy probes for `veloc.cfg` at the resilient codebase root (and the install/build root) to learn which `/tmp/...` directories to poll for new checkpoint files; the LLM had only placed the file under `bin/` (where the runtime executes from), so the discovery probe failed.

→ **Feedback into iter 2**: `validate_stderr: "[validate] FATAL: No VeloC checkpoint directories resolved from veloc.cfg under /home/ndhai/diaspora/guard-agent/build/tests_baseline/HPCG or .../build/resilient. The checkpoint-observed injection strategy needs scratch/persistent paths to poll. Either ship a valid veloc.cfg or use the legacy fixed-delay strategy."`

### Iter 2 — 320s — ✅ PASS

| Turn | 🧠 Thought | 🔧 Action |
|:---:|---|---|
| **2.a** | The error names two probe locations and neither is `bin/`. Hypothesize: validator parses `scratch=`/`persistent=` from a `veloc.cfg` at the source/build root to know where to poll; the runtime separately reads `veloc.cfg` from PWD (`bin/`) via `VELOC_Init`. So I need **two** identical files: one for the validator, one for the runtime. | read [iter_1/validate_stderr.txt](../../build/iterative_logs/HPCG_baseline/iter_1/validate_stderr.txt) + grep validator runner code → confirms `build_dir/veloc.cfg` then `source_dir/veloc.cfg` are the only probe paths. |
| **2.b** | Add a duplicate `veloc.cfg` at the source root; `bin/veloc.cfg` stays so runtime behavior is unchanged. Both files name the same `/tmp/hpcg_veloc_*` paths, so the polled dirs match what the running process actually writes to. | write [veloc.cfg](../../build/tests_baseline/HPCG/veloc.cfg) at source root with identical `scratch=`/`persistent=` lines (only a comment header differs). |
| **2.c** | Self-review: no functional source change is needed — iter-1 main.cpp/Makefile/wrapper were correct; only the discoverability shim was missing. | (no further edit) |

> ✅ **RESULT**: kill+recovery `123.71 s / 119.7 s = 1.03×` (well under 1.20× cap); 24 checkpoint files observed; both failure-prone and failure-free runs produce stdout matching the cached baseline (`HPCG_VALIDATION=PASSED`).

**Sources** (clickable):
- Iter 1: [`opencode_stdout.txt`](../../build/iterative_logs/HPCG_baseline/iter_1/opencode_stdout.txt), [`inspection.json`](../../build/iterative_logs/HPCG_baseline/iter_1/inspection.json), [`validate_stderr.txt`](../../build/iterative_logs/HPCG_baseline/iter_1/validate_stderr.txt), [`validate_stdout.txt`](../../build/iterative_logs/HPCG_baseline/iter_1/validate_stdout.txt)
- Iter 2: [`opencode_stdout.txt`](../../build/iterative_logs/HPCG_baseline/iter_2/opencode_stdout.txt), [`inspection.json`](../../build/iterative_logs/HPCG_baseline/iter_2/inspection.json), [`validate_stdout.txt`](../../build/iterative_logs/HPCG_baseline/iter_2/validate_stdout.txt)

### 1.2 Critical state identification

| Question | Answer |
|---|---|
| Detection algorithm | Read [`main.cpp`](../../build/tests_baseline/HPCG/src/main.cpp) end-to-end to locate the **Optimized CG Timing Phase** loop (the only loop sized by the user-controlled `--rt=120` walltime), then traced each variable consumed *after* the loop by `TestNorms` and `ReportResults` to decide what must be restored vs. what is re-derivable. Verbatim from [`iter_1/opencode_stdout.txt`](../../build/iterative_logs/HPCG_baseline/iter_1/opencode_stdout.txt): *"Each `CG` call is independent (it `ZeroVector(x)` first, so iteration `i` does not depend on x from `i-1`). The state to checkpoint per iteration is the loop counter `i` and `testnorms_data.values[0..i-1]`."* |
| Source tools / queries the LLM used | `read` [`main.cpp`](../../build/tests_baseline/HPCG/src/main.cpp), [`Make.Linux_MPI`](../../build/tests_baseline/HPCG/setup/Make.Linux_MPI), [`xhpcg_run`](../../build/tests_baseline/HPCG/bin/xhpcg_run), [`app.yaml`](../../build/tests_baseline/HPCG/app.yaml), [`prompt.txt`](../../build/tests_baseline/HPCG/prompt.txt), [`QUICKSTART`](../../build/tests_baseline/HPCG/QUICKSTART), [`ReportResults.cpp`](../../build/tests_baseline/HPCG/src/ReportResults.cpp), [`TestNorms.cpp`](../../build/tests_baseline/HPCG/src/TestNorms.cpp); `glob` for `veloc.h`/`libveloc*` to locate VeloC at `~/usr`; `grep` for `veloc` in workspace → discover canonical [`veloc_guide.md`](../../guard_agent/guides/veloc_guide.md) and Quicksilver reference. |
| State considered & rejected | (a) Per-CG-call inner state (`r`, `z`, `p`, `Ap` Vectors inside `data`) — re-zeroed each iter by `ZeroVector(x)` at loop top, never carries across iters. (b) `SparseMatrix A` and multigrid hierarchy — built once by `GenerateProblem`/`GenerateCoarseProblem`, deterministic given `nx,ny,nz`. (c) `TestCG`/`TestSymmetry` results — re-run from scratch on restart, deterministic. (d) `params.runningTime` and CLI args — re-parsed from same argv. (e) Halo-exchange MPI buffers — recreated by `SetupHalo`. (f) HPCG_fout per-rank log lines — only stdout `HPCG_VALIDATION=` line gates correctness, and that's emitted by the wrapper after the (post-restart) report file is written. |
| State eventually protected | One `VELOC_Mem_protect` region (id=0) covering a single fixed-size `VelocCkptHeader` struct: `i`, `numberOfCgSets`, `optMaxIters`, `optNiters`, `optTolerance`, `opt_worst_time`, `err_count`, `tolerance_failures`, `global_failure`, `times[10]`, `cg_residuals[MAX_CG_SETS=2048]`. Per-rank declared payload `sizeof(VelocCkptHeader)` ≈ 16 KB; per-rank on-disk per frame **66 128 B** (declared + VeloC metadata; observed in raw_metrics) → 264 512 B per logical frame across 4 ranks. |

(Source: [`iter_1/opencode_stdout.txt`](../../build/iterative_logs/HPCG_baseline/iter_1/opencode_stdout.txt) design-plan + post-refactor self-review sections.)

### 1.3 Protection + recovery algorithm

```pseudocode
ON STARTUP:
  1. MPI_Init(&argc, &argv)                                     # main.cpp:81
  2. VELOC_Init(MPI_COMM_WORLD, "veloc.cfg")                    # main.cpp:88
  3. HPCG_Init; problem setup; reference SpMV/MG/CG timing;
     TestCG; OptimizeProblem; TestSymmetry                      # main.cpp (unchanged)
  4. # After numberOfCgSets is derived from opt_worst_time:
     ckpt_hdr = new VelocCkptHeader(); memset(0)                # main.cpp:396-397
     ckpt_hdr->{i,numberOfCgSets,optMaxIters,optNiters,
                optTolerance,opt_worst_time,
                err_count,tolerance_failures,global_failure,
                times[10]} = current values                     # main.cpp:398-407
     IF numberOfCgSets <= MAX_CG_SETS:
        VELOC_Mem_protect(0, ckpt_hdr, 1, sizeof(...))          # main.cpp:419
  5. v = VELOC_Restart_test("hpcgckpt", 0)                       # main.cpp:426
     IF v > 0 AND VELOC_Restart("hpcgckpt", v) == SUCCESS:       # main.cpp:433
        # Single-phase restart populates the entire header.
        Overwrite local numberOfCgSets, optMaxIters, optNiters,
        optTolerance, opt_worst_time, err_count,
        tolerance_failures, global_failure, times[0..9]
        from ckpt_hdr->...                                       # main.cpp:435-443
  6. testnorms_data.values = new double[numberOfCgSets]          # main.cpp:460
     for k in [0, ckpt_hdr->i):
        testnorms_data.values[k] = ckpt_hdr->cg_residuals[k]     # main.cpp:461-463

DURING COMPUTATION:
  for (int i = ckpt_hdr->i; i < numberOfCgSets; ++i):           # main.cpp:465
     ZeroVector(x); CG(A, data, b, x, optMaxIters, optTolerance,
                       niters, normr, normr0, &times[0], true)   # main.cpp:466-467
     testnorms_data.values[i] = normr / normr0                   # main.cpp:470
     IF numberOfCgSets <= MAX_CG_SETS:                           # main.cpp:475
        ckpt_hdr->i = i + 1
        ckpt_hdr->{optMaxIters,optTolerance,err_count,
                   global_failure,times[10]} = current
        ckpt_hdr->cg_residuals[i] = testnorms_data.values[i]
        VELOC_Checkpoint("hpcgckpt", i + 1)                      # main.cpp:483

POST-LOOP (covers failure between loop end and ReportResults):
  IF numberOfCgSets <= MAX_CG_SETS:
     ckpt_hdr->i = numberOfCgSets                                # main.cpp:494
     ckpt_hdr->global_failure = global_failure
     for k in [0,10): ckpt_hdr->times[k] = times[k]
     VELOC_Checkpoint("hpcgckpt", numberOfCgSets + 1)            # main.cpp:497
  delete ckpt_hdr                                                # main.cpp:502

ON SHUTDOWN:
  TestNorms; ReportResults; HPCG_Finalize                        # main.cpp (unchanged)
  VELOC_Finalize(1)                                              # main.cpp:551
  MPI_Finalize                                                   # main.cpp:556
```

(Pseudocode reflects the LLM's actual implementation in [`build/tests_baseline/HPCG/src/main.cpp`](../../build/tests_baseline/HPCG/src/main.cpp).)

### 1.4 LLM vs reference comparison

#### State coverage

| Application state | LLM | Reference | Notes |
|---|:---:|:---:|---|
| Loop index `i` | ☑ | ☑ | LLM saves as `ckpt_hdr->i`; reference saves as 4th `fwrite` field. Both resume at `i+1`. |
| `testnorms_data.values[0..numberOfCgSets-1]` | ☑ (fixed-size 2048-slot buffer) | ☑ (`std::vector<double>` of length `numberOfCgSets`) | LLM allocates worst-case 16 KB once; reference snapshots the live `values[]` into a `std::vector` at each save. Both restore identically. |
| `times[0..9]` (timing accumulators) | ☑ | ☑ | Both save the full 10-slot timing array consumed by `ReportResults`. |
| `numberOfCgSets`, `optMaxIters`, `optTolerance` | ☑ (overwrite locals) | ☑ (validate, not restore) | LLM **overwrites** locals from checkpoint — defends against `opt_worst_time` drift on a re-run. Reference instead **re-derives** them and refuses to load if they don't match (`fread` mismatch → return false → start fresh). |
| `optNiters`, `opt_worst_time`, `err_count`, `tolerance_failures`, `global_failure` | ☑ | ☐ | LLM treats every value consumed by `ReportResults` as protected state; reference relies on these being deterministic from re-running pre-loop setup. |
| `SparseMatrix A`, multigrid hierarchy, `CGData` | ☐ | ☐ | Both skip — re-built deterministically from `--nx/--ny/--nz` on every run. |
| `xexact`, `b`, `x` Vectors | ☐ | ☐ | Both skip — `x` is re-zeroed every iter; `b`/`xexact` re-derived from problem geometry. |
| Reference SpMV/MG/CG timing-phase results | ☐ | ☐ | Both skip — they only feed `OptimizeProblem` and YAML report fields, not validity. |
| Per-rank `HPCG_fout` log file (`hpcg_log_…txt`) | ☐ | ☐ | Both skip — not in the `HPCG_VALIDATION=` comparison pattern. |

#### Checkpoint strategy

| Aspect | LLM | Reference |
|---|---|---|
| Where checkpoint is invoked (`file:func:line`) | [`src/main.cpp:main:483`](../../build/tests_baseline/HPCG/src/main.cpp#L483) (`VELOC_Checkpoint`) plus a final post-loop call at [`L497`](../../build/tests_baseline/HPCG/src/main.cpp#L497) | [`src/main.cpp:main:377`](../../tests/apps/checkpointed/HPCG/src/main.cpp#L377) → [`src/hpcg_ckpt.cpp:hpcg_ckpt_save:66`](../../tests/apps/checkpointed/HPCG/src/hpcg_ckpt.cpp#L66) (`fwrite` + atomic `tmp+rename`) |
| Which process(es) invoke | All 4 MPI ranks (each writes its own VeloC checkpoint file collectively) | All 4 ranks (each writes `checkpoints/hpcg_ckpt.<rank>` independently) |
| Cadence | **Every CG-set iteration** (`i+1` = ckpt version), plus one final checkpoint after the loop with `i = numberOfCgSets` | Every `CKPT_EVERY` iterations (default **5**), plus one mandatory save when `i+1 == numberOfCgSets` |
| Per-write storage (per-frame, all ranks) | **264 512 B** (≈ 258 KB; 4 ranks × 66 128 B/rank — sizeof(VelocCkptHeader) ≈ 16 KB + VeloC metadata) | **24 768 B** (≈ 24 KB; 4 ranks × 6 192 B/rank — header + `times[10]` + `numberOfCgSets`-sized residuals via raw `fwrite`) |
| Frames retained on disk | **6** (`max_versions=3` × 2 dirs scratch+persistent → 6 files / rank × 4 ranks = **24 files**) | **1** (each rank overwrites the same `hpcg_ckpt.<rank>` via `tmp + rename`; 4 files total) |
| Cumulative on disk at end | **396 768 B** (≈ 387 KB) across 24 files | **24 768 B** (≈ 24 KB) across 4 files |

(Per-frame metrics from [`build/validation_output/HPCG_baseline/benchmarks/raw_metrics.json`](../../build/validation_output/HPCG_baseline/benchmarks/raw_metrics.json) and [`build/validation_output/HPCG_reference/benchmarks/raw_metrics.json`](../../build/validation_output/HPCG_reference/benchmarks/raw_metrics.json). Both raw_metrics files report the snapshot under field `checkpoint_per_frame_bytes`.)

#### Recovery strategy

| Aspect | LLM | Reference |
|---|---|---|
| Where recovery is detected (`file:line`) | [`src/main.cpp:426`](../../build/tests_baseline/HPCG/src/main.cpp#L426) — `VELOC_Restart_test("hpcgckpt", 0)` returns latest version | [`src/main.cpp:354`](../../tests/apps/checkpointed/HPCG/src/main.cpp#L354) → [`src/hpcg_ckpt.cpp:hpcg_ckpt_load:28`](../../tests/apps/checkpointed/HPCG/src/hpcg_ckpt.cpp#L28) — `fopen(checkpoints/hpcg_ckpt.<rank>)` + magic-number check |
| What's done after restore | `VELOC_Restart` overwrites the entire `VelocCkptHeader` (single region, single phase); locals (`numberOfCgSets`, `optMaxIters`, `optNiters`, `optTolerance`, `opt_worst_time`, `err_count`, `tolerance_failures`, `global_failure`, `times[]`) are reassigned from the restored struct; `testnorms_data.values` is allocated with the restored `numberOfCgSets` and seeded from `cg_residuals[0..i)`; loop resumes at `i = ckpt_hdr->i` | `hpcg_ckpt_load` validates `numberOfCgSets`/`optMaxIters` match the freshly-derived values; on mismatch returns false → fresh start. On match, restores `times[10]` and the residual `std::vector`; `hpcg_start = saved_i + 1`; loop skips ahead |
| Time to recover (kill+recovery / failure-free baseline) | **1.03 ×** (123.71 s / 119.7 s; iter-2 PASS) — far under the 1.2 × production cap | **0.87 ×** observed in benchmarks (resilient `small-nofail` mean 53.15 s vs original 61.08 s for `--rt=60`); benchmarks did not record `recovery_time_s` for either codebase, and the reference benchmark's `small-once` scenario was actually run **failure-free** for the resilient codebase (`injected: false` in [raw_metrics.json](../../build/validation_output/HPCG_reference/benchmarks/raw_metrics.json)), so this ratio reflects checkpoint overhead, not an injected-failure recovery |
| Output correctness | **Bit-identical** stdout (`Test 1/2: PASS text`) for both failure-prone and failure-free resilient runs vs cached vanilla baseline | Numerically equivalent; reference also produces `HPCG result is VALID` |

---

**Key observations**
- Iter 1 failed not because of a code defect in the LLM's resilience design (which was structurally correct on first attempt) but because of a **discoverability mismatch**: the validator probes `<source_dir>/veloc.cfg` and `<build_dir>/veloc.cfg`, while VeloC at runtime reads `veloc.cfg` from PWD (which is `bin/` for HPCG). The LLM placed the file only at the runtime location. Iter 2's fix was a 1-file copy with no source-code change.
- The LLM's "everything that touches `ReportResults` goes in the header" stance produces a per-frame payload **~10.7× larger** than the reference (66 128 vs 6 192 B per rank), but in absolute terms both are tiny (KB-scale) because HPCG's loop-carried state is just a residual vector and a few scalars — most of HPCG's memory is the deterministic-from-inputs sparse matrix.
- The LLM **eliminates** the variable-size-array problem by reserving `MAX_CG_SETS=2048` slots in a fixed-size struct (16 KB sunk cost) so the entire checkpoint is one `VELOC_Mem_protect` region with single-phase `VELOC_Restart`. The reference instead serializes a `std::vector<double>` of exactly `numberOfCgSets` doubles via raw `fwrite`/`fread`, but pays the cost of a custom validator (magic number + size match) on every load.
- The LLM checkpoints **every** CG iteration (cadence 1) where the reference checkpoints **every 5** (`CKPT_EVERY=5`); on the small benchmark each iteration is short and the per-rank payload is sub-100 KB, so the cadence-1 overhead is invisible in wall time (1.03× recovery ratio).
- The LLM keeps **6 logical frames** on disk via VeloC's `max_versions=3` (× 2 scratch+persistent dirs) for 24 total files; the reference keeps exactly **1 frame** via `tmp+rename` overwrite for 4 total files. LLM's cumulative on-disk footprint is ~16× larger but bounded and small (387 KB total).
