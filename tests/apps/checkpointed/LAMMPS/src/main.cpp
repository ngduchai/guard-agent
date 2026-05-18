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
 * workload so Step 0.6c cross-consistency passes:
 *   [0] (double)atom->natoms                        (total atoms, globally consistent)
 *   [1] (double)atom->nlocal                        (rank 0's local atom count)
 *   [2] (double)update->ntimestep                   (final timestep)
 *   [3] update->dt                                  (timestep size)
 *   [4] (double)update->ntimestep * update->dt      (final simulated time)
 *   [5] (double)world_size                          (number of MPI ranks)
 *
 * atom->natoms is a globally consistent count (LAMMPS maintains it via
 * MPI_Allreduce internally).  atom->nlocal is per-rank; we capture rank 0's
 * value as a distribution-sanity check.  update->ntimestep and dt are
 * identical on every rank.  Rank-root-only.
 */
static void dumpValidationSignatureBin_lammps(LAMMPS *lammps, MPI_Comm comm)
{
  int rank, size;
  MPI_Comm_rank(comm, &rank);
  MPI_Comm_size(comm, &size);
  if (rank != 0) return;
  double buf[6];
  buf[0] = (double)lammps->atom->natoms;
  buf[1] = (double)lammps->atom->nlocal;
  buf[2] = (double)lammps->update->ntimestep;
  buf[3] = lammps->update->dt;
  buf[4] = (double)lammps->update->ntimestep * lammps->update->dt;
  buf[5] = (double)size;
  FILE* f = std::fopen("validation_output.bin", "wb");
  if (f) {
    std::fwrite(buf, sizeof(double), 6, f);
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
