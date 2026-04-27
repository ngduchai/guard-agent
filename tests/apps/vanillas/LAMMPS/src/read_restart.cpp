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

/* ----------------------------------------------------------------------
   Vanilla build: native checkpoint/restart code has been stripped.  This
   stub keeps the ReadRestart symbol so dependent translation units still
   link, but the command body always errors out and the CommandStyle macro
   has been removed from the header.
------------------------------------------------------------------------- */

#include "read_restart.h"

#include "error.h"

using namespace LAMMPS_NS;

ReadRestart::ReadRestart(LAMMPS *lmp) : Command(lmp) {}

void ReadRestart::command(int /*narg*/, char ** /*arg*/)
{
  error->all(FLERR,
             "read_restart command is disabled in this vanilla build "
             "(native checkpoint/restart support has been removed)");
}
