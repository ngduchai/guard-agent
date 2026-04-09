# Chameleon Data Structures

## Key Structures
| Variable | Type | Description |
|----------|------|-------------|
| `descA` | `CHAM_desc_t*` | Tile matrix descriptor |
| `descA->mat` | `void*` | Local tile storage |
| `descA->mb/nb` | `int` | Tile dimensions |
| `descA->mt/nt` | `int` | Number of tile rows/columns |

## MPI Distribution
- 2D block-cyclic over P x Q process grid
- Each tile is NB x NB doubles
- Fixed tile sizes throughout computation

## State Size Estimate
For N=5000, NB=200, 4 ranks: ~50 MB per rank
