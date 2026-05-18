/* ----------------------------------------------------------------------
   SPARTA - Stochastic PArallel Rarefied-gas Time-accurate Analyzer
   http://sparta.github.io
   Steve Plimpton, sjplimp@gmail.com, Michael Gallis, magalli@sandia.gov
   Sandia National Laboratories

   Copyright (2014) Sandia Corporation.  Under the terms of Contract
   DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains
   certain rights in this software.  This software is distributed under
   the GNU General Public License.

   See the README file in the top-level SPARTA directory.
------------------------------------------------------------------------- */

#include "mpi.h"
#include "sparta.h"
#include "input.h"
#include "particle.h"
#include "update.h"
#include <cmath>
#include <cstdio>

using namespace SPARTA_NS;

/* SPARTA validation signature dumper (Step 0 v8: file-based comparison).
 *
 * Writes 6 raw doubles (48 bytes) to "validation_output.bin" in CWD on rank 0.
 * Byte layout MUST be identical between vanilla and reference at the same
 * workload so Step 0.6c cross-consistency passes.
 *
 * SCHEMA REDESIGN (2026-05-18 v2, was v1 = commit 2980e5f20): v1 captured
 * only seed-INVARIANT counts/timesteps (nparticles, ntimestep, dt, firststep,
 * laststep).  The perturbation knob for SPARTA is the RNG seed which only
 * affects particle positions/velocities/states, NOT counts.  v1 calibration
 * would fail.  v2 captures per-particle-state sums via MPI_Reduce so the
 * signature reacts to seed changes:
 *   [0] global sum of |x[0]|  (x positions)
 *   [1] global sum of |x[1]|  (y positions)
 *   [2] global sum of |x[2]|  (z positions)
 *   [3] global sum of |v[0]|  (x velocities)
 *   [4] global sum of |v[1]|  (y velocities)
 *   [5] global sum of |v[2]|  (z velocities)
 *
 * Local sums computed by walking particle->particles[0..nlocal-1].  Global
 * sums via MPI_Reduce(MPI_SUM).  Absolute values used so positions in
 * symmetric domains don't cancel.  Rank-root-only file write.
 */
static void dumpValidationSignatureBin_sparta(SPARTA *sparta) {
  int rank;
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);

  Particle::OnePart *parts = sparta->particle->particles;
  int nlocal = sparta->particle->nlocal;
  double local_sums[6] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
  for (int i = 0; i < nlocal; i++) {
    local_sums[0] += std::abs(parts[i].x[0]);
    local_sums[1] += std::abs(parts[i].x[1]);
    local_sums[2] += std::abs(parts[i].x[2]);
    local_sums[3] += std::abs(parts[i].v[0]);
    local_sums[4] += std::abs(parts[i].v[1]);
    local_sums[5] += std::abs(parts[i].v[2]);
  }
  double global_sums[6];
  MPI_Reduce(local_sums, global_sums, 6, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

  if (rank != 0) return;

  FILE* f = std::fopen("validation_output.bin", "wb");
  if (f) {
    std::fwrite(global_sums, sizeof(double), 6, f);
    std::fclose(f);
  }
}

/* ----------------------------------------------------------------------
   main program to drive SPARTA
------------------------------------------------------------------------- */

int main(int argc, char **argv)
{
  MPI_Init(&argc,&argv);

  SPARTA *sparta = new SPARTA(argc,argv,MPI_COMM_WORLD);
  sparta->input->file();

  /* Step 0 v8: emit binary validation signature for file-based comparison.
   * Must be called after input->file() (simulation done, ntimestep finalised)
   * and before delete sparta (object members still valid).
   */
  dumpValidationSignatureBin_sparta(sparta);

  delete sparta;

  MPI_Finalize();
}
