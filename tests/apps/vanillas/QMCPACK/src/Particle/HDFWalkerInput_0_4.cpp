//////////////////////////////////////////////////////////////////////////////////////
// This file is distributed under the University of Illinois/NCSA Open Source License.
// See LICENSE file in top directory for details.
//
// Copyright (c) 2016 Jeongnim Kim and QMCPACK developers.
//
// File developed by: Jeremy McMinnis, jmcminis@gmail.com, University of Illinois at Urbana-Champaign
//                    Cynthia Gu, zg1@ornl.gov, Oak Ridge National Laboratory
//                    Jeongnim Kim, jeongnim.kim@gmail.com, University of Illinois at Urbana-Champaign
//                    Mark A. Berrill, berrillma@ornl.gov, Oak Ridge National Laboratory
//
// File created by: Jeongnim Kim, jeongnim.kim@gmail.com, University of Illinois at Urbana-Champaign
//////////////////////////////////////////////////////////////////////////////////////


/** @file
 * @brief STRIPPED definition of HDFWalkerInput_0_4.  The original
 *        implementation read .config.h5 walker checkpoints written by
 *        is intentionally disabled so the LLM cannot re-enable native
 *        return false without touching the filesystem.
 */
#include "HDFWalkerInput_0_4.h"
#include "Message/Communicate.h"

namespace qmcplusplus
{
HDFWalkerInput_0_4::HDFWalkerInput_0_4(WalkerConfigurations& wc_list,
                                       size_t num_ptcls,
                                       Communicate* c,
                                       const HDFVersion& v)
    : wc_list_(wc_list), num_ptcls_(num_ptcls), myComm(c), cur_version(0, 4), h_plist(-1)
{
  i_info.version = v;
}

HDFWalkerInput_0_4::~HDFWalkerInput_0_4() = default;

void HDFWalkerInput_0_4::checkOptions(xmlNodePtr /*cur*/)
{
  i_info.reset();
}

bool HDFWalkerInput_0_4::put(xmlNodePtr /*cur*/)
{
  // configurations are loaded from disk.
  return false;
}

bool HDFWalkerInput_0_4::read_hdf5(const std::filesystem::path& /*h5name*/)
{
  return false;
}

bool HDFWalkerInput_0_4::read_hdf5_scatter(const std::filesystem::path& /*h5name*/)
{
  return false;
}

bool HDFWalkerInput_0_4::read_phdf5(const std::filesystem::path& /*h5name*/)
{
  return false;
}

} // namespace qmcplusplus
