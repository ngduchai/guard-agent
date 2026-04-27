/* -*- c++ -*- ----------------------------------------------------------
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
   This vanilla build has had its native checkpoint/restart implementation
   removed.  Only a minimal type-stub remains; the CommandStyle macro that
   would register `read_restart` as an input-script command has been
   stripped.
------------------------------------------------------------------------- */

#ifdef COMMAND_CLASS
// CommandStyle(read_restart,ReadRestart) was here; intentionally removed.
#else

#ifndef LMP_READ_RESTART_H
#define LMP_READ_RESTART_H

#include "command.h"

namespace LAMMPS_NS {

class ReadRestart : public Command {
 public:
  ReadRestart(class LAMMPS *);
  void command(int, char **) override;
};

}    // namespace LAMMPS_NS

#endif
#endif
