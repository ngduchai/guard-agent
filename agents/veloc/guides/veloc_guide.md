# VeloC (Very-Low Overhead Checkpointing) — Complete Guide

> **Source:** https://veloc.readthedocs.io/en/latest/  
> **License:** UChicago Argonne LLC and Lawrence Livermore National Security, LLC

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration File Reference](#configuration-file-reference)
4. [C API Reference](#c-api-reference)
   - [Return Codes](#return-codes)
   - [Initialization and Finalization](#initialization-and-finalization)
   - [Memory-Based Mode](#memory-based-mode)
   - [File-Based Mode](#file-based-mode)
   - [Checkpoint Functions](#checkpoint-functions)
   - [Restart Functions](#restart-functions)
5. [C++ Client API (veloc::client_t)](#c-client-api-velocclient_t)
6. [Complete Code Examples](#complete-code-examples)
   - [Memory-Based API Example](#memory-based-api-example)
   - [File-Based API Example](#file-based-api-example)
7. [CMakeLists.txt Integration](#cmakeliststxt-integration)
8. [Execution Modes](#execution-modes)
9. [Batch Job Pattern](#batch-job-pattern)
10. [Best Practices and Checkpoint Frequency](#best-practices-and-checkpoint-frequency)

---

## Overview

VeloC (Very-Low Overhead Checkpointing System) is a multi-level checkpointing library designed for HPC applications. It provides:

- **Memory-based checkpoints**: Automatic serialization of registered memory regions.
- **File-based checkpoints**: Full application control over serialization.
- **Synchronous mode**: All resilience strategies run in-process (blocking).
- **Asynchronous mode**: Resilience strategies run in a background process (`veloc-backend`), returning control to the application immediately.
- **Multi-level storage**: Checkpoints are saved to a fast node-local scratch directory first, then flushed to a persistent parallel file system.
- **Erasure coding (EC)**: Optional redundancy across nodes.
- **Checksum verification**: Optional integrity checking.

---

## Installation

```bash
# Clone the latest stable release (replace x.y with the version number)
git clone -b 'veloc-x.y' --depth 1 https://github.com/ECP-VeloC/veloc.git <source_dir>

# Or clone the development branch
git clone --single-branch --depth 1 https://github.com/ECP-VeloC/veloc.git <source_dir>

cd <source_dir>

# Bootstrap dependencies (if standard libraries are missing)
./bootstrap.sh

# Build and install
./auto-install.py <install_dir>

# If Python cannot find bootstrapped libraries:
export PYTHONPATH=~/.local/lib/python3.6/site-packages
./auto-install.py <install_dir>
```

After installation:
- **Client library**: `<install_dir>/lib/`
- **Header file**: `<install_dir>/include/veloc.h` (C API) and `<install_dir>/include/veloc.hpp` (C++ API)
- **Active backend**: `<install_dir>/bin/veloc-backend`
- **Examples**: `<source_dir>/src/test/`

---

## Configuration File Reference

VeloC uses an INI-style configuration file (e.g., `veloc.cfg`).

### Mandatory Fields

```ini
scratch = <path>      # Node-local path for temporary checkpoints (fast, ephemeral)
persistent = <path>   # Persistent path for durable checkpoints (PFS, survives job)
```

### Optional Fields

```ini
# Execution mode: "sync" (default) or "async"
mode = async

# Minimum seconds between consecutive persistent flushes (default: 0 = always flush)
# Set to -1 to fully disable persistent flushing
persistent_interval = 300

# Minimum seconds between consecutive erasure-coding checkpoints (default: 0 = always)
# Set to -1 to fully disable EC
ec_interval = 600

# Seconds between watchdog checks of client processes (default: 0 = no watchdog)
watchdog_interval = 30

# Number of checkpoint versions to keep on persistent storage (default: 0 = keep all)
max_versions = 3

# Number of checkpoint versions to keep on scratch (default: 0 = keep all)
# WARNING: if left at 0, scratch may fill up — set this if scratch space is limited
scratch_versions = 2

# Failure domain for smart EC distribution (default: hostname)
failure_domain = <hostname>

# AXL transfer type for optimized PFS flushes (default: empty = use built-in POSIX)
# See AXL documentation for valid values (e.g., "AXL_XFER_SYNC", "AXL_XFER_ASYNC_BBAPI")
axl_type = AXL_XFER_SYNC

# Enable checksum calculation and verification (default: false)
chksum = true

# Path for checksum metadata (required when chksum = true)
meta = <persistent_meta_path>
```

### Minimal Example (`veloc.cfg`)

```ini
scratch = /tmp/scratch
persistent = /tmp/persistent
mode = async
```

### Production Example

```ini
scratch = /dev/shm/veloc_scratch
persistent = /lustre/project/myapp/checkpoints
mode = async
persistent_interval = 300
max_versions = 3
scratch_versions = 2
chksum = true
meta = /lustre/project/myapp/checkpoints_meta
```

---

## C API Reference

Include the header in your source files:

```c
#include <veloc.h>
```

Link against the VeloC library:

```
-L<install_dir>/lib -lveloc-client
```

### Return Codes

All VeloC functions return an `int`:

| Code | Value | Meaning |
|------|-------|---------|
| `VELOC_SUCCESS` | 0 | Function completed successfully |
| `VELOC_FAILURE` | -1 | Failure; VeloC prints an error message |

### Initialization and Finalization

#### `VELOC_Init` — Collective initialization

```c
int VELOC_Init(MPI_Comm comm, const char *cfg_file);
```

| Parameter | Description |
|-----------|-------------|
| `comm` | MPI communicator for the checkpoint group (typically `MPI_COMM_WORLD`) |
| `cfg_file` | Path to the VeloC configuration file |

**Must be called collectively by all processes before any other VeloC function. Call immediately after `MPI_Init()`.**

#### `VELOC_Init_single` — Non-collective initialization

```c
int VELOC_Init_single(unsigned int unique_id, const char *cfg_file);
```

| Parameter | Description |
|-----------|-------------|
| `unique_id` | Unique identifier for this process (enables independent checkpointing) |
| `cfg_file` | Path to the VeloC configuration file |

In non-collective mode, each process checkpoints independently. `VELOC_Restart_test` returns the latest version available for the calling process only.

#### `VELOC_Finalize` — Finalization

```c
int VELOC_Finalize(int drain);
```

| Parameter | Description |
|-----------|-------------|
| `drain` | Non-zero: wait for background backend to flush all pending checkpoints to persistent storage before returning. Zero: finalize immediately. |

**Must be called collectively by all processes. Call immediately before `MPI_Finalize()`.**

---

### Memory-Based Mode

In memory-based mode, VeloC automatically serializes registered memory regions.

#### `VELOC_Mem_protect` — Register a memory region

```c
int VELOC_Mem_protect(int id, void *ptr, size_t count, size_t base_size);
```

| Parameter | Description |
|-----------|-------------|
| `id` | Application-defined unique ID for this memory region (unique per process) |
| `ptr` | Pointer to the beginning of the memory region |
| `count` | Number of elements in the region |
| `base_size` | Size of each element in bytes (e.g., `sizeof(double)`) |

Each process registers its own memory regions independently. Registration can happen at any time before initiating a checkpoint or restart.

**Example:**
```c
double *h = malloc(sizeof(double) * M * nbLines);
double *g = malloc(sizeof(double) * M * nbLines);
int i = 0;

VELOC_Mem_protect(0, &i, 1, sizeof(int));
VELOC_Mem_protect(1, h, M * nbLines, sizeof(double));
VELOC_Mem_protect(2, g, M * nbLines, sizeof(double));
```

#### `VELOC_Mem_unprotect` — Deregister a memory region

```c
int VELOC_Mem_unprotect(int id);
```

| Parameter | Description |
|-----------|-------------|
| `id` | The ID previously used in `VELOC_Mem_protect` |

---

### File-Based Mode

In file-based mode, the application manually serializes/deserializes data to/from checkpoint files. VeloC provides the file path to use.

#### `VELOC_Route_file` — Get the checkpoint file path

```c
int VELOC_Route_file(char *original_name, char *ckpt_file_name);
```

| Parameter | Description |
|-----------|-------------|
| `original_name` | The logical name of the checkpoint file (used for PFS persistence) |
| `ckpt_file_name` | Output buffer (size `VELOC_MAX_NAME`) — the actual path to use for I/O |

**Must be called after `VELOC_Checkpoint_begin()` or `VELOC_Restart_begin()`.**

The application opens `ckpt_file_name` for reading (restart) or writing (checkpoint), performs I/O, then closes the file before calling `VELOC_Checkpoint_end()` or `VELOC_Restart_end()`.

---

### Checkpoint Functions

#### `VELOC_Checkpoint_begin` — Begin checkpoint phase

```c
int VELOC_Checkpoint_begin(const char *name, int version);
```

| Parameter | Description |
|-----------|-------------|
| `name` | Alphanumeric label for the checkpoint (letters and numbers only, no spaces) |
| `version` | Version number; must increase with each checkpoint (e.g., iteration number) |

**Must be called collectively by all processes in the checkpoint group.**

#### `VELOC_Checkpoint_mem` — Serialize registered memory regions

```c
int VELOC_Checkpoint_mem(void);
```

Writes all memory regions registered with `VELOC_Mem_protect` to the local checkpoint file. Must be called between `VELOC_Checkpoint_begin()` and `VELOC_Checkpoint_end()`.

#### `VELOC_Checkpoint_end` — End checkpoint phase

```c
int VELOC_Checkpoint_end(int success);
```

| Parameter | Description |
|-----------|-------------|
| `success` | Non-zero if this process successfully wrote its checkpoint; zero otherwise |

**Must be called collectively by all processes.**

- **Synchronous mode**: Blocks until all resilience strategies complete. Return value indicates success/failure.
- **Asynchronous mode**: Returns immediately; resilience strategies run in background. Always returns `VELOC_SUCCESS`.

#### `VELOC_Checkpoint_wait` — Wait for background checkpoint to complete

```c
int VELOC_Checkpoint_wait(void);
```

Waits for any background resilience strategies to finish. Only meaningful in asynchronous mode. In synchronous mode, returns `VELOC_SUCCESS` immediately.

**Best practice**: Call `VELOC_Checkpoint_wait()` before starting a new checkpoint in async mode to avoid overlapping checkpoints.

#### `VELOC_Checkpoint` — Convenience wrapper (memory-based)

```c
int VELOC_Checkpoint(const char *name, int version);
```

Equivalent to:
1. `VELOC_Checkpoint_wait()` (if in async mode)
2. `VELOC_Checkpoint_begin(name, version)`
3. `VELOC_Checkpoint_mem()`
4. `VELOC_Checkpoint_end(1)`

**Use this for the simplest memory-based checkpointing.**

---

### Restart Functions

#### `VELOC_Restart_test` — Find the latest available checkpoint version

```c
int VELOC_Restart_test(const char *name, int max_ver);
```

| Parameter | Description |
|-----------|-------------|
| `name` | Label of the checkpoint to probe |
| `max_ver` | Upper bound on version to search (0 = no limit, find the most recent) |

**Returns**: `VELOC_FAILURE` if no version is available, or a positive integer representing the most recent available version.

Use `max_ver > 0` when the most recent version is corrupted and you need to fall back to an earlier one.

#### `VELOC_Restart_begin` — Open restart phase

```c
int VELOC_Restart_begin(const char *name, int version);
```

| Parameter | Description |
|-----------|-------------|
| `name` | Label of the checkpoint |
| `version` | Version to restore (from `VELOC_Restart_test` or any earlier available version) |

**Must be called collectively by all processes.**

#### `VELOC_Recover_mem` — Restore all registered memory regions

```c
int VELOC_Recover_mem(void);
```

Convenience wrapper equivalent to `VELOC_Recover_selective(VELOC_RECOVER_ALL, NULL, 0)`.

#### `VELOC_Recover_selective` — Restore selected memory regions

```c
int VELOC_Recover_selective(int mode, int *ids, int length);
```

| Parameter | Description |
|-----------|-------------|
| `mode` | `VELOC_RECOVER_ALL`: restore all regions; `VELOC_RECOVER_SOME`: restore only `ids`; `VELOC_RECOVER_REST`: restore all except `ids` |
| `ids` | Array of region IDs (used with `VELOC_RECOVER_SOME` and `VELOC_RECOVER_REST`) |
| `length` | Number of elements in `ids` |

All IDs to be restored must have been previously registered with `VELOC_Mem_protect()`. The registered memory region must be large enough to hold the checkpoint data.

#### `VELOC_Restart_end` — Close restart phase

```c
int VELOC_Restart_end(int success);
```

| Parameter | Description |
|-----------|-------------|
| `success` | Non-zero if this process successfully restored its state; zero otherwise |

**Must be called collectively by all processes.**

#### `VELOC_Restart` — Convenience wrapper (memory-based)

```c
int VELOC_Restart(const char *name, int version);
```

Equivalent to:
1. `VELOC_Restart_begin(name, version)`
2. `VELOC_Recover_mem()`
3. `VELOC_Restart_end(1)`

---

## C++ Client API (`veloc::client_t`)

VeloC also provides a C++ header-only client API via `veloc.hpp`. This is useful for non-MPI or single-process applications.

```cpp
#include <veloc.hpp>
```

### Getting a Client Instance

```cpp
// Non-collective (single process or independent checkpointing)
veloc::client_t *ckpt = veloc::get_client(unsigned int unique_id, const char *cfg_file);
```

### Key Methods

```cpp
// Register a memory region
ckpt->mem_protect(int id, void *ptr, size_t base_size, size_t count);

// Checkpoint (memory-based, convenience)
ckpt->checkpoint(const char *name, int version);

// Test for latest checkpoint version
int v = ckpt->restart_test(const char *name, int max_ver);

// Restart (memory-based, convenience)
ckpt->restart(const char *name, int version);

// Finalize
delete ckpt;  // or ckpt->finalize()
```

**Note**: The C++ API method signatures may differ slightly from the C API (e.g., `mem_protect` takes `base_size` before `count`). Always check `veloc.hpp` for the exact signatures in your installed version.

---

## Complete Code Examples

### Memory-Based API Example

This example shows the full pattern for adding VeloC memory-based checkpointing to an iterative MPI application:

```c
#include <mpi.h>
#include <veloc.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);

    // (1) Initialize VeloC immediately after MPI_Init
    assert(VELOC_Init(MPI_COMM_WORLD, argv[2]) == VELOC_SUCCESS);

    // Application initialization
    int M = 256, nbLines = 64;
    double *h = (double *)malloc(sizeof(double) * M * nbLines);
    double *g = (double *)malloc(sizeof(double) * M * nbLines);
    int i = 0;
    int n = 1000;  // total iterations
    int K = 100;   // checkpoint every K iterations

    // (2) Register memory regions for checkpoint/restart
    VELOC_Mem_protect(0, &i, 1, sizeof(int));
    VELOC_Mem_protect(1, h, M * nbLines, sizeof(double));
    VELOC_Mem_protect(2, g, M * nbLines, sizeof(double));

    // (3) Check for a previous checkpoint
    int v = VELOC_Restart_test("myapp", 0);

    // (4) Restore from checkpoint if one exists
    if (v > 0) {
        printf("Restarting from checkpoint version %d (iteration %d)\n", v, v);
        assert(VELOC_Restart("myapp", v) == VELOC_SUCCESS);
    } else {
        i = 0;  // fresh start
    }

    // Main computation loop
    while (i < n) {
        // ... perform computation ...

        i++;

        // (5) Checkpoint every K iterations
        if (i % K == 0) {
            assert(VELOC_Checkpoint("myapp", i) == VELOC_SUCCESS);
        }
    }

    // (6) Finalize VeloC before MPI_Finalize
    // drain=1: wait for background flushes to complete
    VELOC_Finalize(1);
    MPI_Finalize();
    return 0;
}
```

### File-Based API Example

This example shows the file-based API for applications that need custom serialization:

```c
#include <mpi.h>
#include <veloc.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    assert(VELOC_Init(MPI_COMM_WORLD, argv[2]) == VELOC_SUCCESS);

    int M = 256, nbLines = 64;
    double *h = (double *)malloc(sizeof(double) * M * nbLines);
    double *g = (double *)malloc(sizeof(double) * M * nbLines);
    int i = 0;
    int n = 1000;
    int K = 100;

    // Check for previous checkpoint
    int v = VELOC_Restart_test("myapp", 0);

    if (v > 0) {
        // --- RESTART (file-based) ---
        assert(VELOC_Restart_begin("myapp", v) == VELOC_SUCCESS);

        char veloc_file[VELOC_MAX_NAME];
        assert(VELOC_Route_file("myapp_ckpt.dat", veloc_file) == VELOC_SUCCESS);

        int valid = 1;
        FILE *fd = fopen(veloc_file, "rb");
        if (fd != NULL) {
            if (fread(&i, sizeof(int), 1, fd) != 1) valid = 0;
            if (fread(h, sizeof(double), M * nbLines, fd) != (size_t)(M * nbLines)) valid = 0;
            if (fread(g, sizeof(double), M * nbLines, fd) != (size_t)(M * nbLines)) valid = 0;
            fclose(fd);
        } else {
            valid = 0;
        }

        assert(VELOC_Restart_end(valid) == VELOC_SUCCESS);
    } else {
        i = 0;
    }

    // Main computation loop
    while (i < n) {
        // ... perform computation ...

        i++;

        // --- CHECKPOINT (file-based) ---
        if (i % K == 0) {
            // Wait for any previous async checkpoint to complete
            assert(VELOC_Checkpoint_wait() == VELOC_SUCCESS);
            assert(VELOC_Checkpoint_begin("myapp", i) == VELOC_SUCCESS);

            char veloc_file[VELOC_MAX_NAME];
            assert(VELOC_Route_file("myapp_ckpt.dat", veloc_file) == VELOC_SUCCESS);

            int valid = 1;
            FILE *fd = fopen(veloc_file, "wb");
            if (fd != NULL) {
                if (fwrite(&i, sizeof(int), 1, fd) != 1) valid = 0;
                if (fwrite(h, sizeof(double), M * nbLines, fd) != (size_t)(M * nbLines)) valid = 0;
                if (fwrite(g, sizeof(double), M * nbLines, fd) != (size_t)(M * nbLines)) valid = 0;
                fclose(fd);
            } else {
                valid = 0;
            }

            assert(VELOC_Checkpoint_end(valid) == VELOC_SUCCESS);
        }
    }

    VELOC_Finalize(1);
    MPI_Finalize();
    return 0;
}
```

### C++ Non-Collective API Example

```cpp
#include <veloc.hpp>
#include <mpi.h>
#include <cassert>

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);

    int rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);

    // Initialize VeloC with unique process ID (non-collective mode)
    veloc::client_t *ckpt = veloc::get_client((unsigned int)rank, "veloc.cfg");

    // Allocate and register data
    const int N = 1000;
    float *data = new float[N];
    ckpt->mem_protect(0, data, sizeof(float), N);

    int iter = 0;
    const char *ckpt_name = "myapp";

    // Check for previous checkpoint
    int v = ckpt->restart_test(ckpt_name, 0);
    if (v > 0) {
        ckpt->restart(ckpt_name, v);
        // iter is restored from checkpoint
    }

    // Main loop
    while (iter < 10000) {
        // ... computation ...
        iter++;

        if (iter % 100 == 0) {
            ckpt->checkpoint(ckpt_name, iter);
        }
    }

    delete ckpt;
    MPI_Finalize();
    return 0;
}
```

---

## CMakeLists.txt Integration

```cmake
cmake_minimum_required(VERSION 3.14)
project(MyApp CXX C)

find_package(MPI REQUIRED)

# Set VeloC install directory (can also be passed via -DVELOC_DIR=...)
set(VELOC_DIR "/path/to/veloc/install" CACHE PATH "VeloC installation directory")

# Add VeloC include and library paths
include_directories(${VELOC_DIR}/include)
link_directories(${VELOC_DIR}/lib)

add_executable(myapp main.cc)

target_link_libraries(myapp
    MPI::MPI_CXX
    veloc-client      # VeloC client library
)

# Set RPATH so the binary finds libveloc-client.so at runtime
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "${VELOC_DIR}/lib"
    BUILD_WITH_INSTALL_RPATH TRUE
)
```

Alternatively, set `LD_LIBRARY_PATH` at runtime:

```bash
export LD_LIBRARY_PATH=<install_dir>/lib:$LD_LIBRARY_PATH
```

---

## Execution Modes

### Synchronous Mode

No extra setup needed. Run the application as a normal MPI job:

```bash
mpirun -np 4 ./myapp <args> veloc.cfg
```

All resilience strategies run in-process and block until complete.

### Asynchronous Mode

Set `mode = async` in `veloc.cfg`. The `veloc-backend` process must be running on each node:

```bash
# Ensure veloc-backend is in PATH
export PATH=<install_dir>/bin:$PATH
export LD_LIBRARY_PATH=<install_dir>/lib:$LD_LIBRARY_PATH

# Run the application (veloc-backend is launched automatically per node)
mpirun -np 4 ./myapp <args> veloc.cfg
```

The backend creates log files at `/dev/shm/veloc-backend-<hostname>-<uid>.log` by default. Control the log location with:

```bash
export VELOC_LOG=/shared/logs/veloc
```

---

## Batch Job Pattern

For HPC batch jobs where nodes may fail:

```bash
#!/bin/bash
#SBATCH --nodes=N+K          # Reserve N+K nodes to survive up to K failures
#SBATCH --no-kill            # Do NOT kill the job when a node fails

while true; do
    # Run the application on surviving nodes
    mpirun -np $((SLURM_NNODES * RANKS_PER_NODE)) ./myapp <args> veloc.cfg
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "Application completed successfully."
        break
    else
        echo "Application failed with exit code $EXIT_CODE. Restarting..."
        # VeloC will automatically restart from the latest checkpoint
    fi
done
```

---

## Best Practices and Checkpoint Frequency

### Young-Daly Formula for Optimal Checkpoint Interval

The optimal checkpoint interval `T*` that minimizes total overhead is:

```
T* = sqrt(2 * C * MTBF)
```

Where:
- `C` = checkpoint cost (time to write one checkpoint)
- `MTBF` = Mean Time Between Failures of the system

**Example**: If checkpointing takes 60 seconds and MTBF is 10 hours (36000 s):
```
T* = sqrt(2 * 60 * 36000) ≈ 2078 seconds ≈ 35 minutes
```

### General Best Practices

1. **Always call `VELOC_Init` immediately after `MPI_Init`** and `VELOC_Finalize` immediately before `MPI_Finalize`.

2. **Use `VELOC_Checkpoint_wait()` before starting a new checkpoint** in async mode to avoid overlapping checkpoints.

3. **Set `scratch_versions` and `max_versions`** to avoid filling up storage. A value of 2–3 is typical.

4. **Use `drain=1` in `VELOC_Finalize`** to ensure all pending checkpoints are flushed to persistent storage before the job ends.

5. **Checkpoint names must be alphanumeric** (letters and numbers only, no spaces or special characters).

6. **Version numbers must strictly increase** with each checkpoint. Using the iteration number is a natural choice.

7. **Check `VELOC_Restart_test` return value carefully**: it returns `VELOC_FAILURE` (negative) if no checkpoint exists, or a positive version number if one does.

8. **In file-based mode**, always use the path returned by `VELOC_Route_file` for I/O — never use your own path directly.

9. **For non-contiguous data structures** (linked lists, trees, etc.), use the file-based API for full control over serialization.

10. **Set `persistent_interval = -1` and `ec_interval = -1`** to disable those features if not needed, rather than setting a large number.

### Checkpoint Placement Pattern

```c
// Standard pattern for iterative applications
for (int iter = start_iter; iter < max_iter; iter++) {
    // 1. Perform computation
    do_work(iter);

    // 2. Checkpoint at regular intervals
    if ((iter + 1) % checkpoint_interval == 0) {
        int rc = VELOC_Checkpoint("myapp", iter + 1);
        if (rc != VELOC_SUCCESS) {
            fprintf(stderr, "Checkpoint failed at iteration %d\n", iter + 1);
            // Handle error — application may continue or abort
        }
    }
}
```

### Restart Pattern

```c
// Standard restart pattern at application startup
int start_iter = 0;
int v = VELOC_Restart_test("myapp", 0);
if (v > 0) {
    // Checkpoint found — restore state
    int rc = VELOC_Restart("myapp", v);
    if (rc == VELOC_SUCCESS) {
        start_iter = v;  // Resume from checkpointed iteration
        printf("Resumed from iteration %d\n", start_iter);
    } else {
        // Restart failed — try an older version
        v = VELOC_Restart_test("myapp", v - 1);
        if (v > 0) {
            VELOC_Restart("myapp", v);
            start_iter = v;
        }
        // If still failing, start fresh
    }
}
```

---

## Key Constants

| Constant | Description |
|----------|-------------|
| `VELOC_SUCCESS` | Return code for success (0) |
| `VELOC_FAILURE` | Return code for failure (-1) |
| `VELOC_MAX_NAME` | Maximum length of a checkpoint file path buffer |
| `VELOC_RECOVER_ALL` | Mode for `VELOC_Recover_selective`: restore all regions |
| `VELOC_RECOVER_SOME` | Mode for `VELOC_Recover_selective`: restore specified regions |
| `VELOC_RECOVER_REST` | Mode for `VELOC_Recover_selective`: restore all except specified |

---

## Quick Reference Card

```
INITIALIZATION
  VELOC_Init(comm, cfg_file)              — collective init (MPI apps)
  VELOC_Init_single(unique_id, cfg_file)  — non-collective init

MEMORY REGISTRATION
  VELOC_Mem_protect(id, ptr, count, base_size)  — register region
  VELOC_Mem_unprotect(id)                        — deregister region

CHECKPOINTING (memory-based, simple)
  VELOC_Checkpoint(name, version)         — checkpoint all regions

CHECKPOINTING (manual / file-based)
  VELOC_Checkpoint_wait()                 — wait for async checkpoint
  VELOC_Checkpoint_begin(name, version)   — begin checkpoint phase
  VELOC_Checkpoint_mem()                  — serialize memory regions
  VELOC_Route_file(orig, buf)             — get checkpoint file path
  VELOC_Checkpoint_end(success)           — end checkpoint phase

RESTART (memory-based, simple)
  VELOC_Restart_test(name, max_ver)       — find latest version
  VELOC_Restart(name, version)            — restore all regions

RESTART (manual / file-based)
  VELOC_Restart_test(name, max_ver)       — find latest version
  VELOC_Restart_begin(name, version)      — begin restart phase
  VELOC_Recover_mem()                     — restore all regions
  VELOC_Route_file(orig, buf)             — get checkpoint file path
  VELOC_Restart_end(success)              — end restart phase

FINALIZATION
  VELOC_Finalize(drain)                   — finalize (drain=1 recommended)
```
