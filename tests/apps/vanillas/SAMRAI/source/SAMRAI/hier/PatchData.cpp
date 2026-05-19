/*************************************************************************
 *
 * This file is part of the SAMRAI distribution.  For full copyright
 * information, see COPYRIGHT and LICENSE.
 *
 * Copyright:     (c) 1997-2026 Lawrence Livermore National Security, LLC
 * Description:   Abstract base class for patch data objects
 *
 ************************************************************************/
#include "SAMRAI/hier/PatchData.h"

namespace SAMRAI {
namespace hier {

const int PatchData::HIER_PATCH_DATA_VERSION = 2;

PatchData::PatchData(
   const Box& domain,
   const IntVector& ghosts):
   d_box(domain),
   d_ghost_box(domain),
   d_ghosts(ghosts),
   d_timestamp(0.0)
{
   TBOX_ASSERT_OBJDIM_EQUALITY2(domain, ghosts);

   d_ghost_box.grow(ghosts);
}

PatchData::~PatchData()
{
}

void
PatchData::copyFuseable(
   const PatchData& src,
   const BoxOverlap& overlap)
{
   copy(src, overlap);
}

void
PatchData::packStreamFuseable(
   tbox::MessageStream& stream,
   const BoxOverlap& overlap) const
{
   packStream(stream, overlap);
}

void
PatchData::unpackStreamFuseable(
   tbox::MessageStream& stream,
   const BoxOverlap& overlap)
{
   unpackStream(stream, overlap);
}

}
}
