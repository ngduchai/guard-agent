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

### 4.2. Injection steps (per candidate file)

For each selected source file:

1. **Read the file**  
   - Use `read_code_file(path)` to load the code.

2. **Add includes**  
   - Ensure `#include <veloc.h>` is present in the translation unit.
   - In the **new file content** you generate (see below), make sure the include appears near other system headers (e.g. after `#include <mpi.h>`).

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

After understanding the original file via `read_code_file`, you must generate a **complete new version of the file** that:

- Preserves all original logic and structure (except for the added VeloC calls and any minimal control-flow needed to support restart).
- Adds the includes and VeloC calls described above.

Then emit an MCP step using:

- `write_code_file(path, content, overwrite=True)` with `content` set to the full new file body (including all original code plus the injected VeloC logic).

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

- As with CMake, prefer adding a **separate resilient executable** target rather than overwriting the original one.

### 5.5. General notes

- Paths to headers and libraries are system-dependent; the agent should propose **generic patterns** and note that the user may need to adjust module names or paths according to local documentation.
- `STEP_ADD_BUILD` should not perform non-build changes (no code injection here); it should only adjust includes and link/target configuration so that the code injected in `STEP_CODE_INJECTION` compiles and links successfully.

---

## 6. VeloC API vs MCP tools

**Important:** `VELOC_Init`, `VELOC_Register`, `VELOC_Checkpoint`, `VELOC_Restart`, and `VELOC_Finalize` are **C library functions** provided by the VeloC library. They are **not** MCP tools. The agent must **inject them as source code** into the user's C/C++ files by generating updated file contents that contain these calls and then writing those files via `write_code_file(path, content, overwrite=True)`. Do not invent or call an MCP tool named `veloc_register` or `VELOC_Register`—there is no such tool; `VELOC_Register` is only valid as C code inside the codebase.

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
  Create new source files (e.g. wrappers, utility modules, `veloc.conf`) or write fully regenerated source files after a transformation. Use `overwrite=True` when replacing an existing file with a complete new version that includes injected VeloC logic.

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
- Use `read_code_file` + LLM reasoning + `write_code_file(path, content, overwrite=True)` to regenerate entire functions, modules, or whole source files that include the injected VeloC calls.

4. **Update build configuration**
   - Identify build files (`CMakeLists.txt`, `Makefile`, etc.) via `list_project_files`.
   - Use `read_code_file` to understand the current build configuration, then regenerate a full new version of each relevant build file (adding VeloC include paths, libraries, and resilient targets) and write it with `write_code_file(path, content, overwrite=True)`.

5. **Validation hints (for the user)**
   - Suggest compiling and running a short test with:
     - A small number of steps.
     - Intentionally killing the job after a checkpoint to verify restart behavior.
   - Recommend adjusting `checkpoint_interval_seconds` and storage directories based on system I/O performance and job walltime.

This guide should be provided as *system or tool context* to the LLM so it understands how to safely and idiomatically inject VeloC-based resilience into arbitrary user codebases.

