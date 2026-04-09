# Nektar++ Data Structures

## Key Structures
| Variable | Type | Description |
|----------|------|-------------|
| `ExpList` | `Array<OneD, NekDouble>` | Spectral element expansion coefficients |
| `m_fields[i]` | `MultiRegions::ExpListSharedPtr` | Solution field (velocity, pressure) |
| `m_graph` | `SpatialDomains::MeshGraph` | Mesh topology |
| `m_session` | `LibUtilities::SessionReader` | Configuration parameters |

## MPI Distribution
- Elements distributed across ranks via graph partitioning
- Each rank owns local elements + ghost layer
- DOFs per element: (p+1)^d for polynomial order p in d dimensions
- Fixed mesh = fixed state size

## State Size Estimate
For 10K hex elements, order p=5, 3D incompressible NS (4 fields):
- DOFs per element: 216 (6^3)
- Per rank (2500 elements): 2500 * 216 * 4 * 8 bytes ≈ 17 MB
