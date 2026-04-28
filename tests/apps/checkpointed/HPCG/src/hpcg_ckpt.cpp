#include "hpcg_ckpt.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define HPCG_CKPT_MAGIC 0x48504347 /* 'HPCG' */

static const char *ckpt_dir() {
  const char *d = getenv("CHKPT_DIR");
  return (d && *d) ? d : "checkpoints";
}

int hpcg_ckpt_every() {
  const char *e = getenv("CKPT_EVERY");
  if (!e || !*e) return 5;
  int v = atoi(e);
  return v > 0 ? v : 5;
}

static void ckpt_path(char *buf, size_t n, int rank) {
  snprintf(buf, n, "%s/hpcg_ckpt.%04d", ckpt_dir(), rank);
}

bool hpcg_ckpt_load(int rank, int numberOfCgSets, int optMaxIters,
                    double /*optTolerance*/, int *i_out, double *times,
                    std::vector<double> &values) {
  char path[512];
  ckpt_path(path, sizeof(path), rank);
  FILE *f = fopen(path, "rb");
  if (!f) return false;

  int magic = 0, n = 0, mi = 0, i = -1, nv = 0;
  double tol = 0.0;
  bool ok = (fread(&magic, sizeof(int), 1, f) == 1) &&
            (fread(&n, sizeof(int), 1, f) == 1) &&
            (fread(&mi, sizeof(int), 1, f) == 1) &&
            (fread(&tol, sizeof(double), 1, f) == 1) &&
            (fread(&i, sizeof(int), 1, f) == 1);
  if (!ok || magic != HPCG_CKPT_MAGIC || n != numberOfCgSets ||
      mi != optMaxIters) {
    fclose(f);
    return false;
  }
  if (fread(times, sizeof(double), 10, f) != 10) {
    fclose(f);
    return false;
  }
  if (fread(&nv, sizeof(int), 1, f) != 1 || nv != numberOfCgSets) {
    fclose(f);
    return false;
  }
  values.resize(static_cast<size_t>(nv));
  if (static_cast<int>(fread(values.data(), sizeof(double), nv, f)) != nv) {
    fclose(f);
    return false;
  }
  fclose(f);
  *i_out = i;
  return true;
}

void hpcg_ckpt_save(int rank, int numberOfCgSets, int optMaxIters,
                    double optTolerance, int i, const double *times,
                    const std::vector<double> &values) {
  mkdir(ckpt_dir(), 0755);
  char path[512], tmp[576];
  ckpt_path(path, sizeof(path), rank);
  snprintf(tmp, sizeof(tmp), "%s.tmp", path);

  FILE *f = fopen(tmp, "wb");
  if (!f) return;
  int magic = HPCG_CKPT_MAGIC;
  fwrite(&magic, sizeof(int), 1, f);
  fwrite(&numberOfCgSets, sizeof(int), 1, f);
  fwrite(&optMaxIters, sizeof(int), 1, f);
  fwrite(&optTolerance, sizeof(double), 1, f);
  fwrite(&i, sizeof(int), 1, f);
  fwrite(times, sizeof(double), 10, f);
  int nv = static_cast<int>(values.size());
  fwrite(&nv, sizeof(int), 1, f);
  if (nv > 0) fwrite(values.data(), sizeof(double), nv, f);
  fflush(f);
  fclose(f);
  rename(tmp, path);
}
