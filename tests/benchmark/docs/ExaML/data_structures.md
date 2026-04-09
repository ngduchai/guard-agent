# ExaML Data Structures

## Key Structures

| Variable | Type | Description |
|----------|------|-------------|
| `tr->likelihood` | `double` | Current tree log-likelihood |
| `tr->start` | `nodeptr` | Root of the tree structure |
| `tr->nodep` | `nodeptr*` | Array of internal/leaf nodes |
| `tr->partitionData` | `pInfo*` | Per-partition model parameters (alpha, frequencies, rates) |
| `tr->aliaswgt` | `int*` | Alignment column weights (per-rank subset) |
| `tr->yVector` | `unsigned char**` | Compressed alignment data (per-rank columns) |

## MPI Distribution
- Alignment columns distributed cyclically across ranks
- Each rank computes partial likelihood for its assigned columns
- Tree topology replicated on all ranks

## State Size Estimate
For a 1000-taxon, 100K-column alignment with 4 partitions:
- Tree: ~8 KB (topology + branch lengths)
- Model params: ~1 KB per partition
- Local alignment: ~25 MB per rank (100K/nranks columns)
