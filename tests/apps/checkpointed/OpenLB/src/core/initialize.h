/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Adrian Kummerlaender
 *  E-mail contact: info@openlb.net
 *  The most recent release of OpenLB can be downloaded at
 *  <http://www.openlb.net/>
 *
 *  This program is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU General Public License
 *  as published by the Free Software Foundation; either version 2
 *  of the License, or (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public
 *  License along with this program; if not, write to the Free
 *  Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 *  Boston, MA  02110-1301, USA.
*/

#ifndef CORE_INITIALIZE_H
#define CORE_INITIALIZE_H

#include "olbInit.h"

namespace olb {

/// Initialize OpenLB
/**
 * Sets up MPI, thread pool and verifies platform requirements.
 **/
void initialize(int *argc, char ***argv, bool multiOutput=false, bool verbose=true)
{
  std::set_terminate(terminateHandler);

#ifdef PARALLEL_MODE_MPI
  bool mpiInitialized = false;
  if (singleton::mpi().init(argc, argv)) {
    mpiInitialized = true;
  }
#endif

#ifndef FEATURE_HIDE_LOGO
  // create an OstreamManager object in order to enable multi output
  if (singleton::mpi().isMainProcessor()) {
  std::cout << R"(
    ┃
    ┃  ┏━━━━┓      ▁▁▁▁                   ▁▁    ▁▁▁▁
    ┃  ┃    ┃     ╱ ▁▁ ╲▁▁▁▁  ▁▁▁  ▁▁▁▁  ╱ ╱   ╱ ▁▁ ╲
 ┏━━╋━┓┃    ┃    ╱ ╱ ╱ ╱ ▁▁ ╲╱ ▁ ╲╱ ▁▁ ╲╱ ╱   ╱ ╱▁╱ ╱
 ┃  ┗━╋╋━━━━┻┓  ╱ ╱▁╱ ╱ ╱▁╱ ╱  ▁▁╱ ╱ ╱ ╱ ╱▁▁▁╱ ╱▁╱ ╱
 ┃    ┃┃     ┃  ╲▁▁▁▁╱ ▁▁▁▁╱╲▁▁▁╱▁╱ ╱▁╱▁▁▁▁▁╱▁▁▁▁▁╱
 ┗━━━━┛┃     ┃      ╱▁╱ ==========================>>
       ┗━━━━━┛
)" << std::endl;
  }
#endif

  olb::OstreamManager clout(std::cout, "initialize");
  clout << "Version  : " << OLB_VERSION << std::endl;
  clout << "Platform :";
#ifdef PLATFORM_CPU_SISD
  clout << " CPU_SISD";
#endif
#ifdef PLATFORM_CPU_SIMD
  clout << " CPU_SIMD";
#endif
#ifdef PLATFORM_GPU_CUDA
  clout << " GPU_CUDA";
#endif
#ifdef PLATFORM_GPU_HIP
  clout << " GPU_HIP";
#endif
  clout << std::endl;
  clout << "Parallel :";
#if !(defined(PARALLEL_MODE_MPI) || defined(PARALLEL_MODE_OMP))
  clout << " None";
#else
#ifdef PARALLEL_MODE_MPI
  clout << " MPI";
#endif
#ifdef PARALLEL_MODE_OMP
  clout << " OMP";
#endif
#endif
  clout << std::endl;

  clout.setMultiOutput(multiOutput);

#ifdef PARALLEL_MODE_MPI
  if (mpiInitialized) {
    clout << "MPI      : " << singleton::mpi().getSize() << " ranks" << std::endl;
  } else {
    clout << "MPI      : Failed!" << std::endl;
  }
#endif

#ifdef PARALLEL_MODE_OMP
  if (singleton::omp().init(argc, argv)) {
    clout << "OMP      : " << singleton::omp().getSize() << " threads" << std::endl;
  } else {
    clout << "OMP      : Failed!" << std::endl;
  }
#endif

  /// Verify requirements for using all enabled platforms
#ifdef PLATFORM_GPU_CUDA
  checkPlatform<Platform::GPU_CUDA>();
#endif
#ifdef PLATFORM_GPU_HIP
  checkPlatform<Platform::GPU_HIP>();
#endif

  int nThreads = 1;
  if (const char* envOlbNumThreads = std::getenv("OLB_NUM_THREADS")) {
    nThreads = std::stoi(envOlbNumThreads);
  }
  singleton::pool().init(nThreads, verbose);

  #ifdef FEATURE_VDB
  openvdb::initialize();
  #endif
}

/// Initialize OpenLB
void initialize(int argc, char **argv, bool multiOutput=false, bool verbose=true)
{
  initialize(&argc, &argv, multiOutput, verbose);
}

}

#endif
