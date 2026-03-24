//************************************************************************
//  ExaMiniMD v. 1.0
//  Copyright (2018) National Technology & Engineering Solutions of Sandia,
//  LLC (NTESS).
//
//  Under the terms of Contract DE-NA-0003525 with NTESS, the U.S. Government
//  retains certain rights in this software.
//
//  ExaMiniMD is licensed under 3-clause BSD terms of use: Redistribution and
//  use in source and binary forms, with or without modification, are
//  permitted provided that the following conditions are met:
//
//    1. Redistributions of source code must retain the above copyright notice,
//       this list of conditions and the following disclaimer.
//
//    2. Redistributions in binary form must reproduce the above copyright notice,
//       this list of conditions and the following disclaimer in the documentation
//       and/or other materials provided with the distribution.
//
//    3. Neither the name of the Corporation nor the names of the contributors
//       may be used to endorse or promote products derived from this software
//       without specific prior written permission.
//
//  THIS SOFTWARE IS PROVIDED BY NTESS "AS IS" AND ANY EXPRESS OR IMPLIED
//  WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
//  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
//  IN NO EVENT SHALL NTESS OR THE CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
//  INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
//  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
//  SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
//  HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
//  STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
//  IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
//  POSSIBILITY OF SUCH DAMAGE.
//
//  Questions? Contact Christian R. Trott (crtrott@sandia.gov)
//************************************************************************

#include<examinimd.h>
#include<cstring>

// ExaMiniMD can be used as a library
// This main file is simply a driver
//
// VeloC resilience support:
//   Optional argument: --veloc-cfg <path>
//   If not provided, defaults to "veloc.cfg" in the current working directory.
//   This argument is transparent to the original application — it is stripped
//   from argv before being passed to ExaMiniMD::init().

#ifdef EXAMINIMD_ENABLE_MPI
#include "mpi.h"
#endif

#ifdef EXAMINIMD_ENABLE_VELOC
#include <veloc.h>
#endif

int main(int argc, char* argv[]) {

   #ifdef EXAMINIMD_ENABLE_MPI
   MPI_Init(&argc,&argv);
   #endif

   // --- Extract --veloc-cfg from argv (transparent to original app) ---
   const char* veloc_cfg_path = "veloc.cfg";  // default
   int new_argc = 0;
   char** new_argv = new char*[argc];
   for (int i = 0; i < argc; i++) {
     if (strcmp(argv[i], "--veloc-cfg") == 0 && i + 1 < argc) {
       veloc_cfg_path = argv[i + 1];
       i++; // skip the next argument (the path)
     } else {
       new_argv[new_argc++] = argv[i];
     }
   }

   #ifdef EXAMINIMD_ENABLE_VELOC
   // Initialize VeloC immediately after MPI_Init, before Kokkos
   if (VELOC_Init(MPI_COMM_WORLD, veloc_cfg_path) != VELOC_SUCCESS) {
     fprintf(stderr, "ERROR: VELOC_Init failed with config '%s'\n", veloc_cfg_path);
     MPI_Abort(MPI_COMM_WORLD, 1);
   }
   #endif

   Kokkos::initialize(new_argc, new_argv);

   ExaMiniMD examinimd;
   examinimd.init(new_argc, new_argv);
  
   examinimd.run(examinimd.input->nsteps);

   examinimd.print_performance();

   examinimd.shutdown();

   Kokkos::finalize();

   #ifdef EXAMINIMD_ENABLE_VELOC
   VELOC_Finalize(1); // drain=1: flush pending checkpoints before finalizing
   #endif

   #ifdef EXAMINIMD_ENABLE_MPI
   MPI_Finalize();
   #endif

   delete[] new_argv;
}
