//========================================================================================
// Athena++ astrophysical MHD code
// Copyright(C) 2014 James M. Stone <jmstone@princeton.edu> and other code contributors
// Licensed under the 3-clause BSD License, see LICENSE file for details
//========================================================================================
//================================= Athena++ Main Program ================================
//! \file main.cpp
//! \brief Athena++ main program
//!
//! Based on the Athena MHD code (Cambridge version), originally written in 2002-2005 by
//! Jim Stone, Tom Gardiner, and Peter Teuben, with many important contributions by many
//! other developers after that, i.e. 2005-2014.
//!
//! Athena++ was started in Jan 2014.  The core design was finished during 4-7/2014 at the
//! KITP by Jim Stone.  GR was implemented by Chris White and AMR by Kengo Tomida during
//! 2014-2016.  Contributions from many others have continued to the present.
//========================================================================================

// C headers

// C++ headers
#include <cmath>      // sqrt()
#include <csignal>    // ISO C/C++ signal() and sigset_t, sigemptyset() POSIX C extensions
#include <cstdint>    // int64_t
#include <cstdio>     // sscanf()
#include <cstdlib>    // strtol
#include <ctime>      // clock(), CLOCKS_PER_SEC, clock_t
#include <exception>  // exception
#include <iomanip>    // setprecision()
#include <iostream>   // cout, endl
#include <limits>     // max_digits10
#include <new>        // bad_alloc
#include <string>     // string

// Athena++ headers
#include "athena.hpp"
#include "athena_arrays.hpp"
#include "chem_rad/chem_rad.hpp"
#include "coordinates/coordinates.hpp"
#include "hydro/hydro.hpp"
#include "crdiffusion/mg_crdiffusion.hpp"
#include "fft/turbulence.hpp"
#include "globals.hpp"
#include "gravity/fft_gravity.hpp"
#include "gravity/mg_gravity.hpp"
#include "mesh/mesh.hpp"
#include "nr_radiation/implicit/radiation_implicit.hpp"
#include "nr_radiation/radiation.hpp"
#include "outputs/io_wrapper.hpp"
#include "outputs/outputs.hpp"
#include "parameter_input.hpp"
#include "task_list/chem_rad_task_list.hpp"
#include "utils/utils.hpp"

// MPI/OpenMP headers
#ifdef MPI_PARALLEL
#include <mpi.h>
#endif

#ifdef OPENMP_PARALLEL
#include <omp.h>
#endif

//----------------------------------------------------------------------------------------
//! \fn int main(int argc, char *argv[])
//! \brief Athena++ main program

int main(int argc, char *argv[]) {
  std::string athena_version = "version 24.0 - June 2024";
  char *input_filename = nullptr;
  char *prundir = nullptr;
  int narg_flag = 0;  // set to 1 if -n        argument is on cmdline
  int iarg_flag = 0;  // set to 1 if -i <file> argument is on cmdline
  int mesh_flag = 0;  // set to <nproc> if -m <nproc> argument is on cmdline
  int wtlim = 0;
  std::uint64_t mbcnt = 0;

  //--- Step 1. --------------------------------------------------------------------------
  // Initialize MPI environment, if necessary

#ifdef MPI_PARALLEL
#ifdef OPENMP_PARALLEL
  int mpiprv;
  if (MPI_SUCCESS != MPI_Init_thread(&argc, &argv, MPI_THREAD_MULTIPLE, &mpiprv)) {
    std::cout << "### FATAL ERROR in main" << std::endl
              << "MPI Initialization failed." << std::endl;
    return(0);
  }
  if (mpiprv != MPI_THREAD_MULTIPLE) {
    std::cout << "### FATAL ERROR in main" << std::endl
              << "MPI_THREAD_MULTIPLE must be supported for the hybrid parallelzation. "
              << MPI_THREAD_MULTIPLE << " : " << mpiprv
              << std::endl;
    MPI_Finalize();
    return(0);
  }
#else  // no OpenMP
  if (MPI_SUCCESS != MPI_Init(&argc, &argv)) {
    std::cout << "### FATAL ERROR in main" << std::endl
              << "MPI Initialization failed." << std::endl;
    return(0);
  }
#endif  // OPENMP_PARALLEL
  // Get process id (rank) in MPI_COMM_WORLD
  if (MPI_SUCCESS != MPI_Comm_rank(MPI_COMM_WORLD, &(Globals::my_rank))) {
    std::cout << "### FATAL ERROR in main" << std::endl
              << "MPI_Comm_rank failed." << std::endl;
    MPI_Finalize();
    return(0);
  }

  // Get total number of MPI processes (ranks)
  if (MPI_SUCCESS != MPI_Comm_size(MPI_COMM_WORLD, &Globals::nranks)) {
    std::cout << "### FATAL ERROR in main" << std::endl
              << "MPI_Comm_size failed." << std::endl;
    MPI_Finalize();
    return(0);
  }
#else  // no MPI
  Globals::my_rank = 0;
  Globals::nranks  = 1;
#endif  // MPI_PARALLEL

  //--- Step 2. --------------------------------------------------------------------------
  // Check for command line options and respond.

  for (int i=1; i<argc; i++) {
    // If argv[i] is a 2 character string of the form "-?" then:
    if (*argv[i] == '-'  && *(argv[i]+1) != '\0' && *(argv[i]+2) == '\0') {
      // check validity of command line options + arguments:
      char opt_letter = *(argv[i]+1);
      switch(opt_letter) {
        // options that do not take arguments:
        case 'n':
        case 'c':
        case 'h':
          break;
          // options that require arguments:
        default:
          if ((i+1 >= argc) // flag is at the end of the command line options
              || (*argv[i+1] == '-') ) { // flag is followed by another flag
            if (Globals::my_rank == 0) {
              std::cout << "### FATAL ERROR in main" << std::endl
                        << "-" << opt_letter << " must be followed by a valid argument\n";
#ifdef MPI_PARALLEL
              MPI_Finalize();
#endif
              return(0);
            }
          }
      }
      switch(*(argv[i]+1)) {
        case 'i':                      // -i <input_filename>
          input_filename = argv[++i];
          iarg_flag = 1;
          break;
        case 'd':                      // -d <run_directory>
          prundir = argv[++i];
          break;
        case 'n':
          narg_flag = 1;
          break;
        case 'm':                      // -m <nproc>
          mesh_flag = static_cast<int>(std::strtol(argv[++i], nullptr, 10));
          break;
        case 't':                      // -t <hh:mm:ss>
          int wth, wtm, wts;
          std::sscanf(argv[++i], "%d:%d:%d", &wth, &wtm, &wts);
          wtlim = wth*3600 + wtm*60 + wts;
          break;
        case 'c':
          if (Globals::my_rank == 0) ShowConfig();
#ifdef MPI_PARALLEL
          MPI_Finalize();
#endif
          return(0);
          break;
        case 'h':
        default:
          if (Globals::my_rank == 0) {
            std::cout << "Athena++ " << athena_version << std::endl;
            std::cout << "Usage: " << argv[0] << " [options] [block/par=value ...]\n";
            std::cout << "Options:" << std::endl;
            std::cout << "  -i <file>       specify input file [athinput]\n";
            std::cout << "  -d <directory>  specify run dir [current dir]\n";
            std::cout << "  -n              parse input file and quit\n";
            std::cout << "  -c              show configuration and quit\n";
            std::cout << "  -m <nproc>      output mesh structure and quit\n";
            std::cout << "  -t hh:mm:ss     wall time limit for final output\n";
            std::cout << "  -h              this help\n";
            ShowConfig();
          }
#ifdef MPI_PARALLEL
          MPI_Finalize();
#endif
          return(0);
          break;
      }
    } // else if argv[i] not of form "-?" ignore it here (tested in ModifyFromCmdline)
  }

  if (input_filename == nullptr) {
    // no input file is given
    std::cout << "### FATAL ERROR in main" << std::endl
              << "No input file is specified." << std::endl;
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }

  // Set up the signal handler
  SignalHandler::SignalHandlerInit();
  if (Globals::my_rank == 0 && wtlim > 0)
    SignalHandler::SetWallTimeAlarm(wtlim);

  // Note steps 3-6 are protected by a simple error handler
  //--- Step 3. --------------------------------------------------------------------------
  // Construct object to store input parameters, then parse input file and command line.
  // With MPI, the input is read by every process in parallel using MPI-IO.

  ParameterInput *pinput;
  IOWrapper infile;
#ifdef ENABLE_EXCEPTIONS
  try {
#endif
    pinput = new ParameterInput;
    if (iarg_flag == 1) {
      infile.Open(input_filename, IOWrapper::FileMode::read);
      pinput->LoadFromFile(infile);
      infile.Close();
    }
    pinput->ModifyFromCmdline(argc ,argv);
#ifdef ENABLE_EXCEPTIONS
  }
  catch(std::bad_alloc& ba) {
    std::cout << "### FATAL ERROR in main" << std::endl
              << "memory allocation failed initializing class ParameterInput: "
              << ba.what() << std::endl;
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }
  catch(std::exception const& ex) {
    std::cout << ex.what() << std::endl;  // prints diagnostic message
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }
#endif // ENABLE_EXCEPTIONS

  //--- Step 4. --------------------------------------------------------------------------
  // Construct and initialize Mesh

  Mesh *pmesh;
#ifdef ENABLE_EXCEPTIONS
  try {
#endif
    pmesh = new Mesh(pinput, mesh_flag);
#ifdef ENABLE_EXCEPTIONS
  }
  catch(std::bad_alloc& ba) {
    std::cout << "### FATAL ERROR in main" << std::endl
              << "memory allocation failed initializing class Mesh: "
              << ba.what() << std::endl;
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }
  catch(std::exception const& ex) {
    std::cout << ex.what() << std::endl;  // prints diagnostic message
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }
#endif // ENABLE_EXCEPTIONS

  // Dump input parameters and quit if code was run with -n option.
  if (narg_flag) {
    if (Globals::my_rank == 0) pinput->ParameterDump(std::cout);
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }

  // Quit if -m was on cmdline.  This option builds and outputs mesh structure.
  if (mesh_flag > 0) {
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }

  //--- Step 5. --------------------------------------------------------------------------
  // Construct and initialize TaskList

  TimeIntegratorTaskList *ptlist;
#ifdef ENABLE_EXCEPTIONS
  try {
#endif
    ptlist = new TimeIntegratorTaskList(pinput, pmesh);
#ifdef ENABLE_EXCEPTIONS
  }
  catch(std::bad_alloc& ba) {
    std::cout << "### FATAL ERROR in main" << std::endl << "memory allocation failed "
              << "in creating task list " << ba.what() << std::endl;
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }
#endif // ENABLE_EXCEPTIONS

  SuperTimeStepTaskList *pststlist = nullptr;
  if (STS_ENABLED) {
#ifdef ENABLE_EXCEPTIONS
    try {
#endif
      pststlist = new SuperTimeStepTaskList(pinput, pmesh, ptlist);
#ifdef ENABLE_EXCEPTIONS
    }
    catch(std::bad_alloc& ba) {
      std::cout << "### FATAL ERROR in main" << std::endl << "memory allocation failed "
                << "in creating task list " << ba.what() << std::endl;
#ifdef MPI_PARALLEL
      MPI_Finalize();
#endif
      return(0);
    }
#endif // ENABLE_EXCEPTIONS
  }

  // chemistry radiation
  ChemRadiationIntegratorTaskList *pchemradlist = nullptr;
  if (CHEMRADIATION_ENABLED) {
#ifdef ENABLE_EXCEPTIONS
    try {
#endif
      pchemradlist = new ChemRadiationIntegratorTaskList(pinput, pmesh);
#ifdef ENABLE_EXCEPTIONS
    }
    catch(std::bad_alloc& ba) {
      std::cout << "### FATAL ERROR in main" << std::endl << "memory allocation failed "
                << "in creating task list " << ba.what() << std::endl;
#ifdef MPI_PARALLEL
      MPI_Finalize();
#endif
      return(0);
    }
#endif // ENABLE_EXCEPTIONS
  }

  //--- Step 6. --------------------------------------------------------------------------
  // Set initial conditions by calling problem generator

#ifdef ENABLE_EXCEPTIONS
  try {
#endif
    pmesh->Initialize(0, pinput);
#ifdef ENABLE_EXCEPTIONS
  }
  catch(std::bad_alloc& ba) {
    std::cout << "### FATAL ERROR in main" << std::endl << "memory allocation failed "
              << "in problem generator " << ba.what() << std::endl;
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }
  catch(std::exception const& ex) {
    std::cout << ex.what() << std::endl;  // prints diagnostic message
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }
#endif // ENABLE_EXCEPTIONS

  //--- Step 7. --------------------------------------------------------------------------
  // Change to run directory, initialize outputs object, and make output of ICs

  Outputs *pouts;
#ifdef ENABLE_EXCEPTIONS
  try {
#endif
    ChangeRunDir(prundir);
    pouts = new Outputs(pmesh, pinput);
    pouts->MakeOutputs(pmesh, pinput);
#ifdef ENABLE_EXCEPTIONS
  }
  catch(std::bad_alloc& ba) {
    std::cout << "### FATAL ERROR in main" << std::endl
              << "memory allocation failed setting initial conditions: "
              << ba.what() << std::endl;
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }
  catch(std::exception const& ex) {
    std::cout << ex.what() << std::endl;  // prints diagnostic message
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }
#endif // ENABLE_EXCEPTIONS

  //=== Step 8. === START OF MAIN INTEGRATION LOOP =======================================
  // For performance, there is no error handler protecting this step (except outputs)

  if (Globals::my_rank == 0) {
    std::cout << "\nSetup complete, entering main loop...\n" << std::endl;
  }

  clock_t tstart = clock();
#ifdef OPENMP_PARALLEL
  double omp_start_time = omp_get_wtime();
#endif

  while ((pmesh->time < pmesh->tlim) &&
         (pmesh->nlim < 0 || pmesh->ncycle < pmesh->nlim)) {
    if (Globals::my_rank == 0)
      pmesh->OutputCycleDiagnostics();

    if (STS_ENABLED) {
      pmesh->sts_loc = TaskType::op_split_before;
      // compute nstages for this STS
      if (pmesh->sts_integrator == "rkl2") { // default
        pststlist->nstages =
            static_cast<int>
              (0.5*(-1. + std::sqrt(9. + 16.*(0.5*pmesh->dt)/pmesh->dt_parabolic))) + 1;
      } else { // rkl1
        pststlist->nstages =
            static_cast<int>
              (0.5*(-1. + std::sqrt(1. + 8.*pmesh->dt/pmesh->dt_parabolic))) + 1;
      }
      if (pststlist->nstages % 2 == 0) { // guarantee odd nstages for STS
        pststlist->nstages += 1;
      }
      // take super-timestep
      for (int stage=1; stage<=pststlist->nstages; ++stage)
        pststlist->DoTaskListOneStage(pmesh, stage);

      pmesh->sts_loc = TaskType::main_int;
    }

    if (pmesh->turb_flag > 1) pmesh->ptrbd->Driving(); // driven turbulence

    if (CRDIFFUSION_ENABLED) {
      pmesh->pmcrd->Solve(0, pmesh->dt);
    }

    // chemistry with radiation
    if (CHEMRADIATION_ENABLED) {
      clock_t tstart_rad, tstop_rad;
      tstart_rad = std::clock();

      pchemradlist->DoTaskListOneStage(pmesh, 1);

      // radiation tasklist timing output
      if (pmesh->my_blocks(0)->pchemrad->output_zone_sec) {
        tstop_rad = std::clock();
        double cpu_time = (tstop_rad>tstart_rad ?
            static_cast<double> (tstop_rad-tstart_rad) :
            1.0)/static_cast<double> (CLOCKS_PER_SEC);
        std::uint64_t nzones =
          static_cast<std::uint64_t> (pmesh->my_blocks(0)->GetNumberOfMeshBlockCells());
        // double zone_sec = static_cast<double> (nzones) / cpu_time;
        printf("ChemRadiation tasklist: ");
        printf("ncycle = %d, total time in sec = %.2e, zone/sec=%.2e\n",
            pmesh->ncycle, cpu_time, Real(nzones)/cpu_time);
      }
    }

    for (int stage=1; stage<=ptlist->nstages; ++stage) {
      ptlist->DoTaskListOneStage(pmesh, stage);
      if (ptlist->CheckNextMainStage(stage)) {
        if (SELF_GRAVITY_ENABLED == 1) // fft (0: discrete kernel, 1: continuous kernel)
          pmesh->pfgrd->Solve(stage, 0);
        else if (SELF_GRAVITY_ENABLED == 2) // multigrid
          pmesh->pmgrd->Solve(stage);
      }
      if (IM_RADIATION_ENABLED) {
        pmesh->pimrad->Iteration(pmesh,ptlist,stage);
      }
    }

    if (STS_ENABLED && pmesh->sts_integrator == "rkl2") {
      pmesh->sts_loc = TaskType::op_split_after;
      // take super-timestep
      for (int stage=1; stage<=pststlist->nstages; ++stage)
        pststlist->DoTaskListOneStage(pmesh, stage);
    }

    pmesh->UserWorkInLoop();

    pmesh->ncycle++;
    pmesh->time += pmesh->dt;
    mbcnt += pmesh->nbtotal;
    pmesh->step_since_lb++;

    pmesh->LoadBalancingAndAdaptiveMeshRefinement(pinput);

    pmesh->NewTimeStep();

#ifdef ENABLE_EXCEPTIONS
    try {
#endif
      if (pmesh->time < pmesh->tlim) // skip the final output as it happens later
        pouts->MakeOutputs(pmesh,pinput);
#ifdef ENABLE_EXCEPTIONS
    }
    catch(std::bad_alloc& ba) {
      std::cout << "### FATAL ERROR in main" << std::endl
                << "memory allocation failed during output: " << ba.what() <<std::endl;
#ifdef MPI_PARALLEL
      MPI_Finalize();
#endif
      return(0);
    }
    catch(std::exception const& ex) {
      std::cout << ex.what() << std::endl;  // prints diagnostic message
#ifdef MPI_PARALLEL
      MPI_Finalize();
#endif
      return(0);
    }
#endif // ENABLE_EXCEPTIONS

    // check for signals
    if (SignalHandler::CheckSignalFlags() != 0) {
      break;
    }
  } // END OF MAIN INTEGRATION LOOP ======================================================
  // Make final outputs, print diagnostics, clean up and terminate

  if (Globals::my_rank == 0 && wtlim > 0)
    SignalHandler::CancelWallTimeAlarm();


  //--- Step 9. --------------------------------------------------------------------------
  // Output the final cycle diagnostics and make the final outputs

  if (Globals::my_rank == 0)
    pmesh->OutputCycleDiagnostics();

  pmesh->UserWorkAfterLoop(pinput);

#ifdef ENABLE_EXCEPTIONS
  try {
#endif
    pouts->MakeOutputs(pmesh,pinput,true);
#ifdef ENABLE_EXCEPTIONS
  }
  catch(std::bad_alloc& ba) {
    std::cout << "### FATAL ERROR in main" << std::endl
              << "memory allocation failed during output: " << ba.what() <<std::endl;
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }
  catch(std::exception const& ex) {
    std::cout << ex.what() << std::endl;  // prints diagnostic message
#ifdef MPI_PARALLEL
    MPI_Finalize();
#endif
    return(0);
  }
#endif // ENABLE_EXCEPTIONS

  /* Step 0 v9 (Athena++-B 2026-05-24): collective MPI reduction of
   * volume-integrated hydro state for the binary validation signature.
   * Must run BEFORE the rank-0-only diagnostic block below — MPI_Reduce is
   * collective and would deadlock if entered by rank 0 alone.
   *
   * Accumulates per-rank sums of (rho * dV), (m_x * dV), and
   * (0.5 * m_x^2 / rho * dV) across all MeshBlocks owned by this rank,
   * then MPI_SUM-reduces to rank 0.  Pattern mirrors
   * src/outputs/history.cpp:79-104,324-329 (HistoryOutput's volume-weighted
   * sums + MPI_IN_PLACE reduce).  Cast Real -> double so the reduction
   * buffer matches the validation_output.bin layout regardless of whether
   * Athena++ was configured for single or double precision (athena.hpp:34/39).
   */
  double athena_sig_mass = 0.0;
  double athena_sig_mom_x = 0.0;
  double athena_sig_ke_x = 0.0;
  {
    AthenaArray<Real> vol;
    const int ncells1 = pmesh->my_blocks(0)->block_size.nx1 + 2*(NGHOST);
    vol.NewAthenaArray(ncells1);
    for (int b = 0; b < pmesh->nblocal; ++b) {
      MeshBlock *pmb = pmesh->my_blocks(b);
      for (int k = pmb->ks; k <= pmb->ke; ++k) {
        for (int j = pmb->js; j <= pmb->je; ++j) {
          pmb->pcoord->CellVolume(k, j, pmb->is, pmb->ie, vol);
          for (int i = pmb->is; i <= pmb->ie; ++i) {
            const double u_d  = static_cast<double>(pmb->phydro->u(IDN, k, j, i));
            const double u_mx = static_cast<double>(pmb->phydro->u(IM1, k, j, i));
            const double dV   = static_cast<double>(vol(i));
            athena_sig_mass  += dV * u_d;
            athena_sig_mom_x += dV * u_mx;
            athena_sig_ke_x  += dV * 0.5 * u_mx * u_mx / u_d;
          }
        }
      }
    }
  }
#ifdef MPI_PARALLEL
  {
    double local_buf[3]  = {athena_sig_mass, athena_sig_mom_x, athena_sig_ke_x};
    double global_buf[3] = {0.0, 0.0, 0.0};
    MPI_Reduce(local_buf, global_buf, 3, MPI_DOUBLE, MPI_SUM,
               0, MPI_COMM_WORLD);
    if (Globals::my_rank == 0) {
      athena_sig_mass  = global_buf[0];
      athena_sig_mom_x = global_buf[1];
      athena_sig_ke_x  = global_buf[2];
    }
  }
#endif

  //--- Step 10. -------------------------------------------------------------------------
  // Print diagnostic messages related to the end of the simulation

  if (Globals::my_rank == 0) {
    if (SignalHandler::GetSignalFlag(SIGTERM) != 0) {
      std::cout << std::endl << "Terminating on Terminate signal" << std::endl;
    } else if (SignalHandler::GetSignalFlag(SIGINT) != 0) {
      std::cout << std::endl << "Terminating on Interrupt signal" << std::endl;
    } else if (SignalHandler::GetSignalFlag(SIGALRM) != 0) {
      std::cout << std::endl << "Terminating on wall-time limit" << std::endl;
    } else if (pmesh->ncycle == pmesh->nlim) {
      std::cout << std::endl << "Terminating on cycle limit" << std::endl;
    } else {
      std::cout << std::endl << "Terminating on time limit" << std::endl;
    }

    std::cout << "time=" << pmesh->time << " cycle=" << pmesh->ncycle << std::endl;
    std::cout << "tlim=" << pmesh->tlim << " nlim=" << pmesh->nlim << std::endl;

    if (pmesh->adaptive) {
      std::cout << std::endl << "Number of MeshBlocks = " << pmesh->nbtotal
                << "; " << pmesh->nbnew << "  created, " << pmesh->nbdel
                << " destroyed during this simulation." << std::endl;
    }

    // Calculate and print the zone-cycles/cpu-second and wall-second
#ifdef OPENMP_PARALLEL
    double omp_time = omp_get_wtime() - omp_start_time;
#endif
    clock_t tstop = clock();
    double cpu_time = (tstop>tstart ? static_cast<double> (tstop-tstart) :
                       1.0)/static_cast<double> (CLOCKS_PER_SEC);
    std::uint64_t zonecycles = mbcnt
      *static_cast<std::uint64_t> (pmesh->my_blocks(0)->GetNumberOfMeshBlockCells());
    double zc_cpus = static_cast<double> (zonecycles) / cpu_time;

    std::cout << std::endl << "zone-cycles = " << zonecycles << std::endl;
    std::cout << "cpu time used  = " << cpu_time << std::endl;
    std::cout << "zone-cycles/cpu_second = " << zc_cpus << std::endl;
#ifdef OPENMP_PARALLEL
    double zc_omps = static_cast<double> (zonecycles) / omp_time;
    std::cout << std::endl << "omp wtime used = " << omp_time << std::endl;
    std::cout << "zone-cycles/omp_wsecond = " << zc_omps << std::endl;
#endif

    /* Step 0 v9 (Athena++-B 2026-05-24): emit STATE-derived binary
     * validation signature.  Replaces v8 schema whose slots [3..5] were
     * config constants (nbtotal, tlim, nlim) — explicitly labelled "constant"
     * in the old comment, so half the comparator surface was tautological
     * (a resilient cold-start that skipped simulate() would pass those slots
     * byte-identically).
     *
     * Schema (48 bytes, slot-compatible with v8):
     *   [0] pmesh->time                        (final simulated time)   [STATE]
     *   [1] (double)pmesh->ncycle              (final cycle count)      [STATE]
     *   [2] pmesh->dt                          (final timestep size)    [STATE]
     *   [3] athena_sig_mass                    sum(rho*dV) globally     [STATE-new]
     *   [4] athena_sig_mom_x                   sum(m_x*dV) globally     [STATE-new]
     *   [5] athena_sig_ke_x                    sum(0.5*m_x^2/rho*dV)    [STATE-new]
     *
     * Slots [3..5] are filled by the collective MPI_Reduce inserted before
     * the rank-0 diagnostic block above (mirrors history.cpp:79-104,324-329).
     * Rank-root-only file write.  Comparator: tests/apps/configs/Athena++.yaml
     * comparison.method = numeric-tolerance, tolerance preserved.  Slots
     * [3..5] react to any integrator drift; cold-replayed runs diverge.
     */
    double sig_buf[6];
    sig_buf[0] = pmesh->time;
    sig_buf[1] = static_cast<double>(pmesh->ncycle);
    sig_buf[2] = pmesh->dt;
    sig_buf[3] = athena_sig_mass;
    sig_buf[4] = athena_sig_mom_x;
    sig_buf[5] = athena_sig_ke_x;
    FILE* sig_f = std::fopen("validation_output.bin", "wb");
    if (sig_f) {
      std::fwrite(sig_buf, sizeof(double), 6, sig_f);
      std::fclose(sig_f);
    }
  }

  delete pinput;
  delete pmesh;
  delete ptlist;
  delete pouts;
  delete pchemradlist;

#ifdef MPI_PARALLEL
  MPI_Finalize();
#endif

  return(0);
}
