# deal.II Data Structures

## Key Structures
| Variable | Type | Description |
|----------|------|-------------|
| `triangulation` | `parallel::distributed::Triangulation<dim>` | Distributed mesh |
| `dof_handler` | `DoFHandler<dim>` | DOF distribution |
| `system_matrix` | `PETScWrappers::MPI::SparseMatrix` | Global stiffness matrix |
| `solution` | `PETScWrappers::MPI::Vector` | Solution vector |
| `system_rhs` | `PETScWrappers::MPI::Vector` | Right-hand side |

## MPI Distribution
- Mesh cells distributed via p4est space-filling curve
- Each rank owns a subset of cells; ghost layer for neighbor access
- Vectors/matrices distributed by DOF ownership

## State Size Estimate
Variable - depends on refinement level. Typical 3D problem:
- 1M cells: ~10 MB mesh data, ~100 MB matrix per rank
- Checkpoint: mesh + solution vector (~50 MB per rank)
