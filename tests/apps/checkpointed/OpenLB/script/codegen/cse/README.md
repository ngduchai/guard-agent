# OpenLB Automatic Code Generation

Common subexpression elimination (CSE) is an established approach to
reducing the arithmetic complexity of LBM computation kernels. OpenLB
provides an automated pipeline for CSE-optimized branch-free LBM
collision steps and non-local post-processors.

## Prerequisites

- Python (Mako, SymPy)
- GCC
- Make

(When using Nix Flake, instantiate the environment via `nix develop .#env-code-generation`)

## Usage

### Optimize New Dynamics

Call `optimize_dynamics.sh` with the full template name of the dynamics.

- `--install`: Directly place generated code in the correct location.
- `--deterministic`: Apply (more expensive) deterministic expression sequences.

### Optimize New Post-Processors

Call `optimize_post_processors.sh` with the full template name and the target descriptor.

- `--install`: Directly place generated code in the correct location.
- `--deterministic`: Apply (more expensive) deterministic expression sequences.

### Regenerate All Components

Call `regenerate_dynamics.sh` or `regenerate_post_processors.sh`.

- `-j N`: Set the number of parallel processes.
- `--max-memory <GB>`: Limit RAM per process (CSE can be memory-intensive).

## Directory Structure

- **`source/`**: Python source files and templates
- **`tests/`**: Dynamics and operators tested by CI
- **`optimize_dynamics.sh`**: Optimize single dynamics (optional installation)
- **`optimize_post_processors.sh`**: Optimize single post-processors (optional installation)
- **`regenerate_dynamics.sh`**: Regenerate dynamics outdated by commit
- **`regenerate_post_processors.sh`**: Regenerate post-processors outdated by commit
- **`sync_dynamics_includes.sh`**: Update `src/cse/dynamics/generated_cse.h`
- **`sync_post_processors_includes.sh`**: Update `src/cse/operator/generated_cse.h`
- **`check_includes.sh`**: Verify consistency of `generated_cse.h` files
- **`check_dynamics.sh`**: Regenerate and compare test dynamics to reference
- **`check_post_processors.sh`**: Regenerate and compare test post-processors to reference
- **`update_check_dynamics.sh`**: Regenerate references for test dynamics
- **`update_check_post_processors.sh`**: Regenerate references for test post-processors

## Special Remark

If the optimized code produces incorrect results in combination with
an excessive number of expressions, modify `cse_utils.py`:

Change:

`return block.cse(symbols=generator, optimizations=custom_opti, order='none')`

To:

`return block.cse(symbols=generator)`

For testing, if you want to disable the CSE code, add "#define DISABLE_CSE" to the top of your cpp file.