#ifndef HPCG_CKPT_HPP
#define HPCG_CKPT_HPP

#include <vector>

/* Per-rank POSIX file checkpoint of the timed CG-sets loop in main.cpp.
   Restart resumes at the next CG set after the saved index, restoring the
   accumulated `times[10]` array and the per-set scaled residual history that
   feeds TestNorms.  Checkpoint is rejected if the geometry/iteration
   parameters disagree between save and load (e.g. machine produced a
   different numberOfCgSets), in which case the run starts from scratch. */

bool hpcg_ckpt_load(int rank, int numberOfCgSets, int optMaxIters,
                    double optTolerance, int *i_out,
                    double *times, std::vector<double> &values);

void hpcg_ckpt_save(int rank, int numberOfCgSets, int optMaxIters,
                    double optTolerance, int i, const double *times,
                    const std::vector<double> &values);

int hpcg_ckpt_every(); /* env CKPT_EVERY, default 5 */

#endif
