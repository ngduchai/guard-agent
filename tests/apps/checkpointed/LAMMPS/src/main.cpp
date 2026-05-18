/* ----------------------------------------------------------------------
   LAMMPS - Large-scale Atomic/Molecular Massively Parallel Simulator
   https://www.lammps.org/, Sandia National Laboratories
   LAMMPS development team: developers@lammps.org

   Copyright (2003) Sandia Corporation.  Under the terms of Contract
   DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains
   certain rights in this software.  This software is distributed under
   the GNU General Public License.

   See the README file in the top-level LAMMPS directory.
------------------------------------------------------------------------- */

#include "lammps.h"

#include "input.h"
#include "library.h"
#include "atom.h"
#include "update.h"

#if defined(LAMMPS_EXCEPTIONS)
#include "exceptions.h"
#endif

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <mpi.h>

#if defined(LAMMPS_TRAP_FPE) && defined(_GNU_SOURCE)
#include <fenv.h>
#endif

// import MolSSI Driver Interface library
#if defined(LMP_MDI)
#include <mdi.h>
#endif

using namespace LAMMPS_NS;

// for convenience
static void finalize()
{
  lammps_kokkos_finalize();
  lammps_python_finalize();
}

/* LAMMPS validation signature dumper (Step 0 v8: file-based comparison).
 *
 * Writes 6 raw doubles (48 bytes) to "validation_output.bin" in CWD on rank 0.
 * Byte layout MUST be identical between vanilla and reference at the same
 * workload so Step 0.6c cross-consistency passes.
 *
 * SCHEMA REDESIGN (2026-05-18 v2, was v1 = commit 1249d9b76): v1 captured
 * only seed-INVARIANT counts/timesteps (natoms, nlocal, ntimestep, dt,
 * world_size).  The perturbation knob for LAMMPS is the velocity seed which
 * only affects initial atom velocities and resulting equilibrium configs,
 * NOT counts or timestep counts.  v1 calibration would fail.  v2 captures
 * per-atom-state sums via MPI_Reduce so the signature reacts to seed
 * changes:
 *   [0] global sum of |x[i][0]|  (x positions)
 *   [1] global sum of |x[i][1]|  (y positions)
 *   [2] global sum of |x[i][2]|  (z positions)
 *   [3] global sum of |v[i][0]|  (x velocities)
 *   [4] global sum of |v[i][1]|  (y velocities)
 *   [5] global sum of |v[i][2]|  (z velocities)
 *
 * Local sums computed by walking atom->x[0..nlocal-1] and atom->v[...].
 * Global sums via MPI_Reduce(MPI_SUM).  Absolute values used so positions
 * in symmetric domains don't cancel.  Rank-root-only file write.
 */
static void dumpValidationSignatureBin_lammps(LAMMPS *lammps, MPI_Comm comm)
{
  int rank;
  MPI_Comm_rank(comm, &rank);

  double **x = lammps->atom->x;
  double **v = lammps->atom->v;
  int nlocal = lammps->atom->nlocal;
  double local_sums[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
  for (int i = 0; i < nlocal; i++) {
    local_sums[0] += std::abs(x[i][0]);
    local_sums[1] += std::abs(x[i][1]);
    local_sums[2] += std::abs(x[i][2]);
    local_sums[3] += std::abs(v[i][0]);
    local_sums[4] += std::abs(v[i][1]);
    local_sums[5] += std::abs(v[i][2]);
  }
  double global_sums[6];
  MPI_Reduce(local_sums, global_sums, 6, MPI_DOUBLE, MPI_SUM, 0, comm);

  if (rank != 0) return;

  FILE* f = std::fopen("validation_output.bin", "wb");
  if (f) {
    std::fwrite(global_sums, sizeof(double), 6, f);
    std::fclose(f);
  }
}

/* ----------------------------------------------------------------------
   main program to drive LAMMPS
------------------------------------------------------------------------- */

int main(int argc, char **argv)
{
  MPI_Init(&argc, &argv);
  MPI_Comm lammps_comm = MPI_COMM_WORLD;

#if defined(LMP_MDI)
  // initialize MDI interface, if compiled in

  int mdi_flag;
  if (MDI_Init(&argc, &argv)) MPI_Abort(MPI_COMM_WORLD, 1);
  if (MDI_Initialized(&mdi_flag)) MPI_Abort(MPI_COMM_WORLD, 1);

  // get the MPI communicator that spans all ranks running LAMMPS
  // when using MDI, this may be a subset of MPI_COMM_WORLD

  if (mdi_flag)
    if (MDI_MPI_get_world_comm(&lammps_comm)) MPI_Abort(MPI_COMM_WORLD, 1);
#endif

#if defined(LAMMPS_TRAP_FPE) && defined(_GNU_SOURCE)
  // enable trapping selected floating point exceptions.
  // this uses GNU extensions and is only tested on Linux
  // therefore we make it depend on -D_GNU_SOURCE, too.
  fesetenv(FE_NOMASK_ENV);
  fedisableexcept(FE_ALL_EXCEPT);
  feenableexcept(FE_DIVBYZERO);
  feenableexcept(FE_INVALID);
  feenableexcept(FE_OVERFLOW);
#endif

#ifdef LAMMPS_EXCEPTIONS
  try {
    auto lammps = new LAMMPS(argc, argv, lammps_comm);
    lammps->input->file();
    /* Step 0 v8: emit binary validation signature for file-based comparison.
     * Must be called after input->file() (simulation done) and before
     * delete lammps (atom/update members still valid).
     */
    dumpValidationSignatureBin_lammps(lammps, lammps_comm);
    delete lammps;
  } catch (LAMMPSAbortException &ae) {
    finalize();
    MPI_Abort(ae.universe, 1);
  } catch (LAMMPSException &) {
    finalize();
    MPI_Barrier(lammps_comm);
    MPI_Finalize();
    exit(1);
  } catch (fmt::format_error &fe) {
    fprintf(stderr, "fmt::format_error: %s\n", fe.what());
    finalize();
    MPI_Abort(MPI_COMM_WORLD, 1);
    exit(1);
  } catch (std::exception &e) {
    fprintf(stderr, "Exception: %s\n", e.what());
    finalize();
    MPI_Abort(MPI_COMM_WORLD, 1);
    exit(1);
  }
#else
  try {
    auto lammps = new LAMMPS(argc, argv, lammps_comm);
    lammps->input->file();
    /* Step 0 v8: emit binary validation signature for file-based comparison.
     * Must be called after input->file() (simulation done) and before
     * delete lammps (atom/update members still valid).
     */
    dumpValidationSignatureBin_lammps(lammps, lammps_comm);
    delete lammps;
  } catch (fmt::format_error &fe) {
    fprintf(stderr, "fmt::format_error: %s\n", fe.what());
    finalize();
    MPI_Abort(MPI_COMM_WORLD, 1);
    exit(1);
  }
#endif
  finalize();
  MPI_Barrier(lammps_comm);
  MPI_Finalize();
}
