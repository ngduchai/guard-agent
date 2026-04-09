# DPLASMA Data Structures

## Key Structures

| Variable | Type | Description |
|----------|------|-------------|
| `dcA` | `parsec_tiled_matrix_t` | Distributed tile matrix descriptor |
| `dcA.mat` | `double*` | Local tile data (NB x NB per tile) |
| `dcA.super.mt/nt` | `int` | Number of tile rows/columns |
| `dcA.super.nb` | `int` | Tile size (NB x NB) |
| Task graph | `parsec_taskpool_t*` | DAG of POTRF/TRSM/GEMM tasks |

## MPI Distribution
- 2D block-cyclic distribution over P x Q process grid
- Each rank owns `ceil(mt/P) * ceil(nt/Q)` tiles
- Tile size NB is fixed at launch

## State Size Estimate
For N=10000, NB=200, 4 ranks:
- Tiles per rank: ~625
- Memory per rank: 625 * 200 * 200 * 8 bytes ≈ 200 MB
- ABFT checksums: ~1% overhead
