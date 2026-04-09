# Palabos Data Structures

## Key Structures
| Variable | Type | Description |
|----------|------|-------------|
| `BlockLattice3D` | Template class | 3D lattice of cells |
| `Cell::f[q]` | `T[q]` (double array) | Population distributions (q=19 for D3Q19) |
| `Cell::external` | `T*` | External scalar fields |
| Macroscopic fields | `double` | Density, velocity (derived from f) |

## MPI Distribution
- Lattice decomposed into rectangular blocks
- Each rank owns a contiguous sub-lattice
- 1-cell ghost layer for streaming step
- Fixed size throughout simulation

## State Size Estimate
For 128^3 lattice with D3Q19 on 4 ranks:
- Cells per rank: ~524K
- State per cell: 19 doubles = 152 bytes
- Per rank: ~76 MB
