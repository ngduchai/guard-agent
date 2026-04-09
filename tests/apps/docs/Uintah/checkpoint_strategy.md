# Uintah Checkpoint Strategy

## Reference Implementation
Built-in `DataArchiver` class writes checkpoint data. Also supports LENO (Limited Essentially Non-Oscillatory) fault recovery that reconstructs lost data WITHOUT checkpointing using AMR interpolation.

## Checkpoint Library
Native (DataArchiver). Alternative: LENO for checkpoint-free recovery.

## What Is Checkpointed
- All variables in the DataWarehouse
- Grid structure (all levels, patches)
- Simulation time, timestep, global state

## Where Checkpoints Are Placed
Controlled by `<checkpoint>` element in the `.ups` input file:
```xml
<checkpoint cycle="2" timestepInterval="100"/>
```

## Restart Logic
1. Specify `-restart` flag with UDA directory path
2. DataArchiver reads checkpoint, populates DataWarehouse
3. Grid reconstructed from saved state
4. Tasks resume from restored timestep

## LENO Recovery (checkpoint-free)
- Uses AMR coarse-grid data to reconstruct lost fine-grid data
- Up to 10x faster than traditional checkpoint recovery
- Requires sufficient AMR hierarchy for interpolation

## Checkpoint Overhead
- Traditional: proportional to DataWarehouse size
- LENO: zero checkpoint cost, recovery cost only on failure
