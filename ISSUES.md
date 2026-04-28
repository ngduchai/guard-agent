# ISSUES.md

Issues, feature requests, and improvements tracked here. Update this file whenever an issue is reported, a feature is planned, work is done, or a fix is confirmed.

---

## Statuses

| Status | Meaning |
|--------|---------|
| **Open** | Reported, not yet fixed |
| **Solved** | Fix implemented, awaiting user confirmation |
| **Closed** | Fix confirmed working by user |

---

## Issue format

Each issue is a level-3 heading (`###`) with the fields below. Copy this template when adding a new issue:

```markdown

### #N — Short title `Status`

**Reported:** YYYY-MM-DD

**Explanation:** What is broken or unexpected. Include the page/endpoint, the trigger action, and the observed vs expected behavior.

**Resolution:** (filled when status changes to Solved/Closed)
What was done to fix it — files changed, approach taken, commit hash if available.
```

### Rules

- Number issues sequentially (`#1`, `#2`, …). Never reuse a number.
- Keep **Open** and **Solved** issues near the top; move **Closed** issues to the "Closed issues" section at the bottom.
- When closing, do not delete the issue — move it so the history is preserved.
- Write explanations from the user's perspective (what they see), not implementation internals.

---

### #42 — Three vanilla apps (Athena++, CLAMR, SPARTA) still shipped fully intact native checkpoint code, letting the LLM "cheat" by toggling a config flag `Solved`

**Reported:** 2026-04-27

**Explanation:** Phase 3 vanilla audit identified a second batch of three apps under `tests/apps/vanillas/` whose native checkpoint code paths were intact and reachable through an input deck or CLI flag, defeating the experimental design (the agent must invent resilience from scratch, not toggle a pre-existing capability):

- **Athena++** still shipped `src/outputs/restart.cpp` (`RestartOutput::WriteOutputFile`, an MPI-IO collective writer of the full AMR mesh state) plus the `RestartOutput` class declaration in `outputs.hpp` and the `else if (op.file_type.compare("rst") == 0) { pnew_type = new RestartOutput(op); }` branch in the `Outputs::Outputs` constructor.  An LLM could enable native checkpointing by adding `<output99>{file_type=rst,dt=2.0}` to `inputs/hydro/athinput.blast`.
- **CLAMR** still shipped the entire `crux/` directory (the Crux disk/in-memory checkpoint pipeline with MPI-IO collective Mesh+State serializer), `clamr_mpionly.cpp`'s `Crux *crux` pointer + `store_crux_data` / `restore_crux_data_bootstrap` / `restore_crux_data` functions, the `crux_type` / `checkpoint_outputInterval` / `num_of_rollback_states` / `restart` / `restart_file` / `backup_file_num` globals in `input.cpp`, the `-c <interval>` (CRUX_DISK), `-C <interval>` (CRUX_IN_MEMORY), `-R <file>` (restart-from-backup) and `-b <num>` (rollback count) CLI flag parsers, plus `Crux *crux` parameters on `State::store_checkpoint` / `Mesh::store_checkpoint` / `State::restore_checkpoint` / `Mesh::restore_checkpoint`.  An LLM could enable native checkpointing by appending `-c 250` to the run command.
- **SPARTA** still shipped `src/write_restart.cpp` + `read_restart.cpp` (SPARTA's WriteRestart / ReadRestart command classes), an `Output::create_restart()` driver wired to `WriteRestart`, an `Input::restart()` dispatch on the `restart` command keyword, plus orphan-from-deletion helper methods (`Mixture::write_restart`, `Surf::write_restart` / `read_restart` / `pack_restart`, `Grid::write_restart` / `read_restart` / `pack_restart` / `unpack_restart`, `Particle::write_restart_species` / `read_restart_species` / `write_restart_mixture` / `read_restart_mixture` / `pack_restart` / `unpack_restart`, plus the `_custom` variants for Surf / Grid / Particle).  An LLM could enable native checkpointing by adding `restart 5000 restart.sparta.*` to `examples/free/in.validation`.

**Resolution:** Surgically removed the native checkpoint capability from each of the three apps while preserving build compatibility (each app still builds clean and runs its workload to completion):

- **Athena++** (committed in `c15a2617c`): deleted `src/outputs/restart.cpp`; dropped the `RestartOutput` class from `src/outputs/outputs.hpp`; dropped the `else if ("rst")` branch + `num_rst_outputs` counter + `move-restart-block-to-tail-of-list` reorder loop in `src/outputs/outputs.cpp`; dropped the `wtflag && file_type == "rst"` flush condition from `Outputs::MakeOutputs`; dropped two stale `friend class RestartOutput;` declarations in `src/mesh/mesh.hpp`.  The `Mesh(pinput, restartfile, mesh_flag)` reader constructor (loaded by the `-r` CLI) was left intact since the spec only targets the writer side.  Build: `python configure.py --prob blast -mpi && make -j` succeeds.  Run: `mpirun -np 4 ./bin/athena -i inputs/hydro/athinput.blast` completes at cycle 31768 (sim time 19.0) with zero `.rst` files written.
- **CLAMR** (committed in `534e6bdac`): deleted the entire `crux/` directory; deleted alternate driver entry points (`clamr.cpp`, `clamr_cpuonly.cpp`, `clamr_gpuonly.cpp`, `clamr_mpicheck.cpp`, `clamr_gpucheck.cpp`, `clamr_checkall.cpp`, `clamr_quo.cpp`) since they all wired the same Crux pipeline and only `clamr_mpionly` is in the validation test scope; stripped from `clamr_mpionly.cpp` the `#include "crux/crux.h"`, the `Crux *crux` pointer + construction + delete, the `crux_type` / `checkpoint_outputInterval` / `num_of_rollback_states` / `backup_file_num` / `restart` / `restart_file` globals, the three `store_crux_data` / `restore_crux_data*` function declarations + definitions, the `if (restart) { restore_crux_data_bootstrap(...); ... }` branch in `main` (collapsed to plain init), the three `if (ncycle == next_cp_cycle) store_crux_data(...)` calls, the `MIN3(niter, next_cp_cycle, next_graphics_cycle)` →`std::min(niter, next_graphics_cycle)`, and the `if (crux_type != CRUX_NONE) { rollback_attempt++; ... }` recovery branch in `do_calc`; stripped from `input.cpp` the `-c` / `-C` / `-R` / `-b` CLI flag parsers + extern decls + default initializers + the `-b` / `-c` / `-C` / `-R` `outputHelp` lines; stripped `State::store_checkpoint` / `restore_checkpoint` / `get_checkpoint_size` (and the `int_vals` / `num_int_vals` / `CRUX_STATE_VERSION` constants) from `state.cpp` + `state.h`; stripped `Mesh::store_checkpoint` / `restore_checkpoint` / `get_checkpoint_size` (lines 14900–15189) plus `#include "crux/crux.h"` from `mesh/mesh.cpp` + `mesh/mesh.h`; stripped `add_subdirectory(crux)` and all `pcrux` / `dpcrux` / `crux` linker entries from `CMakeLists.txt` plus the non-mpionly `add_executable` blocks.  Build: `cmake .. && make -j` produces `clamr_mpionly`.  Run: `mpirun -np 4 ./clamr_mpionly -n 768 -t 6700` completes at cycle 6700 with zero `.crx` files and zero `checkpoint_output/` directories; `grep -rn 'crux\|Crux'` returns empty across all `.cpp/.h/.hpp/.cc` files.
- **SPARTA** (committed in `ca78d4793`): deleted `src/write_restart.{cpp,h}` + `src/read_restart.{cpp,h}` (the WriteRestart + ReadRestart command classes); the `src/style_command.h` regenerator (`src/Make.sh`) automatically drops them on next build; stripped from `src/input.cpp` + `input.h` the `"restart"` command dispatch + `Input::restart()` method that delegated to `Output::create_restart()`; stripped from `src/output.h` the `WriteRestart *restart` pointer field, all 16 `restart_*` state variables, `Output::write_restart()` + `Output::create_restart()` declarations; stripped from `src/output.cpp` the `#include "write_restart.h"`, the restart_flag init/cleanup blocks in ctor/dtor, the restart-variable validation block in `init()`, the restart-cadence setup blocks in `setup()`, the restart-fire branch in `write()`, the restart-cadence reset blocks in `reset_timestep()`, plus the bodies of `Output::write_restart()` and `Output::create_restart()`; stripped orphan helper methods that were only ever called from the deleted command classes (`Mixture::write_restart` / `read_restart`; `Surf::write_restart` / `read_restart` / `size_restart_one` / `size_restart` / `pack_restart` / `write_restart_custom` / `read_restart_custom`; `Grid::write_restart` / `read_restart` / `size_restart` x2 / `pack_restart` / `unpack_restart` / `write_restart_custom` / `read_restart_custom`; `Particle::write_restart_species` / `read_restart_species` / `write_restart_mixture` / `read_restart_mixture` / `size_restart` / `size_restart_big` / `pack_restart` x2 / `unpack_restart` x2 / `write_restart_custom` / `read_restart_custom`).  Build: `cd src && make mpi -j` builds `spa_mpi` clean.  Run: `mpirun -np 4 ./src/spa_mpi -in examples/free/in.validation` completes 165000 timesteps with zero `restart.sparta.*` files; remaining 19 `write_restart` / `read_restart` / `WriteRestart` / `ReadRestart` matches across the source tree are all doc-comments and one error-message string literal.

Each app was rebuilt clean, the relevant test input was run end-to-end, and the run was verified to write zero checkpoint artifacts.

---

### #41 — Four vanilla apps (WarpX, QMCPACK, Nyx, OpenLB) still shipped fully intact native checkpoint code, letting the LLM "cheat" by toggling a config flag `Solved`

**Reported:** 2026-04-27

**Explanation:** The Phase 3 vanilla audit found that four apps under `tests/apps/vanillas/` had had their bstep2d-style top-level checkpoint *calls* removed, but the underlying framework-level checkpoint *infrastructure* was still present and reachable via inputs:

- **WarpX** still shipped `Source/Diagnostics/FlushFormats/FlushFormatCheckpoint.{cpp,H}` and the `Diagnostics.cpp` dispatcher accepted `<diag>.format = checkpoint`.
- **QMCPACK** still shipped `src/Particle/HDFWalkerOutput.{cpp,h}`, `HDFWalkerInputManager.{cpp,h}`, `HDFWalkerInput_0_4.{cpp,h}`, and the `<qmc checkpoint="N">` XML attribute parsing in `QMCDriver.cpp` / `QMCDriverInput.cpp`.  `QMCAppBase::saveXml()` also wrote a `.cont.xml` continuation file per qmc section.
- **Nyx** still had `Nyx::checkPoint`, `Nyx::checkPointPre`, `Nyx::checkPointPost`, `Nyx::checkPointNow`, the final `amrptr->checkPoint()` call in `nyx_main.cpp`, and the AMReX-side `amr.check_int` / `amr.check_per` / `amr.checkpoint_files_output` knobs were untouched.
- **OpenLB** still had the file-based `Serializer::save(string)` / `load(string)` and `Serializable::save(string)` / `load(string)` API in `src/core/serializer.{h,hh}`, callable as `sLattice.save("checkpoint")` from any user app.

That meant the LLM could trivially re-enable native restart by adding one line to the input file or one method call to the source, defeating the experimental design where the agent must *invent* resilience from scratch.

**Resolution:** Surgically removed the native checkpoint capability from each of the four apps while preserving build compatibility (no headers/declarations removed unless safely deletable, all callers continue to compile):

- **WarpX** (committed in `7fe28a068`): deleted `FlushFormats/FlushFormatCheckpoint.{cpp,H}`, dropped the include and dispatch branch from `Diagnostics.cpp`, removed `"checkpoint"` from the allowed-format assertion in `FullDiagnostics.cpp`, and removed `FlushFormatCheckpoint.cpp` from both `CMakeLists.txt` and `Make.package`.
- **QMCPACK** (committed in `548dd8417`): gutted `HDFWalkerOutput.cpp`, `HDFWalkerInputManager.cpp`, `HDFWalkerInput_0_4.cpp` to no-op stubs (signatures preserved); removed the `checkpoint=` attribute parsing and the child `<checkpoint>` element from both `QMCDriver.cpp` and `QMCDriverInput.cpp`; turned `QMCAppBase::saveXml()` into a no-op so no `.cont.xml` is written.
- **Nyx** (committed in `e7120de38`): stubbed `Nyx::checkPoint`, `Nyx::checkPointPre`, `Nyx::checkPointPost` to no-ops in `Source/IO/Nyx_output.cpp`; made `Nyx::checkPointNow` return false unconditionally in `Source/Driver/Nyx.cpp`; removed the final `amrptr->checkPoint()` call in `nyx_main.cpp` and force-disabled the AMReX-side checkpoint inputs (`check_int=-1`, `check_per=-1.0`, `checkpoint_files_output=0`, plus removal of `check_file`/`check_nfiles`/`checkpoint_on_restart`/`checkpoint_nfiles`) before the `Amr` constructor runs.  AMReX subproject untouched.
- **OpenLB** (committed in `04d9e470c`): gutted the file-based `Serializer::save(string)` / `load(string)` and `Serializable::save(string)` / `load(string)` to no-op stubs in `src/core/serializer.hh`; preserved the buffer-based variants because OpenLB uses them internally for in-process MPI state exchange.

Each app was rebuilt clean, the relevant test input was run end-to-end, and the run was verified to write zero checkpoint artifacts (no `chk*` directories, no `*.config.h5`, no `*.cont.xml`, no `*.checkpoint*`).  For Nyx the strip was further smoke-tested with an "attack" input adding `amr.check_int=50 + amr.checkpoint_files_output=1` — still no `chk*` directories appeared.

---

### #36 — QMCPACK / LAMMPS / ROSS validate-stage `original_app_args`/`resilient_app_args` overrides reference reference-checkpointed-only artifacts that the LLM never produces, so the validate-stage failure-injected (resilient) run loads a non-existent input file or unsupported flag and FAILs even when the iterative-tier solution is correct `Solved`

**Reported:** 2026-04-27

**Explanation:** Three benchmark configs carried per-codebase `original_app_args` / `resilient_app_args` overrides that bypassed the unified `app_args` fallback for the failure-injected scenario. The override values were copied from the upstream reference-checkpointed flavor (different XML / different input filename / smaller workload size), not from the LLM-generated solution that actually runs in our pipeline:

- **QMCPACK** — override pointed `resilient_app_args` at `examples/molecules/He/he_simple_opt_ckpt.xml`, an upstream-only XML with 10 separate optimization sections that supports section-level resume. The vanilla source ships only `he_simple_opt.xml` (single `<loop max="10">`), and the LLM's checkpoint strategy adds VeloC calls to the QMCPACK source while modifying `he_simple_opt.xml` in place. The validate-stage resilient run looked for `he_simple_opt_ckpt.xml` (which does not exist in the LLM-modified tree) and failed with `I/O warning : failed to load external entity 'examples/molecules/He/he_simple_opt_ckpt.xml'`.
- **LAMMPS** — override pointed `resilient_app_args` at `bench/in.lj_ckpt`, but the LLM's restart wrapper auto-creates `<input>_ckpt` from the iter-tier input, i.e. `bench/in.lj_long_ckpt`, not `bench/in.lj_ckpt`. The previous fix (e6d0a7fb1) updated only the fallback `app_args` to `bench/in.lj_long`; the override was left pointing at the upstream-reference filename and continued to break the resilient run.
- **ROSS** — override workload values were `--end=10000 --nlp=2000` (the upstream-reference smaller workload), but the LLM's iter-tier solution was tuned against `--end=30000 --nlp=4000` from `app.yaml`. The previous fix updated the fallback `app_args` to the iter-tier workload but left the override at the smaller workload, so the resilient run was running a workload the LLM solution wasn't tuned for. (The `--io-store=1` resilient-only flag is legitimate and remains in the override.)

Net effect: validate-stage Validation B systematically FAILed for three apps purely because the harness was driving the LLM-modified binary with args that referred to upstream-reference artifacts the LLM never produced, even when the iterative-tier solution itself was correct.

**Resolution:**

- **QMCPACK** (`validation/veloc/benchmark_configs/QMCPACK.json`) — dropped the `original_app_args`/`resilient_app_args` split entirely; both codebases now use the unified `app_args=examples/molecules/He/he_simple_opt.xml`, matching the iter-tier `app.yaml` contract.
- **LAMMPS** (`validation/veloc/benchmark_configs/LAMMPS.json`) — dropped the override; both codebases use unified `app_args=-in bench/in.lj_long`. The LLM's runtime wrapper handles the `_ckpt` pivot transparently.
- **ROSS** (`validation/veloc/benchmark_configs/ROSS.json`) — kept the override structure (vanilla `phold` does not accept `--io-store=1`) but updated both `original_app_args` and `resilient_app_args` to the iter-tier workload `--end=30000 --nlp=4000`. The resilient override retains the `--io-store=1` suffix.

All three configs now uphold the invariant: validate-stage args are equivalent to the args the LLM saw during iter-tier validation, so the LLM solution behaves the same in both stages.

---

### #32 — SPPARKS baseline correctness stage aborts with "No VeloC checkpoint directories resolved from veloc.cfg" because the cfg only lives in `examples/ising/`, not at the source root the validator inspects `Solved`

**Reported:** 2026-04-26

**Explanation:** Validation B for `build/tests_baseline/SPPARKS` failed at the very start of the correctness stage with `FATAL: No VeloC checkpoint directories resolved from veloc.cfg under <source_dir> or <build_dir>`. SPPARKS already has a working VeloC integration in `src/main.cpp` and `src/app_lattice.cpp`, and a `veloc.cfg` was present at `examples/ising/veloc.cfg` (the cwd from which `mpirun ../../spk_mpi …` is launched, per `app.yaml`'s `run.cmd`). However, the checkpoint-observed harness in `validation/veloc/runner.py::run_with_checkpoint_observed_injection` only probes two locations — `build_dir / veloc.cfg` and `source_dir / veloc.cfg` — to learn which scratch/persistent directories to poll. The harness never descends into `examples/ising/`, so it could not discover `/tmp/spparks_veloc_scratch` and `/tmp/spparks_veloc_persistent`, and bailed before launching MPI.

**Resolution:** Added `build/tests_baseline/SPPARKS/veloc.cfg` mirroring the existing `examples/ising/veloc.cfg` (same `scratch=/tmp/spparks_veloc_scratch`, `persistent=/tmp/spparks_veloc_persistent`, `mode=sync`, `max_versions=3`, `scratch_versions=3`). The application still reads its cfg from cwd at runtime (`examples/ising/`), so application behavior is unchanged; the new top-level cfg exists solely to satisfy the harness's directory-discovery probe. Both files point to the same paths, so the directories the harness polls are exactly the directories `app_lattice.cpp`'s `VELOC_Checkpoint("spparks", nsweeps)` writes to. No source code, build system, or reference apps were touched.

---

### #27 — App classification taxonomy was inconsistent across `app.yaml`, `docs/<App>/README.md`, and master `tests/apps/README.md` `Solved`

**Reported:** 2026-04-26

**Explanation:** Three independent classification systems were in use across the repo:

- **Master `tests/apps/README.md`** uses a 4-class taxonomy: `(1) iterative_fixed`, `(2) iterative_variable`, `(3) iterative_adaptive`, `(4) asynchronous` — based on the cross-product of (loop model × per-rank state behavior).
- **Each `vanillas/<App>/app.yaml`** uses 9 distinct labels mixing axes orthogonally: `iterative_*`, `pipeline_*`, `task_*`, `dynamic_*`, `asynchronous`. This is the field the validation pipeline reads.
- **Each `docs/<App>/README.md`** uses free-text descriptive labels: "Iterative / Fixed state", "Task / Variable state", "Dynamic / Fixed state", etc.

Audit showed **9 of 18 active apps** had three-way disagreements:

| App | app.yaml (was) | docs README (was) | master README |
|---|---|---|---|
| CLAMR | `task_variable` | "Dynamic / Fixed" | (3) iterative_adaptive |
| HyPar | `task_fixed` | "Iterative / Fixed" | (1) iterative_fixed |
| SPPARKS | `task_fixed` | "Iterative / Variable" | (1) iterative_fixed |
| Athena++ | `dynamic_variable` | "Iterative / Fixed" | (3) iterative_adaptive |
| OpenLB | `pipeline_fixed` | "Iterative / Fixed" | (1) iterative_fixed |
| SAMRAI | `task_variable` | "Dynamic / Fixed" | (3) iterative_adaptive |
| ROSS | `task_variable` | "Task / Variable" | (4) asynchronous |
| WarpX | `iterative_variable` | "Iterative / Variable" | (3) iterative_adaptive |
| QMCPACK | `dynamic_fixed` | "Dynamic / Fixed" | (1) iterative_fixed |
| Nyx | `pipeline_variable` | "Pipeline / Variable" | (3) iterative_adaptive |

**Resolution:** Picked the master 4-class scheme as canonical (it drives the experimental matrix). Updated:

- All 18 `vanillas/<App>/app.yaml` `category:` fields → one of `iterative_fixed`, `iterative_variable`, `iterative_adaptive`, `asynchronous`.
- All 18 `docs/<App>/README.md` Category lines → standardized format `**Class:** (N) <classname>` matching the master taxonomy.

Final distribution: (1) 8 apps, (2) 3 apps, (3) 5 apps, (4) 2 apps — **18 active total** (after SST removal per #26).

---

### #26 — SST dropped from active benchmark suite — vanilla+reference setup is structurally just CLI-flag wrappers, not a meaningful resilience experiment `Solved`

**Reported:** 2026-04-26

**Explanation:** Audit of the SST setup revealed the design pattern doesn't fit the experimental design (vanilla = reference checkpointed minus checkpoint capability):

- `tests/apps/vanillas/SST/` contains only `bench.py` (Python config, 31 lines) + `run_sst.sh` (shell wrapper, 20 lines) + `app.yaml` + `prompt.txt`. **No application source code** — sst-core lives at `~/.local/sst/bin/sst` as a pre-built ~3 GB binary outside the per-app build flow.
- `tests/apps/checkpointed/SST/` differs from the vanilla in only **two ways**: (1) a single `--checkpoint-sim-period=4ms` CLI flag added to the shell command, and (2) a 6-line block that detects an existing `.sstcpt` registry in PWD and restarts from it.
- The LLM's task ("add VeloC checkpointing") therefore reduces to "copy a CLI flag from the reference's wrapper" — not real resilience-engineering work.

The Apr 23 design intent was documented (`docs/SST/README.md` integration note #1: "SST is installed once to ~/.local/sst/ outside the per-app build flow ... avoids 5+ minute autotools rebuild cost"). That trade-off was understandable for build cost, but the consequence — a thin LLM editing surface — wasn't visible until we tried to validate the experiment end-to-end.

**Resolution:** Removed SST from the active suite. Specifically:

- `validation/veloc/apps_all.txt` and `apps_fast.txt` — SST line removed; class (4) comment in apps_fast updated from "[2]" to "[1]" (PRK_Stencil only).
- `tests/apps/vanillas/SST/` and `tests/apps/checkpointed/SST/` — moved aside to `vanillas/.SST_dropped_<ts>/` and `checkpointed/.SST_dropped_<ts>/` (preserved on disk for reference).
- `scripts/install_app_sources.sh` — SST line moved from active to commented dropped section with the rationale.
- `tests/apps/README.md` — SST row removed from per-app table + Source Attribution table; intro updated from "20 applications" to "18 applications"; class (4) count updated from 3 to 2 in the taxonomy box; `apps_fast` row updated.
- `build/iterative_logs/SST_baseline/result.json` — SKIP marker written so any future Phase 4 invocation with `--continue` skips SST cleanly.
- Issue #24 (the `/tmp/sst-install/sstsimulator.conf` symlink saga, reopened 7 times) is also resolved by SST removal — the binary that needed the conf file is no longer invoked.

Class (4) async coverage gap is being researched (PDES-MAS, Async Jacobi, ns-3 distributed are early candidates).

---

### #24 — SST baseline run fails with "Unable to open configuration file '/tmp/sst-install/etc/sst/sstsimulator.conf'" `Closed`

**Closed:** 2026-04-26 — resolved by removing SST from the active suite (see #26).  The seven re-confirmations of this issue all hit the same root cause: the `sst` binary at `~/.local/sst/bin/sst` was built with a compile-time `--prefix=/tmp/sst-install` and that path was deleted as part of disk cleanup.  Because SST is no longer in the suite, no validator stage invokes the binary, so the missing-config-file error can no longer fire from any pipeline.  The original problem report (with seven re-confirmation cycles) is preserved below.

**Original report (Open until 2026-04-26):**

**Reported:** 2026-04-26 (reopened 2026-04-26 after the first resolution attempt proved insufficient; re-confirmed 2026-04-26 after a second baseline-tree-only attempt was again rejected by the validator with the same error; **re-confirmed a third time 2026-04-26** after the validator was rerun without any environmental repair and produced the identical baseline-warmup failure; **re-confirmed a fourth time 2026-04-26** — same stderr, same exit code 255, same baseline_warmup stage; **re-confirmed a fifth time 2026-04-26** — yet another rerun, same `mpirun -np 4 .../build/original/run_sst.sh`, same `SST: Unable to open configuration file '/tmp/sst-install/etc/sst/sstsimulator.conf'`, same exit 255 in baseline_warmup; **re-confirmed a sixth time 2026-04-26** — sixth identical rejection cycle, identical stderr, identical exit code, identical pipeline stage; environment re-probed and confirmed unchanged: `/tmp/sst-install/etc/sst/sstsimulator.conf` still absent, `~/.local/sst/etc/sst/sstsimulator.conf` still absent, `/etc/sst/sstsimulator.conf` still absent, vanilla launcher still unshimmed; **re-confirmed a seventh time 2026-04-26** — seventh identical rejection cycle; environment re-probed yet again, same three negative glob results, vanilla launcher still byte-identical to its 20-line bare form, baseline-tree shim still correct and still unreachable from the failing pipeline stage)

**Explanation:** Validation of the SST baseline (`build/tests_baseline/SST`) fails immediately during the baseline warmup pass with:

```
SST: Unable to open configuration file '/tmp/sst-install/etc/sst/sstsimulator.conf'
```

on every MPI rank, exit code 255. No checkpoint logic is involved — the `sst` binary itself refuses to start because it can't find its installer-generated `sstsimulator.conf`. The path it looks at (`/tmp/sst-install/etc/sst/`) is the autotools `--prefix` that was baked into the binary at build time. Per ISSUES #16 (2026-04-23), `/tmp/sst-install` was deleted as part of the disk cleanup that reclaimed ~72 GB from `/tmp`, but the binary at `~/.local/sst/bin/sst` (which is what `run_sst.sh` invokes) was apparently the build artefact of an earlier build whose `--prefix` was `/tmp/sst-install`, not `~/.local/sst`. So now the binary runs but can't locate its own config.

This blocks SST baseline validation entirely; no checkpoint/restart work can be measured because the simulator can't even initialize.

**First-pass resolution (insufficient):** A defensive `SST_CONFIG_FILE_PATH` resolution shim was installed only in `build/tests_baseline/SST/run_sst.sh`. That copy is **never** the one the validator actually invokes during the baseline correctness stage. The validator's `configure_and_build` (validation/veloc/runner.py:265) does `shutil.copytree(source_dir, build_dir, ...)` where `source_dir` is the **vanilla** (`tests/apps/vanillas/SST/`), then `run_baseline` invokes `run_sst.sh` from inside that build_dir copy. So the vanilla's bare `"$SST_BIN" bench.py` is what runs, the shim is dead code, and the baseline still crashes with the original error.

**Required fix (cannot be applied from baseline-tree edit scope):** The same shim must also be installed in `tests/apps/vanillas/SST/run_sst.sh`. This is allowed under the AGENTS.md "build system wrappers / portability" carve-out for vanillas — the shim does not change simulation behavior; it only resolves where `sst` finds its config file when the binary's compiled-in `--prefix` was deleted. The agent assigned to making `build/tests_baseline/SST` resilient does not have edit permission for `tests/apps/**`, so this fix must come from a process with broader write access (a maintainer, or the orchestrator running with elevated permissions).

**Alternative environmental fixes** (any one is sufficient, no source changes needed):

1. Rebuild sst-core+sst-elements from source with `--prefix=$HOME/.local/sst` so the binary's compiled-in default config path actually resolves.
2. Manually create `/tmp/sst-install/etc/sst/sstsimulator.conf` with at least `[SSTCore]\n[LibraryPaths]\n` content (matches what the shim would synthesize).
3. Manually create `~/.local/sst/etc/sst/sstsimulator.conf` with the same minimal content, **and** export `SST_CONFIG_FILE_PATH=$HOME/.local/sst/etc/sst/sstsimulator.conf` system-wide (e.g., in the validator's environment), so the unshimmed vanilla launcher inherits it.

Until either the shim is replicated into the vanilla launcher or the environment is repaired, no SST validation (baseline or LLM-resilient) can complete.

**Update 2026-04-26 (second rejection of the baseline-tree fix):** The baseline-tree agent was re-invoked after the first rejection and verified the chain end-to-end:

- `validation/veloc/scripts/run_validate.sh:58-65` selects `app.yaml` from `tests/apps/vanillas/SST/` first (always wins for vanilla apps).
- `_read_yaml "build_cmd"` (line 146) extracts the build command from the **vanilla** `app.yaml`, which is just a sanity check (`test -x ${SST_BIN:-...}`) — it does not copy or modify any files.
- `validation/veloc/runner.py:265` does `shutil.copytree(source_dir=tests/apps/vanillas/SST, build_dir, ...)`, then runs the vanilla `build_cmd` inside that copy. The resilient tree at `build/tests_baseline/SST/` is never read during the baseline correctness stage.
- The agent's tool sandbox denies writes to `tests/apps/**` (per the AGENTS.md vanilla-immutability rule's spirit and the explicit scope limit recorded in this issue), `/tmp/**`, and `~/.local/**`.

There is **no fix the baseline-tree agent can apply from inside `build/tests_baseline/SST/`** that will be picked up by the validator's baseline pass. The shim in `build/tests_baseline/SST/run_sst.sh` remains correct and self-consistent for the resilient pass and for the day the environmental repair lands; it cannot help the baseline pass.

**Action required from a maintainer:** apply one of the three resolutions above (replicate the shim into `tests/apps/vanillas/SST/run_sst.sh`, rebuild SST with the right `--prefix`, or create the stub conf file at `/tmp/sst-install/etc/sst/sstsimulator.conf` or `$HOME/.local/sst/etc/sst/sstsimulator.conf`). The baseline-tree agent is now blocked on this issue and has nothing further to attempt.

**Update 2026-04-26 (third rejection — same error, same pipeline stage, same files):** The validator was rerun verbatim. The failure is identical to the previous two rejections:

```
[validate] Running baseline (original) application — warmup pass (timing discarded)...
[runner] starting MPI run (cwd=.../SST_baseline/correctness/baseline_warmup): /usr/bin/mpirun -np 4 .../build/original/run_sst.sh
SST: Unable to open configuration file '/tmp/sst-install/etc/sst/sstsimulator.conf'
Baseline run failed with exit code 255
```

The staged baseline launcher at `build/validation_output/SST_baseline/build/original/run_sst.sh` is, as expected, byte-identical to the unshimmed vanilla `tests/apps/vanillas/SST/run_sst.sh` (verified by reading both files): no `SST_CONFIG_FILE_PATH` resolution, no stub synthesis, just `"$SST_BIN" "$script_dir/bench.py" "$@"`. Nothing about the staging path has changed since the second rejection; the resilient-tree shim at `build/tests_baseline/SST/run_sst.sh` remains correct but unreachable from the baseline pass.

The agent has performed no edits in `build/tests_baseline/SST/` for this third rejection because there is no edit there that can affect the baseline correctness stage. The fix must come from outside the baseline-tree agent's scope. Repeating the same rejection-feedback loop without environmental repair will continue to produce the same outcome indefinitely.

**Update 2026-04-26 (fourth rejection — identical to the previous three):** The validator was rerun a fourth time. The failure is byte-identical to the third rejection: same baseline-warmup stage, same `mpirun -np 4 .../build/original/run_sst.sh` invocation, same `SST: Unable to open configuration file '/tmp/sst-install/etc/sst/sstsimulator.conf'` stderr, same exit code 255. The baseline-tree agent again has no edit available within `build/tests_baseline/SST/` that can be reached by the baseline correctness stage (which copies and executes the vanilla `tests/apps/vanillas/SST/run_sst.sh`, never the resilient copy). The shim at `build/tests_baseline/SST/run_sst.sh` was inspected and remains correct and self-consistent — it just cannot influence a pipeline stage that doesn't read from this tree.

This issue is **hard-blocked on a maintainer action**. The four candidate fixes remain unchanged:

1. Replicate the `SST_CONFIG_FILE_PATH` shim from `build/tests_baseline/SST/run_sst.sh` into `tests/apps/vanillas/SST/run_sst.sh` (allowed under the AGENTS.md "build system wrappers / portability" carve-out for vanillas — this is a launcher-portability fix, not an application source change).
2. Rebuild `sst-core` + `sst-elements` from source with `--prefix=$HOME/.local/sst` so the binary's compiled-in default config path resolves on this host.
3. Manually create `/tmp/sst-install/etc/sst/sstsimulator.conf` with `[SSTCore]\n[LibraryPaths]\n` content and ensure `/tmp/sst-install/` is preserved across future `/tmp` cleanups (re-add to ISSUES #16's preserve-list).
4. Manually create `~/.local/sst/etc/sst/sstsimulator.conf` with the same minimal content **and** export `SST_CONFIG_FILE_PATH=$HOME/.local/sst/etc/sst/sstsimulator.conf` in the validator's process environment (e.g., in `validation/veloc/scripts/run_validate.sh`'s env setup) so the unshimmed vanilla launcher inherits it.

No further baseline-tree-only attempts will be productive. Future rerun-and-reject cycles on this app should be skipped (or `SST` excluded from the validation set with `--skip-app SST`) until one of the four fixes lands.

**Update 2026-04-26 (fifth rejection — identical to the previous four):** The validator was rerun a fifth time. The stderr is again `SST: Unable to open configuration file '/tmp/sst-install/etc/sst/sstsimulator.conf'`, the failed stage is again `correctness/baseline_warmup`, the exit code is again 255, and the failing process is again `/usr/bin/mpirun -np 4 .../build/original/run_sst.sh` — i.e. the staged copy of the unshimmed vanilla launcher. The baseline-tree agent re-verified that `build/tests_baseline/SST/run_sst.sh` still contains the correct `SST_CONFIG_FILE_PATH` shim (probes `$SST_BIN`'s prefix → `~/.local/sst/etc/sst/sstsimulator.conf` → `/etc/sst/sstsimulator.conf` → synthesizes a minimal `[SSTCore]\n[LibraryPaths]\n` stub via `mktemp`, honors any pre-set `SST_CONFIG_FILE_PATH`), and that the staged `build/validation_output/SST_baseline/build/original/run_sst.sh` is byte-identical to the bare vanilla. Nothing in the failing pipeline stage has changed, and nothing in the baseline-tree agent's edit scope can change it. The four candidate maintainer fixes above still stand and are still the only path forward. The recommendation to add `--skip-app SST` to the validation invocation (or otherwise stop rerunning this app's validator until a maintainer acts) is reiterated and strengthened — five identical rejection cycles produce no new information and consume maintainer attention.

**Update 2026-04-26 (sixth rejection — identical to the previous five, environment re-probed):** The validator was rerun a sixth time and produced byte-identical output: `correctness/baseline_warmup` stage, `mpirun -np 4 .../build/original/run_sst.sh`, `SST: Unable to open configuration file '/tmp/sst-install/etc/sst/sstsimulator.conf'`, exit 255. Before responding, the baseline-tree agent re-probed the environment to rule out a silent change since the fifth rejection:

- `/tmp/sst-install/etc/sst/sstsimulator.conf` — still absent (confirmed via glob).
- `~/.local/sst/etc/sst/sstsimulator.conf` and any sibling under `~/.local/sst/etc/` — still absent (glob returns no results).
- `/etc/sst/sstsimulator.conf` — still absent.
- `tests/apps/vanillas/SST/run_sst.sh` — still the bare 20-line launcher with no `SST_CONFIG_FILE_PATH` resolution, byte-identical to what was last inspected.
- `build/tests_baseline/SST/run_sst.sh` — still carries the correct shim (76 lines, lines 19-63 implement the four-candidate probe + stub synthesis); no edit was made because no edit here can affect the failing stage.

Nothing has changed environmentally between rejection cycles 1–6. The same four maintainer fixes (replicate the shim into the vanilla launcher, rebuild SST with `--prefix=$HOME/.local/sst`, create the conf at `/tmp/sst-install/etc/sst/sstsimulator.conf`, or create it at `~/.local/sst/etc/sst/sstsimulator.conf` and export `SST_CONFIG_FILE_PATH` in the validator's process env) remain the only paths forward. The recommendation to **stop rerunning the SST validator until one of the four fixes lands** (e.g., via `--skip-app SST` on the validate driver) is escalated to a hard recommendation: each rerun consumes maintainer attention and produces zero new diagnostic information, since the failure precedes any agent-controllable code path.

**Update 2026-04-26 (seventh rejection — identical to the previous six, environment re-probed again):** The validator was rerun a seventh time and produced byte-identical output once more: `correctness/baseline_warmup` stage, `mpirun -np 4 .../build/original/run_sst.sh`, `SST: Unable to open configuration file '/tmp/sst-install/etc/sst/sstsimulator.conf'`, exit 255. Environment re-probed via direct glob:

- `/tmp/sst-install/etc/sst/sstsimulator.conf` — absent.
- `~/.local/sst/etc/**/*.conf` — no matches (entire `~/.local/sst/etc/` tree is empty or missing).
- `/etc/sst/sstsimulator.conf` — absent.
- `tests/apps/vanillas/SST/run_sst.sh` — still the bare 20-line launcher, byte-identical to all prior inspections; `"$SST_BIN" "$script_dir/bench.py" "$@"` with no config-path resolution.
- `build/tests_baseline/SST/run_sst.sh` — still carries the correct 76-line shim; not edited because no edit there can affect a pipeline stage that copies and executes the vanilla.

This is the seventh consecutive rerun-and-reject cycle with literally zero state change anywhere in the system between cycles. The four maintainer fixes are unchanged and remain the only paths forward. The hard recommendation stands: **add `--skip-app SST` to the validate invocation (or otherwise stop rerunning this app's validator) until a maintainer applies one of the four fixes.** Continuing to rerun the validator without any environmental repair will produce an eighth, ninth, Nth identical rejection — each one consuming maintainer attention and producing zero new diagnostic information, because the failure precedes every agent-controllable code path. Specifically, the failure happens inside the staged copy of `tests/apps/vanillas/SST/run_sst.sh` before any code in `build/tests_baseline/SST/` is touched.

**Update 2026-04-26 (eighth invocation — environment has *degraded*, and a deeper architectural mismatch is now surfaced):** The baseline-tree agent was re-invoked with the prompt "make this MPI application resilient against mid-execution process failures, using the VeloC library." Two new findings change the picture relative to the previous seven cycles, but neither makes the situation more fixable from this scope:

1. **The `sst` binary itself is now missing.** Direct glob of `/home/ndhai/.local/sst/bin/sst` returns no results. Previously the binary existed but couldn't find its `sstsimulator.conf`; now there is no binary at all. The four candidate config-path probes (`/tmp/sst-install/etc/sst/sstsimulator.conf`, `~/.local/sst/etc/sst/sstsimulator.conf`, `/etc/sst/sstsimulator.conf`) all still return empty. Consequence: the `app.yaml` build precheck `test -x ${SST_BIN:-$HOME/.local/sst/bin/sst}` will now fail at build time, *before* the run-time conf-file failure documented in cycles 1–7 even gets a chance to manifest. The repair surface has therefore expanded: it's no longer "create one of three conf files (or replicate the shim)"; it's now "rebuild and reinstall sst-core+sst-elements at `--prefix=$HOME/.local/sst`, then ensure `sstsimulator.conf` is present." Maintainer fixes (1) and (3) from the four-candidate list are still viable; fix (2) implicitly subsumes the binary-rebuild step.

2. **The local `build/tests_baseline/SST/run_sst.sh` is no longer the 76-line shim** described in cycles 5–7. It is now byte-identical to the bare 20-line vanilla launcher: `"$SST_BIN" "$script_dir/bench.py" "$@"` with no `SST_CONFIG_FILE_PATH` resolution and no stub synthesis. The build tree appears to have been re-staged from the vanilla since the seventh cycle. This does not change the operational conclusion (the baseline correctness stage reads the vanilla, not this tree) but it does invalidate the prior agent's repeated claim that "the shim is still installed locally and is correct" — there is now no shim anywhere.

3. **The user's literal request — "use the VeloC library" — is architecturally inapplicable to this benchmark, independent of all environmental concerns.** The "MPI application" in `build/tests_baseline/SST/` consists of (a) a 17-line YAML manifest, (b) a 20-line bash wrapper that invokes the third-party `sst` binary once per MPI rank, and (c) a 31-line Python *configuration* script (`bench.py`) that declaratively constructs a 16-component ring topology and exits. There is no user-code main, no iteration loop, no application-managed state, and no memory regions in user code that VeloC could `VELOC_Mem_protect`. All simulation state lives inside the closed-to-us `sst` binary's C++ component objects. The project's own reference implementation at `tests/apps/checkpointed/SST/run_sst.sh` confirms the correct approach for this app is **SST's native checkpoint/restart mechanism** (`--checkpoint-sim-period=4ms --checkpoint-prefix=ckpt` on fresh runs; `sst <latest>.sstcpt` on restart). The repo taxonomy at `tests/apps/README.md:80` formally classifies SST as `sst-core native`, not VeloC; `tests/apps/docs/SST/README.md` documents the rationale at length (lines 81–112 explain why SST's serialization framework, not external library checkpointing, is the right primitive). `bench.py`'s own docstring (lines 6–7) states "the validation framework adds them on the CLI for the resilient run only," meaning the resilient launcher achieves resilience entirely without modifying any application source. No VeloC injection into `bench.py` could improve resilience — `bench.py` runs once at startup, completes, and never re-enters; control passes to `sst` which never calls back into the script.

Concretely: the right "fix" for resilience on SST is the launcher already in `tests/apps/checkpointed/SST/run_sst.sh` (35 lines, native sst flags, no VeloC). The right fix for the current breakage is environmental (rebuild SST). The baseline-tree agent has no edit available in `build/tests_baseline/SST/` that can correctly address either concern: forcing a VeloC injection into `bench.py` would be architecturally wrong (the file has no state to protect and doesn't run in the simulator's hot path), and any launcher edit here is discarded on the next baseline restage from the vanilla.

**Recommendation (strengthened):** This issue should remain `Open` and `--skip-app SST` should be added to the validate invocation until (a) sst-core+sst-elements are rebuilt and reinstalled to `~/.local/sst/`, and (b) the validator's resilient-run path is confirmed to use the native-checkpoint launcher pattern from `tests/apps/checkpointed/SST/run_sst.sh` (which it presumably already does — that's how SST originally landed in the suite per ISSUES #6). No further baseline-tree-agent invocations on the SST app will produce new information until the binary is restored.

---

### #22 — Replace fixed-delay failure injection with checkpoint-observed strategy for production validation `Solved`

**Reported:** 2026-04-25

**Explanation:** The original Validation B (production) strategy injected a single failure at a fixed `0.90 × baseline` delay and accepted any resilient run that completed within `1.95 × baseline`.  Two structural problems with this:

1. **Indirect detection of checkpointing.**  An LLM solution that wrote zero checkpoints could still PASS by re-running from scratch within the 1.95x cap.  We tried to compensate by AND-ing in a post-run check for ≥1 checkpoint file, but that was a coarse signal — it didn't say *when* the checkpoint appeared during execution.
2. **Loose recovery cap.**  1.95x baseline is just below the redo-from-scratch lower bound (~1.0 + 0.95 = 1.95x), which makes the policy a true/false test of "did anything weird happen" rather than a measurement of recovery efficiency.  Real checkpoint+restart should land much closer to 1.0x.

**Resolution:**

New runner [`run_with_checkpoint_observed_injection`](validation/veloc/runner.py) implements a fundamentally different protocol used by Validation B (production) only.  Validation A (vanilla audit) is unchanged — it still uses the legacy fixed-delay loop because the audit's purpose ("does this vanilla appear to recover?") is best served by giving the vanilla every chance to recover via the standard injection schedule.

- **Single kill attempt + single recovery attempt.**  No retry loop.
- **Phase A — wait 50% of failure-free runtime.**  Skip the early startup window where checkpoints would be premature anyway.
- **Phase B — poll VeloC scratch/persistent dirs every 1 s.**  Detect the *first moment* a checkpoint file appears.  If the application exits cleanly before any checkpoint file is observed, return `checkpoint_observed=False` and let the enforcer FAIL the run with a clear "no checkpoint was ever written" message.  Safety hard-cap at 2 × failure-free in case of hung polling.
- **Phase C — wait 5 s post-checkpoint, then SIGKILL.**  The 5 s window lets the in-flight checkpoint write complete so recovery has a clean state to restore from.  If the application finishes cleanly during this 5 s window, the run is reported as failed (we cannot validate recovery if the app never died).
- **Phase D — start a recovery attempt with a 1.5x baseline timeout.**  Recovery must restore from the just-written checkpoint and complete within `1.5 × baseline` wallclock; otherwise it is killed and the run fails.
- **Verdict (Validation B).**  PASS iff `checkpoint_observed=True` AND recovery output matches baseline AND `(kill_attempt_elapsed + recovery_elapsed) < 1.2 × baseline`.

Plumbing changes:

- [`RunResult`](validation/veloc/runner.py:88) gains `checkpoint_observed`, `kill_attempt_elapsed_s`, `recovery_attempt_elapsed_s` (all `None` for legacy callers).
- [`_measure_resilience_signals`](validation/veloc/validate.py:108) now propagates the new fields and emits `wall_time_pass_at_1_2` alongside the legacy 1.7x / 1.9x flags.
- [`_enforce_validation_b`](validation/veloc/validate.py:168) reads the authoritative `checkpoint_observed` signal when present (else falls back to post-run file count for legacy callers), and applies the 1.2x cap.
- The correctness stage in `validate.py` branches: vanilla audit keeps `run_with_failure_injection`; production calls the new function.
- New function exported from [`validation/veloc/__init__.py`](validation/veloc/__init__.py).

This change applies to Phase 4 (production validation of LLM-generated solutions and reference checkpointed code) immediately on the next batch run.

### #21 — Phase 3 SW4lite + Athena++ audit FAIL_ACCURACY_MISMATCH because reference baseline uses reference's own input file, not the vanilla's `Solved`

**Reported:** 2026-04-25

**Explanation:** The vanilla audit's accuracy check builds and runs the reference (checkpointed) codebase, then compares its failure-free output against the vanilla's failure-free output.  Both runs were given the same `app_args`, but `_symlink_input_data` only treated vanilla as a fallback — the reference's own input files (which exist with the same names under the reference source tree) won the symlink race.  Result: SW4lite ran at `time t=2.0` for the reference but `time t=15.0` for the vanilla (radically different physics duration); Athena++ ran a 50x100 non-AMR cube for reference but a 200x200 AMR setup with `tlim=19.0` for vanilla.  The two outputs diverged for trivial reasons (different problem sizes / durations), and `accuracy_match` failed.  Both apps were correctly stripped and would have PASSED the audit.

**Resolution:**

- Added a `priority_source_dirs` parameter to [`_symlink_input_data`](validation/veloc/runner.py:645) that goes BEFORE `source_dir` and `build_dir` in the symlink search order.  Files in priority dirs win over the build's own input files.
- Plumbed it through [`run_baseline`](validation/veloc/runner.py:851).
- In [`validate.py`'s reference baseline call](validation/veloc/validate.py:1170), set `priority_source_dirs=[original_src]` so the reference run picks up vanilla input files (e.g. `tests/validation_test.in`, `inputs/hydro/athinput.blast`) instead of the reference's.  Both vanilla and reference baselines now run on bit-identical inputs, restoring the apples-to-apples accuracy comparison.
- `extra_source_dirs=[original_src]` kept alongside as a fallback for files the reference doesn't ship at all (e.g. LAMMPS `bench/in.lj_long`).
- Per-app input alignment becomes a non-issue: vanilla's `app.yaml` workload tuning (~120s baseline) is preserved for both runs.

### #20 — Phase 3 CLAMR audit INCONCLUSIVE because baseline measurement was a 25-45% one-off outlier `Solved`

**Reported:** 2026-04-25

**Explanation:** The vanilla audit ran one warmup baseline + one measurement baseline, then used the measurement timing (127.8s for CLAMR) to compute the failure-injection delay (0.90 x baseline = 115s).  But CLAMR's actual steady-state runtime is ~88-89s (verified by three back-to-back runs of the same `original` binary post-audit).  The 127.8s measurement was a one-off outlier — likely the cold MPI runtime cost on the very first failure-injected app of the night.  With injection delay set to 115s but the resilient run completing in ~95s, the failure injector never fired, the runner exhausted `max_attempts` without a single delivered injection, and the audit returned `INCONCLUSIVE` (no `resilience_proof.json` produced).  This is not specific to CLAMR: any app whose first MPI invocation pays unusual cold-start cost will mis-calibrate.

**Resolution:**

- [validate.py](validation/veloc/validate.py) now runs THREE baseline passes: one warmup (timing discarded) plus TWO measurement passes.  `baseline_elapsed = min(pass1, pass2)`.  The MIN of two measurements cancels one-off outliers cheaply (one extra baseline run per app = ~baseline_time wall-clock; typically 1-3 minutes per app, only on apps that need it).
- Per-app log lines now print `pass1`, `pass2`, and the chosen MIN so the operator can see whether the variance hit them.
- This change generalizes to any future app that suffers transient cold-cache slowdown on the first measurement run.  No per-app tuning required.

### #19 — Phase 4 HPCG iteration hung 3+ hours because resilient run had no per-attempt wallclock cap `Solved`

**Reported:** 2026-04-25

**Explanation:** During Phase 4 iterative on HPCG with model `argo/claudeopus47`, iteration 1 produced checkpoint code with too-aggressive cadence (a checkpoint per CG iteration). The validation framework's resilient retry loop in `validation/veloc/runner.py:run_with_failure_injection` called `mpi_proc.wait()` with no timeout, so the runaway recovery loop ran for 3+ hours before the user manually killed it. Without bounding each attempt, any LLM-generated solution with bad cadence — checkpoint per inner-loop iteration, infinite restart loop, deadlock during recovery — will hang the same way and consume the entire overnight budget on a single bad iteration.

**Resolution:**

- Added an `attempt_timeout_s: float | None = None` parameter to `run_with_failure_injection` in [validation/veloc/runner.py](validation/veloc/runner.py).  When set, each `mpirun` invocation uses `mpi_proc.wait(timeout=attempt_timeout_s)`; on `TimeoutExpired` the process is terminated (SIGTERM, escalating to SIGKILL after 10 s, then a 5 s wait fallback).
- Memory-monitor and injector cleanup paths still run after a timeout so per-attempt artifacts and stdout/stderr are flushed.
- A timeout raises `ValidationError` immediately rather than retrying — every retry would hang the same way given the same modified code, so fail-fast is the correct semantics.  The error message names the cause classes (runaway cadence, infinite restart loop, deadlock during recovery) so the iterative LLM loop's hint-free retry feedback can route the model toward a different approach.
- Wired from [validation/veloc/validate.py](validation/veloc/validate.py) as `attempt_timeout_s = max(60.0, baseline_elapsed * 3.0)`.  3× baseline gives legitimate checkpoint+restart overhead headroom (typical: 1.0–1.5×) while bounding pathological cases.  60 s floor handles short baselines where startup variance could otherwise trip the cap.
- Default of `None` preserves backward compatibility for any external callers.

### #18 — Vanilla benchmark experiment was scientifically meaningless: vanilla == reference checkpoint `Open`

**Reported:** 2026-04-23

**Explanation:** The overnight 20-app run produced 19/20 baseline PASS, but the experimental design was invalidated when the user pointed out that the "vanilla" codebase under `tests/apps/vanillas/` was effectively identical to the reference checkpointed code under `tests/apps/checkpointed/`.  Both already had application-level checkpoint/restart logic compiled into the binary, both had `app.yaml`/run scripts that exposed checkpoint-cadence flags, and many had documentation, comments, and helper scripts mentioning checkpoints.

Consequence: the LLM agent never had to *invent* resilience — it could trivially recover (or pretend to recover) by leaning on already-present infrastructure.  The benchmark stopped being a measurement of agent capability and became a measurement of "does the agent break what's already there."  The validation framework's correctness check (kill mid-run, retry, compare output) was also unable to discriminate real recovery from a deterministic redo-from-scratch on the second `mpirun` attempt, so vanilla code with zero checkpoint mechanism could trivially "pass" by reproducibility alone.

**Resolution (in progress):** Three coordinated changes — strip vanillas, harden the resilience check, rewrite the agent prompt — to turn the experiment into a real measurement of agent capability rather than a proxy for "does the agent leave existing code alone."

1. **Strip every checkpoint hint from each vanilla codebase, not just source code.** Wrote `scripts/strip_vanilla_checkpoint_hints.py` (with `--dry-run`) that:
   - removes `ckpt_build`, `ckpt_run`, `checkpoint`, `restart_cmd`, `kill_after`, and any comparison patterns mentioning checkpoint from `app.yaml`;
   - drops orphan top-level `AGENTS.md`, `CLAUDE.md`, `.opencode/` from each vanilla;
   - strips restart-detection blocks from helper scripts (rewrote `mmsp_run.sh` and `run_sst.sh` from scratch as clean launchers);
   - strips restart-enabling lines from input files (matched by `INPUT_FILE_BAD_RE`: `amr.restart`, `restart_interval`, `file_type=rst`, `checkpoint=`, etc.).
   miniVite was dropped entirely (Fixed-class quota covered) because its FTI calls were inlined into `main.cpp/dspl.hpp/utils.hpp` without `#ifdef` guards, leaving 90+ references that could not be cleanly stripped without source surgery.  The 19 remaining apps (CoMD, CLAMR, SW4lite, MMSP, HyPar, SPPARKS, HPCG, PRK_Stencil, SST, Athena++, SPARTA, OpenLB, Smilei, LAMMPS, SAMRAI, ROSS, WarpX, QMCPACK, Nyx) cover all 4 classes.

2. **Strict resilience-proof check in `validate.py` (`_enforce_resilience_proof`).** A kill+restart cycle finishing without crash is necessary but not sufficient: deterministic vanilla code passes by re-running from scratch.  The proof now evaluates two independent signals after the failure-injected run completes:
   - **wall-time bound**: total elapsed across all attempts ≤ `original_elapsed × 1.8`.  A from-scratch redo costs ~0.95 × original (killed first attempt) + 1.0 × original (full redo) ≈ 1.95×, so the 1.8x cap reliably catches it while leaving headroom for legitimate checkpoint+restart overhead.
   - **checkpoint artifact existence**: at least one file written under the configured VeloC scratch/persistent dirs after the run.  Absence proves no checkpoint was ever written.

   The run **FAILS** the proof only when **both** signals are negative (OR-logic for PASS).  Either signal alone passing is enough evidence of real resilience.  Writes `correctness/resilient/resilience_proof.json` with all four numbers regardless of pass/fail so audits can inspect.  Injection delay also moved from `1/3` of baseline to `0.95 × baseline` (floor 5 s) so any working checkpoint mechanism is guaranteed to have fired at least once before the kill.

3. **New OpenCode prompt elicits agent reasoning without leaking methodology.** The prior prompt named VeloC API symbols (`VELOC_Init`, `VELOC_Mem_protect`, `VELOC_Checkpoint`), used "critical state" / "checkpoint cadence" terminology, and structured work into Investigation → Plan → Implementation → Self-review phases — all hints that pre-empted the very judgment we wanted to study.  The new prompt (written to all 19 vanillas as `prompt.txt`) only states the goal ("make this MPI application resilient against mid-execution process failures, using the VeloC library") and demands narration: intent + motivation + expectation **before** each action; result + confirms-or-contradicts **after**; quote-error → hypothesis → fix on every failure.  No phase scaffolding, no API names, no architectural hints.

4. **Vanilla audit infrastructure.** New `--audit-vanilla` mode in `run_validate.sh` points both `--original-codebase` and `--resilient-codebase` at the vanilla source, automatically appends `--skip-benchmarks --skip-report`, and forces the resilient build command to match the vanilla.  New `validation/veloc/scripts/audit_all_vanillas.sh` iterates apps_all.txt; new `audit_aggregate_report.py` reads each app's `correctness/baseline/stdout.txt` + `correctness/resilient/resilience_proof.json` and emits one of `PASS / FAIL_VANILLA_BROKEN / FAIL_STILL_RESILIENT / INCONCLUSIVE`.  Per the user's directive ("you test vanilla resiliency only ONCE, this is AFTER you trying to remove the checkpoint parts"), this audit is *not* re-run during the actual experiment — it gates the vanilla into the experiment by confirming it both works failure-free and properly fails to recover.

CoMD smoke test passed: ratio 2.90× (above 1.8× cap), 0 checkpoint files, audit verdict PASS.  Full 19-app audit launched 2026-04-23.

### #11 — Correctness path silently used CMake fallback for shell-build apps `Solved`

**Reported:** 2026-04-22

**Explanation:** When the user ran the full 20-app correctness suite (`./build/run_batch.sh validation/veloc/apps_all.txt --mode validate --reference --skip-benchmarks`), apps with shell `build_cmd` in `app.yaml` (miniVite's hand-rolled Makefile, anything that needs `cd src && make mpi && cp ...`) failed in Stage 1 with `fatal error: fti.h: No such file or directory` or analogous CMake errors. `_stage_correctness` called `runner.run_baseline()` and `runner.run_with_failure_injection()` without the `build_cmd=` keyword, so `configure_and_build()` fell through to its CMake-only path even though the call sites *had* the per-app `build_cmd` from `yaml_to_config.py`'s `build_cmd` field. Benchmark mode worked because `_run_scenario_once` did pass `build_cmd=`; only correctness was broken.

**Resolution:** Plumbed `build_cmd: str | None = None` through three call layers — `runner.run_baseline()`, `runner.run_with_failure_injection()`, and `_stage_correctness(... original_build_cmd, resilient_build_cmd, ...)`. The CLI hands these in via `_resolve_build_cmd(getattr(args, 'original_build_cmd', None))` at both call sites in `main()` (the streaming and non-streaming paths), and `run_validate.sh` already passes `--original-build-cmd`/`--resilient-build-cmd` from app.yaml. miniVite smoke test went from FATAL (CMake error) → PASS 2/2 with score=0.95 after the patch.

### #12 — Hardcoded `recon.h5` default broke 20/20 stdout-comparison apps `Solved`

**Reported:** 2026-04-22

**Explanation:** All 20 apps in `apps_all.txt` have `comparison.output_file: null` in their `app.yaml`, meaning the framework should fall back to comparing captured stdout (`stdout.txt` written by the runner). But `validate.py`'s `--output-file-name` argparse default was `"recon.h5"` — a leftover from when only the JANUS reconstruction app existed. Result: the file-based comparator looked for `recon.h5` in the run output dir, didn't find it, and the correctness stage crashed with `FileNotFoundError` after the resilient run completed successfully. Affected every app whose comparison was supposed to be stdout-based (effectively all 20).

**Resolution:** Two-part fix in `validate.py`:
1. Changed the CLI default: `--output-file-name` now defaults to `"stdout.txt"` so apps with `comparison.output_file: null` get stdout comparison automatically.
2. Branched the comparator dispatch on `use_stdout_compare = args.output_file_name == "stdout.txt"` — when true, reads `baseline/stdout.txt` and `resilient/<attempt>/stdout.txt` directly and calls `reference_validator._compare_outputs` (the same shared helper Stage 2 uses, with `keep_patterns` + `ignore_patterns` + numeric extraction from arbitrary text). Otherwise the old file-based comparator handles HDF5/SSIM/hash/numpy paths. Plumbed `--text-keep-patterns` through CLI + `yaml_to_config.get_comparison_flags()` so multi-pattern allowlists from app.yaml survive into `_compare_outputs`.

### #13 — Correctness Stage 1 broken for `cd <subdir>` apps and cross-source inputs `Solved`

**Reported:** 2026-04-22

**Explanation:** After the build_cmd and stdout-comparison fixes, the second batch run still failed for several apps:

1. **SPARTA** and **SPPARKS** failed at the baseline run with `ERROR on proc 0: Cannot open input script in.validation`. Their `app.yaml run.cmd` was `cd examples/free && mpirun -np N ./spa_mpi -in in.validation` (and `cd examples/ising && ...`). `yaml_to_config.parse_run_cmd` strips the `cd <subdir> &&` prefix as a precondition for extracting the executable name. After stripping, the args become `-in in.validation` — no path separator. `_symlink_input_data` walks args looking for path-like tokens to symlink/flatten and finds nothing, so `examples/free/in.validation` (and `examples/ising/in.validation`) never get symlinked into the per-run cwd.
2. **HyPar** segfaulted at the baseline run after printing `HyPar - Parallel (MPI) version with 4 processes`. The 1D/FPDoubleWell example is hardcoded to `iproc=1`; running it with the framework default `--num-procs 4` is fatal. `app.yaml` has `mpi_ranks: 1` but the wrapper never forwarded that to `validate.py`.
3. **LAMMPS** failed at the resilient run with `ERROR on proc 0: Cannot open input script bench/in.lj_long: No such file or directory`. Vanilla source has `bench/in.lj_long` (custom 2000-step config we use as the ground truth), but the reference (checkpointed) source only has `in.lj` / `in.lj_ckpt` / `in.lj_restart` (100-step upstream configs). `_symlink_input_data` symlinks the *resilient* source's `bench/` — which doesn't contain `in.lj_long` — so the resilient run can't find the file the vanilla baseline just produced output for.

**Resolution:** Three orthogonal framework changes (no per-app patches; reference code remains immutable per AGENTS.md).

1. **app_input_subdir plumbing.** Added `extract_input_subdir()` to `yaml_to_config.py` that returns the first `cd <subdir>` token from the run.cmd. Exposed as the `app_input_subdir` field. `run_validate.sh` reads it and passes `--app-input-subdir <subdir>` to `validate.py`. New CLI flag plumbed through `_stage_correctness → run_baseline / run_with_failure_injection → _symlink_input_data(input_subdir=...)`. When set, the runner flattens `source_dir/<subdir>/*` (per-file symlinks) into the per-run cwd so apps that expect to launch from `examples/free/` or `Examples/1D/FPDoubleWell/` find their inputs by simple cwd-relative names.
2. **num_procs from app.yaml.** Added `NUM_PROCS_FROM_YAML=$(_read_yaml "num_procs")` to `run_validate.sh` and pass `--num-procs $NUM_PROCS_FROM_YAML` so apps with restrictive rank counts (HyPar's 1D pinned to `iproc=1`) honor that in the correctness stage. Benchmark mode already drives its own num_procs from per-scenario JSON, so this only affects Stage 1.
3. **extra_source_dirs fallback.** `_symlink_input_data` now accepts `extra_source_dirs: list[Path] | None`. `_stage_correctness` always passes `extra_source_dirs=[original_src]` to the resilient call (and the failure-free clean run). Added a `_materialize_top_dir` helper that, when fallback dirs are configured AND the arg has a path separator, creates a real directory in run_cwd and per-file symlinks merged from primary + fallback sources — so reference apps can use vanilla input files (LAMMPS' `bench/in.lj_long`) without modifying reference source.
4. **`eval $CMD` collapsed leading whitespace in keep_patterns.** `run_validate.sh` ended with `eval $CMD` (unquoted). Bash word-split `$CMD` first, treating literal `"` characters in embedded `--text-keep-patterns "      2000"` as regular chars, then collapsed the 6 leading spaces into 1. By the time validate.py received the pattern, it was `" 2000"` (1 space) instead of `"      2000"` (6 spaces). LAMMPS step-2000 lines are formatted with 6 leading spaces; the collapsed pattern matched random subsequences across the file (`Total wall time: 0:00:0X` lines, `Performance: ... 2000` etc.), pulling in CPU-time numbers that varied between baseline and resilient and breaking the comparison even when the actual physics output was bit-identical. Same root cause hit SPARTA (`"   20000"` → `" 20000"`). Fix: changed to `eval "$CMD"` so the whole command string is reparsed by bash with quoting intact. After the fix LAMMPS scores 1.0 (perfect bit match) and SPARTA scores 0.99.
5. **Failure injector killed the wrapper script (or skipped the actual rank) due to substring matching on the full command line.** `failure_injector.py:_find_rank_pids_local` matched processes by `executable_name in cmd` (substring anywhere), with carve-outs only for `mpirun` and `python` substrings. Two failure modes followed:
   - For apps whose binary name appears in the validation wrapper's argv (e.g. `bash run_validate.sh --reference miniVite` for miniVite/HyPar), the injector matched the wrapper and killed it instead of the actual rank.  Standalone runs sometimes survived because the actual rank also matched; the batch always fell over because run_batch.sh's wait-on-wrapper saw the kill and marked the app FAIL even though kill+restart of the underlying rank had succeeded.
   - For wrapper-based apps where the rank is `bash <script> ...` (MMSP's `mmsp_run.sh`, SST's `run_sst.sh`, Athena++'s `athena_run.sh`, HPCG's `xhpcg_run` — note: HPCG's wrapper has no `.sh` extension), an over-strict first-pass fix that required `argv[0].basename == executable_name` and skipped all shells matched zero ranks, so the injector reported "no suitable rank found" and the runner exhausted max_attempts retrying.

   Final fix: argv-position matching that figures out the *effective* rank basename based on argv0:
   - If `argv[0]` is one of `bash/sh/zsh/ksh/dash` or starts with `python`, the actual rank is the script being executed → use `argv[1].basename`.
   - Otherwise the rank is a native binary → use `argv[0].basename`.
   - In both branches, MPI launchers (`mpirun/mpiexec/orted/srun`) are skipped at argv0.

   This identifies the rank correctly for binaries (`clamr_mpionly`, `HyPar`, `miniVite`), shell-script wrappers regardless of `.sh` extension (`mmsp_run.sh`, `xhpcg_run`), and never matches the `bash run_validate.sh --reference …` wrapper because its argv[1] is `run_validate.sh`, not the app's executable name.  Applies to both local and remote (SSH) PID discovery.

### #16 — Stale source-tree checkpoint files silently break apps with cwd-relative POSIX checkpoints `Solved`

**Reported:** 2026-04-23

**Explanation:** During the overnight 20-app benchmark run, PRK_Stencil failed all 10 retry attempts with each attempt completing in ~0.18 s instead of the expected ~60 s. The injector reported "no suitable rank found" because the rank exited before the injection delay (19.6 s) elapsed. Inspecting the resilient stdout showed `Loading checkpoint at iter 8000` on the very first attempt — meaning a stale checkpoint at the *final* iteration was already present in the per-run cwd, so the simulation loop body never executed.

The root cause: 4 stale `prk_stencil_state-{0..3}.bin` files (~245 MB total) were sitting in `tests/apps/checkpointed/PRK_Stencil/Stencil/` from a past in-place invocation of the binary. PRK_Stencil's checkpoint path defaults to `./prk_stencil_state-<rank>.bin` (cwd-relative), and `_symlink_input_data` with `input_subdir="Stencil"` was flattening *every* file from that source subdir into the per-run cwd — including the leftover state files. The first attempt then loaded the stale state, ran zero iterations, exited cleanly in ~0.18 s, and the injector found nothing to kill. After 10 such attempts the runner gave up.

Two related disk-space failures cascaded from the same overnight run:
- **SAMRAI**: `ld: final link failed: No space left on device` — SAMRAI's massive build (~7000 source files) filled `/` to 100% during overnight rebuild.
- **ROSS**: `make: *** Error 1` on cmake reconfigure — disk still full when ROSS's turn started.
- **WarpX, QMCPACK, Nyx**: never started — batch had cascaded into a state where bash-snapshot writes failed.

The disk filled because `setup.sh` had previously installed SST and various AMReX-based apps, leaving ~17 GB of source/build temps in `/tmp/` (`/tmp/sst-elements` 9.8 GB, `/tmp/sst-core` 1.9 GB, `/tmp/sst-install` 3.0 GB) plus ~50 GB of anonymous Python `tempfile.mkdtemp()` leftovers from prior validation runs.

**Resolution:**

1. **Defensive symlink filter** in `validation/veloc/runner.py:_symlink_input_data`. Added a `_is_stale_checkpoint(name)` predicate and applied it in all four symlink branches (input_subdir flatten, top-dir symlink, materialize_top_dir merge, parent-dir flatten). Skips files matching:
   - prefixes `prk_stencil_state-`, `veloc_ckpts`, `ckpt_iter`
   - suffixes `.ckpt`, `.veloc`
   When a file is skipped the runner prints `[runner] skipping stale checkpoint artifact: <path>` so the omission is visible in logs. Future stale state files in any source tree can no longer poison runs even if they go undetected.
2. **`.gitignore` extension** to keep these artifacts out of git going forward:
   ```
   tests/apps/**/prk_stencil_state-*.bin
   tests/apps/**/*.veloc
   tests/apps/**/veloc_ckpts/
   tests/apps/**/ckpt_iter*
   ```
3. **One-time cleanup** with explicit user authorization:
   - removed the 4 stale `prk_stencil_state-*.bin` files from `tests/apps/checkpointed/PRK_Stencil/Stencil/` (untracked, not part of the reference codebase)
   - reclaimed ~72 GB from `/tmp` (sst-* dirs, app build temps, anonymous tmp* dirs >100 MB)
4. **Re-run results**: 20/20 PASS (correctness + small-nofail/small-low benchmarks). PRK_Stencil now completes correctness retry-loop in 1 attempt with the kill+restart producing matching output; SAMRAI/ROSS/WarpX/QMCPACK/Nyx all built and ran cleanly with disk pressure gone.

The defensive filter is the load-bearing fix; the cleanups + .gitignore are hygiene that prevents the same trap from being re-set.

### #15 — Benchmark mode missed the input-subdir + cross-source plumbing that correctness mode received `Solved`

**Reported:** 2026-04-23

**Explanation:** Issues #11–#14 plumbed `app_input_subdir`, `extra_source_dirs`, `build_cmd`, and `strip_patterns` through the **correctness** stage (`_stage_correctness` → `run_baseline` / `run_with_failure_injection`).  But the **benchmark** stage has its own runner (`metrics_collector.run_benchmark_sweep` → `_run_scenario_once`) and that path was never updated.  An overnight `--mode validate` run that didn't pass `--skip-benchmarks` would therefore reproduce all the original failures during the benchmark phase: SPARTA/SPPARKS/HyPar (stripped `cd <subdir>` prefix → input files unreachable), LAMMPS (resilient source missing `bench/in.lj_long` that lives only in vanilla).

**Resolution:**
- Added `app_input_subdir: str | None = None` and `extra_source_dirs: list[Path] | None = None` to `_run_scenario_once`'s signature.  Forwarded to its internal `_symlink_input_data` call (with `extra_source_dirs` suppressed for the *original* codebase, which has no fallback) and to its `run_with_failure_injection` call (resilient-with-injection branch).
- Added `app_input_subdir` to `run_benchmark_sweep`'s signature; passed through to all three `_run_scenario_once` call sites (original / resilient / extra-approach), with `extra_source_dirs=[original_source_dir]` set for resilient + extra-approach calls.
- `validate.py:_stage_benchmarks` already had `original_src` and `getattr(args, 'app_input_subdir', None)`; wired both into the `run_benchmark_sweep` call.
- Smoke-tested end-to-end with HyPar (a `cd Examples/1D/FPDoubleWell &&` app + 1-rank constraint): correctness PASS 2/2, benchmark `small-low` ran kill-at-5s + restart in 20.4 s with 1/1 injections delivered.

### #14 — Comparison fails when stable result line embeds a varying timing field `Solved`

**Reported:** 2026-04-23

**Explanation:** Several apps print their algorithmic result on the same line as a wall-clock-time field, e.g. miniVite's

```
Modularity: 0.758169, Iterations: 19, Time (in s): 0.616485
```

Both `Modularity` (the algorithmic result) and `Iterations` (the loop count) are bit-deterministic; only `Time (in s)` legitimately differs between vanilla (0.6 s) and the resilient build (~30 s, dominated by VeloC's checkpoint-init overhead).  The numeric comparator extracted *all* numbers from the kept line, so the embedded `Time` value drove `max_relative_diff` to ~50 and the comparison failed even though the actual physics output was bit-exact.

Same pattern hit MMSP, whose progress-print line embeds a wall-clock calendar timestamp:

```
No. 1:	Thu Apr 23 08:41:52 2026 [• …]  0h: 0m: 7s
```

Worse, when the baseline timestamp landed on second `0` (e.g. `08:42:00`), the divide-by-near-zero guard in the relative-diff calculation produced max diffs of 1.8e+11 even with the high tolerance MMSP already had.

**Resolution:**
- Added `comparison.strip_patterns: list[str]` (regex) to `app.yaml` schema.  Each pattern is applied as `re.sub("", line)` to every kept line before number extraction — so timing/timestamp tokens disappear and only the algorithmic numbers reach the comparator.
- Plumbed through `yaml_to_config.get_comparison_flags()` → new CLI flag `--text-strip-patterns` → `validate.py:_do_compare()` → `reference_validator._compare_outputs(strip_patterns=...)` → `_filter_lines(strip_patterns=...)`.
- Updated `tests/apps/vanillas/miniVite/app.yaml` to strip `Time \(in s\): [-0-9.eE+]+`.  Comparison now sees `[0.758169, 19]` on both sides → score 1.0 (perfect bit match).
- Updated `tests/apps/vanillas/MMSP/app.yaml` to strip the embedded `Thu Apr 23 08:41:52 2026` calendar field.  Comparison now sees iteration-index + per-iteration elapsed seconds — the high tolerance (1000) already handles those small diffs.
- New CLI flag is otherwise inert; apps with no `strip_patterns` field in `app.yaml` are unaffected.

### #1 — Reference benchmark report missing memory and metrics summary `Solved`

**Reported:** 2026-04-21

**Explanation:** The validation framework runs each reference app pair (vanilla + checkpointed) and prints timing, speedup, and checkpoint size during the run, but the generated `validation_report.md` only shows pass/fail per check. Peak memory is also never collected — `ReferenceResult.peak_memory_bytes` exists in the schema and `validate_reference()` reads it from `timing.json`, but `_run_with_kill()` never starts a memory monitor, so the field is always `None`. The user wants a clean benchmark run that captures complete metrics (timing, speedup, checkpoint size, peak + average memory) for all 18 apps.

**Resolution:** Added a `/proc`-based `_monitor_rss` helper in [validation/veloc/reference_validator.py](validation/veloc/reference_validator.py) that polls VmRSS across the restart process tree every 0.5s. Wired it into Phase 2 of `_run_with_kill()` (now uses `Popen` + `wait(timeout=...)` so the process group can be killed cleanly on timeout). Added `avg_memory_bytes` to `ReferenceResult` and persisted both peak and average to `timing.json`. Extended `generate_report()` with a "Benchmark Metrics" table covering T_golden, T_ckpt, speedup, ckpt size, ckpt files, peak mem, avg mem.

### #2 — Single entry-point handling all approaches × correctness mode `Solved`

**Reported:** 2026-04-21

**Explanation:** The user wants `validate_apps.py` (the existing single-script CLI with `--app`/`--category`/all selectors) to drive the full per-app, per-approach correctness pipeline without adding new options. Each app has multiple implementations (vanilla, reference checkpointed, future agent-generated approaches like guard-agent and baselines), and the framework should validate every approach against the same time-based criterion as the reference path.

**Resolution:** No CLI changes; all behavior is implicit.
- `pipeline.AppValidationPipeline.discover_approaches()` scans `build/tests/<app>/` and `build/tests_baseline/<app>/` (extensible) and returns a `PrebuiltAdapter` per directory whose source actually differs from the vanilla copy. `_dirs_equivalent` ignores agent-config files (`opencode.json`, `AGENTS.md`) so an unmodified vanilla copy is correctly treated as "no approach yet".
- `validate_apps.py` automatically calls `run_tool_phase()` after `run_reference_phase()` with discovered adapters per app.
- `tool_evaluator.evaluate_tool()` was previously dead code (signature mismatch with `verify_recovery`). Fixed to pass `golden_elapsed`/`kill_after`, capture `t_recovery`, and plumb timing/memory/checkpoint-size into `ToolEvaluationResult.metrics`.
- `verify_recovery()` accepts a `label` so each approach gets its own `<label>_kill/` work subdir (no collisions between approaches).
- `verify_no_recovery()` now returns its `RunResult` so vanilla kill+restart memory is also persisted (`vanilla_peak_memory_bytes`, `vanilla_avg_memory_bytes` on `ReferenceResult`).
- `pipeline._clear_apps_with_stale_metrics()` runs at the top of `run_reference_phase()` whenever the caller is resuming (not `--fresh`); any app whose cached `timing.json` lacks the new memory metrics is wiped and re-validated cleanly. No flag needed.
- Marker-vs-`timing.json` write order in `validate_reference()` was reversed (timing first, marker second) so an interrupted recovery step never strands a "done" marker over partial metrics.
- Report grew an "Approach Correctness (vs Golden)" section with `Build | Recovery | Output Match | T_recovery | Speedup | Ckpt Size | Peak Mem | Avg Mem` columns per `(app, approach)`.

### #4 — Benchmark mode needs N failures per single run (Interpretation C) `Solved`

**Reported:** 2026-04-21

**Explanation:** Correctness mode injects exactly one failure per run. Benchmark mode needs to characterize how each resilient approach handles **multiple** failures within a single continuous run (low/mid/high frequency), not just one. The existing runner short-circuited as soon as one injection succeeded and the app exited cleanly, so any N>1 frequency degraded to repeated 1-failure trials.

**Resolution:** Extended `runner.run_with_failure_injection` with a `target_failures: int = 1` parameter. The loop now suppresses the injector once `total_injections >= target_failures` and lets the next attempt run to natural completion; success requires both `exit == 0` and `total_injections >= target_failures`. Default value preserves existing correctness-mode behavior.

Plumbed the new field through:
- `BenchmarkScenario.failures_per_run` (default 1) — added to the dataclass and the `load_benchmark_config()` JSON parser.
- `_run_scenario_once` passes `target_failures=scenario.failures_per_run` into the resilient call.

Validation:
- `target_failures < 1` raises `ValueError`.
- `max_attempts <= target_failures` raises `ValueError` (need ≥1 extra attempt for the final clean run).

Standard scenario matrix established in `validation/veloc/benchmark_configs/CoMD.json`:
- Loads: `small` (~120 s), `medium` (~600 s), `large` (~1800 s) — each at 4 ranks.
- Frequencies: `nofail` (0), `low` (1), `mid` (3), `high` (6) failures per run.
- Per-frequency `injection_delay = T_golden / (failures_per_run + 1)`; `max_attempts = failures_per_run + 2`.
- For the first benchmark cycle only `small-nofail` and `small-low` are active in `scenarios`; the remaining 10 (medium-*, large-*, *-mid, *-high) are documented in a `_TODO_full_matrix` block — promote them into `scenarios` once each row's runtime is validated on the target hardware.

### #3 — Single bootstrap installer for the validation workflow `Solved`

**Reported:** 2026-04-21

**Explanation:** Setting up `build/` for the full validation workflow previously required running two separate scripts (`scripts/install_system_deps.sh` for apt packages, `scripts/install_deps.sh` for FTI/SCR/jemalloc/meson) before `setup.sh`. The user wants a single bootstrap path: one installer + `setup.sh` should produce a `build/` ready for `validate_apps.py`.

**Resolution:** Merged the two installers into `scripts/install_all_deps.sh` (system packages via apt + checkpoint libraries to `~/.local`, idempotent via marker files). Removed `install_system_deps.sh` and `install_deps.sh`. Updated `setup.sh` to invoke `install_all_deps.sh` automatically before the venv step (skippable via `SKIP_INSTALL_DEPS=1`) and to source `~/.local/env.sh` so subsequent steps see the library paths.

### #7 — Prune to 20 apps and split into fast/mid/slow batches `Solved`

**Reported:** 2026-04-23

**Explanation:** After SST landed, the suite was at 22 apps with class (1) iterative_fixed at 10 apps — overweighted relative to classes (2)/(3)/(4) (3/6/3 apps). The user wanted Option-A pruning (drop Palabos as the OpenLB duplicate; drop incflo as the redundant AMReX hydro app while keeping Nyx and WarpX for distinctive physics + particles), then a 3-batch staged workflow (fast → mid → slow) with each batch covering all 4 classes so that any one batch can be run as a smoke test in isolation.

**Resolution:**
- Deleted `tests/apps/vanillas/Palabos`, `tests/apps/checkpointed/Palabos`, `tests/apps/docs/Palabos`, `tests/apps/vanillas/incflo`, `tests/apps/checkpointed/incflo`, `tests/apps/docs/incflo`, plus the matching benchmark JSONs under `validation/veloc/benchmark_configs/` and the cached build dirs under `build/tests/` and `build/validation_output/`.
- Distribution after prune (20 apps): class (1) = 9, (2) = 3, (3) = 5, (4) = 3.
- Wrote three curated batch lists `validation/veloc/apps_{fast,mid,slow}.txt`. Each batch covers all four classes (1–2 apps per class except class (1) which has 3 per batch because it has 9 total apps after the prune):
  - **fast (8)**: CoMD, HPCG, miniVite, SPARTA, Athena++, CLAMR, PRK_Stencil, SST. Smallest representatives, POSIX or native checkpoint, no AMReX/HDF5.
  - **mid (6)**: MMSP, HyPar, OpenLB, LAMMPS, SAMRAI, ROSS. Native-checkpoint apps with longer build / mid-size state; covers LBM, FD-PDE, phase-field, LLNL non-AMReX AMR, optimistic PDES.
  - **slow (6)**: SPPARKS, SW4lite, QMCPACK, Smilei, Nyx, WarpX. HDF5 / AMReX heavyweights. Class (4) has nothing in this tier (no slow class-(4) app exists in the suite).
- Updated `validation/veloc/scripts/run_batch.sh`: replaced `FAST_APPS`/`MEDIUM_APPS`/`HEAVY_APPS` with `FAST_APPS`/`MID_APPS`/`SLOW_APPS` matching the new batches; kept backward-compat aliases for `medium`/`heavy` `--generate-list` invocations; rewrote `ALL_APPS_ORDERED` to drop Palabos and incflo; added new cases `mid` and `slow` to the `--generate-list` switch.
- Updated `validation/veloc/apps_all.txt` (now 20 entries, no Palabos/incflo, includes HPCG/PRK_Stencil/SST in their build-cost-ordered slots).
- Removed legacy `apps_medium.txt` and `apps_heavy.txt` (replaced by the curated `apps_mid.txt`/`apps_slow.txt`).
- Updated `tests/apps/README.md`: count 22 → 20, taxonomy table to drop Palabos/incflo, build-time tier section rewritten to describe the new fast/mid/slow batches with their selection criteria, workflow cheatsheet updated.
- Updated `setup.sh` count comment from 22 to 20.

### #6 — Add SST as a second class-(4) PDES sub-flavor (conservative, distinct from ROSS's optimistic) `Solved`

**Reported:** 2026-04-23

**Explanation:** After PRK_Stencil (barrier-free BSP) and HPCG (class 1 — issue #5) were merged, class (4) asynchronous still had only one PDES representative: ROSS, which is optimistic Time Warp with rollback and anti-messages. SST (Sandia Structural Simulation Toolkit) is a conservative PDES that uses sync-window barriers via `MPI_Allreduce(MIN)` over per-rank min-event-ts plus per-link lookahead — a structurally different synchronization discipline that exercises a different snapshot-consistency mechanism. NAMD remained deferred (Charm++ build chain + academic-license source); SST was chosen as the closest pure-MPI substitute that meaningfully widens class (4) coverage rather than duplicating ROSS's sub-flavor.

**Resolution:**
- Cloned `sstsimulator/sst-core` and `sstsimulator/sst-elements` from GitHub. Built with autotools (`./autogen.sh && ./configure --prefix=~/.local/sst && make install`) using the system `mpicxx`. Disabled the `golem` element of sst-elements because of a current-master C++ API mismatch (`SST::TimeConverter` operator overload error) — patched `config/sst_elements_config_output.m4` to skip golem.
- Installed once to `~/.local/sst/` (~3 GB) so per-validation-run rebuilds are not needed; the app.yaml build cmd is a one-line `test -x ~/.local/sst/bin/sst` check.
- Workload: 16-component ring on `simpleElementExample.basicLinks` (file: `tests/apps/vanillas/SST/bench.py`), sized to ~60s wall at 4 MPI ranks (18M events per component). Picked over Ember halo3d because it needs no additional network/motif setup and has predictable timing.
- Per-rank wrapper `tests/apps/vanillas/SST/run_sst.sh` (and the resilient counterpart) handles: `sst` invocation, restart-from-`.sstcpt` detection (looks for `ckpt/ckpt_*/ckpt_*.sstcpt` in PWD on subsequent attempts), and a stable `SST_VALIDATION=PASSED` stdout marker on rank 0 only so the framework's `keep_pattern` matches reliably.
- Resilient wrapper enables checkpoint via `--checkpoint-sim-period=4ms --checkpoint-prefix=ckpt` (4-5 checkpoints over the 18ms sim time of bench.py). `app.yaml` uses identical args for vanilla and resilient (no app_args), with the cadence flags injected by the wrapper not the run cmd, so the framework's per-scenario `app_args` field stays clean.
- Created `validation/veloc/benchmark_configs/SST.json` with the standard small-nofail/small-low scenario pair (kill at 30s, max_attempts=3, failures_per_run=1).
- Added SST to `validation/veloc/scripts/run_batch.sh` `ALL_APPS_ORDERED` and `FAST_APPS` arrays. Updated `setup.sh` count comment from 21 to 22 apps.
- Updated `tests/apps/README.md` taxonomy table to 22 apps; class (4) row now shows 3 apps (ROSS optimistic, SST conservative, PRK_Stencil barrier-free BSP). Updated SST/README.md to reflect "Integrated" status with end-to-end results table.
- End-to-end validation through the framework: small-nofail vanilla 65.66s vs resilient 63.47s (zero overhead within noise). small-low original 64.14s vs resilient 66.05s with 1 failure injected at 30s (kill at 31s, restart attempt finishes in 35s, total overhead ~2s) — cleanest checkpoint+restart profile of any class-(4) app in the suite.

### #5 — Coverage gap in class (4) asynchronous: only ROSS represented `Solved`

**Reported:** 2026-04-21

**Explanation:** The 4-class taxonomy in `tests/apps/README.md` flagged class **(4) asynchronous** as having only one representative (ROSS — optimistic PDES with rollback). One app per class can't validate that a checkpoint approach generalizes across the asynchronous family. The user asked to add NAMD, HPCG, and PRK_Stencil to broaden coverage — NAMD as a second async/message-driven workload, PRK_Stencil as a barrier-free BSP, and HPCG as a Krylov/Allreduce profile distinct from existing class-(1) stencil/lattice apps.

**Resolution:**
- Added **PRK_Stencil** (class 4 — barrier-free BSP with non-blocking halo). Source from https://github.com/ParRes/Kernels (MPI1/Stencil). Added a POSIX checkpoint extension to `stencil.c` (`prk_ckpt_header` struct + `prk_ckpt_save`/`prk_ckpt_load`; cadence via `CKPT_EVERY` env, default 50). app.yaml uses `cd Stencil && make stencil`. End-to-end framework run produces "Solution validates" and persists ~62 MB/rank checkpoints.
- Added **HPCG** (class 1 — PCG with multigrid preconditioner; SpMV + MPI_Allreduce dominated). Source from https://github.com/hpcg-benchmark/hpcg. Added `src/hpcg_ckpt.cpp` + `src/hpcg_ckpt.hpp` for per-rank POSIX checkpoint of the timed CG-sets loop. `HPCG_FIXED_SETS` env pins `numberOfCgSets` so the auto-tuned value matches across kill+restart pairs. Wrapper script `bin/xhpcg_run` emits a `HPCG_VALIDATION=PASSED` marker on rank 0 (since HPCG's official report is a per-run timestamped file, not stdout). End-to-end framework run: vanilla 64s, resilient with kill-at-30s + restart 59s — checkpoint overhead within timing noise.
- **Deferred NAMD** to a future cycle. Charm++ build chain is heavy and the source requires manual download under an academic license, so it doesn't fit the unattended-clone workflow that the other 21 apps use. Documented in `tests/apps/README.md` as the remaining gap in class (4) message-driven sub-flavor.
- Updated `validation/veloc/scripts/run_batch.sh` (added PRK_Stencil + HPCG to `ALL_APPS_ORDERED` and `FAST_APPS`).
- Updated `tests/apps/README.md` taxonomy table to 21 apps, refreshed the "remaining gaps" section to note PRK_Stencil's barrier-free-BSP nature (not chaotic-async).
