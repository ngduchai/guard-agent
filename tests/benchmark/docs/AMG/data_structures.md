# AMG Data Structures

## Key Arrays (Checkpoint State)

Array sizes are fixed after the multigrid hierarchy is built. The hierarchy consists of multiple grid levels, each with its own sparse matrix and vectors.

### Per-Level Sparse Matrix (CSR format, at each multigrid level)
| Variable | Type | Size | Description |
|----------|------|------|-------------|
| `A->i` | `int*` | `nrows+1` | CSR row pointers |
| `A->j` | `int*` | `nnz` | CSR column indices |
| `A->data` | `double*` | `nnz` | CSR non-zero values |

### Per-Level Vectors (size = `nrows` at each level)
| Variable | Type | Description |
|----------|------|-------------|
| `x` | `double*` | Solution vector |
| `b` | `double*` | Right-hand side vector |
| `r` | `double*` | Residual vector |
| `p` | `double*` | PCG search direction |
| `s` | `double*` | Preconditioned residual |
| `tmp` | `double*` | Temporary workspace |

### Interpolation Operators (per level transition)
| Variable | Type | Size | Description |
|----------|------|------|-------------|
| `P->i` | `int*` | `fine_rows+1` | Interpolation row pointers |
| `P->j` | `int*` | `P_nnz` | Interpolation column indices |
| `P->data` | `double*` | `P_nnz` | Interpolation weights |

### Scalar State
| Variable | Type | Description |
|----------|------|-------------|
| `num_iterations` | `int` | Current PCG iteration count |
| `rel_residual_norm` | `double` | Current relative residual |
| `num_levels` | `int` | Number of multigrid levels |

## MPI Distribution
- 3D block decomposition: `px * py * pz` processor grid
- Each rank owns a `nx * ny * nz` block of the structured grid on the finest level
- Coarser levels have progressively fewer points per rank
- Ghost layers exchanged at each level for stencil operations

## State Size Estimate
For a problem with nx=ny=nz=40 per rank, 8 ranks:
- Fine grid points per rank: 64,000
- Fine grid non-zeros per rank: ~448,000 (7-point stencil)
- Vectors (fine level): 6 vectors x 64,000 x 8 bytes = 3.1 MB
- All levels combined (vectors + matrices): ~10-15 MB per rank
- Approximate checkpoint (solver vectors only): ~3.1 MB per rank
