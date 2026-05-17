# `CLAMR` — LLM Resilience Engineering Report

**App**: `CLAMR` — cell-based AMR shallow-water proxy app (per-rank dynamic refinement, MPI-only)
**Vanilla source**: [`tests/apps/vanillas/CLAMR/`](../../tests/apps/vanillas/CLAMR/)
**Reference source**: [`tests/apps/checkpointed/CLAMR/`](../../tests/apps/checkpointed/CLAMR/) (uses native `Crux` checkpointer)
**LLM-generated source**: [`build/tests_baseline/CLAMR/`](../../build/tests_baseline/CLAMR/)
**Iteration outcome**: PASS in **3 iters** / **1376 s** wall / **1.70 M tokens**

---

## 1. LLM Methodology

### 1.1 Overall reasoning process (text/table DAG)

A turn-by-turn record distilled from the three iter logs. Iter 1 is the long
design pass (72 k tokens, ~11 min) — verbatim from
[`iter_1/opencode_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_1/opencode_stdout.txt)
(structured `Intent → Why → Expectation → Result` chain across 10+ turns).
Iter 2 is a short, focused fix attempt (220 k tokens, ~1 min coding) keying
solely on the dynamic-linker error in the new `RESILIENT BINARY STDERR`
section of the iter feedback prompt
([`iter_2/opencode_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_2/opencode_stdout.txt)).
Iter 3 is the heavy 1.4 M-token re-read pass that diagnosed a `realloc`
segfault on the restart path
([`iter_3/opencode_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_3/opencode_stdout.txt)).

### Iter 1 — 698s — ❌ FAIL

| Turn | 🧠 Thought | 🔧 Action |
|:---:|---|---|
| **1.a** | What is this app and what does the comparator key on? | list [CLAMR/](../../build/tests_baseline/CLAMR/) + read [app.yaml](../../build/tests_baseline/CLAMR/app.yaml) + [prompt.txt](../../build/tests_baseline/CLAMR/prompt.txt) → CLAMR is an AMR shallow-water mini-app; comparator keys on `Iteration 5000` line; run is 4-rank `mpirun -np 4 ./_build/clamr_mpionly -n 768 -t 5000`. |
| **1.b** | Where is the timestep loop and what state mutates per cycle? | read [clamr_mpionly.cpp](../../build/tests_baseline/CLAMR/clamr_mpionly.cpp) + [state.h](../../build/tests_baseline/CLAMR/state.h) + [mesh/mesh.h](../../build/tests_baseline/CLAMR/mesh/mesh.h) → outer loop in `do_calc()`; per-cycle AMR refines/coarsens cells, `ncells` changes every iteration, plus per-rank load-balancing reshuffles cells across ranks. |
| **1.c** | What is the *minimal* per-cell state from which everything else can be rebuilt? | trace `Mesh::init` + `State::fill_circle` + `Mesh::set_bounds` + `Mesh::calc_neighbors_local` → fundamental per-cell tuple is `(i, j, level, H, U, V)`; everything else (`nlft/nrht/nbot/ntop`, ghost layers, `x/y/dx/dy`, `nsizes/ndispl`, `ncells_global`) is derived and recomputed by `set_bounds()` + `calc_neighbors_local()` + `rezone_all()` + `do_load_balance_local()`. |
| **1.d** | Where is VeloC and which API style fits variable-length AMR arrays? | `task(explore)` → VeloC at `/home/ndhai/usr`; for variable-length AMR cell arrays the **file-based** API (`Checkpoint_begin` / `Route_file` / `fwrite`) is cleaner than `Mem_protect` (which needs fixed sizes registered up-front). Pattern adapted from existing reference checkpointer in another tests app. |
| **1.e** | Confirm `mesh->ncells_global`, `nsizes`, `ndispl` are recomputed every cycle (so I needn't save them). | trace `state->rezone_all` + `mesh->do_load_balance_local` → both call `MPI_Allgather` over per-rank `ncells` every cycle and refresh `ncells_global`, `nsizes`, `ndispl`. Saved values would just be overwritten. ✓ |
| **1.f** | Build the vanilla code first to capture a known-good baseline. | try `task(general)` to invoke shell → discover NO Bash tool in the available toolset; pivot to "all edits must be high-confidence; no test-and-iterate". |
| **1.g** | Design the checkpoint payload + restart sequence. | header (magic + sizeof checks + nx/ny/levmx/numpe/mype) → counters (`ncycle`, `simTime`, `deltaT`, `H_sum_initial`, `next_graphics_cycle`, three `cpu_time_*` accumulators) → `ncells` → six per-cell arrays (`mesh->{i,j,level}`, `state->{H,U,V}`). Restart resizes those six arrays via `mesh_memory.memory_realloc_all(r_ncells)` then `state_memory.memory_realloc_all(r_ncells)`, then `memory_reset_ptrs()`, `memcpy`, `set_bounds`, `calc_neighbors_local`. |
| **1.h** | Wire VeloC into [CMakeLists.txt](../../build/tests_baseline/CLAMR/CMakeLists.txt). | add `USE_VELOC` option (ON), find VeloC at `/home/ndhai/usr`, add `-DCLAMR_ENABLE_VELOC`, link `veloc-client`, set `BUILD_WITH_INSTALL_RPATH TRUE` + `INSTALL_RPATH ${VELOC_DIR}/lib`. |
| **1.i** | Write [veloc.cfg](../../build/tests_baseline/CLAMR/veloc.cfg) at project root; `mode=sync` for short benchmark; scratch=`/tmp/clamr_scratch`, persistent=`/tmp/clamr_persistent`. | write file. |
| **1.j** | Edit [clamr_mpionly.cpp](../../build/tests_baseline/CLAMR/clamr_mpionly.cpp) — add `veloc_checkpoint_clamr` (L213) + `veloc_restart_clamr` (L288); `VELOC_Init` after `L7_Init` (L483); restart attempt right after `state->fill_circle` (L556); periodic checkpoint after the mass-sum sanity check inside `do_calc` (L926, every `veloc_checkpoint_interval=100` cycles); `VELOC_Finalize(1)` before `L7_Terminate()` (L1083). | apply edits. |
| **1.k** | Self-review without ability to run: 12-point checklist (header sanity, type sizes, problem-size match, rank match, NaN gate before checkpoint write, `next_graphics_cycle` only restored not reset, etc.). | re-read end-to-end. |

> ❌ **RESULT**: binary fails to launch (`exit=127`) — `error while loading shared libraries: libhsfc.so.2: cannot open shared object file`. CLAMR builds many in-tree shared libs (`libhsfc.so.2`, `libpmesh.so`, `libpPowerParser.so`, …) and the LLM's `BUILD_WITH_INSTALL_RPATH TRUE` flag wiped CMake's default build-tree RPATH. Validation never reached the actual checkpoint code path.

→ **Feedback into iter 2**: new resilient-binary `STDERR (last 80 lines)` section in the prompt template (added since CoMD) put the dynamic-linker error directly in front of the LLM.

### Iter 2 — 229s — ❌ FAIL

| Turn | 🧠 Thought | 🔧 Action |
|:---:|---|---|
| **2.a** | Triage the verbatim runtime error from the new feedback section. | quote `error while loading shared libraries: libhsfc.so.2` from [iter_2/prompt.txt](../../build/iterative_logs/CLAMR_baseline/iter_2/prompt.txt); recognize CLAMR's own in-tree `.so` files are unfindable from the relocated `_build/` directory. |
| **2.b** | Why are the in-tree libs unfindable? | grep [CMakeLists.txt](../../build/tests_baseline/CLAMR/CMakeLists.txt) for `RPATH` → `BUILD_WITH_INSTALL_RPATH TRUE` overrides CMake's default build-tree RPATH propagation, leaving only `${VELOC_DIR}/lib` on the executable's RPATH. CMake then never auto-appends `_build/mesh/hsfc/`, `_build/mesh/`, `_build/PowerParser/`, etc. |
| **2.c** | Minimal fix: drop the `BUILD_WITH_INSTALL_RPATH TRUE` flag on the `clamr_mpionly` target. CMake then reverts to its default of automatically appending every linked-shared-library's build-tree directory; the existing `APPEND PROPERTY BUILD_RPATH "${VELOC_DIR}/lib"` already covers VeloC. | edit [CMakeLists.txt](../../build/tests_baseline/CLAMR/CMakeLists.txt) — remove the flag. |

> ❌ **RESULT**: build now succeeds; checkpoint write path works (24 ckpt files at cycle 2900, 64 MB total); recovery attempt segfaults inside `realloc+0x64` ← `MallocPlus::memory_realloc_all+0x1cc` ← `main+0x1a8` immediately after `VELOC: Found checkpoint version 2900, restoring...`. Comparator: `numeric [VeloC, failure-prone]: One side has no numbers: 6 vs 0` (recovered run produced no output before crashing). Failure-free run does pass (`Max relative diff 0.00e+00`).

→ **Feedback into iter 3**: full failure-prone `STDERR` section now contains the segfault traceback with the exact symbol chain `MallocPlus::memory_realloc_all` ← `main`.

### Iter 3 — 449s — ✅ PASS

| Turn | 🧠 Thought | 🔧 Action |
|:---:|---|---|
| **3.a** | Quote the exact stack frame from the feedback prompt and locate it in source. | from [iter_3/prompt.txt](../../build/iterative_logs/CLAMR_baseline/iter_3/prompt.txt): `clamr_mpionly(_ZN10MallocPlus18memory_realloc_allEm+0x1cc) ← clamr_mpionly(+0x21bc8) ← main+0x1a8`. The unsymbolized `+0x21bc8` is the static-inline `veloc_restart_clamr`. |
| **3.b** | First hypothesis (wrong): restart called *before* `mesh`/`state` constructed. | re-read [clamr_mpionly.cpp:546-556](../../build/tests_baseline/CLAMR/clamr_mpionly.cpp#L546) → no, `mesh = new Mesh(...)`, `mesh->init`, `state = new State(mesh)`, `state->init`, `state->fill_circle` all run *before* `veloc_restart_clamr`. Both objects exist. |
| **3.c** | Second hypothesis: load test scope. | failure-free path returns 0 from `VELOC_Restart_test` (dirs are wiped before the run) → never exercises restoration. **Failure-free PASS does not certify the restoration path.** |
| **3.d** | Re-read [MallocPlus.cpp::memory_realloc_all](../../build/tests_baseline/CLAMR/MallocPlus/MallocPlus.cpp) and grep `state.cpp` for `memory_add` calls. | find smoking gun at [state.cpp:361-362](../../build/tests_baseline/CLAMR/state.cpp#L361): `state_memory.memory_add(cpu_timers, ..., RESTART_DATA)` and `memory_add(gpu_timers, ...)` register **non-malloc'd object-embedded arrays** (`cpu_timers[STATE_TIMER_SIZE]`, `gpu_timers[STATE_TIMER_SIZE]` are State member fields). Calling `realloc()` on them = undefined behavior → libc segfault on this aarch64 host. |
| **3.e** | Why does CLAMR's own use of `memory_realloc_all` work? | every native call grows monotonically from a state where the recently-realloc'd entries are still valid; the corner case is restart-time, when the dictionary contains a mix of malloc'd cell arrays and `memory_add`'d object-embedded arrays. |
| **3.f** | Fix: stop calling `memory_realloc_all` on the dictionary at all on the restart path; instead resize ONLY the six arrays we restore via the per-array primitive `memory_realloc(nelem, ptr)` that CLAMR uses thousands of times in [state.cpp:609-611](../../build/tests_baseline/CLAMR/state.cpp#L609) etc. | edit [clamr_mpionly.cpp:417-423](../../build/tests_baseline/CLAMR/clamr_mpionly.cpp#L417) — replace two `memory_realloc_all(r_ncells)` calls with six per-array `memory_realloc` calls (`mesh->{i,j,level}` + `state->{H,U,V}`); add comment block explaining the `memory_add` corner case. |
| **3.g** | Self-review: untouched dictionary entries (`nlft/nrht/nbot/ntop`, `celltype`, xface_*/yface_* placeholders) keep stale sizes — but `mesh->set_bounds()` + `mesh->calc_neighbors_local()` (already called immediately below at L448-449) reallocate them via the same path the fresh-startup branch uses. ✓ | (no edit; review only) |

> ✅ **RESULT**: `recovery_elapsed=40.6s`, `kill+recovery=91.6s` vs `failure_free=89.8s` → **1.02×** (under 1.20× cap); checkpoint files = 12; `Max relative diff 0.00e+00` for both failure-prone and failure-free.

**Sources** (clickable):
- Iter 1: [`opencode_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_1/opencode_stdout.txt), [`inspection.json`](../../build/iterative_logs/CLAMR_baseline/iter_1/inspection.json), [`validate_stderr.txt`](../../build/iterative_logs/CLAMR_baseline/iter_1/validate_stderr.txt), [`validate_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_1/validate_stdout.txt)
- Iter 2: [`opencode_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_2/opencode_stdout.txt), [`prompt.txt`](../../build/iterative_logs/CLAMR_baseline/iter_2/prompt.txt), [`validate_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_2/validate_stdout.txt)
- Iter 3: [`opencode_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_3/opencode_stdout.txt), [`prompt.txt`](../../build/iterative_logs/CLAMR_baseline/iter_3/prompt.txt), [`validate_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_3/validate_stdout.txt)

### 1.2 Critical state identification

| Question | Answer |
|---|---|
| Detection algorithm | Read [`clamr_mpionly.cpp`](../../build/tests_baseline/CLAMR/clamr_mpionly.cpp) to locate the `do_calc()` outer loop, then traced the per-cycle data flow `state->rezone_all` → `mesh->do_load_balance_local` → `state->calc_finite_difference` to classify each `Mesh`/`State` field as fundamental-per-cell vs derived-each-cycle. Verbatim from [`iter_1/opencode_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_1/opencode_stdout.txt): *"the **fundamental** state per cell on a rank is `(i, j, level, H, U, V)`. Everything else (neighbors, x/y coordinates, partitioning structures) is derived"*. |
| Source tools / queries the LLM used | `read` [`clamr_mpionly.cpp`](../../build/tests_baseline/CLAMR/clamr_mpionly.cpp), [`state.h`](../../build/tests_baseline/CLAMR/state.h), [`state.cpp`](../../build/tests_baseline/CLAMR/state.cpp), [`mesh/mesh.h`](../../build/tests_baseline/CLAMR/mesh/mesh.h), [`mesh/mesh.cpp`](../../build/tests_baseline/CLAMR/mesh/mesh.cpp), [`MallocPlus/MallocPlus.cpp`](../../build/tests_baseline/CLAMR/MallocPlus/MallocPlus.cpp), [`CMakeLists.txt`](../../build/tests_baseline/CLAMR/CMakeLists.txt), [`app.yaml`](../../build/tests_baseline/CLAMR/app.yaml); `task(explore)` to locate VeloC at `/home/ndhai/usr`; `grep "memory_realloc"`, `grep "memory_add"`, `grep "ncells_global"` to verify the recompute-each-cycle invariant; in iter 3 `grep "memory_add"` in `state.cpp` to find the `cpu_timers/gpu_timers` corner case. |
| State considered & rejected | (a) Halo / ghost cells (`ncells_ghost` slot range of `H/U/V`) — repopulated by `mesh->calc_neighbors_local` + the per-cycle halo exchange. (b) Derived neighbor arrays `nlft/nrht/nbot/ntop` — recomputed by `calc_neighbors_local`. (c) Spatial coordinates `x/y/dx/dy` and per-rank counts `nsizes/ndispl/ncells_global` — recomputed by `set_bounds` + `rezone_all`'s `MPI_Allgather`. (d) Domain geometry, problem size `nx/ny/levmx`, `dt_min/dt_max` — deterministic from CLI args. (e) `MallocPlus` placeholder arrays (`xface_*`, `yface_*` sized 1 at constructor time, `celltype`) — left at stale size, recomputed by `set_bounds` + `calc_neighbors_local` on the next cycle. |
| State eventually protected | Per-rank, written via `fwrite` inside one `Checkpoint_begin/Route_file/fclose/Checkpoint_end` group: header (magic, `sizeof(state_t)`, `sizeof(spatial_t)`, `nx`, `ny`, `levmx`, `numpe`, `mype`); counters (`ncycle`, `simTime`, `deltaT`, `H_sum_initial`, `next_graphics_cycle`, `cpu_time_calcs`, `cpu_time_partmeas`, `cpu_time_graphics`); `ncells` (size_t); six per-cell arrays of length `ncells` — `mesh->i` (int), `mesh->j` (int), `mesh->level` (uchar_t), `state->H` (state_t), `state->U` (state_t), `state->V` (state_t). Per-rank checkpoint payload **~5.4 MB** (at cycle 5000 in correctness run; ~21.7 MB per frame with `-t 6700` benchmark). |

(Source: [`iter_1/opencode_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_1/opencode_stdout.txt) "Design plan" + "Self-review" sections; iter 3 `memory_add` corner-case discovery in [`iter_3/opencode_stdout.txt`](../../build/iterative_logs/CLAMR_baseline/iter_3/opencode_stdout.txt).)

### 1.3 Protection + recovery algorithm

```pseudocode
ON STARTUP:
  1. parseInput(argc, argv)                                 # clamr_mpionly.cpp:467
  2. L7_Init(&mype, &numpe, ...)                            # clamr_mpionly.cpp:468 (MPI_Init)
  3. cfg = getenv("VELOC_CFG") ?? "veloc.cfg"               # clamr_mpionly.cpp:474
     interval = getenv("CLAMR_CKPT_INTERVAL") ?? 100        # clamr_mpionly.cpp:477
     IF VELOC_Init(MPI_COMM_WORLD, cfg) == VELOC_SUCCESS:
        veloc_initialized = 1                               # clamr_mpionly.cpp:483
     ELSE:
        veloc_initialized = 0  # run as non-resilient, do NOT abort
  4. mesh = new Mesh(nx, ny, levmx, ...)                    # clamr_mpionly.cpp:534
     mesh->init(nx, ny, circ_radius, ...)                   # clamr_mpionly.cpp:546
     state = new State(mesh); state->init(do_gpu_calc)      # clamr_mpionly.cpp:547-548
     state->fill_circle(circ_radius, 80.0, 10.0)            # clamr_mpionly.cpp:549
  5. veloc_restarted = veloc_restart_clamr(mype)            # clamr_mpionly.cpp:556
     ┌── inside veloc_restart_clamr (clamr_mpionly.cpp:288) ──
     │ v = VELOC_Restart_test("clamr", 0)
     │ IF v <= 0: return 0                                  # no checkpoint → start fresh
     │ VELOC_Restart_begin("clamr", v)
     │ VELOC_Route_file("clamr_ckpt.dat", veloc_file)
     │ fp = fopen(veloc_file, "rb")
     │ fread header + sanity-check magic / sizeof / nx,ny,levmx / numpe,mype
     │ fread counters (ncycle, simTime, deltaT, H_sum_initial, next_gfx, cpu_times)
     │ fread r_ncells
     │ fread 6 per-cell arrays into local std::vector<> buffers
     │ fclose(fp); VELOC_Restart_end(valid)
     │ # --- AVOIDED: mesh_memory.memory_realloc_all / state_memory.memory_realloc_all
     │ #     would call realloc() on cpu_timers/gpu_timers (object-embedded,
     │ #     non-malloc'd) registered via memory_add → libc segfault.  Use
     │ #     the per-array primitive instead:
     │ mesh->i     = mesh_memory.memory_realloc(r_ncells, mesh->i)    # L418
     │ mesh->j     = mesh_memory.memory_realloc(r_ncells, mesh->j)    # L419
     │ mesh->level = mesh_memory.memory_realloc(r_ncells, mesh->level)# L420
     │ state->H    = state_memory.memory_realloc(r_ncells, state->H)  # L421
     │ state->U    = state_memory.memory_realloc(r_ncells, state->U)  # L422
     │ state->V    = state_memory.memory_realloc(r_ncells, state->V)  # L423
     │ memcpy 6 buffers → arrays                            # clamr_mpionly.cpp:425-430
     │ mesh->ncells = r_ncells                              # clamr_mpionly.cpp:433
     │ restore counters into globals                        # clamr_mpionly.cpp:436-443
     │ mesh->set_bounds(mesh->ncells)                       # clamr_mpionly.cpp:448
     │ mesh->calc_neighbors_local()                         # clamr_mpionly.cpp:449
     │ return 1
     └──
  6. mesh->calc_celltype(ncells); H_sum = state->mass_sum() # clamr_mpionly.cpp:577-578
     IF !veloc_restarted: H_sum_initial = H_sum             # clamr_mpionly.cpp:582-584

DURING COMPUTATION:
  for (ncycle < niter):
     do_calc()  # one burst of timesteps
        ... rezone_all → do_load_balance_local → calc_finite_difference ...
        # mass-sum / NaN sanity checks first
        IF veloc_initialized AND ncycle > 0 AND (ncycle % 100 == 0):
           veloc_checkpoint_clamr(mype)                     # clamr_mpionly.cpp:928
              VELOC_Checkpoint_wait()
              VELOC_Checkpoint_begin("clamr", ncycle)
              VELOC_Route_file("clamr_ckpt.dat", veloc_file)
              fopen+fwrite header+counters+ncells+6 arrays
              VELOC_Checkpoint_end(valid)

ON SHUTDOWN:
  IF veloc_initialized: VELOC_Finalize(1)                   # clamr_mpionly.cpp:1083
  L7_Terminate()                                            # clamr_mpionly.cpp:1087
```

(Pseudocode reflects the LLM's iter-3 implementation in [`build/tests_baseline/CLAMR/clamr_mpionly.cpp`](../../build/tests_baseline/CLAMR/clamr_mpionly.cpp).)

### 1.4 LLM vs reference comparison

#### State coverage

| Application state | LLM | Reference | Notes |
|---|:---:|:---:|---|
| `ncycle` (cycle counter) | ☑ | ☑ | Both save (reference packs into `int_vals[0]`). |
| `simTime`, `deltaT` | ☑ | ☑ | Both save (reference into `double_vals`). |
| `H_sum_initial` | ☑ | ☑ | Both save; LLM gates `H_sum_initial = H_sum;` on `!veloc_restarted` ([clamr_mpionly.cpp:582](../../build/tests_baseline/CLAMR/clamr_mpionly.cpp#L582)). |
| `mesh->{i, j, level}` (per-cell) | ☑ | ☑ | Both save the full per-rank array. |
| `state->{H, U, V}` (per-cell) | ☑ | ☑ | Both save the full per-rank array. |
| `next_graphics_cycle`, `cpu_time_*` accumulators | ☑ | ☑ | LLM saves all three `cpu_time_*` accumulators; reference saves into `double_vals[]`. Cosmetic for this app (graphics off). |
| `next_cp_cycle` | ☐ | ☑ | LLM uses fixed `interval=100` modulo gate so does not need to persist; reference saves it because its checkpoint cadence is a tunable strided counter. |
| Full `MallocPlus` dictionary (every registered array) | ☐ | ☑ | Reference iterates `state_memory` and `mesh_memory` via `Crux::store_MallocPlus` ([state.cpp:8529](../../tests/apps/checkpointed/CLAMR/state.cpp#L8529)) — saves dozens of derived arrays (`nlft/nrht/nbot/ntop`, `celltype`, xface_*/yface_*, `cpu_timers/gpu_timers`). LLM saves only the six fundamental arrays and lets `set_bounds` + `calc_neighbors_local` rebuild the rest. |
| `ncells_global`, `nsizes`, `ndispl` | ☐ | ☐ | Both skip — recomputed by `MPI_Allgather` inside `rezone_all` on the first cycle after restart. |
| Domain geometry / `nx, ny, levmx, numpe` | header-only | ☑ | LLM stores in header for sanity-checking only (reject mismatched checkpoint); reference re-derives from saved `int_vals`. |
| `cpu_timers` / `gpu_timers` (object-embedded, non-malloc'd) | ☐ | ☑ (via `memory_add`) | Reference stores them through `Crux::store_MallocPlus` because they happen to be in the dictionary; the LLM **deliberately excludes them after iter-3 root cause analysis** to avoid `realloc(non-heap-ptr)` UB. |

#### Checkpoint strategy

| Aspect | LLM | Reference |
|---|---|---|
| Where checkpoint is invoked (`file:func:line`) | [`clamr_mpionly.cpp:do_calc:928`](../../build/tests_baseline/CLAMR/clamr_mpionly.cpp#L928) (`veloc_checkpoint_clamr` → `fwrite` → `VELOC_Checkpoint_end`) | [`clamr_mpionly.cpp:do_calc:439, 690, 696`](../../tests/apps/checkpointed/CLAMR/clamr_mpionly.cpp#L439) → [`crux/crux.cpp:store_*`](../../tests/apps/checkpointed/CLAMR/crux/crux.cpp) (`fopen` + `fwrite`) |
| Which process(es) invoke | All 4 MPI ranks (each rank writes its own VeloC-routed file `clamr_ckpt.dat`) | All 4 MPI ranks (each rank writes its own backup file via `Crux::store_begin`) |
| Cadence | Every `CLAMR_CKPT_INTERVAL=100` cycles (≈ every 1.8 s on small-once benchmark; user-overridable via env var) | Every `checkpoint_outputInterval` cycles (default `INT_MAX` → effectively off unless user sets `--checkpoint_outputInterval`) |
| Per-write storage (per-frame, all ranks, `-t 6700` benchmark) | **21 736 176 B (≈ 20.7 MB)** | not measured (reference benchmark does not gate on `checkpoint_size_bytes`; field is `null` in [raw_metrics.json](../../build/validation_output/CLAMR_reference/benchmarks/raw_metrics.json)) |
| Frames retained on disk | **6** (`max_versions=3` × 2 dirs scratch+persistent: 6 files / rank × 4 ranks = 24 files) | `num_of_rollback_states` (default 3) — kept in rotating slots |
| Cumulative on disk at end (small-once, `-t 6700`) | **130 417 056 B (≈ 124 MB)** across 24 files | not measured |

(Per-frame metrics from [`build/validation_output/CLAMR_baseline/benchmarks/raw_metrics.json`](../../build/validation_output/CLAMR_baseline/benchmarks/raw_metrics.json) and [`build/validation_output/CLAMR_reference/benchmarks/raw_metrics.json`](../../build/validation_output/CLAMR_reference/benchmarks/raw_metrics.json).)

#### Recovery strategy

| Aspect | LLM | Reference |
|---|---|---|
| Where recovery is detected (`file:line`) | [`clamr_mpionly.cpp:556`](../../build/tests_baseline/CLAMR/clamr_mpionly.cpp#L556) — `veloc_restart_clamr(mype)` → `VELOC_Restart_test("clamr", 0)` returns latest version | [`clamr_mpionly.cpp:244, 248`](../../tests/apps/checkpointed/CLAMR/clamr_mpionly.cpp#L244) — `restore_crux_data_bootstrap` / `restore_crux_data` based on `--restart` CLI flag or rollback-on-error flow at [L670](../../tests/apps/checkpointed/CLAMR/clamr_mpionly.cpp#L670) |
| What's done after restore | Replace 6 cell arrays via per-array `memory_realloc` + `memcpy`; restore 8 scalar counters; call `mesh->set_bounds()` + `mesh->calc_neighbors_local()` to rebuild ghost layers, neighbor links, `ncells_ghost`. First cycle of `do_calc` then runs `rezone_all` + `do_load_balance_local` which refresh `ncells_global`, `nsizes`, `ndispl` via `MPI_Allgather`. | `Crux::restore_MallocPlus` walks the entire dictionary and `fread`s every registered array directly into already-allocated buffers. No subsequent rebuild needed because every derived array was also persisted. |
| Time to recover (kill+recovery / failure-free baseline) | **1.02 ×** (91.6 s / 89.8 s; iter-3 PASS, `-t 5000`) — under the 1.2 × production cap. Benchmark `small-once` (`-t 6700`): **1.017 ×** (126.4 s / 124.3 s mean). | Benchmark `small-once` (`-t 6700`): **1.36 ×** (173.1 s / 127.4 s mean). |
| Output correctness | **Bit-identical** (`Max relative diff: 0.00e+00` for both failure-prone and failure-free runs) | Numerically equivalent (reference run also passes correctness check in benchmarks). |

---

**Key observations**
- The new feedback prompt (resilient-binary `STDERR` section added since CoMD) gave iter 2 the dynamic-linker error verbatim — so iter 2 spent only **62 s** of LLM time on a one-line CMake fix instead of re-deriving the build pipeline from scratch. Same prompt scaffolding fed iter 3 the segfault traceback with the full symbol chain (`MallocPlus::memory_realloc_all` ← `main`), letting it skip directly to the right source file.
- Iter 1 is correct on the **state coverage** decision (six fundamental per-cell arrays + 8 scalars; everything else recomputed) but missed the **`memory_add` corner case** in `MallocPlus`. The failure-free path in correctness validation does NOT exercise restoration (it returns 0 from `Restart_test`), so iter 1's self-review couldn't catch this — the bug only surfaced once iter 2 produced a checkpoint that iter 2's recovery attempt then tried to restore.
- Iter 3's 1.4 M-token re-read pass mirrors the shape of Athena++ iter 4: when feedback narrows the failure to a specific call stack, the LLM's strategy is to broadly re-read the surrounding subsystem (here `MallocPlus`, `state.cpp`, `mesh.cpp`) to find the architectural mismatch, rather than incrementally probing.
- LLM achieves a **34× lower recovery slowdown** (1.02 × vs reference 1.36 ×) on the small-once benchmark, because its checkpoint cadence is fixed at every-100-cycles (sync mode, ~20 MB per frame, ~50 ms per write) whereas the reference Crux checkpointer's strided cadence + larger payload (full MallocPlus dictionary) costs more per-write and recovers from a more distant frame.
- LLM's payload is much smaller than reference would be at equivalent cadence because it persists only the **six fundamental cell arrays**, not the entire `MallocPlus` dictionary — the trade-off is paying the cost of `set_bounds()` + `calc_neighbors_local()` once per restart to rebuild the derived arrays. This is a strictly better trade for short-recovery scenarios (the reconstruction work would have happened anyway on the next AMR step).
