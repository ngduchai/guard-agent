# Nektar++ Checkpoint Strategy

## Reference Implementation
Native checkpoint/restart via `.fld` field files. Supports both XML (one file per rank) and HDF5 (single parallel file) formats.

## Checkpoint Library
Native (built into Nektar++). Optional HDF5 for parallel I/O.

## What Is Checkpointed
- All solution fields (velocity components, pressure, etc.)
- Spectral coefficients for each element
- Simulation time and step number

## Where Checkpoints Are Placed
At configurable intervals (`IO_CheckSteps` parameter in session file).

## Restart Logic
1. Rename `.fld` checkpoint to `.rst`
2. Provide `.rst` as initial condition in session XML
3. Use `--set-start-time` and `--set-start-chknumber` CLI flags
4. Solver resumes from restored field state

## Checkpoint Overhead
- HDF5 parallel: ~0.5-2 seconds for typical problems
- XML per-rank: faster write but many small files
