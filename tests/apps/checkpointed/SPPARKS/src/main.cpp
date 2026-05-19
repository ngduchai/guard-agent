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
 * SCHEMA REDESIGN (2026-05-19 v3-fixed, was v3-broken = commit d76349a61):
 * v3-broken attempted to access AppLattice::naccept/nattempt via dynamic_cast,
 * but those members are `protected:` in AppLattice (line 92 of app_lattice.h)
 * and not reachable from outside the class — BUILD FAIL.
 *
 * v3-fixed drops the AppLattice access entirely and relies on TWO spatial
 * moments computed from iarray[0] (which IS publicly accessible via App).
 * The first moment captures gross spatial distribution; the second moment
 * (sum of i*i*spin) is much more sensitive to which specific sites have
 * which spin — small KMC rearrangements that don't change total spin sum
 * still move the second moment substantially.
 *
 * Schema layout:
 *   [0] global sum(spin[i] * (i+1))         (first spatial moment)
 *   [1] global sum(spin[i] * (i+1)^2)       (second spatial moment; high sensitivity)
 *   [2] global sum(spin[i] * (i+1)^3)       (third moment; even higher amplitude)
 *   [3] global sum(spin[i])                  (bulk spin sum; kept as baseline marker)
 *   [4] app->time                            (final time marker)
 *   [5] (double)world_size                   (decomposition sanity)
 *
 * Site indices are rank-local (0..nlocal-1); ranks with different spatial
 * configurations produce different moments.  Temperature perturbation changes
 * KMC accept/reject rates → different final lattice config → different moments.
 *
 * Local sums via loop over iarray[0][0..nlocal-1].  Global sums via
 * MPI_Reduce(MPI_SUM).  Rank-root-only file write.
 */
static void dumpValidationSignatureBin_spparks(SPPARKS *spk) {
  int rank, size;
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Comm_size(MPI_COMM_WORLD, &size);

  int nlocal = spk->app->nlocal;
  // local_sums layout: [moment1, moment2, moment3, sum, nlocal]
  double local_sums[5] = {0.0, 0.0, 0.0, 0.0, 0.0};

  // Three spatial moments + bulk sum from per-site integer state
  if (spk->app->ninteger >= 1 && spk->app->iarray != nullptr
      && spk->app->iarray[0] != nullptr) {
    int *iarr = spk->app->iarray[0];
    for (int i = 0; i < nlocal; i++) {
      double v = (double)iarr[i];
      double idx = (double)(i + 1);
      local_sums[0] += v * idx;              // 1st moment
      local_sums[1] += v * idx * idx;        // 2nd moment
      local_sums[2] += v * idx * idx * idx;  // 3rd moment
      local_sums[3] += v;                     // bulk sum
    }
  }
  local_sums[4] = (double)nlocal;

  double global_sums[5];
  MPI_Reduce(local_sums, global_sums, 5, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

  if (rank != 0) return;

  double buf[6];
  buf[0] = global_sums[0];               // global 1st spatial moment
  buf[1] = global_sums[1];               // global 2nd spatial moment
  buf[2] = global_sums[2];               // global 3rd spatial moment
  buf[3] = global_sums[3];               // global bulk sum
  buf[4] = spk->app->time;               // final time
  buf[5] = (double)size;                 // world size

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
