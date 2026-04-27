# tests/apps/patches/

Per-app input-file patches applied **only** during reference-mode benchmarks
(`run_validate.sh --reference <APP>`).

## Why this exists

The validation framework benchmarks three flavors of each app:

| Flavor | Source | Checkpoint mechanism |
|---|---|---|
| **vanilla** | `tests/apps/vanillas/<APP>/` | None (checkpoint logic stripped) |
| **LLM-baseline** | `build/tests_baseline/<APP>/` (LLM-modified vanilla) | VeloC, added by the LLM |
| **reference** | `tests/apps/checkpointed/<APP>/` (immutable upstream) | The app's own native mechanism (HDF5 `.rst`, POSIX state files, AMReX `chk*`, etc.) |

For a fair "same scenarios" comparison, all three flavors must run the **same workload** —
same MPI rank count, same mesh size, same iteration count. We achieve this by sharing
**vanilla's** input config across all three (`--reference-input-priority` forces vanilla
inputs to win over the reference's tiny upstream-demo configs).

But vanilla's input config is intentionally minimal — it's pure computation, no
checkpoint output. When the reference binary runs against vanilla's input, it never
writes any native checkpoint files, and `checkpoint_size_bytes` ends up as `None`.

That's where this directory comes in.

## How patches are applied

`run_validate.sh --reference <APP>` builds a temporary overlay at run time:

1. Copy the entire vanilla input tree into a tmp dir.
2. Overlay every file from `tests/apps/patches/<APP>/` on top (overwrites where present).
3. Pass the tmp overlay as the highest-priority input source to `validate.py`.
4. Clean up the tmp dir on exit.

The overlay is read-only at run time; the original vanilla tree is never modified.

The patch is **sparse** — it only contains the files you want to override. You don't
need to copy the whole input tree. For example, an Athena++ patch that only adds
a checkpoint-output block to one file looks like:

```
tests/apps/patches/Athena++/
└── inputs/
    └── hydro/
        └── athinput.blast    # vanilla's content + extra <output3> file_type=rst block
```

## Patch precedence (highest → lowest)

```
tests/apps/patches/<APP>/        # this directory (reference benchmarks only)
tests/apps/vanillas/<APP>/       # the workload-tuned vanilla inputs
tests/apps/checkpointed/<APP>/   # upstream reference's own inputs (lowest)
```

This means: a file present in the patch dir wins. Files absent from the patch dir
fall through to vanilla. Files absent from both fall through to the reference.

## Why patches mostly only touch CHECKPOINT-related parameters

Most apps have a few config knobs that turn on their native checkpoint mechanism
without changing the simulation itself. The patch adds those knobs. Examples:

| App | Patch contents |
|---|---|
| **Athena++** | Adds `<output3> file_type=rst dt=5.0` block to athinput.blast |
| **HyPar** | Sets `op_overwrite=no` + `op_file_format=binary` (timestamped op_NNNNN.bin) |
| **LAMMPS** | Adds `restart 1000 restart.lj` directive |
| **Nyx** | Sets `amr.checkpoint_files_output=1` + `amr.check_file=chk` + `amr.check_int=50` |
| **QMCPACK** | Adds `checkpoint="0"` attribute to `<qmc method="linear">` inside `<loop>` |
| **SAMRAI** | Adds `restart_interval=100` + `restart_write_dirname` to `Main { ... }` block |
| **SPARTA** | Adds `restart 2000 restart.sparta` directive |
| **SW4lite** | Adds `checkpoint cycleInterval=50 file=restart` directive |
| **Smilei** | Appends `Checkpoints(dump_step=100, exit_after_dump=False, ...)` Python block |
| **WarpX** | Appends `chkpoint` AMReX checkpoint diagnostic (4 lines) |

### Apps with NO file-based patch

| App | How checkpoint is enabled |
|---|---|
| **CLAMR** | CLI flag `-c N` already in `validation/veloc/benchmark_configs/CLAMR.json`'s `app_args` |
| **CoMD** | Hardcoded in reference's `src-mpi/CoMD.c` (`ckptRate=500`, no flag); reference binary auto-writes |
| **HPCG** | Env vars `CKPT_EVERY` + `HPCG_FIXED_SETS`; `run_validate.sh --reference` exports them per-app |
| **MMSP** | Reference binary writes timestamped `test.NNNN.dat` files unconditionally per the run-cmd's increment arg |
| **OpenLB** | Hardcoded in reference's `bstep2d.cpp` (`iT % 5000`); reference binary auto-writes |
| **PRK_Stencil** | Env var `CKPT_EVERY`; `run_validate.sh --reference` exports it per-app |
| **ROSS** | CLI flag `--io-store=1` already in `validation/veloc/benchmark_configs/ROSS.json`'s `resilient_app_args` |
| **SPPARKS** | **No real native checkpoint mechanism upstream** — `dump sites` writes visualization output, not full restart state. `checkpoint_size_bytes` for SPPARKS reference will be 0 / very small (only stats files match POSIX patterns). Documented limitation; treat SPPARKS reference checkpoint-size as not-applicable. |

**Patches must NEVER**:
- Change the workload size (mesh resolution, time limit, particle count, etc.).
  The whole point is "same scenario, just enable checkpointing." If a patch
  changes the workload, vanilla and reference benchmarks are no longer
  comparable.
- Modify any source code or build configuration.
- Add files outside the input directory tree.

## Adding a new patch

1. Find the app's vanilla input file you need to extend
   (e.g. `tests/apps/vanillas/Athena++/inputs/hydro/athinput.blast`).
2. Copy that file into `tests/apps/patches/<APP>/` at the same relative path
   (e.g. `tests/apps/patches/Athena++/inputs/hydro/athinput.blast`).
3. Edit the copy to **append** the checkpoint-enabling stanza only.
   Do not change anything else.
4. Run `bash validation/veloc/scripts/run_validate.sh --reference <APP> --skip-correctness --benchmark-num-runs 1`
   and verify the resulting `build/validation_output/<APP>_reference/benchmarks/raw_metrics.json`
   shows `checkpoint_size_bytes > 0` for the resilient runs.
5. Commit the new patch under `tests/apps/patches/<APP>/`.

## Cleanup

The tmp overlay directory is created via `mktemp -d` and removed by an `EXIT`
trap in `run_validate.sh`. If a run is killed mid-execution (e.g. SIGKILL from
the parent batch script), the tmp dir may be orphaned. Look under
`/tmp/ref_input_overlay.*` and remove stale ones manually if you suspect this.
