/*! @file Solve.c
    @author Debojyoti Ghosh
    @brief  Solve the governing equations in time
*/

#include <stdio.h>
#include <math.h>
#include <string.h>
#include <vector>
#include <common_cpp.h>
#include <io_cpp.h>
#include <timeintegration_cpp.h>
#include <mpivars_cpp.h>
#include <simulation_object.h>

#ifdef with_librom
#include <librom_interface.h>
#endif

#ifdef with_veloc
#include <veloc.h>
#include <climits>
#endif

#ifdef compute_rhs_operators
extern "C" int ComputeRHSOperators(void*,void*,double);
#endif
extern "C" int CalculateError(void*,void*); /*!< Calculate the error in the final solution */
int OutputSolution(void*,int,double);   /*!< Write solutions to file */
extern "C" void ResetFilenameIndex(char*, int); /*!< Reset filename index */
#ifdef with_librom
extern "C" int CalculateROMDiff(void*,void*); /*!< Calculate the diff of PDE and ROM solutions */
int OutputROMSolution(void*,int,double);   /*!< Write ROM solutions to file */
#endif

/*! This function integrates the semi-discrete ODE (obtained from discretizing the
    PDE in space) using natively implemented time integration methods. It initializes
    the time integration object, iterates the simulation for the required number of
    time steps, and calculates the errors. After the specified number of iterations,
    it writes out some information to the screen and the solution to a file.
*/
int Solve(  void  *s,     /*!< Array of simulation objects of type #SimulationObject */
            int   nsims,  /*!< number of simulation objects */
            int   rank,   /*!< MPI rank of this process */
            int   nproc   /*!< Number of MPI processes */
         )
{
  SimulationObject* sim = (SimulationObject*) s;

  /* make sure none of the simulation objects sent in the array
   * are "barebones" type */
  for (int ns = 0; ns < nsims; ns++) {
    if (sim[ns].is_barebones == 1) {
      fprintf(stderr, "Error in Solve(): simulation object %d on rank %d is barebones!\n",
              ns, rank );
      return 1;
    }
  }

  /* write out iblank to file for visualization */
  for (int ns = 0; ns < nsims; ns++) {
    if (sim[ns].solver.flag_ib) {

      char fname_root[_MAX_STRING_SIZE_] = "iblank";
      if (nsims > 1) {
        char index[_MAX_STRING_SIZE_];
        GetStringFromInteger(ns, index, (int)log10((nsims)+1));
        strcat(fname_root, "_");
        strcat(fname_root, index);
      }

      WriteArray( sim[ns].solver.ndims,
                  1,
                  sim[ns].solver.dim_global,
                  sim[ns].solver.dim_local,
                  sim[ns].solver.ghosts,
                  sim[ns].solver.x,
                  sim[ns].solver.iblank,
                  &(sim[ns].solver),
                  &(sim[ns].mpi),
                  fname_root );
    }
  }

#ifdef with_librom
  if (!rank) printf("Setting up libROM interface.\n");
  libROMInterface rom_interface( sim, nsims, rank, nproc, sim[0].solver.dt );
  const std::string& rom_mode( rom_interface.mode() );
  std::vector<double> op_times_arr(0);
#endif

#ifdef with_librom
  if ((rom_mode == _ROM_MODE_TRAIN_) || (rom_mode == _ROM_MODE_NONE_)) {
#endif
    /* Define and initialize the time-integration object */
    TimeIntegration TS;
    if (!rank) printf("Setting up time integration.\n");
    TimeInitialize(sim, nsims, rank, nproc, &TS);
    double ti_runtime = 0.0;

#ifdef with_veloc
    /*
     * VeloC checkpoint/restart support.
     *
     * Register the solution arrays for each simulation domain and the
     * iteration counter / time with VELOC.  Memory IDs:
     *   0         : current iteration index (start_iter after restore)
     *   1         : simulation time (waqt)
     *   100+ns    : solution array for simulation domain ns
     */
    int veloc_ckpt_iter = 0;  /* current iteration checkpoint counter (for version) */
    int veloc_start_iter = 0; /* iteration to start from (0 unless restarting) */
    double veloc_waqt = 0.0;  /* simulation time to restore */

    /* Register meta-data scalars */
    VELOC_Mem_protect(0, &veloc_start_iter, 1, sizeof(int));
    VELOC_Mem_protect(1, &veloc_waqt,       1, sizeof(double));

    /* Register solution arrays */
    for (int ns = 0; ns < nsims; ns++) {
      long u_size = (long)sim[ns].solver.npoints_local_wghosts * sim[ns].solver.nvars;
      VELOC_Mem_protect(100 + ns, sim[ns].solver.u, (size_t)u_size, sizeof(double));
    }

    /* Check whether a restart checkpoint is available.
     * VELOC_Restart_test returns the latest version strictly less than the
     * given upper bound, or VELOC_FAILURE if none found.
     * Passing INT_MAX finds any available checkpoint. */
    int ckpt_version = VELOC_Restart_test("hypar_ckpt", INT_MAX);
    if (ckpt_version > 0) {  /* VELOC_FAILURE is -1; versions start at 1 */
      /* Restart from checkpoint */
      if (!rank) printf("VeloC: Restarting from checkpoint version %d.\n", ckpt_version);
      if (VELOC_Restart_begin("hypar_ckpt", ckpt_version) == VELOC_SUCCESS) {
        if (VELOC_Recover_mem() == VELOC_SUCCESS) {
          VELOC_Restart_end(1);
          /* Apply restored state */
          TS.start_iter = veloc_start_iter;
          TS.waqt       = veloc_waqt;
          TS.iter       = veloc_start_iter; /* loop below starts at iter=start_iter */
          /* Also update the per-simulation start_iter so downstream code is consistent */
          for (int ns = 0; ns < nsims; ns++) {
            sim[ns].solver.start_iter = veloc_start_iter;
          }
          veloc_ckpt_iter = ckpt_version; /* so next checkpoint gets a higher version */
          if (!rank) printf("VeloC: Restored to iteration %d, time %f.\n",
                            veloc_start_iter, veloc_waqt);
        } else {
          VELOC_Restart_end(0);
          if (!rank) printf("VeloC: Checkpoint recovery failed, starting from scratch.\n");
        }
      }
    } else {
      if (!rank) printf("VeloC: No checkpoint found, starting from scratch.\n");
    }

    /* Checkpoint frequency: use file_op_iter if set, else every 10 steps */
    int ckpt_freq = sim[0].solver.file_op_iter;
    if (ckpt_freq <= 0) ckpt_freq = 10;

    if (!rank) printf("Solving in time (from %d to %d iterations)\n", TS.start_iter, TS.n_iter);
    for (TS.iter = TS.start_iter; TS.iter < TS.n_iter; TS.iter++) {

#ifdef with_librom
      if ((rom_mode == _ROM_MODE_TRAIN_) && (TS.iter%rom_interface.samplingFrequency() == 0)) {
        rom_interface.takeSample( sim, TS.waqt );
      }
#endif

      /* Call pre-step function */
      TimePreStep (&TS);
#ifdef compute_rhs_operators
      /* compute and write (to file) matrix operators representing the right-hand side */
//      if (((TS.iter+1)%solver->file_op_iter == 0) || (!TS.iter))
//        { ComputeRHSOperators(solver,mpi,TS.waqt);
#endif

      /* Step in time */
      TimeStep (&TS);

      /* Call post-step function */
      TimePostStep (&TS);

      ti_runtime += TS.iter_wctime;

      /* Print information to screen */
      TimePrintStep(&TS);

      /* VeloC checkpoint: take a checkpoint at specified intervals */
      if (((TS.iter + 1) % ckpt_freq == 0) || (TS.iter + 1 == TS.n_iter)) {
        /* Prepare metadata for restart */
        veloc_start_iter = TS.iter + 1;    /* next iteration after this one */
        veloc_waqt       = TS.waqt;        /* current simulation time */
        veloc_ckpt_iter++;
        if (VELOC_Checkpoint_begin("hypar_ckpt", veloc_ckpt_iter) == VELOC_SUCCESS) {
          if (VELOC_Checkpoint_mem() == VELOC_SUCCESS) {
            VELOC_Checkpoint_end(1);
            if (!rank) printf("VeloC: Checkpoint taken at iteration %d (version %d).\n",
                              TS.iter + 1, veloc_ckpt_iter);
          } else {
            VELOC_Checkpoint_end(0);
            if (!rank) fprintf(stderr, "VeloC: Checkpoint failed at iteration %d.\n", TS.iter + 1);
          }
        }
      }
    }

#else /* no VeloC */

    if (!rank) printf("Solving in time (from %d to %d iterations)\n", 0, TS.n_iter);
    for (TS.iter = 0; TS.iter < TS.n_iter; TS.iter++) {

#ifdef with_librom
      if ((rom_mode == _ROM_MODE_TRAIN_) && (TS.iter%rom_interface.samplingFrequency() == 0)) {
        rom_interface.takeSample( sim, TS.waqt );
      }
#endif

      /* Call pre-step function */
      TimePreStep (&TS);
#ifdef compute_rhs_operators
      /* compute and write (to file) matrix operators representing the right-hand side */
//      if (((TS.iter+1)%solver->file_op_iter == 0) || (!TS.iter))
//        { ComputeRHSOperators(solver,mpi,TS.waqt);
#endif

      /* Step in time */
      TimeStep (&TS);

      /* Call post-step function */
      TimePostStep (&TS);

      ti_runtime += TS.iter_wctime;

      /* Print information to screen */
      TimePrintStep(&TS);

    }

#endif /* with_veloc */

    double t_final = TS.waqt;
    TimeCleanup(&TS);

    if (!rank) {
      printf( "Completed time integration (Final time: %f), total wctime: %f (seconds).\n",
              t_final, ti_runtime );
      if (nsims > 1) printf("\n");
    }

    /* calculate error if exact solution has been provided */
    for (int ns = 0; ns < nsims; ns++) {
      CalculateError(&(sim[ns].solver),
                     &(sim[ns].mpi) );
    }

#ifdef with_librom
    op_times_arr.push_back(TS.waqt);

    for (int ns = 0; ns < nsims; ns++) {
      ResetFilenameIndex( sim[ns].solver.filename_index,
                          sim[ns].solver.index_length );
    }

    if (rom_interface.mode() == _ROM_MODE_TRAIN_) {

      rom_interface.train();
      if (!rank) printf("libROM: total training wallclock time: %f (seconds).\n",
                        rom_interface.trainWallclockTime() );

      double total_rom_predict_time = 0;
      for (int iter = 0; iter < op_times_arr.size(); iter++) {

        double waqt = op_times_arr[iter];

        rom_interface.predict(sim, waqt);
        if (!rank) printf(  "libROM: Predicted solution at time %1.4e using ROM, wallclock time: %f.\n",
                            waqt, rom_interface.predictWallclockTime() );
        total_rom_predict_time += rom_interface.predictWallclockTime();

        /* calculate diff between ROM and PDE solutions */
        if (iter == (op_times_arr.size()-1)) {
          if (!rank) printf("libROM:   Calculating diff between PDE and ROM solutions.\n");
          for (int ns = 0; ns < nsims; ns++) {
            CalculateROMDiff(  &(sim[ns].solver),
                               &(sim[ns].mpi) );
          }
        }
        /* write the ROM solution to file */
        OutputROMSolution(sim, nsims,waqt);

      }

      if (!rank) {
        printf( "libROM: total prediction/query wallclock time: %f (seconds).\n",
                total_rom_predict_time );
      }

      rom_interface.saveROM();

    } else {

      for (int ns = 0; ns < nsims; ns++) {
        sim[ns].solver.rom_diff_norms[0]
          = sim[ns].solver.rom_diff_norms[1]
          = sim[ns].solver.rom_diff_norms[2]
          = -1;
      }

    }

  } else if (rom_mode == _ROM_MODE_PREDICT_) {

    for (int ns = 0; ns < nsims; ns++) {
      sim[ns].solver.rom_diff_norms[0]
        = sim[ns].solver.rom_diff_norms[1]
        = sim[ns].solver.rom_diff_norms[2]
        = -1;
      strcpy(sim[ns].solver.ConservationCheck,"no");
    }

    rom_interface.loadROM();
    rom_interface.projectInitialSolution(sim);

    {
      int start_iter = 0;
      int n_iter = sim[0].solver.n_iter;
      double dt = sim[0].solver.dt;

      double cur_time = start_iter * dt;
      op_times_arr.push_back(cur_time);

      for (int iter = start_iter; iter < n_iter; iter++) {
        cur_time += dt;
        if (    ( (iter+1)%sim[0].solver.file_op_iter == 0)
            &&  ( (iter+1) < n_iter) ) {
          op_times_arr.push_back(cur_time);
        }
      }

      double t_final = n_iter*dt;
      op_times_arr.push_back(t_final);
    }

    double total_rom_predict_time = 0;
    for (int iter = 0; iter < op_times_arr.size(); iter++) {

      double waqt = op_times_arr[iter];

      rom_interface.predict(sim, waqt);
      if (!rank) printf(  "libROM: Predicted solution at time %1.4e using ROM, wallclock time: %f.\n",
                          waqt, rom_interface.predictWallclockTime() );
      total_rom_predict_time += rom_interface.predictWallclockTime();

      /* write the solution to file */
      for (int ns = 0; ns < nsims; ns++) {
        if (sim[ns].solver.PhysicsOutput) {
          sim[ns].solver.PhysicsOutput( &(sim[ns].solver),
                                        &(sim[ns].mpi),
                                        waqt );
        }
      }
      OutputSolution(sim, nsims, waqt);

    }

    /* calculate error if exact solution has been provided */
    for (int ns = 0; ns < nsims; ns++) {
      CalculateError(&(sim[ns].solver),
                     &(sim[ns].mpi) );
    }

    if (!rank) {
      printf( "libROM: total prediction/query wallclock time: %f (seconds).\n",
              total_rom_predict_time );
    }

  }
#endif

  return 0;
}
