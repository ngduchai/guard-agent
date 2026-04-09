# AMReX Data Structures

## Key Structures
| Variable | Type | Description |
|----------|------|-------------|
| `MultiFab` | `amrex::MultiFab` | Collection of FABs (arrays) distributed across ranks |
| `BoxArray` | `amrex::BoxArray` | Description of grid boxes at one level |
| `DistributionMapping` | `amrex::DistributionMapping` | Box→rank assignment |
| `StateData` | `amrex::StateData` | Pair of MultiFabs (old + new time) |

## MPI Distribution
- Each AMR level has its own BoxArray + DistributionMapping
- Boxes distributed across ranks for load balance
- Variable number of boxes per level (changes with regridding)

## State Size Estimate
Variable - depends on number of AMR levels and refinement:
- Base grid 128^3, 2 levels, refinement ratio 2: ~128 MB total
- Checkpoint includes all levels + header metadata
