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
 * workload so Step 0.6c cross-consistency passes.
 *
 * SCHEMA REDESIGN (2026-05-18 v2, was v1 = commit aae27dc64): v1 captured
 * temperature-INVARIANT counts (nsites, world_size) and app->time which is
 * FIXED by the `run UNTIL time=18800` command in the validation input.  All
 * 6 v1 fields would be perturbation-invariant -> Step B calibration FAIL.
 *
 * v2 captures per-site state aggregates via MPI_Reduce so the signature
 * reacts to temperature changes (KMC accept/reject rates depend on T,
 * producing different final lattice configurations):
 *   [0] global sum of iarray[0][i]    (integer state, e.g. Ising spins)
 *   [1] global sum of iarray[0][i]^2  (state variance amplitude)
 *   [2] global sum of darray[0][i]    (double state, if ndouble>0; else 0)
 *   [3] app->time                     (kept as final-time marker; fixed for
 *                                      `run until time=N` inputs but informative)
 *   [4] (double)global_nsites         (sanity check)
 *   [5] (double)world_size            (decomposition sanity)
 *
 * Defensive: ninteger >= 1 expected (lattice apps have at least one int
 * per site); ndouble may be 0 (skipped if so).  Local sums over
 * iarray[0][0..nlocal-1] and darray[0][0..nlocal-1].  Global sums via
 * MPI_Reduce(MPI_SUM).  Rank-root-only file write.
 */
static void dumpValidationSignatureBin_spparks(SPPARKS *spk) {
  int rank, size;
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Comm_size(MPI_COMM_WORLD, &size);

  int nlocal = spk->app->nlocal;
  double local_sums[5] = {0.0, 0.0, 0.0, 0.0, 0.0};

  // Per-site integer state sums (most lattice apps use iarray[0])
  if (spk->app->ninteger >= 1 && spk->app->iarray != nullptr
      && spk->app->iarray[0] != nullptr) {
    int *iarr = spk->app->iarray[0];
    for (int i = 0; i < nlocal; i++) {
      double v = (double)iarr[i];
      local_sums[0] += v;
      local_sums[1] += v * v;
    }
  }
  // Per-site double state sum (if app has continuous per-site values)
  if (spk->app->ndouble >= 1 && spk->app->darray != nullptr
      && spk->app->darray[0] != nullptr) {
    double *darr = spk->app->darray[0];
    for (int i = 0; i < nlocal; i++) {
      local_sums[2] += darr[i];
    }
  }
  local_sums[3] = (double)nlocal;  // for global nsites computation

  double global_sums[5];
  MPI_Reduce(local_sums, global_sums, 5, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

  if (rank != 0) return;

  double buf[6];
  buf[0] = global_sums[0];
  buf[1] = global_sums[1];
  buf[2] = global_sums[2];
  buf[3] = spk->app->time;
  buf[4] = global_sums[3];  // = global nsites
  buf[5] = (double)size;

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
