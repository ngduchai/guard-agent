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

#include "fix_store_global.h"

#include "comm.h"
#include "error.h"
#include "memory.h"

#include <cstring>

using namespace LAMMPS_NS;
using namespace FixConst;

/* ---------------------------------------------------------------------- */

FixStoreGlobal::FixStoreGlobal(LAMMPS *lmp, int narg, char **arg) :
    Fix(lmp, narg, arg), vstore(nullptr), astore(nullptr), rbuf(nullptr)
{
  if (narg != 5) error->all(FLERR, "Illegal fix STORE/GLOBAL command: incorrect number of args");

  // syntax: id group style n1 n2
  //   N2 = 1 is vector, N2 > 1 is array, no tensor allowed (yet)

  vecflag = arrayflag = 0;

  n1 = utils::inumeric(FLERR, arg[3], false, lmp);
  n2 = utils::inumeric(FLERR, arg[4], false, lmp);
  if (n1 <= 0 || n2 <= 0)
    error->all(FLERR, "Illegal fix STORE/GLOBAL dimension args: must be >0: {} {}", n1, n2);
  if (n2 == 1)
    vecflag = 1;
  else
    arrayflag = 1;
  nrow = n1;
  ncol = n2;

  vstore = nullptr;
  astore = nullptr;


  if (vecflag)
    memory->create(vstore, n1, "fix/store:vstore");
  else if (arrayflag)
    memory->create(astore, n1, n2, "fix/store:astore");
  memory->create(rbuf, n1 * n2 + 2, "fix/store:rbuf");

  // zero the storage

  if (vecflag) {
    for (int i = 0; i < n1; i++) vstore[i] = 0.0;
  } else if (arrayflag) {
    for (int i = 0; i < n1; i++)
      for (int j = 0; j < n2; j++) astore[i][j] = 0.0;
  }
}

/* ---------------------------------------------------------------------- */

FixStoreGlobal::~FixStoreGlobal()
{
  memory->destroy(vstore);
  memory->destroy(astore);
  memory->destroy(rbuf);
}

/* ---------------------------------------------------------------------- */

int FixStoreGlobal::setmask()
{
  int mask = 0;
  return mask;
}

/* ----------------------------------------------------------------------
   reset size of global vector/array
   invoked by caller if size is unknown at time this fix is instantiated
   caller will do subsequent initialization
------------------------------------------------------------------------- */

void FixStoreGlobal::reset_global(int n1_caller, int n2_caller)
{
  memory->destroy(vstore);
  memory->destroy(astore);
  memory->destroy(rbuf);
  vstore = nullptr;
  astore = nullptr;

  vecflag = arrayflag = 0;
  if (n2_caller == 1)
    vecflag = 1;
  else
    arrayflag = 1;

  n1 = n1_caller;
  n2 = n2_caller;
  if (vecflag)
    memory->create(vstore, n1, "fix/store:vstore");
  else if (arrayflag)
    memory->create(astore, n1, n2, "fix/store:astore");
  memory->create(rbuf, n1 * n2 + 2, "fix/store:rbuf");
}

/* ----------------------------------------------------------------------
   memory usage of global data
------------------------------------------------------------------------- */

double FixStoreGlobal::memory_usage()
{
  return (double) n1 * n2 * sizeof(double);
}
