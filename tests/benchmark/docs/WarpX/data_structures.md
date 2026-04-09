# WarpX Data Structures

## Key Arrays and Structures

| Variable Name | Type | Size | Description |
|---|---|---|---|
| `Efield_fp[3]` | `amrex::MultiFab` (array of 3) | `(nx+1) * ny * nz` per component per level (staggered Yee grid) | Fine-patch electric field components (Ex, Ey, Ez) on each AMR level |
| `Bfield_fp[3]` | `amrex::MultiFab` (array of 3) | `nx * (ny+1) * nz` per component per level (staggered Yee grid) | Fine-patch magnetic field components (Bx, By, Bz) on each AMR level |
| `current_fp[3]` | `amrex::MultiFab` (array of 3) | Same staggering as E fields per level | Fine-patch current density components (Jx, Jy, Jz) deposited from particles |
| `rho_fp` | `amrex::MultiFab` | `nx * ny * nz` per level (cell-centered) | Fine-patch charge density on each AMR level |
| `Efield_cp[3]` | `amrex::MultiFab` (array of 3) | Coarse-patch grid dimensions per level | Coarse-patch electric field for AMR interpolation at refinement boundaries |
| `Bfield_cp[3]` | `amrex::MultiFab` (array of 3) | Coarse-patch grid dimensions per level | Coarse-patch magnetic field for AMR interpolation at refinement boundaries |
| `F_fp` | `amrex::MultiFab` | `nx * ny * nz` per level | Divergence cleaning scalar field (for Boris/Marder correction) |
| `mypc` | `MultiParticleContainer` | N_species containers, each with N_particles | Container holding all particle species; each species is an `amrex::ParticleContainer` |
| `particle.x, y, z` | `amrex::Real` per particle | N_particles per species | Particle position coordinates |
| `particle.ux, uy, uz` | `amrex::Real` per particle | N_particles per species | Particle momentum (gamma * velocity) components |
| `particle.w` | `amrex::Real` per particle | N_particles per species | Particle weight (number of physical particles represented) |
| `particle.id, cpu` | `int` per particle | N_particles per species | Unique particle identifier and originating CPU for tracking |
| `pml_E[3]`, `pml_B[3]` | `amrex::MultiFab` (array of 3) | PML region cells per level | Split-field PML absorbing boundary layer fields |
| `costs` | `amrex::LayoutData<Real>` | One value per box per level | Load-balancing cost estimate per grid box |

## MPI Distribution

- **Field data**: Each AMR level's domain is divided into non-overlapping rectangular boxes. AMReX's `DistributionMapping` assigns boxes to MPI ranks using a space-filling curve (SFC) or knapsack algorithm for load balancing. Each rank stores only the MultiFab data for its assigned boxes, plus ghost cells (typically 1-4 cells wide) filled from neighbors.
- **Particle data**: Particles are distributed according to which box they reside in. Each rank owns the particles within its assigned boxes. During redistribution, particles that cross box boundaries are packed into messages and sent to the new owning rank. Particle data is stored in a Structure-of-Arrays (SoA) layout within each tile for cache efficiency.
- **AMR levels**: Each level has its own independent distribution mapping. Finer levels typically cover a smaller fraction of the domain but may have higher particle density.

## State Size Estimate

For a typical 3D production run with `256^3` cells on the base level and 2 AMR levels (refinement ratio 2):

- **Level 0 fields**: 6 field components (E + B) x `256^3` x 8 bytes = ~6.4 GB
- **Level 1 fields**: 6 components x `512^3` coverage (partial, ~25% fill) x 8 bytes = ~12.8 GB (if 25% filled)
- **Current + charge**: ~3.2 GB per level
- **PML fields**: ~10-20% overhead on field storage
- **Particles**: For 10^9 particles with 7 reals + 2 ints per particle = ~64 GB
- **Total typical state**: 50-150 GB depending on problem size, number of particles, and AMR coverage

Per-rank memory for a 1000-rank run: approximately 50-150 MB of field data plus particle data (highly variable depending on particle load balance).
