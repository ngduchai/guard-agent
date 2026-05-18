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
#include <cstdio>

using namespace SPARTA_NS;

/* SPARTA validation signature dumper (Step 0 v8: file-based comparison).
 *
 * Writes 6 raw doubles (48 bytes) to "validation_output.bin" in CWD on rank 0.
 * Byte layout MUST be identical between vanilla and reference at the same
 * workload so Step 0.6c cross-consistency passes:
 *   [0] global nparticles (MPI_SUM of particle->nlocal across ranks)
 *   [1] (double)update->ntimestep                   (final timestep)
 *   [2] update->dt                                  (timestep size)
 *   [3] (double)update->ntimestep * update->dt      (final simulated time)
 *   [4] (double)update->firststep                   (first step of run)
 *   [5] (double)update->laststep                    (last step of run)
 *
 * particle->nlocal is per-rank; reduced via MPI_Reduce(MPI_SUM) onto rank 0.
 * The other Update fields are identical on every rank.
 */
static void dumpValidationSignatureBin_sparta(SPARTA *sparta) {
  int rank;
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);

  long long local_n = (long long)sparta->particle->nlocal;
  long long global_n = 0;
  MPI_Reduce(&local_n, &global_n, 1, MPI_LONG_LONG, MPI_SUM, 0, MPI_COMM_WORLD);

  if (rank != 0) return;

  double buf[6];
  buf[0] = (double)global_n;
  buf[1] = (double)sparta->update->ntimestep;
  buf[2] = sparta->update->dt;
  buf[3] = (double)sparta->update->ntimestep * sparta->update->dt;
  buf[4] = (double)sparta->update->firststep;
  buf[5] = (double)sparta->update->laststep;

  FILE* f = std::fopen("validation_output.bin", "wb");
  if (f) {
    std::fwrite(buf, sizeof(double), 6, f);
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
