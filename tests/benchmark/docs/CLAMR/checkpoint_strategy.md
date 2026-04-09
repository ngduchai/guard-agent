# CLAMR Checkpoint Strategy

## Reference Implementation
CLAMR has a **native checkpoint/restart** mechanism built directly into the application. The checkpoint implementation is part of the CLAMR source code and does not depend on an external checkpoint library.

## Checkpoint Library
- **Native** (built-in to CLAMR)
- Uses standard POSIX file I/O to write checkpoint files
- Optional: HDF5 output format for portable checkpoint files

## What Is Checkpointed
All state required to restart the simulation from a given time step:
- Cell state arrays: `H`, `U`, `V` (water height and velocities)
- Mesh structure: cell positions (`i`, `j`), refinement levels (`level`), neighbor connectivity
- Scalar state: `ncycle`, `simTime`, `deltaT`, `ncells`, `levmx`
- Mesh metadata: global mesh dimensions, refinement parameters
- Because the mesh is adaptive, the **full mesh structure** must be saved (unlike fixed-mesh codes)

Total checkpoint size: ~7 MB per rank for a 1M-cell problem on 8 ranks

## Where Checkpoints Are Placed
At the **end of each time step**, after state update and AMR are complete:

```
for (int cycle = start_cycle; cycle < max_cycles; cycle++) {
    compute_fluxes();
    update_state();
    do_amr();
    load_balance();
    // <- CHECKPOINT HERE (if cycle % checkpoint_interval == 0)
}
```

## Restart Logic
1. Check for a valid checkpoint file (via command-line flag `-R` or checkpoint file presence)
2. If restarting: read all cell state arrays, mesh structure, and scalar state from checkpoint file
3. Rebuild ghost cell layers and neighbor connectivity from the restored mesh
4. Resume the time step loop from the saved cycle number
5. If no checkpoint: initialize mesh and state from problem parameters

## Checkpoint Overhead
- Per-checkpoint overhead: ~2-5% of a time step (depends on cell count and I/O bandwidth)
- Frequency: configurable via `-c <interval>` command-line flag
- Checkpoint file size scales linearly with cell count
- The dynamic mesh structure makes checkpoints larger than a fixed-mesh code with the same number of unknowns

## Configuration
```bash
# Run with checkpoint every 100 steps
./clamr_mpionly -n 1000 -c 100

# Restart from checkpoint
./clamr_mpionly -R checkpoint_file
```
