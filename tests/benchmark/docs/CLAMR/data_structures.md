# CLAMR Data Structures

## Key Arrays (Checkpoint State)

Array sizes **change dynamically** as the mesh adapts (refines/coarsens). The number of cells per rank varies over time due to AMR and load balancing.

### Cell State Arrays (per cell, size = `ncells` — dynamic)
| Variable | Type | Size | Description |
|----------|------|------|-------------|
| `H` | `double*` | `ncells` | Water height |
| `U` | `double*` | `ncells` | X-velocity (momentum/height) |
| `V` | `double*` | `ncells` | Y-velocity (momentum/height) |

### Mesh Structure (per cell, size = `ncells` — dynamic)
| Variable | Type | Size | Description |
|----------|------|------|-------------|
| `i` | `int*` | `ncells` | Cell x-index in logical grid |
| `j` | `int*` | `ncells` | Cell y-index in logical grid |
| `level` | `int*` | `ncells` | AMR refinement level of cell |
| `celltype` | `int*` | `ncells` | Cell type (real, ghost, boundary) |
| `nlft`, `nrht`, `nbot`, `ntop` | `int*` | `ncells` | Neighbor indices (left, right, bottom, top) |

### Scalar State
| Variable | Type | Description |
|----------|------|-------------|
| `ncycle` | `int` | Current time step number |
| `simTime` | `double` | Current simulation time |
| `deltaT` | `double` | Current time step size |
| `ncells` | `int` | Current number of cells on this rank |
| `levmx` | `int` | Maximum refinement level |

## MPI Distribution
- Cells distributed across ranks using space-filling curve (Hilbert curve) ordering
- Dynamic load balancing redistributes cells periodically
- Ghost cells maintained for neighbor stencil operations across rank boundaries
- Cell count per rank fluctuates due to AMR refinement/coarsening and load rebalancing

## State Size Estimate
For a mesh with ~1M total cells on 8 ranks:
- Cells per rank: ~125,000
- State arrays: 3 arrays x 125,000 x 8 bytes = 3.0 MB
- Mesh structure: 8 arrays x 125,000 x 4 bytes = 4.0 MB
- Approximate checkpoint: ~7 MB per rank
