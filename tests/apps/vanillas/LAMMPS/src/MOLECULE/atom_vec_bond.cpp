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

#include "atom_vec_bond.h"
#include "atom.h"

using namespace LAMMPS_NS;

/* ---------------------------------------------------------------------- */

AtomVecBond::AtomVecBond(LAMMPS *lmp) : AtomVec(lmp)
{
  molecular = Atom::MOLECULAR;
  bonds_allow = 1;
  mass_type = PER_TYPE;

  atom->molecule_flag = 1;

  // strings with peratom variables to include in each AtomVec method
  // strings cannot contain fields in corresponding AtomVec default strings
  // order of fields in a string does not matter
  // except: fields_data_atom & fields_data_vel must match data file

  fields_grow = {"molecule", "num_bond", "bond_type", "bond_atom", "nspecial", "special"};
  fields_copy = {"molecule", "num_bond", "bond_type", "bond_atom", "nspecial", "special"};
  fields_border = {"molecule"};
  fields_border_vel = {"molecule"};
  fields_exchange = {"molecule", "num_bond", "bond_type", "bond_atom", "nspecial", "special"};
  fields_restart = {"molecule", "num_bond", "bond_type", "bond_atom"};
  fields_create = {"molecule", "num_bond", "nspecial"};
  fields_data_atom = {"id", "molecule", "type", "x"};
  fields_data_vel = {"id", "v"};

  setup_fields();

  bond_per_atom = 0;
  bond_negative = nullptr;
}

/* ---------------------------------------------------------------------- */

AtomVecBond::~AtomVecBond()
{
  delete[] bond_negative;
}

/* ----------------------------------------------------------------------
/* ----------------------------------------------------------------------
/* ----------------------------------------------------------------------
/* ----------------------------------------------------------------------
/* ----------------------------------------------------------------------
   modify what AtomVec::data_atom() just unpacked
   or initialize other atom quantities
------------------------------------------------------------------------- */

void AtomVecBond::data_atom_post(int ilocal)
{
  num_bond[ilocal] = 0;
  nspecial[ilocal][0] = 0;
  nspecial[ilocal][1] = 0;
  nspecial[ilocal][2] = 0;
}
