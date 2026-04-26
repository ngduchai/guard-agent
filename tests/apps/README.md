# Benchmark Applications — Index

This directory holds the 18 applications that the validation pipeline runs against. Every app has three things:

```
tests/apps/
├── vanillas/<App>/        # immutable upstream source + app.yaml (validation contract)
├── checkpointed/<App>/    # immutable reference implementation with native checkpoint/restart
├── docs/<App>/README.md   # developer-facing description of state, workflow, checkpoint protocol
└── README.md              # ← you are here
```

The 18 apps are chosen so that each non-empty cell of the **(loop model × per-rank state behavior)** matrix is covered. Picking one app per class for `validation/veloc/apps_fast.txt` lets a benchmark sweep exercise every distinct **MPI checkpoint protocol** with the minimum number of runs.

---

## The 4-Class Taxonomy

Each class corresponds to a distinct MPI checkpoint protocol — what the writer must coordinate and what the payload must contain.

```
                              per-rank state behavior
                          fixed       variable      adaptive
                       ┌──────────┬──────────┬──────────┐
            iterative  │   (1)    │   (2)    │   (3)    │   ← MPI_Barrier-based
   loop                │   8 apps │   3 apps │   5 apps │
   model               ├──────────┼──────────┼──────────┤
            async      │    —     │   (4)    │    —     │   ← GVT-based snapshot
                       │          │   2 apps │          │
                       └──────────┴──────────┴──────────┘
```

### Classes

| # | Class | Definition | Checkpoint protocol |
|---|---|---|---|
| **(1)** | `iterative_fixed` — Iterative + identical kernel + fixed state | All ranks execute the same kernel sequence on partitions of unchanging shape and size | `MPI_Barrier` → each rank dumps its slice. Bytes-on-disk per rank are predictable from rank count alone. |
| **(2)** | `iterative_variable` — Iterative + identical kernel + variable state | Same kernel sequence across ranks, but per-rank data size fluctuates each step (particles/atoms migrate between subdomains) | `MPI_Barrier` → each rank dumps its slice. Length-prefixed records or per-rank index files since per-rank size varies. |
| **(3)** | `iterative_adaptive` — Iterative + adaptive mesh | Same kernel set, but the data structure itself adapts (AMR refine/coarsen, dynamic load balance); some ranks own multi-level patches while others own single-level | Collective metadata exchange + collective parallel write (HDF5 / MPI-IO). Capture topology metadata + per-rank variable-size payload atomically across the regrid boundary. |
| **(4)** | `asynchronous` — No global step | Ranks process events at locally-determined logical virtual times. Includes optimistic PDES (events + rollback / anti-messages), conservative PDES (null-message), and asynchronous iterative methods (chaotic relaxation, async Jacobi) | GVT computation via `MPI_Allreduce` over per-rank LVT, then distributed snapshot capturing LP state + pending event queue + anti-message log. **No `MPI_Barrier`** — algorithm has no consistent global step to barrier on. |

### How to classify a new app

Read the main loop and ask, in this order:

1. Does the loop have an `MPI_Barrier` (or implicit collective) per step? **No** → **(4) asynchronous**.
2. Does the data structure reshape during execution (AMR regrid, load balance)? **Yes** → **(3) iterative_adaptive**.
3. Does per-rank state size change every step (particle migration)? **Yes** → **(2) iterative_variable**.
4. Otherwise → **(1) iterative_fixed**.

The four checks are unambiguous; placement is determined by the structure of the main loop, not by app domain.

---

## All 18 Applications

Grouped by class (then alphabetical within class):

| App | Class | Lang | Checkpoint | Description |
|-----|-------|------|-----------|-------------|
| [CoMD](docs/CoMD/README.md) | (1) iterative_fixed | C | POSIX file I/O | Classical molecular dynamics proxy (LJ / EAM potentials) |
| [HPCG](docs/HPCG/README.md) | (1) iterative_fixed | C++ | POSIX file I/O | High Performance Conjugate Gradient — PCG with multigrid preconditioner; SpMV + MPI_Allreduce dominated |
| [HyPar](docs/HyPar/README.md) | (1) iterative_fixed | C++ | native | Finite-difference solver for hyperbolic–parabolic PDEs |
| [miniVite](docs/miniVite/README.md) | (1) iterative_fixed | C++ | POSIX file I/O | Distributed Louvain community detection |
| [MMSP](docs/MMSP/README.md) | (1) iterative_fixed | C++ | native | Mesoscale Microstructure Simulation (Cahn–Hilliard phase-field) |
| [OpenLB](docs/OpenLB/README.md) | (1) iterative_fixed | C++ | native | Lattice Boltzmann CFD (bstep2d example) |
| [QMCPACK](docs/QMCPACK/README.md) | (1) iterative_fixed | C++ | HDF5 | Quantum Monte Carlo electronic-structure code |
| [SPPARKS](docs/SPPARKS/README.md) | (1) iterative_fixed | C++ | native | Stochastic kinetic Monte Carlo on lattice |
| [SW4lite](docs/SW4lite/README.md) | (1) iterative_fixed | C++ | native | Seismic wave propagation mini-app (LLNL); 4th-order FD |
| [LAMMPS](docs/LAMMPS/README.md) | (2) iterative_variable | C++ | native | Large-scale molecular dynamics simulator |
| [Smilei](docs/Smilei/README.md) | (2) iterative_variable | C++ | HDF5 | Particle-in-cell plasma physics code |
| [SPARTA](docs/SPARTA/README.md) | (2) iterative_variable | C++ | native | Direct Simulation Monte Carlo (DSMC) rarefied gas dynamics |
| [Athena++](docs/Athena++/README.md) | (3) iterative_adaptive | C++ | native | Astrophysical MHD with AMR |
| [CLAMR](docs/CLAMR/README.md) | (3) iterative_adaptive | C++ | native | Cell-based AMR mini-app (shallow-water equations) |
| [Nyx](docs/Nyx/README.md) | (3) iterative_adaptive | C++ | AMReX native | Cosmological hydrodynamics + N-body (AMReX) |
| [SAMRAI](docs/SAMRAI/README.md) | (3) iterative_adaptive | C++ | native | Structured AMR application infrastructure (LLNL) |
| [WarpX](docs/WarpX/README.md) | (3) iterative_adaptive | C++ | AMReX native | Electromagnetic PIC on AMReX (subcycled AMR + particles) |
| [PRK_Stencil](docs/PRK_Stencil/README.md) | (4) asynchronous | C | POSIX file I/O | Parallel Research Kernels MPI1 Stencil — barrier-free 2D star-shaped stencil with non-blocking halo |
| [ROSS](docs/ROSS/README.md) | (4) asynchronous | C | RIO (POSIX) | Parallel discrete-event simulator (PHOLD), optimistic Time Warp |

Per-app contracts (build commands, MPI rank count, comparison method, run timeout) are declared in `vanillas/<App>/app.yaml` — that is the file the validation pipeline reads.

---

## Coverage Gaps and Suggested Additions

Class **(4) asynchronous** is now covered by three apps with structurally different async profiles:

| Sub-flavor | Coordination idiom | Example | In suite? |
|---|---|---|---|
| Optimistic PDES with rollback | events + anti-messages, GVT computation | ROSS | ✓ |
| Barrier-free BSP (asynchronous iterative) | nearest-neighbor MPI_Wait; no per-step MPI_Barrier or MPI_Allreduce | PRK_Stencil | ✓ |
| Message-driven async execution | Charm++ / AMPI; messages drive computation, no global step | NAMD, ChaNGa | ✗ (deferred — Charm++ build is heavy and source requires academic-license registration) |

PRK_Stencil is *barrier-free BSP* rather than chaotic-async; it still has neighbor synchronization via non-blocking halo. The author of the kernel deliberately removed the per-iteration `MPI_Allreduce`/`MPI_Barrier` so that drift between ranks is uncoordinated. This is the closest "no global step" pattern reachable with vanilla MPI; true chaotic relaxation (e.g. async Jacobi where ranks read stale neighbor data without waiting) would require a custom proxy.

ROSS covers the optimistic-PDES synchronization discipline; the conservative-PDES counterpart (SST) was dropped 2026-04-26 because its vanilla+reference setup was just shell-wrapper differences around a pre-built binary, not a meaningful resilience-engineering experiment. A replacement candidate for class (4) async is being researched (see ISSUES.md #26).

**Remaining recommendation:** add **NAMD** to (4) when the Charm++ toolchain is available. It is the only major production async-via-messaging code with native checkpoint/restart at petascale.

---

## Build-Time Tiers

For batch runs the apps are also tagged by approximate build + run cost:

| Tier | Apps | Use case |
|------|------|----------|
| `fast` (7) | CoMD, HPCG, SPARTA, Athena++, CLAMR, PRK_Stencil | First-cycle smoke runs; smallest representatives covering all 4 classes (SST removed 2026-04-26 — see ISSUES #26) |
| `mid` (6) | MMSP, HyPar, OpenLB, LAMMPS, SAMRAI, ROSS | Second-cycle: native checkpoint, ~few-minute runs, distinct mechanisms |
| `slow` (6) | SPPARKS, SW4lite, QMCPACK, Smilei, Nyx, WarpX | Third-cycle: HDF5 / AMReX heavyweights with bigger state |

Each tier picks roughly 1–2 apps per class (class (1) gets 3 because it has 9 apps total). The fast batch is the smoke run; mid and slow follow once the framework is healthy.

Generate the corresponding lists with:

```bash
./build/run_batch.sh --generate-list fast    > validation/veloc/apps_fast.txt
./build/run_batch.sh --generate-list mid     > validation/veloc/apps_mid.txt
./build/run_batch.sh --generate-list slow    > validation/veloc/apps_slow.txt
./build/run_batch.sh --generate-list all     > validation/veloc/apps_all.txt
```

The shipped `apps_fast.txt` / `apps_mid.txt` / `apps_slow.txt` are curated batches covering all four taxonomy classes per batch (1–2 apps per class, except class (1) which has 3 per batch because it has 9 apps total).

---

## How These Three Sets Are Used

### `vanillas/<App>/`
The unmodified upstream source plus a small `app.yaml` describing how to build, run, and compare it. **Immutable.** The validation pipeline reads `app.yaml` to discover the app and to know its build/run/compare contract; the source itself is never modified.

### `checkpointed/<App>/`
The reference implementation that includes native checkpoint/restart support (POSIX file, HDF5, or AMReX-native, as listed above). **Immutable.** Used as the ground-truth recovery behavior against which agent-generated approaches are compared.

### `docs/<App>/README.md`
A developer-facing write-up for each app, all in the same five-section format:

1. **Header** — category, language, checkpoint library.
2. **Application Description** — what the science is and where the app comes from.
3. **Computation Workflow** — Mermaid flowchart + per-phase narrative; the checkpoint trigger is highlighted in orange.
4. **Critical State** — table of every field the checkpoint must preserve, with C type and how it evolves.
5. **MPI Task Lifetime** — sequence diagrams for the per-step communication pattern and the application-lifetime view.
6. **Checkpoint Protection** — write trigger / what is saved / write protocol / restart protocol / consistency considerations.

Open any `docs/<App>/README.md` to learn the resilience-relevant internals of that app without reading its source.

---

## Workflow Cheatsheet

```bash
# 1. List every app
./build/run_batch.sh --generate-list all

# 2. Validate the reference checkpoint of the 8 fast/matrix apps
./build/run_batch.sh validation/veloc/apps_fast.txt \
  --mode validate --reference --skip-correctness

# 3. Resume after an interrupt (per-trial fine-grained resume)
./build/run_batch.sh validation/veloc/apps_fast.txt \
  --mode validate --reference --skip-correctness --continue

# 4. Inspect aggregated metrics for one app
python -c "
import json
d = json.load(open('build/validation_output/CoMD_reference/benchmarks/raw_metrics.json'))
for s, c in d['summary'].items():
    print(s, c)
"
```

For per-app benchmark scenario JSONs, see `validation/veloc/benchmark_configs/<App>.json`.

---

## Source Attribution

Every benchmark application is open-source upstream code, copied into `vanillas/<App>/` (with checkpoint logic stripped) and `checkpointed/<App>/` (with the upstream native checkpoint mechanism intact).  License files are preserved verbatim under each app's directory.  This table is the canonical record of where each app came from; reproducing the benchmark requires re-fetching from these URLs at the listed refs.

| App | Upstream URL | Origin / Authors | Key reference |
|---|---|---|---|
| **CoMD** | https://github.com/exmatex/CoMD | ExMatEx co-design center, Los Alamos National Laboratory (LLNL) | Mohd-Yusof, Swaminarayan & Germann, *CoMD-1.1*, ECP proxy app suite |
| **CLAMR** | https://github.com/lanl/CLAMR | Triad National Security, LLC (Los Alamos National Laboratory) | Nicholaeff, Davis, Trujillo & Robey, *Cell-Based AMR on the GPU with Applications to the Shallow Water Equations*, LA-UR-12-23994 (2012) |
| **SW4lite** | https://github.com/geodynamics/sw4lite | LLNL (Geodynamics CIG) — proxy of full SW4 (https://geodynamics.org/cig/software/sw4) | Petersson & Sjögreen, *High-order accurate finite-difference schemes for the elastic wave equation in 3D*, JCP (2015) |
| **MMSP** | https://github.com/mesoscale/mmsp | Mesoscale Microstructure Simulation Project, RPI (Trevor Keller et al.) | Doi: 10.5281/zenodo.19985417 — Keller et al., *MMSP*, JOSS |
| **HyPar** | https://github.com/debog/hypar | Debojyoti Ghosh, Argonne National Laboratory | https://hypar.readthedocs.io and http://hypar.github.io |
| **SPPARKS** | https://github.com/sandialabs/spparks (also https://spparks.github.io) | Sandia National Laboratories (Steven Plimpton et al.) | Plimpton, Battaile, Chandross, Holm et al., *SPPARKS*, GPL release |
| **HPCG** | https://github.com/hpcg-benchmark/hpcg | HPCG Benchmark project (Sandia/UTK — Heroux, Dongarra, Luszczek) | Dongarra, Heroux & Luszczek, *HPCG: A new HPC benchmark*, Int. J. HPCA (2016) |
| **PRK_Stencil** | https://github.com/ParRes/Kernels (subdirectory `MPI1/Stencil`) | Parallel Research Kernels, Intel + IBM (Van der Wijngaart, Mattson et al.) | Van der Wijngaart & Mattson, *The Parallel Research Kernels: A tool for architecture and programming system investigation*, IEEE HPEC (2014) |
| **Athena++** | https://github.com/PrincetonUniversity/athena | Princeton University (Stone, Tomida, White, Felker, Beckwith) | Doi: 10.5281/zenodo.11660592 — Stone et al., *The Athena++ Adaptive Mesh Refinement Framework*, ApJS (2020) |
| **SPARTA** | https://github.com/sandialabs/sparta | Sandia National Laboratories (Plimpton, Gallis et al.) | Plimpton & Gallis, *SPARTA Direct Simulation Monte Carlo (DSMC) Simulator*, GPL |
| **OpenLB** | https://gitlab.com/openlb/release (also https://www.openlb.net) | OpenLB Consortium, Karlsruhe Institute of Technology (Krause, Kummerländer et al.) | Krause et al., *OpenLB — Open source lattice Boltzmann code*, Comp. Math. Appl. (2021) |
| **Smilei** | https://github.com/SmileiPIC/Smilei | Smilei collaboration, École Polytechnique / CNRS / CEA | Derouillat, Beck, Pérez, Vinci et al., *Smilei: A collaborative, open-source, multi-purpose particle-in-cell code*, Comp. Phys. Comm. (2018) |
| **LAMMPS** | https://github.com/lammps/lammps (ref: `stable_2Aug2023`) | Sandia National Laboratories (Plimpton, Thompson, Trott, Crozier et al.) | Thompson, Aktulga, Berger, Bolintineanu, Brown, Crozier et al., *LAMMPS - a flexible simulation tool for particle-based materials modeling at the atomic, meso, and continuum scales*, Comp. Phys. Comm. (2022) |
| **SAMRAI** | https://github.com/LLNL/SAMRAI | Lawrence Livermore National Laboratory (Hornung, Wissink, Kohn) | Hornung, Wissink & Kohn, *Managing complex data and geometry in parallel structured AMR applications*, Eng. Comp. (2006) |
| **ROSS** | https://github.com/ROSS-org/ROSS | ROSS-org, Rensselaer Polytechnic Institute (Carothers, Bauer, Pearce et al.) | Carothers, Bauer & Pearce, *ROSS: A high-performance, low-memory, modular Time Warp system*, J. Par. Distrib. Comput. (2002) |
| **WarpX** | https://github.com/ECP-WarpX/WarpX | ECP/BLAST consortium — Lawrence Berkeley National Laboratory + LLNL + SLAC + LBNL (Vay, Almgren, Lehe, Myers et al.) | Vay, Almgren, Bell, Ge, Grote, Hogan et al., *Warp-X: A new exascale computing platform for beam–plasma simulations*, NIM-A (2018) |
| **QMCPACK** | https://github.com/QMCPACK/qmcpack | QMCPACK collaboration (Argonne, ORNL, Sandia, UIUC; Kim, Kent, Annaberdiyev, Benali et al.) | Kim, Annaberdiyev, Benali, Bennett et al., *QMCPACK: an open source ab initio quantum Monte Carlo package*, J. Phys. Condens. Matter (2018) |
| **Nyx** | https://github.com/AMReX-Astro/Nyx | AMReX-Astro consortium — Lawrence Berkeley National Laboratory + Stony Brook (Almgren, Bell, Lukic, Van Andel) | Doi: 10.5281/zenodo.5059767 + 10.21105/joss.03068 — Almgren et al., *Nyx: A massively parallel AMR code for computational cosmology*, ApJ (2013) |

The `vanillas/<App>/` copies are derived by **stripping the native checkpoint mechanism** out of each upstream tree (per-file edits documented in each app's `vanillas/<App>/prompt.txt`), preserving everything else verbatim.  Run `scripts/install_app_sources.sh` to re-fetch any subset.

> **Build wrappers** (a `CMakeLists.txt` for CoMD, a per-rank launcher `mmsp_run.sh` / `run_sst.sh` / `xhpcg_run` / `athena_run.sh` / `warpx_used_inputs` / etc.) **are intentionally added** to vanillas where the upstream build / launch model doesn't fit the validation harness's `mpirun -np N <exe> <args>` shape.  These wrappers are documented per-app under `docs/<App>/README.md`.

---

## Adding a New App

1. Drop the upstream source into `vanillas/<App>/` and write a minimal `app.yaml` (look at any existing one as a template — `vanillas/CoMD/app.yaml` is the simplest).
2. Add the same source plus its native checkpoint/restart code to `checkpointed/<App>/`.
3. Write `docs/<App>/README.md` matching the format of the existing 19 (use [docs/CoMD/README.md](docs/CoMD/README.md) as the canonical template).
4. Optionally write `validation/veloc/benchmark_configs/<App>.json` if you want benchmark scenarios beyond the default.
5. Place the new app in its class — (1) `iterative_fixed`, (2) `iterative_variable`, (3) `iterative_adaptive`, or (4) `asynchronous` — in the taxonomy table here, into the right tier in `validation/veloc/scripts/run_batch.sh`, and into `apps_fast.txt` if it displaces an existing pick.

The validation pipeline auto-discovers any directory containing `app.yaml`, so steps 1–2 are sufficient to make the app runnable; the rest are presentation.
