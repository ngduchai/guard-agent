# SAMRAI checkpoint enablement (input-file based, no CLI flag)

## Summary
SAMRAI's LinAdv reference application has **no CLI flag** for enabling
checkpointing. Native checkpoint writes are controlled entirely by the
`Main { restart_interval = N }` key inside the input file, which is consumed
by `RestartManager::writeRestartFile()` every `N` integrator iterations.

## File to edit
`tests/apps/checkpointed/SAMRAI/validation_inputs/linadv.2d.input`
(and/or its overlay copy under `tests/apps/patches/SAMRAI/validation_inputs/`)

## Where the value is read in upstream source
- `source/test/applications/LinAdv/main.cpp:296-299` — reads
  `restart_interval` from `Main {}` block (defaults to `0` = disabled).
- `source/test/applications/LinAdv/main.cpp:329-330` — `write_restart =
  (restart_interval > 0) && !restart_write_dirname.empty()`.
- `source/test/applications/LinAdv/main.cpp:518-525` — every
  `iteration_num % restart_interval == 0`, calls
  `tbox::RestartManager::getManager()->writeRestartFile(restart_write_dirname, iteration_num)`.

## Why the current input produces ZERO checkpoints
The current `linadv.2d.input` already declares:
```
Main {
   ...
   restart_interval = 100
   restart_write_dirname = "restart_linadv"
}
TimeRefinementIntegrator {
   end_time             = 100.e0
   max_integrator_steps = 5000
}
```
However, the simulation almost certainly terminates on `end_time` (or fewer
than 100 coarse-level integrator iterations) before iteration 100 ever fires
on the coarsest level, so the modulus check `iteration_num % 100 == 0` never
triggers. Result: zero checkpoint files written.

Additionally, note the build-time guard at `main.cpp:318-327`:
```c++
#if (TESTING == 1) && !defined(HAVE_HDF5)
   is_from_restart = false;
   restart_interval = 0;
#endif
```
`linadv` is compiled with `TESTING=1` (see
`source/test/applications/LinAdv/CMakeLists.txt:55`), so SAMRAI **must** be
built with HDF5 enabled (CMake `-DENABLE_HDF5=ON`, the default) for restarts
to work at all. Verify HDF5 is linked before tuning the cadence.

## Recommended change

Set `restart_interval` to a small enough value that ~5-10 checkpoints land
within a ~100s benchmark run. Without knowing the exact iteration rate, a
conservative starting point is:

```
Main {
   dim = 2
   base_name = "linadv_val"
   log_all_nodes = FALSE
   viz_dump_interval = 0
   restart_interval = 10           # was: 100  -> ~5-10 checkpoints/run
   restart_write_dirname = "restart_linadv"
}
```

If 10 still produces zero or fewer than 5 checkpoints in a 100s run, drop
to `restart_interval = 5` or `restart_interval = 2`. If it produces too
many (>15), raise to `restart_interval = 20`. Tune empirically against
`raw_metrics.json:checkpoint_size_bytes`.

## What NOT to do
- Do not edit `tests/apps/checkpointed/SAMRAI/...` directly (reference code
  is immutable per AGENTS.md). Apply the change via the patches overlay at
  `tests/apps/patches/SAMRAI/validation_inputs/linadv.2d.input`.
- Do not add a CLI flag — there is no such flag in the upstream `main.cpp`.
  The only positional CLI args (see `main.cpp:154-164`) are
  `<input file> [<restart dir> <restore number>]`, and the latter two are
  for *reading* a restart, not for *enabling* checkpoint writes.
