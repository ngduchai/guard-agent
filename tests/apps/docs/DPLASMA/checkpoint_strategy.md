# DPLASMA Checkpoint Strategy

## Reference Implementation
DPLASMA uses Algorithm-Based Fault Tolerance (ABFT), not traditional checkpointing. ABFT encodes redundancy directly into the matrix operations.

## Fault Tolerance Method
**ABFT** (not traditional checkpoint/restart):
- Right factor protected by ABFT checksums
- Left factor protected by horizontal parallel diskless checkpointing
- Integrated into the PaRSEC task DAG

## What Is Protected
- Matrix tiles during factorization (checksum encoding)
- Left factor via diskless checkpoint (replicated across neighbor ranks)

## Where Protection Is Applied
- Checksum tiles computed before factorization begins
- Checksums updated as part of the trailing matrix update tasks
- No explicit "checkpoint location" - protection is continuous

## Recovery Logic
1. Detect rank failure (PaRSEC runtime detects MPI process loss)
2. Recover lost tiles from ABFT checksums (right factor)
3. Recover left factor from diskless checkpoint replicas
4. Resume DAG execution from the failed point

## Overhead
- ABFT encoding: ~2-5% of computation time
- Diskless checkpoint: ~1% memory overhead
- Recovery: reconstruct only lost tiles, not full restart
