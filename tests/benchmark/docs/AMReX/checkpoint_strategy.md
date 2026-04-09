# AMReX Checkpoint Strategy

## Reference Implementation
Comprehensive built-in checkpoint/restart. Checkpoint directories contain a Header file + per-level subdirectories with MultiFab binary data.

## Checkpoint Library
Native (built into AMReX). Parallel I/O via AMReX's own routines.

## What Is Checkpointed
- Header: finest level, simulation time, timestep, BoxArray per level
- MultiFab data at each level (all state variables)
- Particle data (if applicable, via ParticleContainer::Checkpoint)

## Where Checkpoints Are Placed
Controlled by `amr.check_int` (interval) or `amr.check_per` (wall-clock period).

## Restart Logic
1. Set `amr.restart = chkNNNNN` in inputs file
2. AMReX reads Header, reconstructs BoxArrays + DistributionMappings
3. Reads MultiFab data for each level
4. Resumes time stepping from saved time

## Checkpoint Overhead
- Parallel I/O: scales with number of ranks
- Size: proportional to total cells across all AMR levels
