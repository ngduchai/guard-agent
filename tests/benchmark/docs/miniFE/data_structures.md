# miniFE Data Structures

## Key Arrays (Checkpoint State)

All arrays below are **fixed-size** after mesh generation and assembly. Sizes are determined at initialization and never change.

### Sparse Matrix (CSR format)
| Variable | Type | Size | Description |
|----------|------|------|-------------|
| `A.rows` | `int*` | `nrows+1` | CSR row pointers |
| `A.packed_cols` | `int*` | `nnz` | CSR column indices |
| `A.packed_coefs` | `double*` | `nnz` | CSR non-zero values |

### Vectors (per local-row arrays, size = `nrows`)
| Variable | Type | Description |
|----------|------|-------------|
| `x` | `double*` | Solution vector |
| `b` | `double*` | Right-hand side vector |
| `r` | `double*` | Residual vector |
| `p` | `double*` | Search direction vector |
| `Ap` | `double*` | Matrix-vector product result |

### Scalar State
| Variable | Type | Description |
|----------|------|-------------|
| `num_iterations` | `int` | Current CG iteration count |
| `rtrans` | `double` | Current r^T*r dot product |
| `oldrtrans` | `double` | Previous r^T*r dot product |
| `tolerance` | `double` | Convergence tolerance |

## MPI Distribution
- Mesh nodes distributed in 1D contiguous blocks across ranks
- Each rank owns `nrows = total_nodes / numRanks` rows (approximately)
- Halo nodes stored in a separate receive buffer; send/receive lists computed from the matrix sparsity pattern

## State Size Estimate
For a 100x100x100 mesh on 8 ranks:
- Nodes per rank: ~125,000
- Non-zeros per rank: ~3.4M (27-point stencil)
- Vectors: 5 vectors x 125,000 x 8 bytes = 5 MB
- Sparse matrix coefficients: 3.4M x 8 bytes = 27.2 MB
- Approximate checkpoint (vectors only): ~5 MB per rank
- Approximate checkpoint (full state): ~32 MB per rank
