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
   stub keeps the WriteRestart symbol so existing references (e.g.
   Output::restart of type WriteRestart*) still link, but every member
   function is a no-op or an error.  The CommandStyle macro has also been
   removed from the header, so `write_restart` is no longer a valid LAMMPS
   command.
------------------------------------------------------------------------- */

#include "write_restart.h"

#include "error.h"

using namespace LAMMPS_NS;

WriteRestart::WriteRestart(LAMMPS *lmp) : Command(lmp) {}

void WriteRestart::command(int /*narg*/, char ** /*arg*/)
{
  error->all(FLERR,
             "write_restart command is disabled in this vanilla build "
             "(native checkpoint/restart support has been removed)");
}

void WriteRestart::multiproc_options(int /*multiproc_caller*/,
                                     int /*mpiioflag_caller*/,
                                     int /*narg*/,
                                     char ** /*arg*/)
{
  // no-op
}

void WriteRestart::write(const std::string & /*file*/)
{
  // no-op: native restart writing has been removed in this vanilla build
}
