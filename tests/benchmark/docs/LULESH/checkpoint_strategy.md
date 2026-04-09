# LULESH Checkpoint Strategy

## Reference Implementation
The checkpointed version uses **lulesh-perm** (`luleshMPI-perm.cc`), which integrates with the **SCR (Scalable Checkpoint/Restart)** library via the PerMA (Persistent Memory Allocator) interface.

## Checkpoint Library
- **SCR** (Scalable Checkpoint/Restart) from LLNL
- Alternative: **VeloC** (compatible since SCR uses VeloC components internally)

## What Is Checkpointed
All nodal and element fields that change during the simulation:
- Node positions: `x`, `y`, `z`
- Node velocities: `xd`, `yd`, `zd`
- Element energy: `e`
- Element pressure: `p`
- Element viscosity: `q`, `ql`, `qq`
- Element volumes: `v`, `volo`
- Scalar state: `cycle`, `time`, `deltatime`

Total checkpoint size: ~3.4 MB per rank for a 30^3 problem

## Where Checkpoints Are Placed
At the **top of the main time step loop**, before force computation begins:

```
for (cycle = start_cycle; cycle < max_cycles; cycle++) {
    // ← CHECKPOINT HERE
    CalcForceForNodes();
    CalcAccelerationForNodes();
    ...
}
```

## Restart Logic
1. Check if a valid checkpoint exists (SCR_Have_restart)
2. If yes: read checkpoint data, restore all fields, set `cycle` to saved value
3. If no: start from initial conditions (cycle 0)
4. Resume time step loop from the restored cycle

## Checkpoint Overhead
- Per-step overhead: ~3.2% (from lulesh-perm measurements)
- Partial persistence: ~8.3 MB/node vs ~80 MB for full state dump
- Frequency: configurable, typically every N iterations

## Configuration
SCR configuration via environment variables:
```bash
export SCR_CHECKPOINT_SECONDS=60   # checkpoint interval
export SCR_CACHE_BASE=/tmp/scr     # node-local storage
```
