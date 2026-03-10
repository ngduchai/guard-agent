# VeloC Configuration Cheat Sheet

This document summarizes the **VeloC configuration file** format and minimal options,
based on the official Quick Start guide’s *Configure* section  
([VeloC Quick Start – Configure](https://veloc.readthedocs.io/en/latest/quick.html#configure)).

It is intended as a **ready-to-use reference** when generating or editing `veloc.conf`-style files.

---

## 1. Configuration File Basics

- VeloC reads its configuration from a **plain text file** (e.g., `veloc.conf` or `test.cfg`).
- Each line is a simple `key = value` pair:

  ```text
  key = value
  ```

- In the Quick Start single-node setup, a minimal config looks like:

  ```text
  scratch = /tmp/scratch
  persistent = /tmp/persistent
  mode = async
  ```

  as shown in the official docs  
  ([Quick Start – Configure](https://veloc.readthedocs.io/en/latest/quick.html#configure)).

---

## 2. Core Keys

### 2.1 `scratch`

- **Purpose**: path to the **local, fast storage** where VeloC writes *scratch* checkpoints.
- **Type**: absolute or relative filesystem path (string).
- **Example**:

  ```text
  scratch = /tmp/scratch
  ```

- **Notes**:
  - Should point to a directory with **low latency** and **sufficient space** (e.g., local SSD or node-local filesystem).
  - VeloC will create and populate this directory with per-rank checkpoint files (e.g., `heatdis-x-y.dat` in the Quick Start example).

### 2.2 `persistent`

- **Purpose**: path to the **persistent / parallel filesystem** used for durable checkpoints.
- **Type**: absolute or relative filesystem path (string).
- **Example**:

  ```text
  persistent = /tmp/persistent
  ```

- **Notes**:
  - Typically points to a shared filesystem (e.g., Lustre, GPFS, NFS) visible across nodes.
  - Checkpoints propagated here survive node failures and job restarts.

### 2.3 `mode`

- **Purpose**: controls whether VeloC operates in **synchronous** or **asynchronous** mode.
- **Type**: string; the Quick Start example uses:

  ```text
  mode = async
  ```

- **Semantics (as implied by the docs)**:
  - `async`:
    - Checkpoints are pushed to the persistent tier **in the background**.
    - `VELOC_Checkpoint_end` returns quickly and the application can continue computation.
    - `VELOC_Checkpoint_wait` can be used to block until background work completes.
  - `sync`:
    - Calls to created checkpoint is blocked until checkpoints are fluxhed to the persistent tier 

---

## 3. Minimal Single-Node Test Configuration

The Quick Start guide demonstrates a minimal **single-node** test configuration:

```text
scratch = /tmp/scratch
persistent = /tmp/persistent
mode = async
```

Usage (from the official example):

1. Create a temporary working directory, e.g.:

   ```bash
   mkdir -p /tmp/work
   cd /tmp/work
   ```

2. Create `test.cfg` with the contents above.
3. Run the sample application (adapted from the docs):

   ```bash
   export LD_LIBRARY_PATH=<install_dir>/lib
   export PATH=<install_dir>/bin:$PATH

   mpirun -np 2 <source_dir>/build/test/heatdis_mem 256 test.cfg
   ```

4. After a successful run, VeloC will populate:
   - `scratch` and `persistent` directories with files like `heatdis-x-y.dat` (x = rank, y = iteration).
   - A backend log under `/dev/shm/veloc-backend-<hostname>-<uid>.log` with information about checkpoint management.

5. To verify restart behavior (per the Quick Start):
   - Delete a **highest-version** checkpoint file from both `scratch` and `persistent`.
   - Re-run the same command.
   - The application should restart from the **preceding** version and then continue to completion, re-populating the directories.

---

## 4. Practical Guidance for Agents

- **When generating configs**:
  - Always set **both** `scratch` and `persistent` to **valid, writable directories**.
  - Prefer node-local `scratch` paths (e.g., under `/tmp` or node-local SSD) and shared `persistent` paths (e.g., under a parallel filesystem).
  - Use `mode = async` for HPC-style runs unless the user explicitly prefers synchronous behavior.

- **Do not invent keys**:
  - Only use configuration keys that are documented in the official VeloC user guide.
  - For advanced parameters (beyond `scratch`, `persistent`, `mode`), consult the full user guide at  
    [VeloC User Guide](https://veloc.readthedocs.io/en/latest/userguide.html).

