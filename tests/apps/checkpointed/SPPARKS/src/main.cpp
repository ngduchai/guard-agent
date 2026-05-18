/* ----------------------------------------------------------------------
   SPPARKS - Stochastic Parallel PARticle Kinetic Simulator

   Website
   https://spparks.github.io/

   See authors 
   https://spparks.github.io/authors.html

   Copyright(C) 1999-2025 National Technology & Engineering Solutions
   of Sandia, LLC (NTESS). Under the terms of Contract DE-NA0003525 with
   NTESS, the U.S. Government retains certain rights in this software.

   This software is distributed under the GNU General Public License.  See 
   LICENSE in top-level SPPARKS directory.
------------------------------------------------------------------------- */

#include "mpi.h"
#include "spparks.h"
#include "input.h"
#include "app.h"
#include <cstdio>

using namespace SPPARKS_NS;

/* SPPARKS validation signature dumper (Step 0 v8: file-based comparison).
 *
 * Writes 6 raw doubles (48 bytes) to "validation_output.bin" in CWD on rank 0.
 * Byte layout MUST be identical between vanilla and reference at the same
 * workload so Step 0.6c cross-consistency passes:
 *   [0] global nsites (MPI_SUM of app->nlocal across ranks)
 *   [1] app->time                                   (final simulation time)
 *   [2] (double)rank0_nlocal                        (rank 0's local site count)
 *   [3] (double)world_size                          (number of MPI ranks)
 *   [4] (double)(global_nsites)                     (duplicate for invariance)
 *   [5] (double)world_size * app->time              (combined invariant)
 *
 * app->time is identical on every rank (advanced collectively); app->nlocal is
 * per-rank, reduced via MPI_Reduce(MPI_SUM).  Uses only base-class App fields
 * to remain agnostic of which SPPARKS app subclass is in use (AppLattice,
 * AppPotts, AppDiffusion, etc.).
 */
static void dumpValidationSignatureBin_spparks(SPPARKS *spk) {
  int rank, size;
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Comm_size(MPI_COMM_WORLD, &size);

  long long local_n = (long long)spk->app->nlocal;
  long long global_n = 0;
  MPI_Reduce(&local_n, &global_n, 1, MPI_LONG_LONG, MPI_SUM, 0, MPI_COMM_WORLD);

  long long rank0_n = 0;
  if (rank == 0) rank0_n = local_n;

  if (rank != 0) return;

  double buf[6];
  buf[0] = (double)global_n;
  buf[1] = spk->app->time;
  buf[2] = (double)rank0_n;
  buf[3] = (double)size;
  buf[4] = (double)global_n;
  buf[5] = (double)size * spk->app->time;

  FILE* f = std::fopen("validation_output.bin", "wb");
  if (f) {
    std::fwrite(buf, sizeof(double), 6, f);
    std::fclose(f);
  }
}

/* ----------------------------------------------------------------------
   main program to drive SPPARKS
------------------------------------------------------------------------- */

int main(int argc, char **argv)
{
  MPI_Init(&argc,&argv);

  SPPARKS *spk = new SPPARKS(argc,argv,MPI_COMM_WORLD);
  spk->input->file();

  /* Step 0 v8: emit binary validation signature for file-based comparison.
   * Must be called after input->file() (simulation done, app->time finalised
   * and app->nlocal stable) and before delete spk (object members still valid).
   */
  if (spk->app) {
    dumpValidationSignatureBin_spparks(spk);
  }

  delete spk;

  MPI_Finalize();
}
