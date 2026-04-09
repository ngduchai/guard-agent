# SAMRAI Data Structures

## Key Structures
| Variable | Type | Description |
|----------|------|-------------|
| `PatchHierarchy` | `SAMRAI::hier::PatchHierarchy` | Multi-level AMR hierarchy |
| `PatchLevel` | `SAMRAI::hier::PatchLevel` | Collection of patches at one level |
| `Patch` | `SAMRAI::hier::Patch` | Single rectangular grid patch |
| `PatchData` | `SAMRAI::pdat::CellData<double>` | Cell-centered data on a patch |
| `RestartManager` | `SAMRAI::tbox::RestartManager` | Checkpoint orchestrator |

## MPI Distribution
- Patches distributed across MPI ranks
- Each level independently load-balanced
- Patch sizes configurable (min/max box size)

## State Size Estimate
Problem-dependent. For a 2-level hierarchy with 256^3 base grid:
- ~1000 patches total
- ~500 MB aggregate data
- Checkpoint: full hierarchy + all patch data
