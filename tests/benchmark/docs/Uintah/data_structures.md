# Uintah Data Structures

## Key Structures
| Variable | Type | Description |
|----------|------|-------------|
| `DataWarehouse` | `DataWarehouse*` | Stores all simulation variables |
| `Grid` | `Grid*` | AMR patch hierarchy |
| `Patch` | `Patch*` | Single structured grid patch |
| `CCVariable<double>` | template | Cell-centered variable on a patch |
| `NCVariable<double>` | template | Node-centered variable on a patch |
| `TaskGraph` | DAG | Directed acyclic graph of computation tasks |

## MPI Distribution
- Patches distributed across ranks via load balancer
- Each task operates on one patch
- DataWarehouse manages data locality

## State Size Estimate
Problem-dependent. Typical MPM simulation:
- 1M particles: ~200 MB total state
- Checkpoint: all DataWarehouse variables for all patches
