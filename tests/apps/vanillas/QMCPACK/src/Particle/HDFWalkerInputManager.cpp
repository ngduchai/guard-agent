//////////////////////////////////////////////////////////////////////////////////////
// This file is distributed under the University of Illinois/NCSA Open Source License.
// See LICENSE file in top directory for details.
//
// Copyright (c) 2016 Jeongnim Kim and QMCPACK developers.
//
// File developed by: Jeremy McMinnis, jmcminis@gmail.com, University of Illinois at Urbana-Champaign
//                    Cynthia Gu, zg1@ornl.gov, Oak Ridge National Laboratory
//                    Jeongnim Kim, jeongnim.kim@gmail.com, University of Illinois at Urbana-Champaign
//                    Raymond Clay III, j.k.rofling@gmail.com, Lawrence Livermore National Laboratory
//                    Mark A. Berrill, berrillma@ornl.gov, Oak Ridge National Laboratory
//
// File created by: Jeongnim Kim, jeongnim.kim@gmail.com, University of Illinois at Urbana-Champaign
//////////////////////////////////////////////////////////////////////////////////////


/** @file
 * @brief STRIPPED definition of HDFWalkerInputManager.  The original
 *        implementation read .config.h5 walker checkpoints via
 *        is intentionally disabled so the LLM cannot re-enable native
 *        false (no walker set was loaded), and getFileRoot() returns "".
 */
#include "HDFWalkerInputManager.h"
#include "Message/Communicate.h"

namespace qmcplusplus
{
HDFWalkerInputManager::HDFWalkerInputManager(WalkerConfigurations& wc_list, size_t num_ptcls, Communicate* c)
    : wc_list_(wc_list), num_ptcls_(num_ptcls), myComm(c) {}

HDFWalkerInputManager::~HDFWalkerInputManager() {}

bool HDFWalkerInputManager::put(xmlNodePtr /*cur*/)
{
  // false signals that no walker configurations were loaded from file; the
  // caller falls back to fresh walker initialization.
  return false;
}
} // namespace qmcplusplus
