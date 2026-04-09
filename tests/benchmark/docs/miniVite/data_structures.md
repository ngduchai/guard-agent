# miniVite Data Structures

## Key Arrays (Checkpoint State)

Array sizes are fixed after graph loading. During coarsening, a new (smaller) graph is created but the original graph structure is not modified.

### Graph Structure (CSR format, per rank)
| Variable | Type | Size | Description |
|----------|------|------|-------------|
| `edge_indices` | `GraphElem*` (int64) | `nv+1` | CSR row pointers (adjacency offsets) |
| `edge_list` | `Edge*` (struct) | `ne` | CSR edge entries (target vertex + weight) |

### Community State (per local vertex, size = `nv`)
| Variable | Type | Description |
|----------|------|-------------|
| `comm` | `GraphElem*` (int64) | Community assignment for each vertex |
| `comm_degree` | `GraphWeight*` (double) | Sum of edge weights within each community |
| `cluster_weight` | `GraphWeight*` (double) | Total weight of edges incident to community |

### Scalar State
| Variable | Type | Description |
|----------|------|-------------|
| `modularity` | `double` | Current global modularity score |
| `num_iters` | `int` | Current Louvain iteration count |
| `num_communities` | `int64` | Current number of distinct communities |
| `coarsening_level` | `int` | Current level of graph coarsening |

## MPI Distribution
- Vertices partitioned contiguously across ranks: rank `i` owns vertices `[start_i, end_i)`
- Ghost vertices maintained for remote endpoints of cross-rank edges
- Community labels of ghost vertices refreshed each iteration via halo exchange

## State Size Estimate
For an RMAT graph with 2^20 vertices and 2^24 edges on 8 ranks:
- Vertices per rank: ~131,072
- Edges per rank: ~2,097,152
- Community arrays: 3 arrays x 131,072 x 8 bytes = 3.1 MB
- Graph structure: ~2M edges x 16 bytes + 131K offsets x 8 bytes = 34 MB
- Approximate checkpoint (community state only): ~3.1 MB per rank
