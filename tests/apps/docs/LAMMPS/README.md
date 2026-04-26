# LAMMPS — Large-scale Atomic/Molecular Massively Parallel Simulator

**Class:** (2) iterative_variable  
**Language:** C++ (MPI)  
**Checkpoint library:** Native restart files

## Application Description

LAMMPS is a classical molecular dynamics engine that integrates Newton's equations of motion for atoms interacting through empirical potentials. The benchmark configuration runs a **3D Lennard-Jones melt**: ~32,000 atoms on an FCC lattice at reduced density 0.8442, simulated in LJ units under the NVE microcanonical ensemble using the velocity Verlet integrator with a cutoff-based LJ pair potential (rc = 2.5sigma). The run is distributed across 4 MPI ranks using 3D spatial domain decomposition.

## Computation Workflow

```mermaid
flowchart TD
    subgraph INIT["Initialization"]
        A1["MPI Init + Parse Input Script"] --> A2["Domain Decomposition\n<i>box → 3D subdomains per rank</i>"]
        A2 --> A3["Create Atoms on FCC Lattice\n<i>positions r[i] assigned to ranks</i>"]
        A3 --> A4["Assign Velocities\n<i>Gaussian dist (seed 87287) → v[i]</i>"]
        A4 --> A5["Build Neighbor Lists + Force Compute\n<i>r[i] → f[i], U[i]</i>"]
    end

    subgraph LOOP["Main Loop — Velocity Verlet (2,000 timesteps)"]
        direction TB
        B0{{"step % 100 == 0?"}} -->|Yes| CKPT["⤢ CHECKPOINT (VARIABLE)\n<i>save r, v, tag, type,\nntimestep, box, FF params (size changes:\natoms migrate between ranks → nlocal changes per step)</i>"]
        CKPT --> B1
        B0 -->|No| B1

        B1["Velocity Half-Step\n<i>v += 0.5 × dt × f/m</i>"]
        B1 --> B2["Position Update\n<i>r += dt × v</i>"]
        B2 --> B3["Atom Exchange\n<i>MPI_Sendrecv (6 faces)</i>\n<i>atoms crossing boundaries migrate</i>"]
        B3 --> B4["Neighbor List Rebuild\n<i>(every 20 steps) bin-sort within cutoff+skin</i>"]
        B4 --> B5["Force Computation\n<i>r[i] → f[i] (LJ pair potential)</i>\n<i>ghost forces via MPI_Sendrecv</i>"]
        B5 --> B6["Velocity Half-Step\n<i>v += 0.5 × dt × f/m</i>"]
        B6 --> B7["Thermo Reduction\n<i>MPI_Allreduce: KE, PE → T, P</i>"]
        B7 --> B0
    end

    subgraph OUT["Output"]
        C1["Performance Summary"]
        C1 --> C2["Print TotEng at step 2000"]
    end

    INIT --> LOOP --> OUT

    style CKPT fill:#f96,stroke:#d33,color:#000,stroke-width:3px,stroke-dasharray: 5 5
    style B3 fill:#fcc,stroke:#d33,color:#000
    style B1 fill:#bde,stroke:#333,color:#000
    style B2 fill:#bde,stroke:#333,color:#000
    style B5 fill:#bde,stroke:#333,color:#000
    style B6 fill:#bde,stroke:#333,color:#000
    style B7 fill:#deb,stroke:#333,color:#000
```

**Data flow per step:** `r,v` →(half-step)→ `v'` →(position)→ `r'` →(exchange)→ `r'` migrated →(neighbors)→ pairs →(force)→ `f'` →(half-step)→ `v''` →(reduce)→ `TotEng`

### Start

1. **MPI initialization** and input script parsing.
2. **Domain partitioning** — 3D grid of subdomains, one per rank.
3. **Atom creation** — atoms placed on FCC lattice and assigned to owning rank by position.
4. **Velocity assignment** — Gaussian distribution with fixed seed (87287) for reproducibility.
5. **Initial neighbor list build** and force computation.

### Main Loop (2,000 timesteps, velocity Verlet)

Each timestep:

1. **Velocity half-step** — `v += 0.5 * dt * f/m` for all local atoms.
2. **Position update** — `r += dt * v` for all local atoms.
3. **Atom exchange** — atoms that crossed subdomain boundaries sent to new owning rank via `MPI_Sendrecv` in all 6 face directions. `nlocal` changes dynamically.
4. **Neighbor list rebuild** — every 20 steps, bin-sorted neighbor list rebuilt from local + ghost atoms within cutoff + skin (2.5 + 0.3 = 2.8sigma).
5. **Force computation** — LJ pair forces for all neighbor pairs. Ghost atom forces accumulated via `MPI_Sendrecv`.
6. **Velocity half-step** — second `v += 0.5 * dt * f/m` completing the Verlet step.
7. **Thermodynamics** — kinetic/potential energy reduced via `MPI_Allreduce`. Temperature, pressure logged.

### End

- Performance summary and loop timing printed.
- `MPI_Finalize`.
- **Validation output:** the `TotEng` value at step 2000.

## Critical State

The state is rank-local and asymmetric — each MPI rank owns a disjoint subset of atoms by spatial position. Ghost atoms are reconstructed each step and are not persistent state.

| Field | Type | Evolution |
|-------|------|-----------|
| `x[i][3]` | Atom position (3 doubles) | Updated every step; atoms migrate between ranks as they cross boundaries |
| `v[i][3]` | Atom velocity (3 doubles) | Updated twice per step via half-step Verlet |
| `tag[i]` | Global atom ID | Static — tracks atoms across rank migration |
| `type[i]` | Atom species | Static (single species for LJ melt) |
| `nlocal` | Local atom count | Variable — changes every step as atoms move |
| `ntimestep` | Current step counter | Monotonically incremented |
| Box bounds | `boxlo/hi` | Fixed for NVE at constant volume |

**Derived:** Forces `f[i]` are recomputed from scratch each step and are not independent state.

**Variable state:** The atom count per rank (`nlocal`) changes every timestep as atoms cross subdomain boundaries, making this a variable-size checkpoint problem.

## MPI Task Lifetime

**Per-rank state:** Each rank owns a spatial subdomain of the 3D simulation box and holds the atoms within it (positions `x`, velocities `v`, global IDs `tag`, types). Ghost atoms from neighboring subdomains are reconstructed each step and are transient.

**How state changes:** The local atom count (`nlocal`) changes every timestep as atoms cross subdomain boundaries. This makes per-rank state variable-sized, though the global atom count is conserved.

**Communication pattern:** Each step performs a 6-face `MPI_Sendrecv` exchange to migrate atoms that crossed boundaries, a neighbor-ghost exchange for force computation, and a global `MPI_Allreduce` for thermodynamic quantities.

```mermaid
sequenceDiagram
    participant R0 as Rank 0
    participant R1 as Rank 1
    participant RN as Rank N

    Note right of RN: Velocity half-step + position update
    R0->>R1: MPI_Sendrecv (atom migration, 6 faces)
    R1->>R0: MPI_Sendrecv (atom migration, 6 faces)
    R0->>R1: MPI_Sendrecv (ghost atoms for forces)
    R1->>R0: MPI_Sendrecv (ghost atoms for forces)
    Note right of RN: Forces (LJ) → velocity half-step
    R0-->>RN: MPI_Allreduce (KE, PE -> T, P)
    Note right of RN: Step complete
```

### Application Lifetime View

```mermaid
sequenceDiagram
    participant R0 as Rank 0
    participant R1 as Rank 1
    participant R2 as Rank 2
    participant R3 as Rank 3

    Note right of R3: INIT: FCC, ~8000 atoms/rank (VARIABLE)
    R0->>R1: MPI_Sendrecv (initial ghost atoms)
    R1->>R0: MPI_Sendrecv (initial ghost atoms)
    R0->>R1: MPI_Sendrecv (atom migration, 6 faces)
    R1->>R0: MPI_Sendrecv (atom migration, 6 faces)
    R0->>R1: MPI_Sendrecv (ghost atoms for forces)
    R1->>R0: MPI_Sendrecv (ghost atoms for forces)
    Note right of R3: LOOP | Verlet → forces → half-step
    R0-->>R3: MPI_Allreduce (KE, PE → T, P)

    R0->>R0: CKPT every 100 → restart.lj.N

    R0->>R1: MPI_Sendrecv (atom migration)
    R1->>R0: MPI_Sendrecv (atom migration)
    Note right of R3: LOOP continues (same pattern)
    R0-->>R3: MPI_Allreduce (KE, PE → T, P)

    Note right of R3: FINALIZE: TotEng, MPI_Finalize
```

**Key observations:**
- **State size behavior:** Each rank's atom count (`nlocal`) fluctuates every timestep as atoms cross subdomain boundaries. Global atom count (~32,000) is conserved, but per-rank state is variable-sized, making checkpoint size unpredictable per rank.
- **Communication pattern:** Nearest-neighbor `MPI_Sendrecv` in 6 face directions for atom migration and ghost exchange (point-to-point), plus a global `MPI_Allreduce` for thermodynamic reductions each step.
- **Checkpoint coordination:** All ranks contribute local atom data to a single merged binary restart file. No explicit barrier — LAMMPS serializes rank contributions internally. On restart, atoms are re-partitioned to match the current MPI decomposition.

## Checkpoint Protection

### Write trigger

The input script `in.lj_ckpt` adds:
```
restart 100 restart.lj
```
This writes a binary restart file every 100 steps. LAMMPS uses two-file rotation — alternating between `restart.lj.100`, `restart.lj.200`, etc. — so at least one complete checkpoint is always available.

### What is saved

A complete snapshot in LAMMPS binary format:
- All atom positions, velocities, global IDs, types
- Force field parameters (epsilon, sigma, cutoff)
- Simulation box geometry
- Current timestep counter
- All simulation settings (fix styles, neighbor list parameters)

Each rank contributes its local atom data; the file is a globally consistent merged dump.

### Restart protocol (`run_with_restart.sh`)

1. Find the most recent `restart.lj.*` file via `ls -t`.
2. If found, generate an on-the-fly input script calling `read_restart` on that file.
3. Re-specify force field coefficients (not stored in restart file).
4. Issue `run 2000 upto` — the `upto` keyword runs until step 2000 total, not 2000 additional steps.
5. If no checkpoint exists, fall back to fresh run from `in.lj_ckpt`.

### Restart mechanics

On `read_restart`, LAMMPS reconstructs the full atom state, re-partitions atoms to match the current MPI decomposition (may differ from checkpoint time), rebuilds neighbor lists, and resumes from the saved `ntimestep`.

### Output comparison

Both vanilla and checkpointed runs must reach step 2000 with matching `TotEng`. The `keep_patterns: ["      2000"]` filter isolates the step-2000 thermodynamic row, making comparison insensitive to timing and layout differences.
