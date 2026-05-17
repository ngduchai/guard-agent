/*************************************************************************
 *
 * This file is part of the SAMRAI distribution.  For full copyright
 * information, see COPYRIGHT and LICENSE.
 *
 * Copyright:     (c) 1997-2026 Lawrence Livermore National Security, LLC
 * Description:   Patch container class for patch data objects
 *
 ************************************************************************/
#include "SAMRAI/hier/Patch.h"

#include <typeinfo>
#include <string>

namespace SAMRAI {
namespace hier {

const int Patch::HIER_PATCH_VERSION = 2;

/*
 *************************************************************************
 *
 * Allocate a patch container but do not instantiate any components.
 *
 *************************************************************************
 */

Patch::Patch(
   const Box& box,
   const std::shared_ptr<PatchDescriptor>& descriptor):
   d_box(box),
   d_descriptor(descriptor),
   d_patch_data(d_descriptor->getMaxNumberRegisteredComponents()),
   d_patch_level_number(-1),
   d_patch_in_hierarchy(false)
{
   TBOX_ASSERT(box.getLocalId() >= 0);
}

/*
 *************************************************************************
 *
 * The virtual destructor does nothing; all memory deallocation is
 * managed automatically by the pointer and array classes.
 *
 *************************************************************************
 */

Patch::~Patch()
{
}

/*
 *************************************************************************
 *
 * Calculate the amount of memory space required to allocate the
 * specified component(s).  This information can then be used by a
 * fixed-size memory allocator.
 *
 *************************************************************************
 */

size_t
Patch::getSizeOfPatchData(
   const ComponentSelector& components) const
{
   size_t size = 0;
   const int max_set_component = components.getMaxIndex();

   for (int i = 0; i < max_set_component && components.isSet(i); ++i) {
      size += d_descriptor->getPatchDataFactory(i)->getSizeOfMemory(
            d_box);
   }

   return size;
}

/*
 *************************************************************************
 *
 * Allocate the specified patch data object(s) on the patch.
 *
 *************************************************************************
 */

void
Patch::allocatePatchData(
   const int id,
   const double time)
{
   const int ncomponents = d_descriptor->getMaxNumberRegisteredComponents();

   TBOX_ASSERT((id >= 0) && (id < ncomponents));

   if (ncomponents > static_cast<int>(d_patch_data.size())) {
      d_patch_data.resize(ncomponents);
   }

   if (!checkAllocated(id)) {
      d_patch_data[id] =
         d_descriptor->getPatchDataFactory(id)->allocate(*this);
   }
   d_patch_data[id]->setTime(time);
}

void
Patch::allocatePatchData(
   const ComponentSelector& components,
   const double time)
{
   const int ncomponents = d_descriptor->getMaxNumberRegisteredComponents();
   if (ncomponents > static_cast<int>(d_patch_data.size())) {
      d_patch_data.resize(ncomponents);
   }

   for (int i = 0; i < ncomponents; ++i) {
      if (components.isSet(i)) {
         if (!checkAllocated(i)) {
            d_patch_data[i] =
               d_descriptor->getPatchDataFactory(i)->allocate(*this);
         }
         d_patch_data[i]->setTime(time);
      }
   }
}

/*
 *************************************************************************
 *
 * Deallocate (or set to null) the specified component(s).
 *
 *************************************************************************
 */

void
Patch::deallocatePatchData(
   const ComponentSelector& components)
{
   const int ncomponents = static_cast<int>(d_patch_data.size());
   for (int i = 0; i < ncomponents; ++i) {
      if (components.isSet(i)) {
         d_patch_data[i].reset();
      }
   }
}

/*
 *************************************************************************
 *
 * Set the time stamp for the specified components in the patch.
 *
 *************************************************************************
 */

void
Patch::setTime(
   const double timestamp,
   const ComponentSelector& components)
{
   const int ncomponents = static_cast<int>(d_patch_data.size());
   for (int i = 0; i < ncomponents; ++i) {
      if (components.isSet(i) && d_patch_data[i]) {
         d_patch_data[i]->setTime(timestamp);
      }
   }
}

void
Patch::setTime(
   const double timestamp)
{
   const int ncomponents = static_cast<int>(d_patch_data.size());
   for (int i = 0; i < ncomponents; ++i) {
      if (d_patch_data[i]) {
         d_patch_data[i]->setTime(timestamp);
      }
   }
}

/*
 *************************************************************************
 *
 * Checks that class and restart file version numbers are equal.  If so,
 * reads in data from database and have each patch_data item read
 * itself in from the database
 *
 *************************************************************************
 */

void
Patch::getFromRestart(
   const std::shared_ptr<tbox::Database>& restart_db)
{
   /* Checkpoint/restart API removed in vanilla strip 2026-05-15. */
}

/*
 *************************************************************************
 *
 * Write out the class version number to restart database.  Then,
 * writes out data to restart database and have each patch_data item write
 * itself out to the restart database.  The following data
 * members are written out: d_box, d_patch_number,
 * d_patch_level_number,
 * d_patch_in_hierarchy, d_patch_data[].
 * The database key for all data members is identical to the
 * name of the data member except for the d_patch_data.  These have
 * keys of the form "variable##context" which is the form that they
 * are stored by the patch descriptor.  In addition a list of the
 * patch_data names ("patch_data_namelist") and the number of patch data
 * items saved ("namelist_count") are also written to the database.
 * The PatchDataRestartManager determines which patchdata are written to
 * the database.
 *
 *************************************************************************
 */
void
Patch::putToRestart(
   const std::shared_ptr<tbox::Database>& restart_db) const
{
   /* Checkpoint/restart API removed in vanilla strip 2026-05-15. */
}

/*
 *************************************************************************
 *
 * Print information about the patch.
 *
 *************************************************************************
 */

int
Patch::recursivePrint(
   std::ostream& os,
   const std::string& border,
   int depth) const
{
   NULL_USE(depth);

   const tbox::Dimension& dim(d_box.getDim());

   os << border
      << d_box
      << "\tdims: " << d_box.numberCells(0)
   ;
   for (tbox::Dimension::dir_t i = 1; i < dim.getValue(); ++i) {
      os << " X " << d_box.numberCells(i);
   }
   os << "\tsize: " << d_box.size()
      << "\n";
   return 0;
}

std::ostream&
operator << (
   std::ostream& s,
   const Patch& patch)
{
   const int ncomponents = static_cast<int>(patch.d_patch_data.size());
   s << "Patch::box = "
   << patch.d_box << std::endl << std::flush;
   s << "Patch::patch_level_number = " << patch.d_patch_level_number
   << std::endl << std::flush;
   s << "Patch::patch_in_hierarchy = " << patch.d_patch_in_hierarchy
   << std::endl << std::flush;
   s << "Patch::number_components = " << ncomponents
   << std::endl << std::flush;
   for (int i = 0; i < ncomponents; ++i) {
      s << "Component(" << i << ")=";
      if (!patch.d_patch_data[i]) {
         s << "NULL\n";
      } else {
         auto& p = *patch.d_patch_data[i];
         s << typeid(p).name()
         << " [GCW=" << patch.d_patch_data[i]->getGhostCellWidth() << "]\n";
      }
   }
   return s;
}

}
}
