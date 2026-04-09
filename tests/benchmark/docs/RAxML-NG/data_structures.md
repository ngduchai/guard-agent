# RAxML-NG Data Structures

## Key Structures

| Variable | Type | Description |
|----------|------|-------------|
| `Tree` | `pll_utree_t*` | Unrooted binary tree topology |
| `TreeInfo::pll_partition` | `pll_partition_t*` | Partition with CLVs, tip patterns |
| `Model` | `Model` | Substitution model parameters per partition |
| `Options` | `Options` | Run configuration (search strategy, bootstraps) |
| `Checkpoint` | `CheckpointManager` | Serialized search state |

## MPI Distribution
- Coarse-grained: each MPI rank runs independent tree search(es)
- No alignment data distribution across MPI ranks (each has full alignment)
- Parallelism is at the tree search level

## State Size Estimate
- Tree topology: ~4 KB per 1000 taxa
- Model parameters: ~0.5 KB per partition
- Checkpoint file: ~10 KB total (tree + model + search state)
