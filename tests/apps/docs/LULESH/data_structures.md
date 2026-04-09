# LULESH Data Structures

## Key Arrays (Checkpoint State)

All arrays below are **fixed-size** throughout the simulation. Sizes are determined at initialization and never change.

### Nodal Fields (per-node arrays, size = `numNode`)
| Variable | Type | Description |
|----------|------|-------------|
| `m_x`, `m_y`, `m_z` | `Real_t*` (double) | Node coordinates |
| `m_xd`, `m_yd`, `m_zd` | `Real_t*` (double) | Node velocities |
| `m_xdd`, `m_ydd`, `m_zdd` | `Real_t*` (double) | Node accelerations |
| `m_fx`, `m_fy`, `m_fz` | `Real_t*` (double) | Node forces |
| `m_nodalMass` | `Real_t*` (double) | Nodal mass |

### Element Fields (per-element arrays, size = `numElem`)
| Variable | Type | Description |
|----------|------|-------------|
| `m_e` | `Real_t*` (double) | Energy |
| `m_p` | `Real_t*` (double) | Pressure |
| `m_q` | `Real_t*` (double) | Artificial viscosity |
| `m_ql`, `m_qq` | `Real_t*` (double) | Linear/quadratic viscosity terms |
| `m_v` | `Real_t*` (double) | Relative volume |
| `m_volo` | `Real_t*` (double) | Reference volume |
| `m_delv` | `Real_t*` (double) | Volume derivative |
| `m_vdov` | `Real_t*` (double) | Volume derivative over volume |
| `m_ss` | `Real_t*` (double) | Sound speed |
| `m_elemMass` | `Real_t*` (double) | Element mass |

### Scalar State
| Variable | Type | Description |
|----------|------|-------------|
| `m_dtcourant` | `Real_t` | Courant time step constraint |
| `m_dthydro` | `Real_t` | Hydro time step constraint |
| `m_cycle` | `Int_t` | Current iteration number |
| `m_time` | `Real_t` | Current simulation time |
| `m_deltatime` | `Real_t` | Current time step size |

## MPI Distribution
- Mesh decomposed into `cbrt(numRanks)` x `cbrt(numRanks)` x `cbrt(numRanks)` blocks
- Each rank has `numElem = sizeX^3` elements and `numNode = (sizeX+1)^3` nodes
- Ghost nodes at subdomain boundaries (1 layer deep)

## State Size Estimate
For `-s 30` (30^3 elements per rank):
- Elements: 27,000
- Nodes: 31^3 = 29,791
- Approximate checkpoint: ~14 arrays x 30,000 x 8 bytes ≈ 3.4 MB per rank
