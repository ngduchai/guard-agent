# Nyx Data Structures

## Key Arrays and Structures

| Variable Name | Type | Size | Description |
|---|---|---|---|
| `S_old`, `S_new` | `amrex::MultiFab` | `(nx * ny * nz) * ncomp` per level; ncomp = 6 (density, 3 momenta, energy, electron fraction) | Conserved gas state at old and new time levels |
| `D_old`, `D_new` | `amrex::MultiFab` | `(nx * ny * nz) * ncomp_diag` per level | Diagnostic/derived hydrodynamic quantities |
| `phi_old`, `phi_new` | `amrex::MultiFab` | `nx * ny * nz` per level (cell-centered) | Gravitational potential at old and new time levels |
| `gravity.grad_phi` | `amrex::MultiFab[3]` | Face-centered, one component per direction per level | Gravitational acceleration components (-grad phi) |
| `DarkMatterPC` | `amrex::ParticleContainer` | N_particles, each with 3 reals (pos) + 3 reals (vel) + mass + id + cpu | Dark matter N-body particle container |
| `particle.pos[3]` | `amrex::Real` per particle | N_particles | Dark matter particle positions (comoving coordinates) |
| `particle.vel[3]` | `amrex::Real` per particle | N_particles | Dark matter particle velocities (peculiar velocity) |
| `particle.mass` | `amrex::Real` per particle | N_particles | Dark matter particle mass |
| `a_old`, `a_new` | `amrex::Real` (scalar) | 1 | Cosmological scale factor at old and new times |
| `e_src` | `amrex::MultiFab` | `nx * ny * nz` per level | Energy source term from heating/cooling |
| `volume`, `area[3]` | `amrex::MultiFab` | Grid-sized per level | Cell volumes and face areas (may vary in non-Cartesian geometry) |
| `fluxes[3]` | `amrex::MultiFab` (array of 3) | Face-centered per level | Hydrodynamic fluxes at cell interfaces in each direction |
| `fine_mask` | `amrex::iMultiFab` | `nx * ny * nz` per level | Integer mask indicating cells covered by finer AMR levels |

## MPI Distribution

- **Gas field data**: Distributed identically to WarpX and other AMReX codes -- each AMR level's box array is mapped to MPI ranks via a `DistributionMapping`. Each rank holds MultiFab data for its assigned boxes plus ghost cells (4 cells for PPM hydro, 1 cell for gravity).
- **Dark matter particles**: Stored in the `ParticleContainer` with particles assigned to ranks based on their spatial position (which box they reside in). Redistribution occurs after particle push steps. Particle mass deposition uses cloud-in-cell (CIC) interpolation, requiring ghost cell overlap and `SumBoundary` to accumulate mass deposited in neighboring boxes.
- **Gravity data**: The gravitational potential and acceleration are stored as MultiFabs with the same distribution as the gas state. The multigrid solver operates on the same decomposition.

## State Size Estimate

For a typical cosmological simulation with `512^3` base grid, 2 AMR levels (refinement ratio 2), and 512^3 dark matter particles:

- **Gas state (S_old + S_new)**: 2 x 6 components x `512^3` x 8 bytes = ~12.9 GB (level 0 only)
- **Gravity (phi + grad_phi)**: 4 fields x `512^3` x 8 bytes = ~4.3 GB per level
- **Level 1 gas + gravity** (25% fill): ~4.3 GB
- **Level 2 gas + gravity** (5% fill): ~3.4 GB
- **Dark matter particles**: `512^3` particles x (6 reals + 1 mass + 2 ints) x 8 bytes = ~8.6 GB
- **Flux/scratch arrays**: ~6 GB across levels
- **Total typical state**: 30-50 GB

Per-rank for 512 ranks: approximately 60-100 MB of field data plus ~17 MB of particle data.
