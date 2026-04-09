# CoMD Checkpoint Strategy

## Reference Implementation
The checkpointed version uses **comd-ft** (https://github.com/shashankgugnani/comd-ft), which adds POSIX-based checkpoint/restart to CoMD.

## Checkpoint Library
- **POSIX file I/O** (direct binary write/read)
- No external checkpoint library dependency

## What Is Checkpointed
Essential simulation state for restart:
- Current timestep (`step`)
- Atom positions (`r[nLocal]`)
- Atom momenta (`p[nLocal]`)
- Atom global IDs (`gid[nLocal]`)
- Atom species (`iSpecies[nLocal]`)
- Number of local atoms (`nLocal`)
- Simulation time
- Link cell assignment

## Where Checkpoints Are Placed
At the **top of the main time step loop**, before velocity advance:

```c
for (step = startStep; step < nSteps; step++) {
    // ← CHECKPOINT HERE (write state to file)
    advanceVelocity(sim, dt/2);
    advancePosition(sim, dt);
    redistributeAtoms(sim);
    computeForce(sim);
    advanceVelocity(sim, dt/2);
}
```

## Restart Logic
1. On startup, check if checkpoint file exists
2. If yes: read binary checkpoint, restore atoms and step counter
3. Skip to the saved step in the time loop
4. Continue computation from checkpoint

## Checkpoint Format
Binary file containing:
```
[int: step] [int: nLocal]
[double[3]*nLocal: positions]
[double[3]*nLocal: momenta]
[int*nLocal: gids]
[int*nLocal: species]
```

## Checkpoint Overhead
- Very low (~1-2% per step) since state is small
- Configurable frequency via command-line parameter
