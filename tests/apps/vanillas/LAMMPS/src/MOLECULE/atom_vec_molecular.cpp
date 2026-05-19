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

#include "atom_vec_molecular.h"
#include "atom.h"

using namespace LAMMPS_NS;

/* ---------------------------------------------------------------------- */

AtomVecMolecular::AtomVecMolecular(LAMMPS *lmp) : AtomVec(lmp)
{
  molecular = Atom::MOLECULAR;
  bonds_allow = angles_allow = dihedrals_allow = impropers_allow = 1;
  mass_type = PER_TYPE;

  atom->molecule_flag = 1;

  // strings with peratom variables to include in each AtomVec method
  // strings cannot contain fields in corresponding AtomVec default strings
  // order of fields in a string does not matter
  // except: fields_data_atom & fields_data_vel must match data file

  // clang-format off
  fields_grow = {"molecule", "num_bond", "bond_type", "bond_atom", "num_angle", "angle_type",
    "angle_atom1", "angle_atom2", "angle_atom3", "num_dihedral", "dihedral_type", "dihedral_atom1",
    "dihedral_atom2", "dihedral_atom3", "dihedral_atom4", "num_improper", "improper_type",
    "improper_atom1", "improper_atom2", "improper_atom3", "improper_atom4", "nspecial", "special"};
  fields_copy = {"molecule", "num_bond", "bond_type", "bond_atom", "num_angle", "angle_type",
    "angle_atom1", "angle_atom2", "angle_atom3", "num_dihedral", "dihedral_type", "dihedral_atom1",
    "dihedral_atom2", "dihedral_atom3", "dihedral_atom4", "num_improper", "improper_type",
    "improper_atom1", "improper_atom2", "improper_atom3", "improper_atom4", "nspecial", "special"};
  fields_border = {"molecule"};
  fields_border_vel = {"molecule"};
  fields_exchange = {"molecule", "num_bond", "bond_type", "bond_atom", "num_angle", "angle_type",
    "angle_atom1", "angle_atom2", "angle_atom3", "num_dihedral", "dihedral_type", "dihedral_atom1",
    "dihedral_atom2", "dihedral_atom3", "dihedral_atom4", "num_improper", "improper_type",
    "improper_atom1", "improper_atom2", "improper_atom3", "improper_atom4", "nspecial", "special"};
  fields_restart = {"molecule", "num_bond", "bond_type", "bond_atom", "num_angle", "angle_type",
    "angle_atom1", "angle_atom2", "angle_atom3", "num_dihedral", "dihedral_type", "dihedral_atom1",
    "dihedral_atom2", "dihedral_atom3", "dihedral_atom4", "num_improper", "improper_type",
    "improper_atom1", "improper_atom2", "improper_atom3", "improper_atom4"};
  fields_create = {"molecule", "num_bond", "num_angle", "num_dihedral", "num_improper", "nspecial"};
  fields_data_atom = {"id", "molecule", "type", "x"};
  fields_data_vel = {"id", "v"};
  // clang-format on

  setup_fields();

  bond_per_atom = angle_per_atom = dihedral_per_atom = improper_per_atom = 0;
  bond_negative = angle_negative = dihedral_negative = improper_negative = nullptr;
}

/* ---------------------------------------------------------------------- */

AtomVecMolecular::~AtomVecMolecular()
{
  delete[] bond_negative;
  delete[] angle_negative;
  delete[] dihedral_negative;
  delete[] improper_negative;
}

/* ----------------------------------------------------------------------
/* ----------------------------------------------------------------------
/* ----------------------------------------------------------------------
/* ----------------------------------------------------------------------
/* ----------------------------------------------------------------------
   modify what AtomVec::data_atom() just unpacked
   or initialize other atom quantities
------------------------------------------------------------------------- */

void AtomVecMolecular::data_atom_post(int ilocal)
{
  num_bond[ilocal] = 0;
  num_angle[ilocal] = 0;
  num_dihedral[ilocal] = 0;
  num_improper[ilocal] = 0;
  nspecial[ilocal][0] = 0;
  nspecial[ilocal][1] = 0;
  nspecial[ilocal][2] = 0;
}
