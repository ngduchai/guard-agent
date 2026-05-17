# `CoMD` — LLM Resilience Engineering Report

**App**: `CoMD` — classical molecular dynamics MPI proxy app (LJ / EAM force kernels, link-cell decomposition)
**Vanilla source**: [`tests/apps/vanillas/CoMD/`](../../tests/apps/vanillas/CoMD/)
**Reference source**: [`tests/apps/checkpointed/CoMD/`](../../tests/apps/checkpointed/CoMD/)
**LLM-generated source**: [`build/tests_baseline/CoMD/`](../../build/tests_baseline/CoMD/)
**Iteration outcome**: PASS in **2 iters** / **1238 s** wall / **0.43 M tokens**

---

## 1. LLM Methodology

### 1.1 Overall reasoning process (text/table DAG)

A turn-by-turn record of LLM thought↔action across all iterations,
distilled from the `What I intend to do next → Why → Expectation → Result`
chain literally found in
[`iter_1/opencode_stdout.txt`](../../build/iterative_logs/CoMD_baseline/iter_1/opencode_stdout.txt)
(9 distinct turns: layout → app.yaml → main loop → SimFlat enumeration → VeloC location → veloc.cfg + Makefile + CoMD.c edit → static self-review)
and the much shorter chain in
[`iter_2/opencode_stdout.txt`](../../build/iterative_logs/CoMD_baseline/iter_2/opencode_stdout.txt)
(3 unstructured turns: triage of `1.21x ≥ 1.2x` ratio → cadence arithmetic → one-constant edit).

### Iter 1 — 865s — ❌ FAIL

| Turn | 🧠 Thought | 🔧 Action |
|:---:|---|---|
| **1.a** | What app is this and what does the comparator key on? | list [CoMD/](../../build/tests_baseline/CoMD/) + read [app.yaml](../../build/tests_baseline/CoMD/app.yaml) + [prompt.txt](../../build/tests_baseline/CoMD/prompt.txt) → CoMD MD proxy app; comparator keys on `Final energy`/`eFinal`/`Final atom count` with tolerance 0.001; run is 4-rank `2×2×1` decomposition, 100 outer iters. |
| **1.b** | Where is the timestep loop, what's in SimFlat, where do final results print? | read [CoMD.c:113-126](../../build/tests_baseline/CoMD/src-mpi/CoMD.c#L113) + [timestep.c](../../build/tests_baseline/CoMD/src-mpi/timestep.c) → outer loop is `for (; iStep<nSteps; iStep+=printRate)`; final-print site is [CoMD.c:309-322](../../build/tests_baseline/CoMD/src-mpi/CoMD.c#L309); mutating per-step state lives in `sim->atoms` (r,p,f,U,gid,iSpecies) + `sim->boxes->nAtoms[]` + ePotential/eKinetic. |
| **1.c** | What's the exact array sizing and does halo data need saving? | read [initAtoms.c](../../build/tests_baseline/CoMD/src-mpi/initAtoms.c) + [linkCells.c](../../build/tests_baseline/CoMD/src-mpi/linkCells.c) + [CoMDTypes.h](../../build/tests_baseline/CoMD/src-mpi/CoMDTypes.h) → arrays sized `MAXATOMS*nTotalBoxes` (local + halo); only `nAtoms[]` mutates per step in LinkCell; halo zone re-populated by `redistributeAtoms` → `haloExchange` on every timestep, so checkpointing only the local-box slot range is sufficient. |
| **1.d** | Where is VeloC installed and what API surface does it expose? | `task(explore)` → `veloc.h` at `~/usr/include`, `libveloc-client.so` at `~/usr/lib`; API: `VELOC_Init(comm,cfg)` + `Mem_protect(id,ptr,count,base_size)` + `Restart_test(name,0)` + `Restart(name,v)` + `Checkpoint(name,version)` + `Finalize(1)`. |
| **1.e** | Confirm `nLocal` is recomputed every iter (so I needn't trust the saved value past the next sumAtoms call). | `grep "atoms->nLocal"` in [CoMD.c](../../build/tests_baseline/CoMD/src-mpi/CoMD.c) → `sumAtoms` (CoMD.c:455-465) zeroes nLocal then sums `boxes->nAtoms[0..nLocalBoxes)`, called at top of every iter; also `--atoms->nLocal` in linkCells.c:256 during `moveAtom` — so saved value is defensive only. |
| **1.f** | Build the vanilla code first to capture a known-good baseline before changing anything. | try to invoke `make` → discover NO Bash tool in the available toolset; pivot to "all edits must be high-confidence; no test-and-iterate". |
| **1.g** | Design 12 protect regions: iStep, nLocal, nGlobal, ePotential, eKinetic, nAtoms[nLocalBoxes], + 6 atom arrays sized MAXATOMS*nLocalBoxes; checkpoint AFTER `iStep += printRate` so saved counter is the resume point and state is post-timestep-consistent. | edit [Makefile.vanilla](../../build/tests_baseline/CoMD/src-mpi/Makefile.vanilla) — `VELOC_DIR ?= ~/usr`; `-DHAVE_VELOC`; `-lveloc-client` + `-Wl,-rpath`. |
| **1.h** | Integrate Init/protect/Restart/Checkpoint into main; need Init AFTER `initParallel` but BEFORE `Mem_protect`; `#ifdef HAVE_VELOC` keeps vanilla buildable. | edit [CoMD.c:113-281](../../build/tests_baseline/CoMD/src-mpi/CoMD.c#L113) — `VELOC_Init` at L154/156, 12 `Mem_protect` at L172-183, `Restart_test`/`Restart` at L186/192, `Checkpoint` at L249 every `COMD_CKPT_INTERVAL_DEFAULT=5` outer iters, `Finalize` at L281. |
| **1.i** | Write veloc.cfg at project root (mpirun cwd); use sync mode for short benchmark. | write [veloc.cfg](../../build/tests_baseline/CoMD/veloc.cfg) (`mode=sync`, `scratch=/tmp/comd_scratch`, `persistent=/tmp/comd_persistent`, `max_versions=3`). |
| **1.j** | No Bash → do thorough static review (12-point checklist: include guards, mid-function decls under -std=c99, MPI_Init ordering, Mem_protect ordering, halo-zone repopulation invariant, etc.). | re-read modified `CoMD.c` end-to-end; verify all 12 protect IDs, that halo `nAtoms[ii]` is zeroed by `emptyHaloCells` at start of next redistribute, and that `f[]` is consumed correctly by next `advanceVelocity`. |

> ❌ **RESULT**: output bit-equal (`Max relative diff 0.00e+00`); 24 ckpt files observed; kill+recovery `180.0 s / 149.0 s = 1.21×` ≥ 1.20× cap. With `nSteps=1500`, `printRate=100` → 15 outer iters at ~10 s each; ckpt every 5 iters ≈ 50 s apart; kill landed 30 s after last ckpt → recovery had to redo 30 s of work + 99 s residual.

→ **Feedback into iter 2**: `validate_stderr: "kill+recovery wall-time ratio 1.21x ≥ 1.2x cap"`

### Iter 2 — 373s — ✅ PASS

| Turn | 🧠 Thought | 🔧 Action |
|:---:|---|---|
| **2.a** | Triage — correctness PASSes (24 files written, output bit-equal); only the 1.21× timing margin fails. With kill 30 s after last ckpt and 99 s recovery, the lever is checkpoint cadence, not state coverage. | read [iter_1/validate_stderr.txt](../../build/iterative_logs/CoMD_baseline/iter_1/validate_stderr.txt) + recompute: `nSteps=1500`, `printRate=100` → 15 outer iters, ~10 s each; current cadence `COMD_CKPT_INTERVAL=5` ≈ 50 s; need ≤ 1.2× = 178.8 s ⇒ ~20 s slack → tighten to per-iter ckpt (≈ 10 s apart, redo window ≤ 10 s). |
| **2.b** | 27 MB/rank under sync VeloC writes in well under 1 s on /tmp; safe to flip cadence 5 → 1. | edit [CoMD.c:215](../../build/tests_baseline/CoMD/src-mpi/CoMD.c#L215) — `COMD_CKPT_INTERVAL_DEFAULT` 5 → 1; user-override via `COMD_CKPT_INTERVAL` env still works. |
| **2.c** | Self-review — no other change needed; `max_versions=3` in cfg garbage-collects old frames; correctness gates still untouched. | (no edit; review only) |

> ✅ **RESULT**: recovery 99 s → 74 s; kill+recovery `154.6 s / 149.0 s = 1.04×` (under 1.20× cap); output bit-equal.

**Sources** (clickable):
- Iter 1: [`opencode_stdout.txt`](../../build/iterative_logs/CoMD_baseline/iter_1/opencode_stdout.txt), [`inspection.json`](../../build/iterative_logs/CoMD_baseline/iter_1/inspection.json), [`validate_stderr.txt`](../../build/iterative_logs/CoMD_baseline/iter_1/validate_stderr.txt), [`validate_stdout.txt`](../../build/iterative_logs/CoMD_baseline/iter_1/validate_stdout.txt)
- Iter 2: [`opencode_stdout.txt`](../../build/iterative_logs/CoMD_baseline/iter_2/opencode_stdout.txt), [`inspection.json`](../../build/iterative_logs/CoMD_baseline/iter_2/inspection.json), [`validate_stdout.txt`](../../build/iterative_logs/CoMD_baseline/iter_2/validate_stdout.txt)

### 1.2 Critical state identification

| Question | Answer |
|---|---|
| Detection algorithm | Read [`CoMD.c`](../../build/tests_baseline/CoMD/src-mpi/CoMD.c) to locate the outer `for (; iStep<nSteps; )` loop ([CoMD.c:113-126](../../build/tests_baseline/CoMD/src-mpi/CoMD.c#L113)), then traced `SimFlat` field-by-field in [`CoMDTypes.h`](../../build/tests_baseline/CoMD/src-mpi/CoMDTypes.h) to classify each as static-post-init or mutated per step. Verbatim from [`iter_1/opencode_stdout.txt`](../../build/iterative_logs/CoMD_baseline/iter_1/opencode_stdout.txt): *"Since the simulation is deterministic (no randomness past init), the only mutating state inside the loop is in `sim->atoms` (positions r, momenta p, forces f, gid, iSpecies) and `sim->boxes` (which atom is in which link cell — `nAtoms[]`)"*. |
| Source tools / queries the LLM used | `read` [`CoMD.c`](../../build/tests_baseline/CoMD/src-mpi/CoMD.c), [`CoMDTypes.h`](../../build/tests_baseline/CoMD/src-mpi/CoMDTypes.h), [`initAtoms.{h,c}`](../../build/tests_baseline/CoMD/src-mpi/initAtoms.c), [`linkCells.{h,c}`](../../build/tests_baseline/CoMD/src-mpi/linkCells.c), [`timestep.c`](../../build/tests_baseline/CoMD/src-mpi/timestep.c), [`mytype.h`](../../build/tests_baseline/CoMD/src-mpi/mytype.h), [`parallel.h`](../../build/tests_baseline/CoMD/src-mpi/parallel.h), [`Makefile.vanilla`](../../build/tests_baseline/CoMD/src-mpi/Makefile.vanilla), [`app.yaml`](../../build/tests_baseline/CoMD/app.yaml); `task(explore)` to locate VeloC install at `~/usr`; `grep "atoms->nLocal"`, `grep "nLocal\\s*[+\\-]="` to verify `sumAtoms` recomputes `nLocal` each iter. |
| State considered & rejected | (a) Halo-cell slots in `r/p/f/U/gid/iSpecies` arrays — *"Halo box slots are unnecessary — they'll be repopulated by `haloExchange` inside `redistributeAtoms` on the first step"*. (b) `Domain`/`LinkCell` geometry, `BasePotential`, `SpeciesData` — immutable post-init. (c) `HaloExchange` MPI buffers — recreated by `initSimulation` on restart. (d) Static `iStepPrev` in `printThings` — cosmetic only, not in comparison patterns. |
| State eventually protected | 12 regions registered with `VELOC_Mem_protect`: `iStep` (4 B), `nLocal`/`nGlobal` (8 B), `ePotential`/`eKinetic` (16 B), `boxes->nAtoms[0..nLocalBoxes)` (~`nLocalBoxes * 4 B`), and the local-box slot range of `gid`/`iSpecies` (each `MAXATOMS*nLocalBoxes * 4 B`), `r`/`p`/`f` (each `MAXATOMS*nLocalBoxes * 24 B`), `U` (`MAXATOMS*nLocalBoxes * 8 B`). Per-rank checkpoint payload ~27 MB → ~108 MB / frame across 4 ranks. |

(Source: [`iter_1/opencode_stdout.txt`](../../build/iterative_logs/CoMD_baseline/iter_1/opencode_stdout.txt) design-plan + self-review sections.)

### 1.3 Protection + recovery algorithm

```pseudocode
ON STARTUP:
  1. initParallel(&argc, &argv)                          # CoMD.c:139 (MPI_Init inside)
  2. cfg = getenv("COMD_VELOC_CFG") ?? "veloc.cfg"        # CoMD.c:154
     VELOC_Init(MPI_COMM_WORLD, cfg)                      # CoMD.c:156
  3. sim = initSimulation(cmd); validate = initValidate   # CoMD.c (unchanged)
  4. nLocalBoxes = sim->boxes->nLocalBoxes                # CoMD.c:170
     nLocalSlots = MAXATOMS * nLocalBoxes
     # Register 12 protected regions
     VELOC_Mem_protect(0, &iStep, 1, sizeof(int))         # CoMD.c:172
     VELOC_Mem_protect(1, &sim->atoms->nLocal,  ...)      # CoMD.c:173
     ... (regions 2..4: nGlobal, ePotential, eKinetic) ...
     VELOC_Mem_protect(5, sim->boxes->nAtoms,  nLocalBoxes, sizeof(int))      # CoMD.c:177
     VELOC_Mem_protect(6..11, gid|iSpecies|r|p|f|U, nLocalSlots, ...)         # CoMD.c:178-183
  5. v = VELOC_Restart_test("comd", 0)                    # CoMD.c:186
     IF v > 0:
        VELOC_Restart("comd", v)                          # CoMD.c:192
        # All 12 regions restored; halo cells will be rebuilt by
        # redistributeAtoms() on the next timestep iteration

DURING COMPUTATION:
  ckptInterval = getenv("COMD_CKPT_INTERVAL") ?? 1        # CoMD.c:215-221
  sinceLastCkpt = 0
  for (; iStep < nSteps; ):                               # CoMD.c:226
     sumAtoms; printThings; timestep(sim, printRate, dt)
     iStep += printRate
     IF ++sinceLastCkpt >= ckptInterval:                  # CoMD.c:246
        sinceLastCkpt = 0
        VELOC_Checkpoint("comd", iStep)                   # CoMD.c:249

ON SHUTDOWN:
  finalizeSubsystems()
  VELOC_Finalize(1)                                       # CoMD.c:281
  destroyParallel()  # MPI_Finalize
```

(Pseudocode reflects the LLM's actual implementation in [`build/tests_baseline/CoMD/src-mpi/CoMD.c`](../../build/tests_baseline/CoMD/src-mpi/CoMD.c).)

### 1.4 LLM vs reference comparison

#### State coverage

| Application state | LLM | Reference | Notes |
|---|:---:|:---:|---|
| `iStep` (loop counter) | ☑ | ☑ | Both save (LLM as int, reference via `sim->iteration` field). |
| `atoms->{r,p,f,U,gid,iSpecies}` (local slots) | ☑ | ☑ | LLM protects only local-box slots (`MAXATOMS*nLocalBoxes`); reference dumps all `MAXATOMS*nTotalBoxes`. Both produce bit-correct output. |
| `boxes->nAtoms[]` | ☑ (local only) | ☑ (full) | LLM relies on `emptyHaloCells()` to zero halo entries on next `updateLinkCells` call. |
| `atoms->{nLocal,nGlobal}` | ☑ | ☑ | Both save; both are also recomputed by `sumAtoms` at top of each iter (defensive). |
| `ePotential`, `eKinetic` | ☑ | ☑ | Saved by both (consumed by `printThings` immediately after restart). |
| `Domain` substruct (procGrid/procCoord/globalMin/Max/Extent/localMin/Max/Extent) | ☐ | ☑ | LLM skips because `initDecomposition` is deterministic given same `-i/-j/-k` and lattice extent. Reference saves redundantly. |
| `LinkCell` geometry (`gridSize`, `boxSize`, `invBoxSize`, `localMin/Max`, `nLocalBoxes`, `nHaloBoxes`, `nTotalBoxes`) | ☐ | ☑ | LLM skips (deterministic from `initLinkCells`). |
| `nSteps`, `printRate`, `dt` | ☐ | ☑ | LLM skips (re-derived from CLI args on restart). |
| `species->{name,atomicNo,mass}` | ☐ | ☑ | LLM skips (deterministic from potential file). |
| Halo-slot atom data (`gid/iSpecies/r/p/f/U` for `[nLocalBoxes, nTotalBoxes)`) | ☐ | ☑ | LLM relies on `haloExchange()` to repopulate from neighbors; reference saves. |

#### Checkpoint strategy

| Aspect | LLM | Reference |
|---|---|---|
| Where checkpoint is invoked (`file:func:line`) | [`src-mpi/CoMD.c:main:249`](../../build/tests_baseline/CoMD/src-mpi/CoMD.c#L249) (`VELOC_Checkpoint`) | [`src-mpi/CoMD.c:main:140`](../../tests/apps/checkpointed/CoMD/src-mpi/CoMD.c#L140) → [`src-mpi/checkpoint.c:writeCheckpoint:208`](../../tests/apps/checkpointed/CoMD/src-mpi/checkpoint.c#L208) (`write` syscall) |
| Which process(es) invoke | All 4 MPI ranks (each writes its own VeloC checkpoint file) | All 4 ranks (each writes `CoMD_state-<rank>.txt` independently) |
| Cadence | Every `COMD_CKPT_INTERVAL=1` outer-loop iteration (≈ every `printRate=100` MD steps; in the run config every ~10 s) | Every 500 MD steps (`ckptRate=500`) — i.e. once at iStep=500, 1000, 1500 (3 events for 1500-step run) |
| Per-write storage (per-frame, all ranks) | **155 824 848 B (≈ 149 MB)** | **213 368 832 B (≈ 204 MB)** |
| Frames retained on disk | **6** (`max_versions=3` × 2 dirs scratch+persistent: 6 files / rank × 4 ranks = 24 files; 6 logical frames) | **1** (each rank overwrites the same `CoMD_state-<rank>.txt`) |
| Cumulative on disk at end | **934 949 088 B (≈ 892 MB)** across 24 files | **213 368 832 B (≈ 204 MB)** across 4 files |

(Per-frame metrics from [`build/validation_output/CoMD_baseline/benchmarks/raw_metrics.json`](../../build/validation_output/CoMD_baseline/benchmarks/raw_metrics.json) and [`build/validation_output/CoMD_reference/benchmarks/raw_metrics.json`](../../build/validation_output/CoMD_reference/benchmarks/raw_metrics.json).)

#### Recovery strategy

| Aspect | LLM | Reference |
|---|---|---|
| Where recovery is detected (`file:line`) | [`src-mpi/CoMD.c:186`](../../build/tests_baseline/CoMD/src-mpi/CoMD.c#L186) — `VELOC_Restart_test("comd", 0)` returns latest version | [`src-mpi/CoMD.c:120`](../../tests/apps/checkpointed/CoMD/src-mpi/CoMD.c#L120) — `thereIsACheckpoint()` (stat-based) |
| What's done after restore | All 12 protected regions overwritten with checkpoint contents; loop resumes from restored `iStep`; first `redistributeAtoms` (inside next `timestep`) calls `emptyHaloCells` then `haloExchange` to repopulate halo cells from neighbours | `loadCheckpoint(sim)` deserializes 17 ints + 34 floats + arrays; `iStep = sim->iteration`; `loaded=1` skips the next ckpt-write check; loop resumes |
| Time to recover (kill+recovery / failure-free baseline) | **1.04 ×** (154.6 s / 149.0 s; iter-2 PASS) — under the 1.2 × production cap | **1.16 × — 1.32 ×** observed in benchmarks (small-low scenario: 234.5 / 234.8 / 264.9 s vs ~201 s baseline) |
| Output correctness | **Bit-identical** (`Max relative diff: 0.00e+00` for both failure-prone and failure-free runs) | Numerically equivalent; reference run also passes correctness check in benchmarks |

---

**Key observations**
- LLM converges in 2 iters by treating timing failure as a tunable-constant fix (cadence 5 → 1) rather than a structural bug. The state-coverage decision is correct on iter 1; only the cadence is wrong.
- LLM's per-frame payload (~149 MB) is smaller than reference (~204 MB) because it skips immutable / re-derivable state — but it keeps 6 retained versions vs reference's 1, so cumulative footprint is ~4.4 × larger.
- LLM achieves a **lower** recovery ratio (1.04 ×) than reference (~1.16 –1.32 ×) thanks to the more aggressive cadence and VeloC's async-drain capability under `mode=sync`.
