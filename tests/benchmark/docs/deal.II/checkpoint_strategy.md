# deal.II Checkpoint Strategy

## Reference Implementation
Native checkpoint via `Triangulation::save()` / `Triangulation::load()` combined with `SolutionTransfer` for moving solution data across mesh changes.

## Checkpoint Library
Native (built into deal.II). Uses p4est serialization for the mesh + parallel HDF5 or binary for solution data.

## What Is Checkpointed
- Full distributed triangulation (mesh topology + refinement levels)
- Solution vectors (FE coefficients on all DOFs)
- Simulation metadata (cycle number, time)

## Where Checkpoints Are Placed
Typically at the end of each refinement cycle, after the solve completes.

## Restart Logic
1. Create a coarse triangulation matching the original
2. Call `Triangulation::load(filename)` to restore refinement
3. Use `SolutionTransfer` to interpolate solution to restored mesh
4. Resume from the saved cycle

## Checkpoint Overhead
Mesh serialization: ~1-2 seconds for 1M cells. Solution I/O dominates for large problems.
