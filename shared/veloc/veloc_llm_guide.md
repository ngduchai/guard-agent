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

## 3. Configuration (`veloc.conf`)

VeloC reads configuration from a text file (typically `veloc.conf`). This file defines:

- **Global options**: e.g., number of protection levels, synchronous/asynchronous behavior.
- **Storage hierarchy**: local memory, local SSD, parallel file system, etc.
- **Paths**: where to store scratch (local) and persistent (global) checkpoints.
- **Policies**: frequency of flushing from fast to permanent storage, retention, compression, etc.

Please refer [VeloC Configuration Spec](https://veloc.readthedocs.io/en/latest/userguide.html#configure-veloc) to generate configuration file.

### 3.1. How the agent should use configuration

Given user resilience requirements (e.g., checkpoint interval in seconds, storage hierarchy, capacity constraints), the agent should:

1. Derive a **checkpoint interval** in terms of simulation steps.
2. Choose appropriate local and global checkpoint directories (respecting user-provided paths).
3. Generate a `veloc.conf` file consistent with the target system.
4. Ensure the application either:
   - Loads `veloc.conf` from the **working directory**, or
   - Uses an environment variable or explicit path to point to the config (depending on the integration pattern).

---

## 4. Algorithm for VeloC code injection (used by STEP_IDENTIFY_AND_INJECT)

When transforming a user-supplied codebase, the agent should follow this **executable algorithm**. It is used by the `STEP_IDENTIFY_AND_INJECT` workflow step (which receives only the list of discovered source file paths and workspace_root from the previous step). The step (1) identifies data to save between failures and (2) injects VeloC using MCP tools only. **To change how injection works, edit this section**; the agent code refers to this guide and does not hard-code the algorithm.

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

### 4.2. Injection steps (per candidate file), refer to [VeloC API](https://veloc.readthedocs.io/en/latest/api.html) to inject the correct code.

For each selected source file:

1. **Read the file**  
   - Use `read_code_file(path)` to load the code.

2. **Add includes**  
   - Ensure `#include <veloc.h>` is present in the translation unit.
   - In the **new file content** you generate (see below), make sure the include appears near other system headers (e.g. after `#include <mpi.h>`).

3. **Insert `VELOC_Init` at startup**  
   - After `MPI_Init` (or immediately after variable declarations in `main` if MPI is initialized elsewhere), insert `VELOC_Init` to initialize VeloC.

4. **Insert `VELOC_Mem_protect` after allocation**  
   - For each buffer identified as persistent state (from the identify-data step), find where it is allocated or its lifetime begins. After that point, insert `VELOC_Mem_protect` to inform VelOC to save the state when making a checkpoint and fill the state with saved checkpoint when
   restart/recovery

5. **Insert `VELOC_Restart` before main compution loop**  
   - Before going to the main time-stepping loop, insert `VELOC_Restart_test` to probe for the most recent version less than max_ver that can be used to restart from. If no upper limit is desired, max_ver can be set to zero to probe for the most recent version. Specifying an upper limit is useful when the most recent version is corrupted (e.g. the restored data structures fail integrity checks) and a new restart is needed based on the preceding version. The application can repeat the process until a valid version is found or no more previous versions are available. The function returns `VELOC_FAILURE` if no version is available or a positive integer representing the most recent version otherwise. If a checkpoint is found, use the returned version to insert logic to attempt a restart with `VELOC_Restart("my_app", returned_version)`.

6. **Insert `VELOC_Checkpoint` inside the loop**  
   - Inside the main loop body, after the state update for each step, insert periodic checkpointing, e.g.:
     - `if (step % checkpoint_interval == 0) { VELOC_Checkpoint(id, step); }`
   - Use a checkpoint interval derived from user requirements (e.g. every N iterations or every T seconds mapped to iterations).

7. **Insert `VELOC_Finalize` at shutdown**  
   - Before `MPI_Finalize`, insert `VELOC_Finalize();`.

### 4.3. Semantic requirements

- Failure-free execution and failure-prone execution (with restart) must be **semantically equivalent** once the program resumes.
- Do not introduce extra MPI communicators or reorder collective calls.
- Always inject code following the [Veloc API](https://veloc.readthedocs.io/en/latest/api.html),  and configuration following [VeloC Configuration](https://veloc.readthedocs.io/en/latest/userguide.html#configure-veloc) **DO NOT** invent new API/Configuration.
- Avoid placing checkpoints inside inner loops; keep them at the global progress level.
- Do not modify third-party or library code; limit edits to the user’s drivers / main simulation files.

---

## 5. Build / compilation guidance (used by STEP_ADD_BUILD)

The `STEP_ADD_BUILD` node should use this guidance to produce MCP steps that make the VeloC-instrumented code compile and link correctly.

### 5.1. Includes

- Ensure each translation unit that uses VeloC calls has:
  - `#include <veloc.h>`
- If this is missing, regenerate the relevant source file(s) with a full new body that adds the include near other system headers (`<mpi.h>`, etc.), and write them with `write_code_file(path, content, overwrite=True)`.

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
- All edits to `CMakeLists.txt` should be done by generating a full new file body and writing it with `write_code_file(path, content, overwrite=True)`.

### 5.4. Makefile-based builds

- Locate `Makefile` or similar via `list_project_files`.
- Update compile and link flags, for example:

  ```make
  CXXFLAGS += -I$(VELOC_INC)
  LDFLAGS  += -L$(VELOC_LIB) -lveloc_client
  ```

Refer to [User Guide](https://veloc.readthedocs.io/en/latest/userguide.html) for more build guide.

5. **Validation hints (for the user)**
   - Suggest compiling and running a short test with:
     - A small number of steps.
     - Intentionally killing the job after a checkpoint to verify restart behavior.
   - Recommend adjusting `checkpoint_interval_seconds` and storage directories based on system I/O performance and job walltime.

This guide should be provided as *system or tool context* to the LLM so it understands how to safely and idiomatically inject VeloC-based resilience into arbitrary user codebases.

