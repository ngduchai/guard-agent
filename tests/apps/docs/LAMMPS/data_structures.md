# LAMMPS Data Structures

## Key Structures
| Variable | Type | Size | Description |
|----------|------|------|-------------|
| `atom->x` | `double**` | nlocal x 3 | Atom positions |
| `atom->v` | `double**` | nlocal x 3 | Atom velocities |
| `atom->f` | `double**` | nlocal x 3 | Atom forces |
| `atom->tag` | `tagint*` | nlocal | Global atom IDs |
| `atom->type` | `int*` | nlocal | Atom types |
| `atom->nlocal` | `int` | 1 | Number of local atoms (VARIABLE) |
| `atom->nghost` | `int` | 1 | Number of ghost atoms |
| `domain->boxlo/hi` | `double[3]` | 6 | Simulation box bounds |
| `update->ntimestep` | `bigint` | 1 | Current timestep |

## MPI Distribution
- 3D spatial decomposition (regular grid of subdomains)
- Atoms assigned to rank owning their position
- nlocal varies as atoms migrate between ranks
- Ghost atoms: copies of neighbor atoms within cutoff

## State Size Estimate
For 100K atoms on 4 ranks (~25K atoms/rank):
- Positions + velocities: 25K * 6 * 8 = 1.2 MB per rank
- Full restart: ~5 MB per rank (includes topology, box, etc.)
