# SU2 Data Structures

## Key Structures
| Variable | Type | Description |
|----------|------|-------------|
| `Solution` | `su2double**` | Conservative variables at each node |
| `Solution_Old` | `su2double**` | Previous iteration solution |
| `Residual` | `su2double*` | Residual vector |
| `Jacobian` | `CSysMatrix` | Implicit system matrix (sparse) |
| `geometry` | `CGeometry*` | Mesh (nodes, elements, edges) |

## MPI Distribution
- Mesh partitioned by METIS at startup
- Each rank owns a subset of nodes/elements
- Halo nodes for partition boundary communication
- Fixed partition throughout solve

## State Size Estimate
For 1M node mesh, 4 conservative variables (2D compressible):
- Solution: 1M * 4 * 8 = 32 MB per rank (before partitioning)
- Restart file: ~32 MB total
