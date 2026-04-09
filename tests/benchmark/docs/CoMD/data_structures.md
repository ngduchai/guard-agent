# CoMD Data Structures

## Key Structures (Checkpoint State)

### SimFlat (main simulation state)
```c
typedef struct SimFlatSt {
    int nSteps;              // total timesteps
    int printRate;           // output frequency
    double dt;               // timestep size
    int step;                // current step ← CHECKPOINT
    double ePotential;       // potential energy
    double eKinetic;         // kinetic energy
    Domain* domain;          // spatial decomposition info
    LinkCell* boxes;         // link cell data structure
    Atoms* atoms;            // atom positions, velocities, forces
    BasePotential* pot;      // force model (LJ or EAM)
    HaloExchange* atomExchange;  // MPI halo exchange
} SimFlat;
```

### Atoms (per-atom arrays, FIXED size = maxTotalAtoms)
| Variable | Type | Size | Description |
|----------|------|------|-------------|
| `gid` | `int*` | maxTotalAtoms | Global atom ID |
| `iSpecies` | `int*` | maxTotalAtoms | Species index |
| `r` | `real3*` | maxTotalAtoms | Positions (x,y,z) ← CHECKPOINT |
| `p` | `real3*` | maxTotalAtoms | Momenta (px,py,pz) ← CHECKPOINT |
| `f` | `real3*` | maxTotalAtoms | Forces (fx,fy,fz) |
| `U` | `real_t*` | maxTotalAtoms | Potential energy per atom |
| `nLocal` | `int` | 1 | Number of local atoms ← CHECKPOINT |
| `nGlobal` | `int` | 1 | Total atoms in simulation |

### LinkCell (spatial hashing)
| Variable | Type | Description |
|----------|------|-------------|
| `nLocalBoxes` | `int` | Number of local link cells |
| `nHaloBoxes` | `int` | Number of halo cells |
| `nAtoms` | `int*` | Atom count per box |

## MPI Distribution
- 3D spatial decomposition: each rank owns a rectangular subdomain
- Atoms are assigned to ranks based on position
- Fixed total atom count (atoms do NOT migrate in standard LJ mode)
- Halo: 1 cell layer deep in each direction

## State Size Estimate
For a 10x10x10 domain with 4 atoms/cell:
- Atoms per rank: ~4,000
- Checkpoint: positions (3 doubles) + momenta (3 doubles) + gid + species = ~200 KB per rank
