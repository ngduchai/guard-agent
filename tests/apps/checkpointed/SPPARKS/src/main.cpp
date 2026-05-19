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
#include "app_lattice.h"
#include <cstdio>

using namespace SPPARKS_NS;

/* SPPARKS validation signature dumper (Step 0 v8: file-based comparison).
 *
 * Writes 6 raw doubles (48 bytes) to "validation_output.bin" in CWD on rank 0.
 * Byte layout MUST be identical between vanilla and reference at the same
 * workload so Step 0.6c cross-consistency passes.
 *
 * SCHEMA REDESIGN (2026-05-19 v3, was v2 = commit 3fe21a916):
 * v2 captured per-site spin sums via iarray[0].  In the Ising-model
 * validation input at T=1.0 (below 2D Ising Tc ~1.13), the system orders
 * into one of two symmetric phases; ±2% temperature perturbation around T=1.0
 * doesn't change which phase dominates, so total spin sum is INVARIANT and
 * Step B calibration reported diff=0.0.
 *
 * v3 captures KMC dynamics counters (naccept, nattempt) from AppLattice
 * subclass.  These directly track accept/reject rates which depend on
 * temperature via the Metropolis criterion exp(-ΔE/T) — small T perturbations
 * produce measurable changes in accept counts.  Keeps a spatial moment
 * sum(spin[i] * i) for sensitivity to spatial reorganization.  Schema:
 *   [0] global naccept                                (KMC accept count, T-sensitive)
 *   [1] global nattempt                               (KMC attempt count)
 *   [2] global sum of iarray[0][i] * (i + 1)          (spatial moment; rearrangement-sensitive)
 *   [3] global sum of iarray[0][i]                    (kept from v2 as baseline marker)
 *   [4] app->time                                     (final-time marker)
 *   [5] (double)world_size                            (decomposition sanity)
 *
 * AppLattice downcast: safe because all SPPARKS lattice-based apps (Ising,
 * Potts, Diffusion) derive from AppLattice.  Falls back to v2 behavior
 * (naccept=nattempt=0) if downcast fails (non-lattice apps).
 *
 * Local sums via loop over iarray[0][0..nlocal-1].  Global sums via
 * MPI_Reduce(MPI_SUM).  Rank-root-only file write.
 */
static void dumpValidationSignatureBin_spparks(SPPARKS *spk) {
  int rank, size;
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Comm_size(MPI_COMM_WORLD, &size);

  int nlocal = spk->app->nlocal;
  // local_sums layout: [naccept, nattempt, spatial_moment, spin_sum, nlocal]
  double local_sums[5] = {0.0, 0.0, 0.0, 0.0, 0.0};

  // Per-site integer state sums + spatial moment (rearrangement-sensitive)
  if (spk->app->ninteger >= 1 && spk->app->iarray != nullptr
      && spk->app->iarray[0] != nullptr) {
    int *iarr = spk->app->iarray[0];
    for (int i = 0; i < nlocal; i++) {
      double v = (double)iarr[i];
      local_sums[2] += v * (double)(i + 1);   // spatial moment
      local_sums[3] += v;                      // simple sum (kept from v2)
    }
  }

  // KMC counters via AppLattice downcast (T-sensitive via Metropolis criterion)
  AppLattice *al = dynamic_cast<AppLattice*>(spk->app);
  if (al != nullptr) {
    local_sums[0] = (double)al->naccept;
    local_sums[1] = (double)al->nattempt;
  }

  local_sums[4] = (double)nlocal;

  double global_sums[5];
  MPI_Reduce(local_sums, global_sums, 5, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

  if (rank != 0) return;

  double buf[6];
  buf[0] = global_sums[0];               // global naccept
  buf[1] = global_sums[1];               // global nattempt
  buf[2] = global_sums[2];               // global spatial moment
  buf[3] = global_sums[3];               // global spin sum
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
