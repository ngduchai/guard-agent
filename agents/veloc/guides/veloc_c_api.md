 # VeloC C API Cheat Sheet

This document summarizes the **VeloC C API** for checkpoint/restart, based on the official docs at  
[VeloC API docs](https://veloc.readthedocs.io/en/latest/api.html).

It is intended as a **quick reference** when instrumenting C/MPI HPC applications with VeloC.

---

## 1. Core Concepts

- **Modes of operation**:
  - **Memory-based checkpoints**: you register memory regions once; VeloC automatically saves/restores them.
  - **File-based checkpoints**: you manually write/read checkpoint files; VeloC manages filenames, hierarchy, and resilience policies.

- **Checkpoint versions**:
  - Each checkpoint has a **label** (`name`, alphanumeric) and an **integer version** (e.g., iteration number).
  - Versions should be **monotonically increasing** for a given name.

- **Return codes** (all functions return `int`):
  - `VELOC_SUCCESS` – operation succeeded.
  - `VELOC_FAILURE` – operation failed; VeloC prints an error message.

---

## 2. Initialization and Finalization

### 2.1 Collective initialization (MPI)

```c
int VELOC_Init(MPI_Comm comm, const char *cfg_file);
```

- **comm**: MPI communicator (typically `MPI_COMM_WORLD`).
- **cfg_file**: path to VeloC configuration file (e.g., `veloc.conf`).
- Must be called **collectively** by all processes in `comm`.
- Typically invoked **immediately after** `MPI_Init`.

### 2.2 Non-collective initialization (single process)

```c
int VELOC_Init_single(unsigned int unique_id, const char *cfg_file);
```

- **unique_id**: unique identifier for this process (user-chosen).
- **cfg_file**: path to VeloC configuration file.
- Allows each process to checkpoint/restart **independently**.
- Changes semantics of `VELOC_Restart_test` to operate per-process.

### 2.3 Finalization

```c
int VELOC_Finalize(int drain);
```

- **drain**:
  - Non-zero: wait for the active backend(s) to **flush pending checkpoints** to persistent storage.
  - Zero: finalize **immediately** without draining.
- Must be called collectively by all processes using VeloC.
- Typically invoked **just before** `MPI_Finalize`.

---

## 3. Memory-Based Mode

In this mode, VeloC automatically serializes registered memory regions during checkpoints and restores them on restart.

### 3.1 Register memory

```c
int VELOC_Mem_protect(int id, void *ptr, size_t count, size_t base_size);
```

- **id**: application-defined unique ID for this memory region (per process).
- **ptr**: pointer to beginning of the region.
- **count**: number of elements.
- **base_size**: size of each element in bytes (e.g., `sizeof(double)`).

Usage:

- Call after allocating critical data structures (arrays, structs).
- The `id` parameter will be use to identify data structures in the checkpoint, so if more than one data structure/variable need `VELOC_Mem_protect` then each time you call `VELOC_Mem_protect`, ensure `id` given by each call are unique.
- Each MPI rank manages its own regions and IDs independently.

### 3.2 Unregister memory

```c
int VELOC_Mem_unprotect(int id);
```

- **id**: memory region ID previously passed to `VELOC_Mem_protect`.
- Call when a region is no longer part of the persistent application state (e.g., freed or no longer needed for restart).

---

## 4. File-Based Mode

In this mode, the application controls how to serialize/deserialize data to checkpoint files.

### 4.1 Obtain checkpoint filename

```c
int VELOC_Route_file(char *original_name, char *ckpt_file_name);
```

- **original_name**: application-visible name (used when persisting to the parallel file system).
- **ckpt_file_name**: buffer that receives the **actual file path** to open for I/O.

Usage:

- Call **after** beginning a checkpoint or restart phase (see Sections 5–6).
- Open `ckpt_file_name` with standard I/O, then `fwrite`/`fread` critical data.

---

## 5. Checkpoint API

### 5.1 Begin checkpoint phase

```c
int VELOC_Checkpoint_begin(const char *name, int version);
```

- **name**: alphanumeric label for this checkpoint (e.g., `"heatdis"`).
- **version**: checkpoint version (e.g., iteration number).
- Must be called **collectively** within the checkpoint group.
- Starts a **checkpoint phase** during which you either:
  - Let VeloC serialize registered memory regions in **memory-based** mode, or
  - Use `VELOC_Route_file` and manual I/O in **file-based** mode.

### 5.2 Serialize registered memory

```c
int VELOC_Checkpoint_mem(void);
```

- No arguments.
- Writes all registered memory regions (via `VELOC_Mem_protect`) to local checkpoint storage.
- Call **between** `VELOC_Checkpoint_begin` and `VELOC_Checkpoint_end`.

### 5.3 End checkpoint phase

```c
int VELOC_Checkpoint_end(int success);
```

- **success**:
  - Non-zero: the process successfully wrote its local checkpoint.
  - Zero: local I/O failed or data is invalid.
- Collectively ends the checkpoint phase.
- Behavior depends on **synchronous vs asynchronous** mode:
  - **Synchronous**: performs all configured resilience actions **before returning**; return value indicates their success.
  - **Asynchronous**: triggers resilience actions in the background and returns immediately; operation itself always reports success.

### 5.4 Wait for background checkpoint completion

```c
int VELOC_Checkpoint_wait(void);
```

- Waits for any background resilience strategies to finish.
- Only meaningful in **asynchronous** mode; in synchronous mode, it returns success without effect.

### 5.5 Convenience checkpoint wrapper

```c
int VELOC_Checkpoint(const char *name, int version);
```

Equivalent to:

1. `VELOC_Checkpoint_wait()` (if asynchronous mode is enabled).
2. `VELOC_Checkpoint_begin(name, version)`.
3. `VELOC_Checkpoint_mem()`.
4. `VELOC_Checkpoint_end(/*success*/ 1)` (assuming all memory regions are valid).

---

## 6. Restart API

### 6.1 Probe for latest available version

```c
int VELOC_Restart_test(const char *name, int max_ver);
```

- **name**: checkpoint label (same as used for checkpointing).
- **max_ver**:
  - 0 – probe for the **most recent** available version.
  - >0 – probe for the most recent version **≤ max_ver**.

Returns:

- `VELOC_FAILURE` (usually `<= 0`) – **no checkpoint** is available.
- Positive integer – most recent version that can be used for restart.

Typical pattern:

- Call at startup, possibly in a loop to walk back from a corrupted version (application-level checks).

### 6.2 Begin restart phase

```c
int VELOC_Restart_begin(const char *name, int version);
```

- **name**: checkpoint label.
- **version**: version to restart from (e.g., result of `VELOC_Restart_test`).
- Must be called collectively within the checkpoint/restart group.

### 6.3 Restore registered memory (selective)

```c
int VELOC_Recover_selective(int mode, int *ids, int length);
```

- **mode**:
  - `VELOC_RECOVER_ALL`: restore **all** regions saved in the checkpoint (ignore `ids`/`length`).
  - `VELOC_RECOVER_SOME`: restore **only** regions with IDs listed in `ids`.
  - `VELOC_RECOVER_REST`: restore **all except** IDs listed in `ids`.
- **ids**: array of region IDs (`int`) previously registered via `VELOC_Mem_protect`.
- **length**: number of elements in `ids`.

Requirements:

- For each region to be restored, you must:
  - Have called `VELOC_Mem_protect` for that ID.
  - Ensure the allocated region is **large enough** for the checkpointed data.

### 6.4 Restore all registered memory (convenience)

```c
int VELOC_Recover_mem(void);
```

Equivalent to:

```c
VELOC_Recover_selective(VELOC_RECOVER_ALL, NULL, 0);
```

### 6.5 End restart phase

```c
int VELOC_Restart_end(int success);
```

- **success**:
  - Non-zero: the process successfully restored its critical state.
  - Zero: restart failed for this process.
- Must be called collectively; after this, the application can resume normal computation.

### 6.6 Convenience restart wrapper

```c
int VELOC_Restart(const char *name, int version);
```

Equivalent to:

1. `VELOC_Restart_begin(name, version)`.
2. `VELOC_Recover_mem()`.
3. `VELOC_Restart_end(/*success*/ 1)` (assuming restore succeeded).

---

## 7. Example Integration Pattern (Memory-Based)

Minimal pattern (MPI code) using the memory-based API:

```c
MPI_Init(&argc, &argv);
VELOC_Init(MPI_COMM_WORLD, argv[2]);  // cfg_file

// Allocate critical state
h = malloc(sizeof(double) * M * nbLines);
g = malloc(sizeof(double) * M * nbLines);

// Register state
VELOC_Mem_protect(0, &i, 1, sizeof(int));
VELOC_Mem_protect(1, h, M * nbLines, sizeof(double));
VELOC_Mem_protect(2, g, M * nbLines, sizeof(double));

// Probe for previous checkpoint
int v = VELOC_Restart_test("heatdis", 0);
if (v > 0) {
    // Restart from checkpoint version v
    assert(VELOC_Restart("heatdis", v) == VELOC_SUCCESS);
} else {
    i = 0;  // fresh start
}

while (i < n) {
    // Compute one iteration step...

    if (i % K == 0) {
        assert(VELOC_Checkpoint("heatdis", i) == VELOC_SUCCESS);
    }
    i++;
}

VELOC_Finalize(0);
MPI_Finalize();
```

---

## 8. Example Integration Pattern (File-Based)

Checkpoint (inside main loop):

```c
if (i % K == 0) {
    assert(VELOC_Checkpoint_wait() == VELOC_SUCCESS);
    assert(VELOC_Checkpoint_begin("heatdis", i) == VELOC_SUCCESS);

    char veloc_file[VELOC_MAX_NAME];
    assert(VELOC_Route_file("heatdis_ckpt", veloc_file) == VELOC_SUCCESS);

    int valid = 1;
    FILE *fd = fopen(veloc_file, "wb");
    if (fd != NULL) {
        if (fwrite(&i, sizeof(int), 1, fd) != 1)             valid = 0;
        if (fwrite(h, sizeof(double), M * nbLines, fd) != M * nbLines) valid = 0;
        if (fwrite(g, sizeof(double), M * nbLines, fd) != M * nbLines) valid = 0;
        fclose(fd);
    } else {
        valid = 0;
    }

    assert(VELOC_Checkpoint_end(valid) == VELOC_SUCCESS);
}
```

Restart:

```c
assert(VELOC_Restart_begin("heatdis", v) == VELOC_SUCCESS);

char veloc_file[VELOC_MAX_NAME];
assert(VELOC_Route_file("heatdis_ckpt", veloc_file) == VELOC_SUCCESS);

int valid = 1;
FILE *fd = fopen(veloc_file, "rb");
if (fd != NULL) {
    if (fread(&i, sizeof(int), 1, fd) != 1)             valid = 0;
    if (fread(h, sizeof(double), M * nbLines, fd) != M * nbLines) valid = 0;
    if (fread(g, sizeof(double), M * nbLines, fd) != M * nbLines) valid = 0;
    fclose(fd);
} else {
    valid = 0;
}

assert(VELOC_Restart_end(valid) == VELOC_SUCCESS);
```

---

## 9. Practical Notes

- **Where to call what**:
  - `VELOC_Init` / `VELOC_Init_single`: near program startup.
  - `VELOC_Mem_protect`: after allocation of long-lived state.
  - `VELOC_Restart_test` / `VELOC_Restart`: before entering the main compute loop.
  - `VELOC_Checkpoint` (or full begin/mem/end sequence): periodically inside the main loop.
  - `VELOC_Finalize`: just before program termination / `MPI_Finalize`.

- **Semantic goal**: failure-free and failure-prone (with restart) runs should be **semantically equivalent** once restarted from the latest successful checkpoint.

