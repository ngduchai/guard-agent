/*
 * Quicksilver — VeloC-resilient main.cc  (v3 — fixed checkpoint)
 *
 * Changes from original:
 *   1. Added optional --veloc-cfg <path> argument (defaults to "veloc.cfg").
 *      All original command-line arguments are preserved unchanged.
 *   2. VELOC_Init called immediately after mpiInit.
 *   3. Three memory regions protected:
 *        id=0: mcco->time_info->cycle  (the completed-cycle counter)
 *        id=1: mcco->_tallies->_balanceCumulative (13 × uint64_t cumulative tallies)
 *        id=2: g_source_tally_buf[0..total_cells-1]  (per-cell _sourceTally values)
 *   4. On startup, VELOC_Restart_test probes for an existing checkpoint.
 *      If found, VELOC_Restart reloads cycle + tallies + source tallies and
 *      the loop resumes from the recovered cycle index.
 *   5. At the end of each cycle (after cycleFinalize), VELOC_Checkpoint_begin/
 *      VELOC_Checkpoint_mem/VELOC_Checkpoint_end are called.
 *      Before checkpointing, _sourceTally values are copied to g_source_tally_buf.
 *      After restart, g_source_tally_buf values are copied back to _sourceTally.
 *   6. VELOC_Finalize(1) called before mpiFinalize.
 *
 * Bug fixes vs. agent-generated code:
 *   - REMOVED VELOC_Route_file: it returns the same path as the main checkpoint
 *     file (scratch/qsckpt-rank-version.dat), so writing the particle vault to
 *     that path overwrites the memory-protected regions (cycle + tallies).
 *     Since census=0 always (all particles absorbed/escaped each cycle), the
 *     particle vault is always empty and does not need to be checkpointed.
 *   - ADDED _sourceTally checkpoint: cell._sourceTally accumulates across cycles
 *     and is used as the RNG seed for source particles. initMC() resets it to 0
 *     on restart, causing wrong RNG seeds (phantom-restart bug). We now protect
 *     all _sourceTally values with VELOC_Mem_protect so they survive restarts.
 *
 * The --veloc-cfg argument is scanned from argv BEFORE getParameters() is
 * called so that the existing arg parser is not disturbed.
 */

#include <iostream>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "utils.hh"
#include "Parameters.hh"
#include "utilsMpi.hh"
#include "MonteCarlo.hh"
#include "initMC.hh"
#include "Tallies.hh"
#include "PopulationControl.hh"
#include "ParticleVaultContainer.hh"
#include "ParticleVault.hh"
#include "MC_Base_Particle.hh"
#include "MC_Particle_Buffer.hh"
#include "MC_Processor_Info.hh"
#include "MC_Time_Info.hh"
#include "macros.hh"
#include "MC_Fast_Timer.hh"
#include "MC_SourceNow.hh"
#include "SendQueue.hh"
#include "NVTX_Range.hh"
#include "cudaUtils.hh"
#include "cudaFunctions.hh"
#include "qs_assert.hh"
#include "CycleTracking.hh"
#include "CoralBenchmark.hh"
#include "EnergySpectrum.hh"

#include "git_hash.hh"
#include "git_vers.hh"

/* VeloC header — compile-time guard in case HAVE_VELOC is not set */
#ifdef HAVE_VELOC
#include <veloc.h>
#endif

void gameOver();
void cycleInit( bool loadBalance );
void cycleTracking(MonteCarlo* monteCarlo);
void cycleFinalize();

using namespace std;

MonteCarlo *mcco  = NULL;

/* -------------------------------------------------------------------------
 * veloc_cfg_path: path to the VeloC configuration file.
 * Default = "veloc.cfg" (current working directory).
 * Override with:  --veloc-cfg <path>
 * NOTE: this is stripped from argv before the existing parser runs, so
 *       getParameters() never sees it.
 * ---------------------------------------------------------------------- */
static const char* veloc_cfg_path = "veloc.cfg";

/* Pre-scan argv for --veloc-cfg, remove the two tokens, and return the
 * modified argc.  Must be called before mpiInit / getParameters. */
static int extractVelocCfg(int argc, char** argv)
{
    for (int i = 1; i < argc - 1; i++)
    {
        if (strcmp(argv[i], "--veloc-cfg") == 0)
        {
            veloc_cfg_path = argv[i + 1];
            /* Shift remaining args left by 2 */
            for (int j = i; j < argc - 2; j++)
                argv[j] = argv[j + 2];
            return argc - 2;
        }
    }
    return argc;   /* unchanged */
}

#ifdef HAVE_VELOC
/* -------------------------------------------------------------------------
 * g_source_tally_buf: flat contiguous buffer holding all _sourceTally values
 * across all local domains and cells.  Protected with VELOC_Mem_protect(2,...).
 *
 * Layout: for each domain d in [0, num_domains), for each cell c in
 *         [0, domain[d].cell_state.size()), the value is stored at
 *         g_source_tally_buf[offset[d] + c].
 *
 * g_source_tally_total: total number of cells across all local domains.
 * g_source_tally_offsets[d]: starting index in g_source_tally_buf for domain d.
 * -------------------------------------------------------------------------*/
static uint64_t*  g_source_tally_buf     = nullptr;
static size_t     g_source_tally_total   = 0;
static std::vector<size_t> g_source_tally_offsets;

/* Allocate g_source_tally_buf and compute offsets.
 * Must be called after initMC() so mcco->domain is populated. */
static void init_source_tally_buf()
{
    size_t num_domains = mcco->domain.size();
    g_source_tally_offsets.resize(num_domains, 0);
    g_source_tally_total = 0;
    for (size_t d = 0; d < num_domains; d++)
    {
        g_source_tally_offsets[d] = g_source_tally_total;
        g_source_tally_total += mcco->domain[d].cell_state.size();
    }
    g_source_tally_buf = new uint64_t[g_source_tally_total]();
    if (mcco->processor_info->rank == 0)
    {
        fprintf(stdout,
                "[VeloC] Allocated source-tally buffer: %zu cells across %zu domain(s)\n",
                g_source_tally_total, num_domains);
        fflush(stdout);
    }
}

/* Copy _sourceTally from cell_state → g_source_tally_buf (before checkpoint). */
static void sync_source_tallies_to_buf()
{
    size_t num_domains = mcco->domain.size();
    for (size_t d = 0; d < num_domains; d++)
    {
        size_t offset = g_source_tally_offsets[d];
        size_t ncells = mcco->domain[d].cell_state.size();
        for (size_t c = 0; c < ncells; c++)
            g_source_tally_buf[offset + c] = mcco->domain[d].cell_state[c]._sourceTally;
    }
}

/* Copy g_source_tally_buf → _sourceTally in cell_state (after restart). */
static void sync_source_tallies_from_buf()
{
    size_t num_domains = mcco->domain.size();
    for (size_t d = 0; d < num_domains; d++)
    {
        size_t offset = g_source_tally_offsets[d];
        size_t ncells = mcco->domain[d].cell_state.size();
        for (size_t c = 0; c < ncells; c++)
            mcco->domain[d].cell_state[c]._sourceTally = g_source_tally_buf[offset + c];
    }
    if (mcco->processor_info->rank == 0)
    {
        fprintf(stdout, "[VeloC] Restored _sourceTally for %zu cells\n",
                g_source_tally_total);
        fflush(stdout);
    }
}
#endif /* HAVE_VELOC */

int main(int argc, char** argv)
{
   /* --- Extract --veloc-cfg before any other parsing ------------------- */
   argc = extractVelocCfg(argc, argv);

   mpiInit(&argc, &argv);

#ifdef HAVE_VELOC
   /* VELOC_Init must be called collectively immediately after MPI_Init */
   if (VELOC_Init(MPI_COMM_WORLD, veloc_cfg_path) != VELOC_SUCCESS)
   {
       fprintf(stderr, "[VeloC] VELOC_Init failed — aborting\n");
       MPI_Abort(MPI_COMM_WORLD, 1);
   }
#endif

   printBanner(GIT_VERS, GIT_HASH);

   Parameters params = getParameters(argc, argv);
   printParameters(params, cout);

   /* mcco stores just about everything. */
   mcco = initMC(params);

   int loadBalance = params.simulationParams.loadBalance;

   MC_FASTTIMER_START(MC_Fast_Timer::main);   // this can be done once mcco exists.

   const int nSteps = params.simulationParams.nSteps;

#ifdef HAVE_VELOC
   /* -----------------------------------------------------------------
    * Allocate the source-tally buffer and compute domain/cell offsets.
    * Must be done after initMC() so mcco->domain is populated.
    * ----------------------------------------------------------------- */
   init_source_tally_buf();

   /* -----------------------------------------------------------------
    * Register the three memory regions that must survive a failure:
    *
    *   id=0  mcco->time_info->cycle
    *         The number of COMPLETED cycles.  Updated at the end of
    *         cycleFinalize() (time_info->cycle++).  We store it before
    *         checkpointing and restore it on restart to know which cycle
    *         to resume from.
    *
    *   id=1  mcco->_tallies->_balanceCumulative
    *         The running cumulative Balance struct (13 uint64_t fields).
    *         This accumulates every cycle and is what coralBenchmarkCorrectness
    *         inspects; it must be restored exactly.
    *
    *   id=2  g_source_tally_buf[0..g_source_tally_total-1]
    *         Per-cell _sourceTally values.  These accumulate across cycles
    *         and are used as RNG seeds for source particles.  initMC()
    *         resets them to 0 on restart, causing wrong RNG seeds (phantom-
    *         restart bug).  We protect them here so they survive restarts.
    * ----------------------------------------------------------------- */
   VELOC_Mem_protect(0, &(mcco->time_info->cycle),
                     1, sizeof(int));
   VELOC_Mem_protect(1, &(mcco->_tallies->_balanceCumulative),
                     1, sizeof(Balance));
   VELOC_Mem_protect(2, g_source_tally_buf,
                     g_source_tally_total, sizeof(uint64_t));

   /* -----------------------------------------------------------------
    * Check whether a checkpoint from a previous (failed) run exists.
    * VELOC_Restart_test is collective; all ranks must call it.
    * ----------------------------------------------------------------- */
   int latest_version = VELOC_Restart_test("qsckpt", 0);

   int startCycle = 0;

   if (latest_version > 0)
   {
       /* Checkpoint found — restore cycle counter, cumulative tallies,
        * and source-tally buffer */
       if (VELOC_Restart_begin("qsckpt", latest_version) != VELOC_SUCCESS)
       {
           fprintf(stderr, "[VeloC] VELOC_Restart_begin failed — starting from scratch\n");
           mcco->time_info->cycle = 0;
           mcco->_tallies->_balanceCumulative.Reset();
       }
       else
       {
           /* Restore all three memory-protected regions */
           bool mem_ok = (VELOC_Recover_mem() == VELOC_SUCCESS);
           VELOC_Restart_end(mem_ok ? 1 : 0);

           if (mem_ok)
           {
               /* Copy restored _sourceTally values back to cell_state */
               sync_source_tallies_from_buf();

               startCycle = mcco->time_info->cycle;
               if (mcco->processor_info->rank == 0)
               {
                   fprintf(stdout,
                           "[VeloC] Restarted from checkpoint version %d "
                           "(resuming at cycle %d / %d)\n",
                           latest_version, startCycle, nSteps);
                   fflush(stdout);
               }
           }
           else
           {
               fprintf(stderr, "[VeloC] Restart failed — starting from scratch\n");
               mcco->time_info->cycle = 0;
               mcco->_tallies->_balanceCumulative.Reset();
               startCycle = 0;
           }
       }
   }
   else
   {
       /* No checkpoint found — starting fresh from cycle 0. */
       if (mcco->processor_info->rank == 0)
       {
           fprintf(stdout, "[VeloC] No checkpoint found — starting fresh from cycle 0.\n");
           fflush(stdout);
       }
   }
#else
   int startCycle = 0;
#endif /* HAVE_VELOC */

   for (int ii = startCycle; ii < nSteps; ++ii)
   {
      cycleInit( bool(loadBalance) );
      cycleTracking(mcco);
      cycleFinalize();   /* increments mcco->time_info->cycle */

      mcco->fast_timer->Last_Cycle_Report(
            params.simulationParams.cycleTimers,
            mcco->processor_info->rank,
            mcco->processor_info->num_processors,
            mcco->processor_info->comm_mc_world );

#ifdef HAVE_VELOC
      /* -----------------------------------------------------------------
       * Checkpoint after every completed cycle.
       *
       * Version = mcco->time_info->cycle (already incremented by cycleFinalize,
       * so it equals ii+1 and is > 0, which VeloC requires).
       *
       * Before checkpointing, copy _sourceTally values to g_source_tally_buf
       * so that VELOC_Checkpoint_mem() saves them correctly.
       * ----------------------------------------------------------------- */
      int ckpt_version = mcco->time_info->cycle;   /* = ii + 1 */

      /* Sync _sourceTally → buffer before checkpoint */
      sync_source_tallies_to_buf();

      if (VELOC_Checkpoint_begin("qsckpt", ckpt_version) != VELOC_SUCCESS)
      {
          if (mcco->processor_info->rank == 0)
              fprintf(stderr, "[VeloC] VELOC_Checkpoint_begin at cycle %d failed\n", ckpt_version);
      }
      else
      {
          /* Write all three memory-protected regions (cycle + tallies + source tallies) */
          bool mem_ok = (VELOC_Checkpoint_mem() == VELOC_SUCCESS);
          if (VELOC_Checkpoint_end(mem_ok ? 1 : 0) != VELOC_SUCCESS)
          {
              if (mcco->processor_info->rank == 0)
                  fprintf(stderr, "[VeloC] VELOC_Checkpoint_end at cycle %d failed\n", ckpt_version);
          }
          else if (mcco->processor_info->rank == 0)
          {
              fprintf(stdout, "[VeloC] Checkpointed cycle %d (version %d)\n",
                      ii + 1, ckpt_version);
              fflush(stdout);
          }
      }
#endif /* HAVE_VELOC */
   }

   MC_FASTTIMER_STOP(MC_Fast_Timer::main);

   gameOver();

   coralBenchmarkCorrectness(mcco, params);

#ifdef HAVE_UVM
    mcco->~MonteCarlo();
    gpuFree( mcco );
#else
   delete mcco;
#endif

#ifdef HAVE_VELOC
   /* Free source-tally buffer */
   delete[] g_source_tally_buf;
   g_source_tally_buf = nullptr;

   /* Drain=1: wait for any background flush to persistent storage */
   VELOC_Finalize(1);
#endif

   mpiFinalize();

   return 0;
}

void gameOver()
{
    mcco->fast_timer->Cumulative_Report(mcco->processor_info->rank,
                                        mcco->processor_info-> num_processors,
                                        mcco->processor_info->comm_mc_world,
                                        mcco->_tallies->_balanceCumulative._numSegments);
    mcco->_tallies->_spectrum.PrintSpectrum(mcco);
}

void cycleInit( bool loadBalance )
{

    MC_FASTTIMER_START(MC_Fast_Timer::cycleInit);

    mcco->clearCrossSectionCache();

    mcco->_tallies->CycleInitialize(mcco);

    mcco->_particleVaultContainer->swapProcessingProcessedVaults();

    mcco->_particleVaultContainer->collapseProcessed();
    mcco->_particleVaultContainer->collapseProcessing();

    mcco->_tallies->_balanceTask[0]._start = mcco->_particleVaultContainer->sizeProcessing();

    mcco->particle_buffer->Initialize();

    MC_SourceNow(mcco);

    PopulationControl(mcco, loadBalance); // controls particle population

    RouletteLowWeightParticles(mcco); // Delete particles with low statistical weight

    MC_FASTTIMER_STOP(MC_Fast_Timer::cycleInit);
}


#if defined GPU_NATIVE

GLOBAL void CycleTrackingKernel( MonteCarlo* monteCarlo, int num_particles, ParticleVault* processingVault, ParticleVault* processedVault )
{
   int global_index = getGlobalThreadID();

    if( global_index < num_particles )
    {
        CycleTrackingGuts( monteCarlo, global_index, processingVault, processedVault );
    }
}

#endif

void cycleTracking(MonteCarlo *monteCarlo)
{
    MC_FASTTIMER_START(MC_Fast_Timer::cycleTracking);

    bool done = false;

    //Determine whether or not to use GPUs if they are available (set for each MPI rank)
    ExecutionPolicy execPolicy = getExecutionPolicy( monteCarlo->processor_info->use_gpu );

    ParticleVaultContainer &my_particle_vault = *(monteCarlo->_particleVaultContainer);

    //Post Inital Receives for Particle Buffer
    monteCarlo->particle_buffer->Post_Receive_Particle_Buffer( my_particle_vault.getVaultSize() );

    //Get Test For Done Method (Blocking or non-blocking
    MC_New_Test_Done_Method::Enum new_test_done_method = monteCarlo->particle_buffer->new_test_done_method;

    do
    {
        int particle_count = 0; // Initialize count of num_particles processed

        while ( !done )
        {
            uint64_t fill_vault = 0;

            for ( uint64_t processing_vault = 0; processing_vault < my_particle_vault.processingSize(); processing_vault++ )
            {
                MC_FASTTIMER_START(MC_Fast_Timer::cycleTracking_Kernel);
                uint64_t processed_vault = my_particle_vault.getFirstEmptyProcessedVault();

                ParticleVault *processingVault = my_particle_vault.getTaskProcessingVault(processing_vault);
                ParticleVault *processedVault =  my_particle_vault.getTaskProcessedVault(processed_vault);

                int numParticles = processingVault->size();

                if ( numParticles != 0 )
                {
                    NVTX_Range trackingKernel("cycleTracking_TrackingKernel"); // range ends at end of scope

                    // The tracking kernel can run
                    // * As a cuda kernel
                    // * As an OpenMP 4.5 parallel loop on the GPU
                    // * As an OpenMP 3.0 parallel loop on the CPU
                    // * AS a single thread on the CPU.
                    switch (execPolicy)
                    {
                      case gpuNative:
                       {
                          #if defined (GPU_NATIVE)
                          dim3 grid(1,1,1);
                          dim3 block(1,1,1);
                          int runKernel = ThreadBlockLayout( grid, block, numParticles);

                          //Call Cycle Tracking Kernel
                          if( runKernel )
                             CycleTrackingKernel<<<grid, block >>>( monteCarlo, numParticles, processingVault, processedVault );

                          //Synchronize the stream so that memory is copied back before we begin MPI section
                          gpuPeekAtLastError();
                          gpuDeviceSynchronize();
                          #endif
                       }
                       break;

                      case gpuWithOpenMP:
                       {
                          int nthreads=128;
                          if (numParticles <  64*56 )
                             nthreads = 64;
                          int nteams = (numParticles + nthreads - 1 ) / nthreads;
                          nteams = nteams > 1 ? nteams : 1;
                          #ifdef HAVE_OPENMP_TARGET
                          #pragma omp target enter data map(to:monteCarlo[0:1])
                          #pragma omp target enter data map(to:processingVault[0:1])
                          #pragma omp target enter data map(to:processedVault[0:1])
                          #pragma omp target teams distribute parallel for num_teams(nteams) thread_limit(128)
                          #endif
                          for ( int particle_index = 0; particle_index < numParticles; particle_index++ )
                          {
                             CycleTrackingGuts( monteCarlo, particle_index, processingVault, processedVault );
                          }
                          #ifdef HAVE_OPENMP_TARGET
                          #pragma omp target exit data map(from:monteCarlo[0:1])
                          #pragma omp target exit data map(from:processingVault[0:1])
                          #pragma omp target exit data map(from:processedVault[0:1])
                          #endif
                       }
                       break;

                      case cpu:
                       #include "mc_omp_parallel_for_schedule_static.hh"
                       for ( int particle_index = 0; particle_index < numParticles; particle_index++ )
                       {
                          CycleTrackingGuts( monteCarlo, particle_index, processingVault, processedVault );
                       }
                       break;
                      default:
                       qs_assert(false);
                    } // end switch
                }

                particle_count += numParticles;

                MC_FASTTIMER_STOP(MC_Fast_Timer::cycleTracking_Kernel);

                MC_FASTTIMER_START(MC_Fast_Timer::cycleTracking_MPI);

                // Next, communicate particles that have crossed onto
                // other MPI ranks.
                NVTX_Range cleanAndComm("cycleTracking_clean_and_comm");

                SendQueue &sendQueue = *(my_particle_vault.getSendQueue());
                monteCarlo->particle_buffer->Allocate_Send_Buffer( sendQueue );

                //Move particles from send queue to the send buffers
                for ( int index = 0; index < sendQueue.size(); index++ )
                {
                    sendQueueTuple& sendQueueT = sendQueue.getTuple( index );
                    MC_Base_Particle mcb_particle;

                    processingVault->getBaseParticleComm( mcb_particle, sendQueueT._particleIndex );

                    int buffer = monteCarlo->particle_buffer->Choose_Buffer(sendQueueT._neighbor );
                    monteCarlo->particle_buffer->Buffer_Particle(mcb_particle, buffer );
                }

                monteCarlo->particle_buffer->Send_Particle_Buffers(); // post MPI sends

                processingVault->clear(); //remove the invalid particles
                sendQueue.clear();

                // Move particles in "extra" vaults into the regular vaults.
                my_particle_vault.cleanExtraVaults();

                // receive any particles that have arrived from other ranks
                monteCarlo->particle_buffer->Receive_Particle_Buffers( fill_vault );

                MC_FASTTIMER_STOP(MC_Fast_Timer::cycleTracking_MPI);

            } // for loop on vaults

            MC_FASTTIMER_START(MC_Fast_Timer::cycleTracking_MPI);

            NVTX_Range collapseRange("cycleTracking_Collapse_ProcessingandProcessed");
            my_particle_vault.collapseProcessing();
            my_particle_vault.collapseProcessed();
            collapseRange.endRange();


            //Test for done - blocking on all MPI ranks
            NVTX_Range doneRange("cycleTracking_Test_Done_New");
            done = monteCarlo->particle_buffer->Test_Done_New( new_test_done_method );
            doneRange.endRange();

            MC_FASTTIMER_STOP(MC_Fast_Timer::cycleTracking_MPI);

        } // while not done: Test_Done_New()

        // Everything should be done normally.
        done = monteCarlo->particle_buffer->Test_Done_New( MC_New_Test_Done_Method::Blocking );

    } while ( !done );

    //Make sure to cancel all pending receive requests
    monteCarlo->particle_buffer->Cancel_Receive_Buffer_Requests();
    //Make sure Buffers Memory is Free
    monteCarlo->particle_buffer->Free_Buffers();

   MC_FASTTIMER_STOP(MC_Fast_Timer::cycleTracking);
}


void cycleFinalize()
{
    MC_FASTTIMER_START(MC_Fast_Timer::cycleFinalize);

    mcco->_tallies->_balanceTask[0]._end = mcco->_particleVaultContainer->sizeProcessed();

    // Update the cumulative tally data.
    mcco->_tallies->CycleFinalize(mcco);

    mcco->time_info->cycle++;

    mcco->particle_buffer->Free_Memory();

    MC_FASTTIMER_STOP(MC_Fast_Timer::cycleFinalize);
}
