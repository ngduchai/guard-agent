# OpenLB - Open Source Lattice Boltzmann Code

OpenLB is a modern C++ framework for the efficient implementation of
Lattice Boltzmann Methods (LBM) addressing a vast range of transport
problems in Computational Fluid Dynamics (CFD) and beyond.

```
    ┃
    ┃  ┏━━━━┓      ▁▁▁▁                   ▁▁    ▁▁▁▁
    ┃  ┃    ┃     ╱ ▁▁ ╲▁▁▁▁  ▁▁▁  ▁▁▁▁  ╱ ╱   ╱ ▁▁ ╲
 ┏━━╋━┓┃    ┃    ╱ ╱ ╱ ╱ ▁▁ ╲╱ ▁ ╲╱ ▁▁ ╲╱ ╱   ╱ ╱▁╱ ╱
 ┃  ┗━╋╋━━━━┻┓  ╱ ╱▁╱ ╱ ╱▁╱ ╱  ▁▁╱ ╱ ╱ ╱ ╱▁▁▁╱ ╱▁╱ ╱
 ┃    ┃┃     ┃  ╲▁▁▁▁╱ ▁▁▁▁╱╲▁▁▁╱▁╱ ╱▁╱▁▁▁▁▁╱▁▁▁▁▁╱
 ┗━━━━┛┃     ┃      ╱▁╱ ==========================>>
       ┗━━━━━┛
```

## Key Features

* **Physics:** Single and multiphase flows, thermal flows, turbulence modeling (LES, WM), chemical reactive flows, resolved and subgrid-scale particulate flows, radiative transport, porous media, fluid-structure interaction… and combinations thereof!
* **HPC:** Parallelization via MPI and OpenMP; Vectorization via AVX2/512; GPU acceleration via CUDA and HIP (ROCm); Integrated automatic code optimization pipeline for common subexpression elimination (CSE).
* **Examples:** 130+ example cases exploring all application areas and providing solid foundations for new ones.
* **Input/Output:** Built-in pre- and postprocessing. Integrated meshing (voxelizing) based on STL files, VTI data and constructive solid geometry (CSG) indicators. Simulation output as VTK, CSV, Gnuplot and images.
* **Modern C++:** Utilizes the C++20 standard and template metaprogramming for flexibility and performance.

## Dependencies

* **Compiler:** C++20 compliant compiler (recent versions of GCC, Clang, Intel ICX).
* **Build System:** GNU Make.
* **Parallelization:** OpenMPI / Intel MPI
* **GPU (Optional):** NVIDIA CUDA 12.4+; AMD ROCm
* **Code generation (Optional):** Python 3+ with SymPy, Mako

For users of the [Nix](https://nixos.org/) ecosystem, a `flake.nix` declaring various environments is included.

## Quick Start

### Compilation

1. **Configure:** Adjust the `config.mk` file to fit your local compiler environment
   (examples for some common configurations are available in `config/`)

2.  **Run an Example:**
    ```bash
    cd examples/laminar/cavity2d
    make
    ./cavity2d
    ```

### Directory Structure

* `src/`: Library source code.
* `examples/`: Simulation setups categorized by physics.
* `config/`: Make configuration templates.
* `scripts/codegen`: Automatic code optimization.
* `tests/benchmarks`: Automated validation cases.

## Documentation

A comprehensive user guide is available [online](https://www.openlb.net/user-guide/).

## Community

The OpenLB [forum](https://www.openlb.net/forum/) is an open discussion board for all aspects of LBM and OpenLB.
Feel free to post any problems, questions, suggestions or contributions.

There is an annual one-week [Spring School](https://www.openlb.net/spring-school-2026/)
where you can learn about LBM and OpenLB directly from the developer team and invited
guest lecturers.

For a list of all present and past authors see `CONTRIBUTORS.txt`.

For high-priority direct support in any matter related to OpenLB,
the [consortium](https://www.openlb.net/consortium/) is available.

In any case, you can also reach us via mail at info@openlb.net.

## How to cite OpenLB

Standardized citation metadata is available in the `CITATION.cff` file.

To cite OpenLB in general instead of a specific release we suggest:

```
@article{OpenLB2021,
  title = {OpenLB - Open Source Lattice Boltzmann Code},
  year = {2021},
  issn = {08981221},
  doi = {10.1016/j.camwa.2020.04.033},
  journal = {Computers \& Mathematics with Applications},
  author = {Krause, Mathias J. and Kummerl{\"a}nder, Adrian and Avis, Samuel J. and Kusumaatmaja, Halim and Dapelo, Davide and Klemens, Fabian and Gaedtke, Maximilian and Hafen, Nicolas and Mink, Albert and Trunk, Robin and Marquardt, Jan E. and Maier, Marie-Luise and Haussmann, Marc and Simonis, Stephan},
}
```

This article is available as [open access](https://doi.org/10.1016/j.camwa.2020.04.033).

## How to Contribute

We welcome contributions from the community to help improve OpenLB!

### Public Contributions & Issues

For bug reports, feature requests, and code contributions, please use our public repository on GitLab:

Repository: [gitlab.com/openlb/release](https://gitlab.com/openlb/release)

Workflow: Please submit merge requests or open tickets in the issue tracker there.

### Discussion

If you are unsure if a behavior is a bug or need general assistance,
feel free to use the OpenLB Forum first.

### Project Partners

Please note that some of the active development by consortium members
and project partners takes place in the internal repository:
[gitlab.com/openlb/olb](https://gitlab.com/openlb/olb)

### Code Formatting

The basic formatting rules are [described](https://editorconfig.org/) by
the `.editorconfig` file for automatic application in a wide variety of
text editors and IDEs.

## License

OpenLB is provided as open source under the terms of the GNU GPL v2 license.

See `LICENSE` for details.