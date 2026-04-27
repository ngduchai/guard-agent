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
   removed.  Only a minimal type-stub remains so that pre-existing references
   in Output (and other places that own a `WriteRestart *`) still compile.
   The CommandStyle(write_restart, WriteRestart) registration has been
   stripped, so users cannot invoke it from an input script either.
------------------------------------------------------------------------- */

#ifdef COMMAND_CLASS
// CommandStyle(write_restart,WriteRestart) was here; intentionally removed.
#else

#ifndef LMP_WRITE_RESTART_H
#define LMP_WRITE_RESTART_H

#include "command.h"

namespace LAMMPS_NS {

class WriteRestart : public Command {
 public:
  WriteRestart(class LAMMPS *);
  void command(int, char **) override;
  void multiproc_options(int, int, int, char **);
  void write(const std::string &);
};

}    // namespace LAMMPS_NS

#endif
#endif
