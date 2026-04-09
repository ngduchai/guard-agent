# LAMMPS Computation Flow

## Overview
LAMMPS performs molecular dynamics with spatial domain decomposition. Each timestep computes forces, integrates equations of motion, and exchanges atoms that migrate across subdomain boundaries.

## Main Loop
```mermaid
flowchart TD
    A[MPI_Init + Read input script] --> B[Create atoms + setup]
    B --> C[Time step loop]
    C --> D["Initial integrate (velocity Verlet half-step)"]
    D --> E[Exchange atoms across boundaries]
    E --> E1[MPI_Sendrecv for migrating atoms]
    E --> F[Build neighbor lists]
    F --> G[Compute forces]
    G --> G1[Pair forces + long-range]
    G1 --> G2[MPI for ghost atom forces]
    G --> H["Final integrate (velocity Verlet half-step)"]
    H --> I[Compute thermodynamics]
    I --> I1[MPI_Allreduce for global energy/temp]
    I --> J{Write restart?}
    J -->|Yes| K[write_restart]
    J -->|No| L{More steps?}
    L -->|Yes| C
    L -->|No| M[Output + MPI_Finalize]
```

## MPI Communication
- **Atom exchange**: `MPI_Sendrecv` for atoms crossing subdomain boundaries (6 directions)
- **Ghost communication**: `MPI_Sendrecv` for ghost atom positions/forces
- **Collective**: `MPI_Allreduce` for global thermodynamic quantities
- **Decomposition**: 3D regular spatial decomposition

## I/O Points
- Restart files: binary dump of full simulation state
- Dump files: atom positions for visualization
- Log: thermodynamic output every N steps
