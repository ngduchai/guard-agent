//////////////////////////////////////////////////////////////////////////////////////
// This file is distributed under the University of Illinois/NCSA Open Source License.
// See LICENSE file in top directory for details.
//
// Copyright (c) 2016 Jeongnim Kim and QMCPACK developers.
//
// File developed by: D.C. Yang, University of Illinois at Urbana-Champaign
//                    Jeremy McMinnis, jmcminis@gmail.com, University of Illinois at Urbana-Champaign
//                    Jeongnim Kim, jeongnim.kim@gmail.com, University of Illinois at Urbana-Champaign
//                    Cynthia Gu, zg1@ornl.gov, Oak Ridge National Laboratory
//                    Mark A. Berrill, berrillma@ornl.gov, Oak Ridge National Laboratory
//
// File created by: Jeongnim Kim, jeongnim.kim@gmail.com, University of Illinois at Urbana-Champaign
//////////////////////////////////////////////////////////////////////////////////////


/** @file
 * @brief STRIPPED definition of HDFWalkerOutput.  The original implementation
 *        wrote *.config.h5 walker checkpoints; in the vanilla benchmark this
 *        capability is intentionally disabled so the LLM cannot re-enable
 *        attribute.  All public methods retain their signatures but perform
 *        no I/O.
 */
#include "HDFWalkerOutput.h"
#include "Message/Communicate.h"

namespace qmcplusplus
{
HDFWalkerOutput::HDFWalkerOutput(size_t num_ptcls, const std::string& aroot, Communicate* c)
    : DoNotAppend(false),
      appended_blocks(0),
      number_of_walkers_(0),
      number_of_particles_(num_ptcls),
      myComm(c),
      currentConfigNumber(0),
      RootName(aroot),
      block(-1)
{}

HDFWalkerOutput::~HDFWalkerOutput() = default;

bool HDFWalkerOutput::dump(const WalkerConfigurations& /*W*/, int /*nblock*/)
{
  // is written.  Returning true keeps callers' control flow unchanged.
  return true;
}

void HDFWalkerOutput::write_configuration(const WalkerConfigurations& /*W*/,
                                          hdf_archive& /*hout*/,
                                          int /*nblock*/)
{
}

} // namespace qmcplusplus
