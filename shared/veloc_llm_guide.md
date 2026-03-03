# VeloC Integration Guide for LLM Agents

This document summarizes how to inject [VeloC](https://github.com/ECP-VeloC/VELOC) checkpointing into a user-supplied HPC codebase and produce a **ready-to-deploy resilient executable**. It is designed to be fed to an LLM orchestrator/agent.

VeloC overview and API details: see the official docs at [veloc.readthedocs.io](https://veloc.readthedocs.io/en/latest/).

---

## 1. When to use VeloC

Use VeloC when:

- The application is **long-running** HPC code (MPI and/or multi-threaded) running on supercomputers or large clusters.
- The user wants **fault-tolerance** (checkpoint/restart) or **suspend-resume / migration / rollback** capabilities.
- The application state can be represented as a collection of buffers (arrays, structs) that can be serialized.

Do **not** use VeloC for:

- Tiny, short-lived scripts where restart is unnecessary.
- Stateless services where recreating state is cheaper than checkpointing.

---

## 2. High-level integration pattern (C / C++)

The canonical integration pattern in C/C++ is:

1. **Include the VeloC header** and link the client library.
2. **Initialize** VeloC near program startup.
3. **Register** application data to be checkpointed.
4. Inside the main simulation / time-stepping loop:
   - Periodically **checkpoint** state (based on iteration or time).
   - On restart, **restore** state and resume from the last successful checkpoint.
5. **Finalize** VeloC at program end.

### 2.1. Minimal C-like skeleton

> NOTE: This is schematic and may omit minor parameters. Always check the official API docs for exact signatures.

```c
#include <mpi.h>
#include <veloc.h>

int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);

    // 1. Initialize VeloC (communicator, application name, config file)
    VELOC_Init(MPI_COMM_WORLD, "my_app", "veloc.conf");

    // 2. Register buffers (per-checkpoint ID or logical variable name)
    // Example for a single global buffer:
    //   int id = 0;
    //   VELOC_Register(id, data_ptr, data_bytes, VELOC_FAST);

    int rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);

    int step = 0;

    // 3. Check if we are restarting from a previous checkpoint
    // Pseudo-code: VELOC_Restart(id, step, ...);
    // If a restart is found, update 'step' and restore data buffers.

    for (; step < max_steps; ++step) {
        // ---- core computation ----
        // update application state buffers here

        // 4. Periodic checkpoint
        if (step % checkpoint_interval == 0) {
            // Pseudo-code: create a checkpoint tagged by 'step'
            // VELOC_Checkpoint(id, step);
        }
    }

    // 5. Finalize
    VELOC_Finalize();
    MPI_Finalize();
    return 0;
}
```

Key ideas:

- Each **checkpoint** is associated with an integer or string ID and a **time step** / version.
- On restart, the application queries VeloC for the **latest available version**, restores data into pre-allocated buffers, and resumes the loop from that step.

---

## 3. Configuration (`veloc.conf`)

VeloC reads configuration from a text file (typically `veloc.conf`). This file defines:

- **Global options**: e.g., number of protection levels, synchronous/asynchronous behavior.
- **Storage hierarchy**: local memory, local SSD, parallel file system, etc.
- **Paths**: where to store local and global checkpoints.
- **Policies**: frequency of flushing from fast to permanent storage, retention, compression, etc.

Typical configuration knobs (names may vary; see docs for exact keys):

- `scratch_dir` / `local_dir`: node-local (fast) checkpoint directory.
- `global_dir`: shared / parallel file system checkpoint directory.
- `max_versions`: how many versions to keep.
- `mode`: synchronous vs. asynchronous write.
- `compression`: compression algorithm (if enabled).

### 3.1. How the agent should use configuration

Given user resilience requirements (e.g., checkpoint interval in seconds, storage hierarchy, capacity constraints), the agent should:

1. Derive a **checkpoint interval** in terms of simulation steps.
2. Choose appropriate local and global checkpoint directories (respecting user-provided paths).
3. Generate a `veloc.conf` file consistent with the target system.
4. Ensure the application either:
   - Loads `veloc.conf` from the **working directory**, or
   - Uses an environment variable or explicit path to point to the config (depending on the integration pattern).

The MCP tool `veloc_configure_checkpoint` can be used to generate a **human-readable configuration snippet** and guidance. The agent can then create or update `veloc.conf` via `write_code_file`.

---

## 4. Algorithm for VeloC code injection (used by STEP_CODE_INJECTION)

When transforming a user-supplied codebase, the agent should follow this **executable algorithm**. It is designed to be implemented by the `STEP_CODE_INJECTION` node using MCP tools only.

### 4.1. Locate injection points

Work only on files under the **workspace** directory that were discovered as candidate sources (e.g. via `list_project_files` + heuristics):

- **Program entry points**:
  - `int main(int argc, char** argv)` in C/C++.
  - Ignore Fortran/Python for now unless they are thin frontends into C/MPI.

- **Initialization / finalization**:
  - Where MPI is initialized (`MPI_Init`, `MPI_Init_thread`) and finalized (`MPI_Finalize`).
  - Where simulation state (arrays/structs) is allocated and freed.

- **Main time-stepping / iteration loops**:
  - Loops over global timesteps or solver iterations (`for (t = 0; t < T; ++t)`, `while (!converged)`).
  - Prefer **outer loops** that represent global progress, not inner loops over local indices.

### 4.2. Injection steps (per candidate file)

For each selected source file:

1. **Read the file**  
   - Use `read_code_file(path)` to load the code.

2. **Add includes**  
   - Ensure `#include <veloc.h>` is present in the translation unit.
   - Use `apply_text_patch` to insert it after existing system includes (e.g. after `#include <mpi.h>`).

3. **Insert `VELOC_Init` at startup**  
   - After `MPI_Init` (or immediately after variable declarations in `main` if MPI is initialized elsewhere), insert:
     - `VELOC_Init(MPI_COMM_WORLD, "my_app", "veloc.conf");` (or a user/target-specific app name).

4. **Insert `VELOC_Register` after allocation**  
   - For each buffer identified as persistent state (from the identify-data step), find where it is allocated or its lifetime begins.
   - After that point, insert `VELOC_Register(id, ptr, size_in_bytes, VELOC_FAST);` or a similar call, with:
     - A stable integer or string `id` per buffer or logical variable.
     - `ptr` pointing to the buffer.
     - `size_in_bytes` matching its size (e.g. `sizeof(double) * N * M`).

5. **Insert `VELOC_Restart` near loop start**  
   - Near the beginning of the main time-stepping loop:
     - Insert logic to attempt a restart:
       - If `VELOC_Restart(id, &step, ...)` (or equivalent API) reports a valid checkpoint:
         - Restore all registered buffers.
         - Set the loop index `step` to the recovered value so the loop resumes from the checkpointed iteration.

6. **Insert `VELOC_Checkpoint` inside the loop**  
   - Inside the main loop body, after the state update for each step, insert periodic checkpointing, e.g.:
     - `if (step % checkpoint_interval == 0) { VELOC_Checkpoint(id, step); }`
   - Use a checkpoint interval derived from user requirements (e.g. every N iterations or every T seconds mapped to iterations).

7. **Insert `VELOC_Finalize` at shutdown**  
   - Before `MPI_Finalize`, insert `VELOC_Finalize();`.

All of the insertions above must be implemented via `apply_text_patch` on the files under the workspace directory.

### 4.3. Semantic requirements

- Failure-free execution and failure-prone execution (with restart) must be **semantically equivalent** once the program resumes.
- Do not introduce extra MPI communicators or reorder collective calls.
- Avoid placing checkpoints inside inner loops; keep them at the global progress level.
- Do not modify third-party or library code; limit edits to the user’s drivers / main simulation files.

---

## 5. Build / compilation guidance (used by STEP_ADD_BUILD)

The `STEP_ADD_BUILD` node should use this guidance to produce MCP steps that make the VeloC-instrumented code compile and link correctly.

### 5.1. Includes

- Ensure each translation unit that uses VeloC calls has:
  - `#include <veloc.h>`
- If this is missing, `STEP_ADD_BUILD` should emit `apply_text_patch` operations to insert the include near other system headers (`<mpi.h>`, etc.).

### 5.2. Libraries / link flags

- The final executable must link against the VeloC client library and any required dependencies, for example:
  - `-lveloc_client` plus its transitive dependencies.
- On systems with modules or Spack/E4S, VeloC is often provided as a module:
  - Suggest `module load veloc` or an equivalent to expose headers and libs.

### 5.3. CMake-based builds

- Locate `CMakeLists.txt` files via `list_project_files`.
- For each relevant target (e.g. `add_executable(my_app ...)`):
  - Add VeloC to the link libraries, for example:

    ```cmake
    find_package(VELOC REQUIRED)  # pattern; exact package name may differ

    target_link_libraries(my_app_veloc PRIVATE VELOC::client)
    ```

  - If there is an existing non-resilient target (e.g. `my_app`), create a **separate resilient target** (e.g. `my_app_veloc`) that uses the VeloC-instrumented sources.
- All edits to `CMakeLists.txt` should be done with `apply_text_patch` or, if necessary, full-file `write_code_file` when regenerating a small build file.

### 5.4. Makefile-based builds

- Locate `Makefile` or similar via `list_project_files`.
- Update compile and link flags, for example:

  ```make
  CXXFLAGS += -I$(VELOC_INC)
  LDFLAGS  += -L$(VELOC_LIB) -lveloc_client
  ```

- As with CMake, prefer adding a **separate resilient executable** target rather than overwriting the original one.

### 5.5. General notes

- Paths to headers and libraries are system-dependent; the agent should propose **generic patterns** and note that the user may need to adjust module names or paths according to local documentation.
- `STEP_ADD_BUILD` should not perform non-build changes (no code injection here); it should only adjust includes and link/target configuration so that the code injected in `STEP_CODE_INJECTION` compiles and links successfully.

---

## 6. VeloC API vs MCP tools

**Important:** `VELOC_Init`, `VELOC_Register`, `VELOC_Checkpoint`, `VELOC_Restart`, and `VELOC_Finalize` are **C library functions** provided by the VeloC library. They are **not** MCP tools. The agent must **inject them as source code** into the user's C/C++ files (e.g. using the `apply_text_patch` MCP tool with a replace string that contains the actual C line). Do not invent or call an MCP tool named `veloc_register` or `VELOC_Register`—there is no such tool; `VELOC_Register` is only valid as C code inside the codebase.

---

## 7. Using MCP tools for automated transformation

The following MCP tools exposed by this server support automated injection:

- `veloc_configure_checkpoint`  
  Generate a human-readable VeLoC configuration summary based on checkpoint interval, directory, and compression. The agent can turn this into a `veloc.conf` file using `write_code_file`.

- `list_project_files`  
  Enumerate candidate source files in the user project (e.g. `src/**/*.c`, `src/**/*.cpp`, `src/**/*.f90`). Use this to locate main programs and time-stepping loops.

- `read_code_file`  
  Fetch the contents of a file so the LLM can understand the structure and decide where to inject **C code** (e.g. VELOC_Init, VELOC_Register, VELOC_Checkpoint).

- `write_code_file`  
  Create new source files (e.g. wrappers, utility modules, `veloc.conf`) or write fully regenerated source files after a transformation.

- `apply_text_patch`  
  Apply controlled text replacements to **inject VeloC C API calls** into the code (e.g. inject the C line `VELOC_Init(...)` after `MPI_Init(...)`, or `VELOC_Register(id, ptr, size, VELOC_FAST);` after a buffer is allocated). Use this for all insertions of VELOC_* calls; use `write_code_file` only for new files or full-file overwrites.

### 7.1. Suggested agent workflow

1. **Discover structure**
   - Call `list_project_files` to find likely entry and driver files.
   - Call `read_code_file` on top-level sources to identify `main` / driver routines and time-stepping loops.

2. **Plan VeloC integration**
   - Decide where to place:
     - `VELOC_Init` / `VELOC_Finalize`
     - `VELOC_Register` calls
     - `VELOC_Restart` logic
     - `VELOC_Checkpoint` calls
   - Call `veloc_configure_checkpoint` to synthesize a configuration comment and convert it into a `veloc.conf` file via `write_code_file`.

3. **Edit code**
   - For simple insertions or replacements, use `apply_text_patch`.
   - For complex refactors, use `read_code_file` + LLM reasoning + `write_code_file` to regenerate entire functions or modules.

4. **Update build configuration**
   - Identify build files (`CMakeLists.txt`, `Makefile`, etc.) via `list_project_files`.
   - Use `read_code_file` and `apply_text_patch` or `write_code_file` to:
     - Add the VeloC include directory and library.
     - Add a new executable target for the resilient build.

5. **Validation hints (for the user)**
   - Suggest compiling and running a short test with:
     - A small number of steps.
     - Intentionally killing the job after a checkpoint to verify restart behavior.
   - Recommend adjusting `checkpoint_interval_seconds` and storage directories based on system I/O performance and job walltime.

This guide should be provided as *system or tool context* to the LLM so it understands how to safely and idiomatically inject VeloC-based resilience into arbitrary user codebases.

