# SAMRAI Checkpoint Strategy

## Reference Implementation
Built-in `RestartManager` class with HDF5-based restart database. All SAMRAI objects implement `putToRestart()` / `getFromRestart()`.

## Checkpoint Library
Native HDF5 (built into SAMRAI).

## What Is Checkpointed
- Full patch hierarchy structure (levels, boxes, mappings)
- All patch data (cell/node/face/edge data)
- Application state registered with RestartManager
- Simulation time and step number

## Where Checkpoints Are Placed
Application controls frequency. Typically every N timesteps:
```cpp
RestartManager::getManager()->writeRestartFile(restart_dir, iteration);
```

## Restart Logic
1. `RestartManager::getManager()->openRestartFile(filename)`
2. Get root database: `getRootDatabase()`
3. Reconstruct all objects from restart database
4. Close restart file and resume

## Checkpoint Overhead
- HDF5 parallel I/O
- Size proportional to total patches across all levels
