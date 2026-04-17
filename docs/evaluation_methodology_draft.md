# Evaluation Methodology

## 1. Evaluation Goals

We evaluate Guard-Agent along three dimensions:

1. **Correctness of checkpoint placement**: Can the approach correctly identify (a) which data structures must be protected, (b) where in the control flow to place checkpoint/restart calls, and (c) under what conditions to trigger recovery?

2. **Robustness across application diversity**: How does performance vary across applications with different data structure characteristics (fixed-size vs. variable-size state), computation patterns (iterative, task-parallel, pipeline, irregular), and codebase complexity (proxy apps to production frameworks)?

3. **Efficiency**: How many LLM iterations, tokens, and wall-clock time are needed to produce a correct resilient version? How does guided analysis (Guard-Agent) compare to unassisted LLM modification (baseline)?

## 2. Application Test-Bed

We construct a test-bed of 20 HPC applications organized in a two-dimensional classification matrix crossing **computation pattern** (4 categories) with **state characteristics** (2 categories), yielding 8 cells with 2--3 applications each.

### 2.1 Classification Matrix

| | Fixed-size State | Variable-size State |
|---|---|---|
| **Iterative / Time-stepping** | CoMD, LULESH, miniFE | LAMMPS, WarpX, Nyx |
| **Task-parallel / DAG** | Chameleon, DPLASMA | CLAMR, deal.II |
| **Pipeline / Staged** | Palabos, Nektar++, SU2 | RAxML-NG, ExaML |
| **Irregular / Adaptive** | AMG, miniVite | SAMRAI, Uintah, AMReX |

**Iterative / Time-stepping** applications advance state through a main loop with a fixed or adaptive time step. Checkpoint placement is typically at the loop boundary. *Fixed-size* variants (CoMD, LULESH, miniFE) maintain constant-size arrays throughout execution, while *variable-size* variants (LAMMPS, WarpX, Nyx) involve particle migration, adaptive mesh refinement, or dynamic load balancing that changes the checkpoint payload between steps.

**Task-parallel / DAG** applications decompose computation into tasks with data dependencies. Checkpoint placement must respect task boundaries and data ownership. Chameleon and DPLASMA use runtime systems (StarPU, PaRSEC) with algorithm-based fault tolerance (ABFT), while CLAMR and deal.II use adaptive refinement that changes mesh topology.

**Pipeline / Staged** applications execute a sequence of distinct computational phases (e.g., mesh generation, solve, post-process). Checkpoints may be placed between stages or within long-running stages. Palabos, Nektar++, and SU2 have fixed pipelines; RAxML-NG and ExaML iterate over a variable-length search space.

**Irregular / Adaptive** applications use data-dependent control flow (graph traversal, multigrid cycles, community detection). The checkpoint payload depends on the current refinement level or graph partition. AMG and miniVite have fixed graph sizes; SAMRAI, Uintah, and AMReX dynamically refine their meshes.

### 2.2 Application Details

| Application | Language | LOC | Build System | MPI Ranks | Checkpoint Library |
|---|---|---|---|---|---|
| CoMD | C | ~2K | Make | 4 | POSIX file I/O |
| LULESH | C++ | ~5K | CMake | 8 | SCR |
| miniFE | C++ | ~3K | Make | 4 | FTI |
| LAMMPS | C++ | ~300K | CMake | 4 | Native restart |
| WarpX | C++ | ~150K | CMake | 1 | Native (AMReX) |
| Nyx | C++ | ~15K | Make | 4 | Native (HPCCG) |
| Chameleon | C++ | ~5K | Make | 4 | Native (HPCG) |
| DPLASMA | C++ | ~5K | Make | 4 | Native (HPCCG) |
| CLAMR | C++ | ~15K | CMake | 4 | Native |
| deal.II | C | ~2K | Make | 1 | Native (XSBench) |
| Palabos | C++ | ~50K | CMake | 1 | Native MPI-IO |
| Nektar++ | C | ~3K | Make | 4 | Native (miniAMR) |
| SU2 | C++ | ~400K | Meson | 1 | Native |
| RAxML-NG | C++ | ~5K | Make | 4 | Native (PENNANT) |
| ExaML | C | ~2K | Make | 1 | Native (XSBench) |
| AMG | C | ~30K | Make | 4 | FTI |
| miniVite | C++ | ~3K | Make | 4 | VeloC / FTI |
| SAMRAI | C++ | ~200K | CMake | 4 | Native HDF5 |
| Uintah | C | ~3K | Make | 4 | Native (miniAMR) |
| AMReX | C++ | ~150K | CMake | 1 | Native |

### 2.3 Selection Criteria

Applications were selected to ensure:

- **Coverage**: Every cell in the 4x2 classification matrix is populated with 2--3 applications.
- **Diversity of checkpoint mechanisms**: The test-bed includes POSIX file I/O, multi-level checkpoint libraries (SCR, FTI, VeloC), algorithm-based fault tolerance (ABFT), and application-native restart mechanisms.
- **Range of complexity**: From proxy apps (~2K LOC) to production frameworks (~400K LOC).
- **Buildability**: All 20 applications compile and run correctly on the evaluation platform (ARM64 Ubuntu 24.04 with OpenMPI 4.1.6).

## 3. Evaluation Approaches

We compare four approaches to adding checkpoint/restart resilience:

### 3.1 Baseline: Unassisted LLM

An LLM agent (OpenCode with various backend models) is given the application source code and a prompt requesting VeloC checkpoint integration. The agent modifies the code iteratively: after each modification, automated validation checks correctness. On failure, error logs are fed back to the agent for another attempt. No domain-specific tools or analysis are provided.

**Models evaluated**: Claude Sonnet 4, Claude Opus 4, GPT-4o, Gemini 2.5 Pro (via OpenCode's model-switching capability).

### 3.2 Human-Written Reference

For each application, we provide a hand-written checkpointed version that serves as the ground truth. These reference implementations use the checkpoint library specified in the application's configuration (Table 2) and have been validated to correctly recover from process failures. The reference is used to:

1. Establish that correct checkpoint/restart *is possible* for each application.
2. Provide golden output for correctness comparison.
3. Measure the overhead of checkpointing (runtime, storage).

### 3.3 Transparent Checkpointing (DMTCP/MANA)

DMTCP with the MANA MPI plugin provides process-level checkpoint/restart without source modification. We evaluate this approach as a "zero-effort" baseline that captures the entire process state (memory, file descriptors, MPI state). While transparent, this approach typically incurs higher overhead and larger checkpoint sizes than application-level approaches.

### 3.4 Guard-Agent (Our Approach)

Guard-Agent augments the LLM agent with domain-specific MCP tools that provide:

- **Code inspection**: Static analysis of the application's data structures, loop nests, MPI communication patterns, and I/O points.
- **Checkpoint plan generation**: Identification of (a) which variables to protect, (b) optimal checkpoint placement in the control flow, and (c) VeloC API call sequences.
- **Knowledge base**: A curated guide to VeloC API usage, common patterns, and pitfalls.
- **Validation execution**: Automated build, run, failure injection, and output comparison.
- **Failure analysis**: Structured diagnosis of build errors, runtime crashes, and output mismatches.

The agent uses these tools within the same iterative loop as the baseline, but with access to structured domain knowledge rather than relying solely on LLM reasoning.

## 4. Metrics

### 4.1 Correctness Metrics

- **Build success**: Does the modified code compile without errors?
- **Runtime success**: Does the modified code execute and produce output?
- **Recovery success**: After failure injection (process kill after checkpoint), does the application restart and complete?
- **Output correctness**: Does the recovered output match the golden output within the application's tolerance? Comparison methods include:
  - *Numeric*: Element-wise floating-point comparison with relative tolerance (for physics simulations).
  - *Text*: Line-by-line exact match after filtering non-deterministic lines (timestamps, timing).
  - *Hash*: SHA-256 byte-identical comparison (for binary outputs).
  - *SSIM*: Structural Similarity Index on HDF5 datasets (for field data).

### 4.2 Efficiency Metrics

- **Iterations to success**: Number of LLM interaction rounds needed to produce a correct resilient version (lower is better).
- **Token consumption**: Total LLM input + output tokens across all iterations (lower is better).
- **Wall-clock time**: Total elapsed time from first prompt to successful validation (lower is better).
- **Success rate**: Fraction of applications successfully made resilient within the iteration budget (higher is better).

### 4.3 Quality Metrics

- **Checkpoint data identification**: Precision and recall of data structures identified for protection, compared to the human-written reference.
- **Checkpoint placement accuracy**: Whether checkpoints are placed at correct control flow points (e.g., main loop boundary, after MPI barriers).
- **Restart logic completeness**: Whether the restart path correctly restores all protected state and resumes computation from the checkpoint.
- **Code diff size**: Lines of code added/modified, as a measure of implementation minimality.

## 5. Experimental Setup

### 5.1 Platform

- **Hardware**: ARM64 (aarch64) development server, 4 cores, 32 GB RAM.
- **OS**: Ubuntu 24.04 LTS.
- **MPI**: OpenMPI 4.1.6.
- **Compilers**: GCC 13.3.0, gfortran 13.3.0.
- **Build tools**: CMake 3.28.3, Make, Meson 1.10.2, Ninja 1.13.0.
- **Checkpoint libraries**: VeloC (latest), FTI 1.6, SCR 3.1.0, jemalloc 5.3.0 (installed to `$HOME/.local`).

### 5.2 Validation Pipeline

The validation pipeline operates in six stages for each application:

1. **Vanilla build**: Compile the original unmodified source code.
2. **Golden run**: Execute the vanilla application without failures to capture reference output.
3. **No-recovery verification**: Kill the vanilla application mid-execution and restart it. Verify that it does *not* produce correct output (confirming that resilience requires explicit checkpointing).
4. **Checkpointed build**: Compile the checkpointed version (either human reference or LLM-generated).
5. **Recovery verification**: Kill the checkpointed application mid-execution and restart it. Verify that it *does* produce correct output (confirming successful recovery).
6. **Output comparison**: Compare the recovered output against the golden reference using the application-specific comparison method and tolerance.

### 5.3 Iterative Evaluation Protocol

For each application and each approach (baseline, Guard-Agent):

1. Start with a clean copy of the vanilla source code.
2. Present the LLM with the application's checkpoint prompt.
3. Allow the LLM to modify source files.
4. Run the validation pipeline.
5. If validation passes: record success metrics and stop.
6. If validation fails: extract error logs (compiler output, runtime errors, output diff) and present them to the LLM as feedback for the next iteration.
7. Repeat until success or the iteration budget (default: 20) is exhausted.

**Resumption safety**: If the evaluation is interrupted (e.g., by system restart), the framework re-copies the vanilla source for any incomplete application before resuming, ensuring that partially-modified code from a previous run does not contaminate the next attempt.

### 5.4 Evaluation Dimensions

#### (i) Data Structure Detection

We evaluate how well each approach identifies the critical data structures that must be checkpointed. For each application, the human-written reference specifies which variables are protected (documented in `tests/apps/docs/<APP>/data_structures.md`). We compare:

- **Precision**: What fraction of the variables the LLM chose to checkpoint are actually necessary?
- **Recall**: What fraction of the necessary variables did the LLM correctly identify?
- **False positives**: Variables checkpointed unnecessarily (increases overhead but doesn't break correctness).
- **False negatives**: Variables missed (causes incorrect recovery --- the most critical failure mode).

We analyze these metrics across the classification matrix to determine whether certain computation patterns or state characteristics are more challenging for LLM-based analysis.

#### (ii) Robustness

We evaluate robustness along three axes:

- **Data structure complexity**: Fixed-size arrays (CoMD) vs. dynamically-allocated linked structures (LAMMPS particles) vs. framework-managed containers (AMReX MultiFab).
- **Computation flow complexity**: Simple main loops (LULESH) vs. nested iteration with convergence checks (AMG V-cycles) vs. task DAGs (DPLASMA) vs. multi-phase pipelines (SU2).
- **Codebase complexity**: Proxy apps with ~2K LOC and flat file structure vs. production frameworks with ~400K LOC, deep directory hierarchies, and complex build systems.

For each axis, we report success rate, iteration count, and token usage, and identify failure modes specific to each complexity level.

#### (iii) Efficiency Improvement

We measure how Guard-Agent's domain-specific tools improve efficiency over the unassisted baseline:

- **Iteration reduction**: How many fewer LLM rounds are needed with Guard-Agent?
- **Token reduction**: How much less LLM computation is consumed?
- **Time reduction**: How much faster is the end-to-end process?
- **Failure mode elimination**: Which categories of errors (build failures, incorrect checkpoint placement, missing restart logic) are prevented by Guard-Agent's analysis tools?

We further analyze which specific Guard-Agent tools contribute most to efficiency gains: code inspection, checkpoint plan generation, knowledge base queries, or validation feedback.

## 6. Reproducibility

All evaluation artifacts are included in the repository:

- **Application sources**: `tests/apps/vanillas/` (20 vanilla applications), `tests/apps/checkpointed/` (20 reference checkpointed versions).
- **Configuration**: `tests/apps/vanillas/*/app.yaml` (build commands, run commands, comparison methods, checkpoint library).
- **Documentation**: `tests/apps/docs/*/` (computation flow, data structures, checkpoint strategy for each application).
- **Dependency installation**: `scripts/install_deps.sh` (checkpoint libraries), `scripts/install_system_deps.sh` (system packages), `scripts/install_app_sources.sh` (source downloads).
- **Evaluation scripts**: `validation/veloc/scripts/run_batch.sh` (batch evaluation), `run_iterative.sh` (per-app iterative loop), `run_evaluate.sh` (full A/B comparison), `run_validate.sh` (single validation).
- **Environment setup**: `scripts/install_deps.sh` generates `$HOME/.local/env.sh` with all required paths.

To reproduce the evaluation on a new system:

```bash
# 1. Install system dependencies
sudo ./scripts/install_system_deps.sh

# 2. Install checkpoint libraries
./scripts/install_deps.sh

# 3. Download application source trees
./scripts/install_app_sources.sh

# 4. Set up environment and build infrastructure
source $HOME/.local/env.sh
./setup.sh --clean

# 5. Verify all 20 apps build and validate
./build/run_validate_apps.sh --fresh

# 6. Run full evaluation
./build/run_batch.sh --generate-list all > all_apps.txt
./build/run_batch.sh all_apps.txt --mode evaluate --max-iters 20
```
