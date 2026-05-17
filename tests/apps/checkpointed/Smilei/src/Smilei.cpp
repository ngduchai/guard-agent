////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
////                                                                                                                ////
////                                                                                                                ////
////                                   PARTICLE-IN-CELL CODE SMILEI                                                 ////
////                    Simulation of Matter Irradiated by Laser at Extreme Intensity                               ////
////                                                                                                                ////
////                          Cooperative OpenSource Object-Oriented Project                                        ////
////                                      from the Plateau de Saclay                                                ////
////                                          started January 2013                                                  ////
////                                                                                                                ////
////                                                                                                                ////
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

#include <ctime>
#include <cstdlib>
#include <cstdio>
#include <unistd.h>
#include <iostream>
#include <iomanip>
#include <string>
#include <vector>
#include <limits>
#include <algorithm>
#include <mpi.h>
#include <omp.h>
#ifdef SMILEI_ACCELERATOR_GPU_OACC
#include <openacc.h>
#endif

#include "Smilei.h"
#include "SmileiMPI_test.h"
#include "Params.h"
#include "PatchesFactory.h"
#include "SyncVectorPatch.h"
#include "Checkpoint.h"
#include "Solver.h"
#include "SimWindow.h"
#include "Diagnostic.h"
#include "Region.h"
#include "DoubleGrids.h"
#include "DoubleGridsAM.h"
#include "Timers.h"
// Explicit includes for the validation-signature dump function below.
// VectorPatch / Particles / Species are pulled in transitively via
// SyncVectorPatch.h, but ElectroMagn.h and Field.h are not — so add them
// here to access EM->Ex_ etc. and Field::data_/number_of_points_ directly.
#include "ElectroMagn.h"
#include "Field.h"
#include "Species.h"
#include "Particles.h"

using namespace std;

// ---------------------------------------------------------------------------------------------------------------------
//                                                   MAIN CODE
// ---------------------------------------------------------------------------------------------------------------------

// Compute physics-derived scalar reductions over the FINAL EM-field state
// and the FINAL particle state.  Mirrors the vanilla; used by the
// validation framework as the golden-vs-recovery comparison anchor.  Dumps
// OUTPUT only (the user-facing PIC state at end of simulation), not
// internal scratch / diagnostic / timer state.
static void dumpValidationSignatureSmilei( VectorPatch &vecPatches, SmileiMPI &smpi )
{
    // Mirrors vanilla v48 dump: 7 EM fields × 5 stats + 2 species × 3
    // quantities × 5 stats = 65 doubles, written to validation_output.bin
    // in process memory layout.  Read by NumericToleranceComparator
    // (np.fromfile dtype=float64), diffed at relative tolerance 1e-12.
    std::vector<double> outvals;

    auto reduce_field = [&]( const char *name, Field *(*get)( ElectroMagn * ),
                             VectorPatch &vp, SmileiMPI &mpi ) {
        double local_sum = 0.0, local_sum2 = 0.0;
        double local_max = -std::numeric_limits<double>::infinity();
        double local_min =  std::numeric_limits<double>::infinity();
        long   local_count = 0;
        for( unsigned int ipatch = 0; ipatch < vp.size(); ++ipatch ) {
            ElectroMagn *EM = vp( ipatch )->EMfields;
            if( !EM ) continue;
            Field *f = get( EM );
            if( !f || !f->data() ) continue;
            const unsigned int n = f->number_of_points_;
            const double *d = f->data();
            for( unsigned int i = 0; i < n; ++i ) {
                const double v = d[i];
                local_sum  += v;
                local_sum2 += v * v;
                if( v > local_max ) local_max = v;
                if( v < local_min ) local_min = v;
            }
            local_count += static_cast<long>(n);
        }
        double agg[2] = { local_sum, local_sum2 };
        MPI_Allreduce( MPI_IN_PLACE, agg,         2, MPI_DOUBLE, MPI_SUM, mpi.world() );
        MPI_Allreduce( MPI_IN_PLACE, &local_max,  1, MPI_DOUBLE, MPI_MAX, mpi.world() );
        MPI_Allreduce( MPI_IN_PLACE, &local_min,  1, MPI_DOUBLE, MPI_MIN, mpi.world() );
        MPI_Allreduce( MPI_IN_PLACE, &local_count,1, MPI_LONG,   MPI_SUM, mpi.world() );
        if( mpi.isMaster() ) {
            std::cout << "VALIDATION_SIGNATURE:"
                      << " field=" << name
                      << " sum="   << std::scientific << std::setprecision(10) << agg[0]
                      << " sum2="  << agg[1]
                      << " max="   << local_max
                      << " min="   << local_min
                      << " count=" << local_count << std::endl;
            outvals.push_back( agg[0] );
            outvals.push_back( agg[1] );
            outvals.push_back( local_max );
            outvals.push_back( local_min );
            outvals.push_back( static_cast<double>( local_count ) );
        }
    };

    reduce_field( "Ex",  []( ElectroMagn *EM ){ return EM->Ex_;  }, vecPatches, smpi );
    reduce_field( "Ey",  []( ElectroMagn *EM ){ return EM->Ey_;  }, vecPatches, smpi );
    reduce_field( "Ez",  []( ElectroMagn *EM ){ return EM->Ez_;  }, vecPatches, smpi );
    reduce_field( "Bx",  []( ElectroMagn *EM ){ return EM->Bx_;  }, vecPatches, smpi );
    reduce_field( "By",  []( ElectroMagn *EM ){ return EM->By_;  }, vecPatches, smpi );
    reduce_field( "Bz",  []( ElectroMagn *EM ){ return EM->Bz_;  }, vecPatches, smpi );
    reduce_field( "rho", []( ElectroMagn *EM ){ return EM->rho_; }, vecPatches, smpi );

    if( vecPatches.size() > 0 ) {
        const unsigned int nSpecies = vecPatches( 0 )->vecSpecies.size();
        for( unsigned int ispec = 0; ispec < nSpecies; ++ispec ) {
            long   n_particles = 0;
            double w_sum = 0.0, w_sum2 = 0.0;
            double w_max = -std::numeric_limits<double>::infinity();
            double w_min =  std::numeric_limits<double>::infinity();
            double x_sum = 0.0, x_sum2 = 0.0;
            double x_max = -std::numeric_limits<double>::infinity();
            double x_min =  std::numeric_limits<double>::infinity();
            double p_sum = 0.0, p_sum2 = 0.0;
            double p_max = -std::numeric_limits<double>::infinity();
            double p_min =  std::numeric_limits<double>::infinity();
            for( unsigned int ipatch = 0; ipatch < vecPatches.size(); ++ipatch ) {
                Particles *parts = vecPatches( ipatch )->vecSpecies[ispec]->particles;
                if( !parts ) continue;
                const unsigned int np = parts->size();
                for( unsigned int ip = 0; ip < np; ++ip ) {
                    const double w = parts->weight( ip );
                    w_sum += w; w_sum2 += w * w;
                    if( w > w_max ) w_max = w;
                    if( w < w_min ) w_min = w;
                    const double x = parts->position( 0, ip );
                    x_sum += x; x_sum2 += x * x;
                    if( x > x_max ) x_max = x;
                    if( x < x_min ) x_min = x;
                    const double p = parts->momentum( 0, ip );
                    p_sum += p; p_sum2 += p * p;
                    if( p > p_max ) p_max = p;
                    if( p < p_min ) p_min = p;
                }
                n_particles += static_cast<long>( np );
            }
            double agg[6] = { w_sum, w_sum2, x_sum, x_sum2, p_sum, p_sum2 };
            MPI_Allreduce( MPI_IN_PLACE, agg,           6, MPI_DOUBLE, MPI_SUM, smpi.world() );
            MPI_Allreduce( MPI_IN_PLACE, &n_particles,  1, MPI_LONG,   MPI_SUM, smpi.world() );
            double mx[3] = { w_max, x_max, p_max };
            double mn[3] = { w_min, x_min, p_min };
            MPI_Allreduce( MPI_IN_PLACE, mx, 3, MPI_DOUBLE, MPI_MAX, smpi.world() );
            MPI_Allreduce( MPI_IN_PLACE, mn, 3, MPI_DOUBLE, MPI_MIN, smpi.world() );
            if( smpi.isMaster() ) {
                const std::string &sname = vecPatches( 0 )->vecSpecies[ispec]->name_;
                std::cout << std::scientific << std::setprecision(10);
                std::cout << "VALIDATION_SIGNATURE: species=" << sname
                          << " field=weight"
                          << " sum=" << agg[0] << " sum2=" << agg[1]
                          << " max=" << mx[0]  << " min="  << mn[0]
                          << " count=" << n_particles << std::endl;
                std::cout << "VALIDATION_SIGNATURE: species=" << sname
                          << " field=position_x"
                          << " sum=" << agg[2] << " sum2=" << agg[3]
                          << " max=" << mx[1]  << " min="  << mn[1]
                          << " count=" << n_particles << std::endl;
                std::cout << "VALIDATION_SIGNATURE: species=" << sname
                          << " field=momentum_x"
                          << " sum=" << agg[4] << " sum2=" << agg[5]
                          << " max=" << mx[2]  << " min="  << mn[2]
                          << " count=" << n_particles << std::endl;
                outvals.push_back( agg[0] );
                outvals.push_back( agg[1] );
                outvals.push_back( mx[0] );
                outvals.push_back( mn[0] );
                outvals.push_back( static_cast<double>( n_particles ) );
                outvals.push_back( agg[2] );
                outvals.push_back( agg[3] );
                outvals.push_back( mx[1] );
                outvals.push_back( mn[1] );
                outvals.push_back( static_cast<double>( n_particles ) );
                outvals.push_back( agg[4] );
                outvals.push_back( agg[5] );
                outvals.push_back( mx[2] );
                outvals.push_back( mn[2] );
                outvals.push_back( static_cast<double>( n_particles ) );
            }
        }
    }

    if( smpi.isMaster() ) {
        std::FILE *fp = std::fopen( "validation_output.bin", "wb" );
        if( fp != nullptr ) {
            std::fwrite( outvals.data(), sizeof(double), outvals.size(), fp );
            std::fclose( fp );
            std::cout << "VALIDATION_SIGNATURE: file=validation_output.bin"
                      << " n_doubles=" << outvals.size() << std::endl;
        }
    }
}

#ifdef SMILEI_ACCELERATOR_GPU_OACC
    #ifdef _OPENACC
    void initialization_openacc()
    {
        char* local_rank_env;
        int local_rank;

        // Initialization of OpenACC
        #pragma acc init

        /* Recovery of the local rank of the process via the environment variable
           set by Slurm, as MPI_Comm_rank cannot be used here because this routine
           is used BEFORE the initialisation of MPI*/
        local_rank_env = getenv("SLURM_LOCALID");
        // Second try on a PBS cluster
        if( ! local_rank_env ) {
            local_rank_env = getenv("PMI_LOCAL_RANK");
        }
        
        if( local_rank_env ) {
            local_rank = atoi( local_rank_env );
            // Define the GPU to use via OpenACC
            acc_set_device_num( local_rank, acc_get_device_type() );
        } else {
            printf( "Error : impossible to determine the local rank of MPI process.\n" );
            exit( 1 );
        }
    }
    #endif
#endif

int main( int argc, char *argv[] )
{
    cout.setf( ios::fixed,  ios::floatfield ); // floatfield set to fixed

    // -------------------------
    // Simulation Initialization
    // -------------------------

    // Create the OpenACC environment
#ifdef SMILEI_ACCELERATOR_GPU_OACC
    initialization_openacc();
#endif

    // Create MPI environment :
#ifdef SMILEI_TESTMODE
    SmileiMPI_test smpi( &argc, &argv );
#else
    SmileiMPI smpi( &argc, &argv );
#endif

    MESSAGE( "                   _            _" );
    MESSAGE( " ___           _  | |        _  \\ \\   Version : " << __VERSION );
    MESSAGE( "/ __|  _ __   (_) | |  ___  (_)  | |   " );
    MESSAGE( "\\__ \\ | '  \\   _  | | / -_)  _   | |" );
    MESSAGE( "|___/ |_|_|_| |_| |_| \\___| |_|  | |  " );
    MESSAGE( "                                /_/    " );
    MESSAGE( "" );

    // Read and print simulation parameters
    TITLE( "Reading the simulation parameters" );
    Params params( &smpi, vector<string>( argv + 1, argv + argc ) );
    OpenPMDparams openPMD( params );
    PyTools::setIteration( 0 );

#if defined( SMILEI_ACCELERATOR_GPU_OMP )
    SMILEI_ASSERT( params.gpu_computing );

    if( ::omp_get_max_threads() != 1 ) {
        // TODO(Etienne M): I believe there is a race condition inside the CCE OpenMP runtime so I constrain Smilei
        // GPU to use only one thread.
        WARNING( "Running Smilei on GPU using more than one OpenMP thread is not fully supported when offloading using OpenMP." );
    }

    const int gpu_count = ::omp_get_num_devices();

    if( gpu_count < 1 ) {
        ERROR( "Smilei needs one accelerator, none detected." );
    } else if( gpu_count > 1 ) {
        // NOTE: We do not support multi gpu per MPI proc in OpenMP mode
        // (nor in OpenACC). This makes management of the device completely
        // oblivious to the program (only one, the one by default).
        // This could be a missed but very advanced optimization for some
        // kernels/exchange.
        ERROR( "Smilei needs only one accelerator (GPU). Look for HIP_VISIBLE_DEVICES or 'gpu-bind=closest' in your SLURM script or use a custom binding script." );
    } else {
        // ::omp_set_default_device(0);
    }

    ::omp_sched_t a_scheduling_strategy{};
    int           a_chunk_size = 0;
    ::omp_get_schedule( &a_scheduling_strategy, &a_chunk_size );

    if( a_scheduling_strategy != ::omp_sched_t::omp_sched_dynamic ) {
        // As of CCE 13, 2022/04/22
        WARNING( "Smilei can break if dynamic is not used." );
    }
#endif

    // Need to move it here because of domain decomposition need in smpi->init(_patch_count)
    //     abstraction of Hilbert curve
    VectorPatch vecPatches( params );
    Region region( params );

    // Initialize MPI environment with simulation parameters
    TITLE( "Initializing MPI" );
    smpi.init( params, vecPatches.domain_decomposition_ );

    // Create timers
    Timers timers( &smpi );

    // Print in stdout MPI, OpenMP, patchs parameters
    params.print_parallelism_params( &smpi );

    TITLE( "Initializing the restart environment" );
    Checkpoint checkpoint( params, &smpi );

    // ------------------------------------------------------------------------
    // Initialize the simulation times time_prim at n=0 and time_dual at n=+1/2
    // Update in "if restart" if necessary
    // ------------------------------------------------------------------------

    // time at integer time-steps (primal grid)
    double time_prim = 0;
    // time at half-integer time-steps (dual grid)
    double time_dual = 0.5 * params.timestep;

    // --------------------
    // Define Moving Window
    // --------------------
    SimWindow *simWindow = new SimWindow( params );

    // ------------------------------------------------------------------------
    // Init nonlinear inverse Compton scattering
    // ------------------------------------------------------------------------
    RadiationTables radiation_tables_;

    // ------------------------------------------------------------------------
    // Create multiphoton_Breit_Wheeler_tables_ object for multiphoton
    // Breit-Wheeler pair creation
    // ------------------------------------------------------------------------
    MultiphotonBreitWheelerTables multiphoton_Breit_Wheeler_tables_;

    // ---------------------------------------------------
    // Special test mode
    // ---------------------------------------------------
    if( smpi.test_mode ) {
        executeTestMode( vecPatches, region, &smpi, simWindow, params, checkpoint, openPMD, &radiation_tables_ );
        return 0;
    }

    // ---------------------------------------------------------------------
    // Init and compute tables for radiation effects
    // (nonlinear inverse Compton scattering)
    // ---------------------------------------------------------------------
    radiation_tables_.initialization( params, &smpi);

    // ---------------------------------------------------------------------
    // Init and compute tables for multiphoton Breit-Wheeler pair creation
    // ---------------------------------------------------------------------
    multiphoton_Breit_Wheeler_tables_.initialization( params, &smpi );

    // reading from dumped file the restart values
    if( params.restart ) {
        // smpi.patch_count recomputed in readPatchDistribution
        checkpoint.readPatchDistribution( &smpi, simWindow );
        // allocate patches according to smpi.patch_count
        PatchesFactory::createVector( vecPatches, params, &smpi, openPMD, &radiation_tables_, checkpoint.this_run_start_step+1, simWindow->getNmoved() );

        // allocate region according to dump
        if( params.multiple_decomposition ) {
            TITLE( "Create SDMD grids" );
            // read region hindex
            checkpoint.readRegionDistribution( region );

            // Build params.map_rank contains MPI ranks assuming that regions are distributed linearly
            int target_map[smpi.getSize()];
            MPI_Allgather(&(region.vecPatch_.refHindex_), 1, MPI_INT,
                          target_map, 1, MPI_INT,
                          MPI_COMM_WORLD);
            region.define_regions_map(target_map, &smpi, params);

            // params.map_rank used to defined regions neighborood
            region.build( params, &smpi, vecPatches, false, simWindow->getNmoved() );
            region.identify_additional_patches( &smpi, vecPatches, params, simWindow );
            region.identify_missing_patches( &smpi, vecPatches, params );
        }

        // vecPatches data read in restartAll according to smpi.patch_count

        // if (params.multiple_decomposition) {
        //     region.vecPatch_.refHindex_ = smpi.getRank();
        //     region.build( params, &smpi, vecPatches, false );
        //     region.identify_additional_patches( &smpi, vecPatches, params, simWindow );
        //     region.identify_missing_patches( &smpi, vecPatches, params );

        //     region.reset_fitting( &smpi, params );

        //     region.clean();
        //     region.reset_mapping();

        //     region.build( params, &smpi, vecPatches, false );
        //     region.identify_additional_patches( &smpi, vecPatches, params, simWindow );
        //     region.identify_missing_patches( &smpi, vecPatches, params );
        // }

        checkpoint.restartAll( vecPatches, region, &smpi, params );

#if !defined( SMILEI_ACCELERATOR_GPU )
        // CPU only, its too early to sort on GPU
        vecPatches.initialParticleSorting( params );
#endif

        TITLE( "Minimum memory consumption (does not include all temporary buffers)" );
        vecPatches.checkMemoryConsumption( &smpi, &region.vecPatch_ );

        // Patch reconfiguration for the adaptive vectorization
        if( params.has_adaptive_vectorization ) {
            vecPatches.configuration( params, timers, 0 );
        }

        // time at integer time-steps (primal grid)
        time_prim = checkpoint.this_run_start_step * params.timestep;
        // time at half-integer time-steps (dual grid)
        time_dual = ( checkpoint.this_run_start_step +0.5 ) * params.timestep;

    // No restart, we initialize a new simulation
    } else {

        PatchesFactory::createVector( vecPatches, params, &smpi, openPMD, &radiation_tables_, 0 );

#if !(defined( SMILEI_ACCELERATOR_GPU ))
        // CPU only, its too early to sort on GPU
        vecPatches.initialParticleSorting( params );
#endif

        // Initialize the electromagnetic fields
        // -------------------------------------
        
        // Create SDMD grids
        if( params.multiple_decomposition ) {
            TITLE( "Create SDMD grids" );
            region.vecPatch_.refHindex_ = smpi.getRank();
            region.build( params, &smpi, vecPatches, false, simWindow->getNmoved() );
            region.identify_additional_patches( &smpi, vecPatches, params, simWindow );
            region.identify_missing_patches( &smpi, vecPatches, params );
            //cout << smpi.getRank() << "\t - local : " << region.local_patches_.size()
            //     <<  "\t - missing : " << region.missing_patches_.size()
            //     <<  "\t - additional : " << region.additional_patches_.size() << endl;

            region.reset_fitting( &smpi, params );
            region.clean();
            region.reset_mapping();

            region.build( params, &smpi, vecPatches, false, simWindow->getNmoved() );
            region.identify_additional_patches( &smpi, vecPatches, params, simWindow );
            region.identify_missing_patches( &smpi, vecPatches, params );
            //cout << smpi.getRank() << "\t - local : " << region.local_patches_.size()
            //     <<  "\t - missing : " << region.missing_patches_.size()
            //     <<  "\t - additional : " << region.additional_patches_.size() << endl;
        }

        TITLE( "Minimum memory consumption (does not include all temporary buffers)" );
        vecPatches.checkMemoryConsumption( &smpi, &region.vecPatch_ );

        TITLE( "Initial fields setup" );

        // Solve "Relativistic Poisson" problem (including proper centering of fields)
        // NOTE: the mean gamma for initialization will be computed for all the species
        // whose fields are initialized at this iteration
        if( params.solve_relativistic_poisson == true ) {
            MESSAGE( 1, "Solving relativistic Poisson at time t = 0" );
            vecPatches.runRelativisticModule( time_prim, params, &smpi,  timers );
        }

        vecPatches.computeCharge();

        // TODO(Etienne M): redundant work is done here. We exchange current
        // density J when in fact, only charge density Rho needs to be exchanged.
        vecPatches.sumDensities( params, time_dual, timers, 0, simWindow, &smpi );

        // Init electric field (Ex/1D, + Ey/2D)
        if( params.solve_poisson == true && !vecPatches.isRhoNull( &smpi ) ) {
            MESSAGE( 1, "Solving Poisson at time t = 0" );
            vecPatches.runNonRelativisticPoissonModule( params, &smpi,  timers );
        }

        MESSAGE( 1, "Applying external fields at time t = 0" );
        vecPatches.applyExternalFields();
        vecPatches.saveExternalFields( params );

        MESSAGE( 1, "Applying prescribed fields at time t = 0" );
        vecPatches.applyPrescribedFields( time_prim );

        MESSAGE( 1, "Applying antennas at time t = 0" );
        vecPatches.applyAntennas( 0.5 * params.timestep );

        // Patch reconfiguration
        if( params.has_adaptive_vectorization ) {
            vecPatches.configuration( params, timers, 0 );
        }

        // if Laser Envelope is used, execute particles and envelope sections of ponderomotive loop
        if( params.Laser_Envelope_model ) {
            MESSAGE( 1, "Initialize envelope" );
            vecPatches.initNewEnvelope( params );
        }

        // Project charge and current densities (and susceptibility if envelope is used) only for diags at t=0
        vecPatches.projectionForDiags( params, &smpi, simWindow, time_dual, timers, 0 );

        // If Laser Envelope is used, comm and synch susceptibility at t=0
        if( params.Laser_Envelope_model ) {
            vecPatches.sumSusceptibility( params, time_dual, timers, 0, simWindow, &smpi );
        }
        
        // Comm and synch charge and current densities for a given species (rho_s, Jx_s...)
        vecPatches.sumDensities( params, time_dual, timers, 0, simWindow, &smpi );

        // Upload corrected data on Regions
        if( params.multiple_decomposition ) {
            if ( params.geometry != "AMcylindrical" ) {
                DoubleGrids::syncFieldsOnRegion( vecPatches, region, params, &smpi );
                SyncVectorPatch::exchangeE( params, region.vecPatch_, &smpi );
                SyncVectorPatch::exchangeB( params, region.vecPatch_, &smpi );
                SyncVectorPatch::finalizeexchangeB( params, region.vecPatch_);
            } else {
                for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  ) {
                    DoubleGridsAM::syncFieldsOnRegion( vecPatches, region, params, &smpi, imode );
                    // Need to fill all ghost zones, not covered by patches ghost zones
                    SyncVectorPatch::exchangeE( params, region.vecPatch_, imode, &smpi );
                    SyncVectorPatch::exchangeB( params, region.vecPatch_, imode, &smpi );
                }
            }
        }

        // rotational cleaning on a single global region for AM spectral
        if( params.initial_rotational_cleaning ) {
            TITLE( "Rotational cleaning" );
            Region region_global( params );
            region_global.build( params, &smpi, vecPatches, true, simWindow->getNmoved() );
            region_global.identify_additional_patches( &smpi, vecPatches, params, simWindow );
            region_global.identify_missing_patches( &smpi, vecPatches, params );
            for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  ) {
                DoubleGridsAM::syncFieldsOnRegion( vecPatches, region_global, params, &smpi, imode );
            }
            if( params.is_pxr && smpi.isMaster()) {
                region_global.coupling( params, true );
            }
            for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  ) {
                DoubleGridsAM::syncFieldsOnPatches( region_global, vecPatches, params, &smpi, timers, imode );
            }
            vecPatches.setMagneticFieldsForDiagnostic( params );
            region_global.clean();

            if( params.multiple_decomposition ) {
                for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  ) {
                    DoubleGridsAM::syncFieldsOnRegion( vecPatches, region, params, &smpi, imode );
                    // Need to fill all ghost zones, not covered by patches ghost zones
                    SyncVectorPatch::exchangeE( params, region.vecPatch_, imode, &smpi );
                    SyncVectorPatch::exchangeB( params, region.vecPatch_, imode, &smpi );
                }
            }
        }
    }

#if defined( SMILEI_ACCELERATOR_GPU )
    TITLE( "GPU allocation and copy of the fields and particles" );
    // Allocate particle and field arrays
    // Also copy particle array content on device
    vecPatches.allocateDataOnDevice( params, &smpi, 
                                        &radiation_tables_, 
                                        &multiphoton_Breit_Wheeler_tables_ );
    // Copy field array content on device
    vecPatches.copyFieldsFromHostToDevice();
#endif

    TITLE( "Open files & initialize diagnostics" );
    vecPatches.initAllDiags( params, &smpi );

    if( !params.restart ) {
        TITLE( "Running diags at time t = 0" );
        #pragma omp parallel shared( smpi, params, vecPatches, simWindow )
        {
            vecPatches.runAllDiags( params, &smpi, 0, timers, simWindow );
        }
        vecPatches.rebootDiagTimers();
    }

    TITLE( "Species creation summary" );
    vecPatches.printGlobalNumberOfParticlesPerSpecies( &smpi );

    if( params.is_pxr ){
        if( params.multiple_decomposition ) {
            region.coupling( params, false );
        } else {
            vecPatches( 0 )->EMfields->MaxwellAmpereSolver_->coupling( params, vecPatches( 0 )->EMfields );
        }
    }

    if( params.is_spectral && params.geometry != "AMcylindrical") {
        vecPatches.saveOldRho( params );
    }

    timers.reboot();
    timers.global.reboot();

    // ------------------------------------------------------------------------
    // Check expected disk usage
    // ------------------------------------------------------------------------
    TITLE( "Expected disk usage (approximate)" );
    vecPatches.checkExpectedDiskUsage( &smpi, params, checkpoint );

    // ------------------------------------------------------------------------
    // check here if we can close the python interpreter
    // ------------------------------------------------------------------------
    TITLE( "Keeping or closing the python runtime environment" );
    params.cleanup( &smpi );

    /*tommaso
        // save latestTimeStep (used to test if we are at the latest timestep when running diagnostics at run's end)
        unsigned int latestTimeStep=checkpoint.this_run_start_step;
    */
    // ------------------------------------------------------------------
    //                     HERE STARTS THE PIC LOOP
    // ------------------------------------------------------------------

    TITLE( "Time-Loop started: number of time-steps n_time = " << params.n_time );
    if( smpi.isMaster() ) {
        params.print_timestep_headers( &smpi );
    }

    int count_dlb = 0;

    unsigned int itime=checkpoint.this_run_start_step+1;
    while( ( itime <= params.n_time ) && ( !checkpoint.exit_asap ) ) {
        
        // calculate new times
        // -------------------
        time_prim += params.timestep;
        time_dual += params.timestep;
        if( params.keep_python_running_ ) {
            PyTools::setIteration( itime ); // sets python variable "Main.iteration" for users
        }
        
        #pragma omp parallel shared (time_dual,smpi,params, vecPatches, region, simWindow, checkpoint, itime)
        {
            
            // Patch reconfiguration
            if( params.has_adaptive_vectorization && params.adaptive_vecto_time_selection->theTimeIsNow( itime ) ) {
                vecPatches.reconfiguration( params, timers, itime );
            }

            // apply collisions if requested
            vecPatches.applyBinaryProcesses( params, itime, timers );

            // Solve "Relativistic Poisson" problem (including proper centering of fields)
            // for species who stop to be frozen
            // NOTE: the mean gamma for initialization will be computed for all the species
            // whose fields are initialized at this iteration
            if( params.solve_relativistic_poisson == true ) {
                vecPatches.runRelativisticModule( time_prim, params, &smpi,  timers );
            }

            // Reset global charge and currents densities to zero and computes rho old before moving particles
            if ( params.geometry == "AMcylindrical" && params.is_spectral )
                vecPatches.computeCharge(true);

            // (1) interpolate the fields at the particle position
            // (2) move the particle
            // (3) calculate the currents (charge conserving method)
            vecPatches.dynamics( params, &smpi, simWindow, radiation_tables_,
                                 multiphoton_Breit_Wheeler_tables_,
                                 time_dual, timers, itime );

            // if Laser Envelope is used, execute particles and envelope sections of ponderomotive loop
            if( params.Laser_Envelope_model ) {
                vecPatches.runEnvelopeModule( params, &smpi, simWindow, time_dual, timers, itime );
            } // end condition if Laser Envelope Model is used
            
            vecPatches.initExchParticles( params, &smpi, simWindow, time_dual, timers, itime );
            
            // Sum densities
            vecPatches.sumDensities( params, time_dual, timers, itime, simWindow, &smpi );

            // apply currents from antennas
            vecPatches.applyAntennas( time_dual );

        } //End omp parallel region

        // solve Maxwell's equations
        if (!params.multiple_decomposition) {
            if( time_dual > params.time_fields_frozen ) {
                #pragma omp parallel shared (time_dual,smpi,params, vecPatches, region, simWindow, checkpoint, itime)
                {
                    // de-apply prescribed fields if requested
                    if ( vecPatches(0)->EMfields->prescribedFields.size() ) {
                        vecPatches.resetPrescribedFields();
                    }
                    vecPatches.solveMaxwell( params, simWindow, itime, time_dual, timers, &smpi );
                }

            }
        }
        else { //if ( params.multiple_decomposition ) 
            if( time_dual > params.time_fields_frozen ) {
                if ( params.geometry != "AMcylindrical" )
                    DoubleGrids::syncCurrentsOnRegion( vecPatches, region, params, &smpi, timers );
                else {
                    for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  )
                        DoubleGridsAM::syncCurrentsOnRegion( vecPatches, region, params, &smpi, timers, imode );
                }
                region.vecPatch_.diag_flag = false;

                //here filter + divergence cleaning
                if ( params.is_spectral && params.geometry == "AMcylindrical") {
                    timers.densitiesCorrection.restart();
                    region.vecPatch_( 0 )->EMfields->MaxwellAmpereSolver_->densities_correction( region.vecPatch_( 0 )->EMfields );
                    timers.densitiesCorrection.update();
                }


                timers.syncDens.restart();
                if( params.geometry != "AMcylindrical" )
                    SyncVectorPatch::sumRhoJ( params, region.vecPatch_, &smpi ); // MPI
                else
                    for( unsigned int imode = 0 ; imode < params.nmodes ; imode++ ) {
                        SyncVectorPatch::sumRhoJ( params, region.vecPatch_, imode, &smpi );
                    }
                timers.syncDens.update( params.printNow( itime ) );


                // de-apply prescribed fields if requested
                if( region.vecPatch_(0)->EMfields->prescribedFields.size() ) {
                    region.vecPatch_.resetPrescribedFields();
                }
                region.solveMaxwell( params, simWindow, itime, time_dual, timers, &smpi );

                // apply external time fields if requested
                if( region.vecPatch_(0)->EMfields->prescribedFields.size() ) {
                    region.vecPatch_.applyPrescribedFields( time_prim );
                }

                if ( params.geometry != "AMcylindrical" )
                    DoubleGrids::syncFieldsOnPatches( region, vecPatches, params, &smpi, timers );
                else {
                    for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  )
                        DoubleGridsAM::syncFieldsOnPatches( region, vecPatches, params, &smpi, timers, imode );
                }
            }
            if( vecPatches.diag_flag ) {

                if (!params.is_spectral) {
                    if ( params.geometry != "AMcylindrical" )
                        DoubleGrids::syncBOnPatches( region, vecPatches, params, &smpi, timers );
                    else {
                        for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  )
                            DoubleGridsAM::syncBOnPatches( region, vecPatches, params, &smpi, timers, imode );
                    }

                    // Currents and densities not corrected on regions
                    #pragma omp parallel shared (time_dual,smpi,params, vecPatches, region, simWindow, checkpoint, itime)
                    {
                        if( params.geometry != "AMcylindrical" ) {
                            SyncVectorPatch::sumRhoJ( params, vecPatches, &smpi ); // MPI
                        }
                        else {
                            for( unsigned int imode = 0 ; imode < params.nmodes ; imode++ ) {
                                SyncVectorPatch::sumRhoJ( params, vecPatches, imode, &smpi );
                            }
                        }
                    }
                }
                else {
                    // Just need to cp Bm in B for all patches
                    vecPatches.setMagneticFieldsForDiagnostic( params );

                    // Currents and densities could have been corrected on regions
                    if ( params.geometry != "AMcylindrical" ) {
                        DoubleGrids::syncCurrentsOnPatches( region, vecPatches, params, &smpi, timers );
                    }
                    else {
                        for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  )
                            DoubleGridsAM::syncCurrentsOnPatches( region, vecPatches, params, &smpi, timers, imode );
                    }
                }
            }
            bool old = (params.geometry == "AMcylindrical" && params.is_spectral);
            region.vecPatch_.resetRhoJ(old);
        }

        #pragma omp parallel shared (time_dual,smpi,params, vecPatches, region, simWindow, checkpoint, itime)
        {
            // finalize particle exchanges and sort particles
            vecPatches.finalizeExchParticlesAndSort( params, &smpi, simWindow, time_dual, timers, itime );

            // Particle merging
            vecPatches.mergeParticles(params, time_dual,timers, itime );

            // Particle injection from the boundaries
            vecPatches.injectParticlesFromBoundaries(params, timers, itime );

            // Clean buffers and resize arrays
            vecPatches.cleanParticlesOverhead(params, timers, itime );

            // Finalize field synchronization and exchanges
            vecPatches.finalizeSyncAndBCFields( params, &smpi, simWindow, time_dual, timers, itime );

            if( !params.multiple_decomposition ) {
                if( time_dual > params.time_fields_frozen ) {
                    // Standard fields operations (maxwell + comms + boundary conditions) are completed
                    // apply prescribed fields can be considered if requested
                    if( vecPatches(0)->EMfields->prescribedFields.size() ) {
                        #pragma omp master
                        vecPatches.applyPrescribedFields( time_prim );
                        #pragma omp barrier
                    }
                }
            }

            // Call the various diagnostics
            vecPatches.runAllDiags( params, &smpi, itime, timers, simWindow );

            // Move window
            vecPatches.moveWindow( params, &smpi, region, simWindow, time_dual, timers, itime );

            // Checkpointing: dump data
            #pragma omp master
            checkpoint.dump( vecPatches, region, itime, &smpi, simWindow, params );
            #pragma omp barrier
            // ----------------------------------------------------------------------

        } //End omp parallel region

        if( params.has_load_balancing && params.load_balancing_time_selection->theTimeIsNow( itime ) ) {
// #if defined( SMILEI_ACCELERATOR_GPU )
//             ERROR( "Load balancing not tested on GPU !" );
// #endif
            count_dlb++;
            // Every 5 DLB, regions are completely recomputed in order to minimize the number of patches not owned.
            if (params.multiple_decomposition && count_dlb%5 ==0 ) {

                // de-apply prescribed fields if requested before load balance and synchronize all fields on patches
                if( region.vecPatch_(0)->EMfields->prescribedFields.size() ) {

                    region.vecPatch_.resetPrescribedFields();

                    if ( params.geometry != "AMcylindrical" )
                        DoubleGrids::syncFieldsOnPatches( region, vecPatches, params, &smpi, timers );
                    else {
                        for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  )
                            DoubleGridsAM::syncFieldsOnPatches( region, vecPatches, params, &smpi, timers, imode );
                    }
                } 
                //Synchronize only B field
                if ( params.geometry != "AMcylindrical" ) {
                    DoubleGrids::syncBOnPatches( region, vecPatches, params, &smpi, timers );
                } else {
                    for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  ) {
                        DoubleGridsAM::syncBOnPatches( region, vecPatches, params, &smpi, timers, imode );
                    }
                }
            }

            timers.loadBal.restart();
            #pragma omp single
            vecPatches.loadBalance( params, time_dual, &smpi, simWindow, itime );
            timers.loadBal.update( params.printNow( itime ) );

            if( params.multiple_decomposition ) {

                if( count_dlb%5 == 0 ) {

                    region.reset_fitting( &smpi, params );
                    region.clean();
                    region.reset_mapping();
                    region.build( params, &smpi, vecPatches, false, simWindow->getNmoved() );
                    if( params.is_pxr ) {
                        region.coupling( params, false );
                    }
                    region.identify_additional_patches( &smpi, vecPatches, params, simWindow );
                    region.identify_missing_patches( &smpi, vecPatches, params );

                    // After resetting the regions, initialize it from the fields on patches.
                    if ( params.geometry != "AMcylindrical" ) {
                        DoubleGrids::syncFieldsOnRegion( vecPatches, region, params, &smpi );
                    } else {
                        for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  ) {
                            DoubleGridsAM::syncFieldsOnRegion( vecPatches, region, params, &smpi, imode );
                        }
                    }
                    // Apply prescribed fields and store original fields on region
                    if( region.vecPatch_(0)->EMfields->prescribedFields.size() ) {
                        region.vecPatch_.applyPrescribedFields( time_prim );
                        //update patches fields
                        if ( params.geometry != "AMcylindrical" )
                            DoubleGrids::syncFieldsOnPatches( region, vecPatches, params, &smpi, timers );
                        else {
                            for (unsigned int imode = 0 ; imode < params.nmodes ; imode++  )
                                DoubleGridsAM::syncFieldsOnPatches( region, vecPatches, params, &smpi, timers, imode );
                        }
                    }

                } else {
                    region.reset_mapping();
                    region.identify_additional_patches( &smpi, vecPatches, params, simWindow );
                    region.identify_missing_patches( &smpi, vecPatches, params );
                }
            }
        }

        // print message at given time-steps
        // --------------------------------
        if( params.printNow( itime ) ) {
            double npart = vecPatches.getGlobalNumberOfParticles( &smpi );
            params.print_timestep( &smpi, itime, time_dual, timers.global, npart ); //contains a timer.update !!!

            #pragma omp master
            timers.consolidate( &smpi );
            #pragma omp barrier
        }

        itime++;
    
    }//END of the time loop

    smpi.barrier();

    // ------------------------------------------------------------------
    //                      HERE ENDS THE PIC LOOP
    // ------------------------------------------------------------------
    TITLE( "End time loop, time dual = " << time_dual );
    timers.global.update();

    // Validation framework golden-vs-recovery comparison anchor.  Must run
    // BEFORE vecPatches.close(&smpi) (which tears down EM fields and
    // particle arrays).
    dumpValidationSignatureSmilei( vecPatches, smpi );

    TITLE( "Time profiling : (print time > 0.001%)" );
    timers.profile( &smpi );

    smpi.barrier();

    /*tommaso
        // ------------------------------------------------------------------
        //                      Temporary validation diagnostics
        // ------------------------------------------------------------------

        if (latestTimeStep==params.n_time)
            vecPatches.runAllDiags(params, smpi, &diag_flag, params.n_time, timer, simWindow);
    */

    // ------------------------------
    //  Cleanup & End the simulation
    // ------------------------------
    if (params.multiple_decomposition) {
        region.clean();
    }
    
#if defined( SMILEI_ACCELERATOR_GPU )
    vecPatches.cleanDataOnDevice( params, &smpi, &radiation_tables_, &multiphoton_Breit_Wheeler_tables_ );
#endif
    
    vecPatches.close( &smpi );
    smpi.barrier(); // Don't know why but sync needed by HDF5 Phasespace managment
    delete simWindow;
    PyTools::closePython();
    TITLE( "END" );

    return 0;

}//END MAIN

// ---------------------------------------------------------------------------------------------------------------------
//                                               END MAIN CODE
// ---------------------------------------------------------------------------------------------------------------------

int executeTestMode( VectorPatch &vecPatches,
                     Region &region,
                     SmileiMPI *smpi,
                     SimWindow *simWindow,
                     Params &params,
                     Checkpoint &checkpoint,
                     OpenPMDparams &openPMD,
                     RadiationTables * radiation_tables_ )
{
    int itime = 0;
    int moving_window_movement = 0;

    if( params.restart ) {
        checkpoint.readPatchDistribution( smpi, simWindow );
        itime = checkpoint.this_run_start_step+1;
        moving_window_movement = simWindow->getNmoved();
    }

    PatchesFactory::createVector( vecPatches, params, smpi, openPMD, radiation_tables_, itime, moving_window_movement );

    if( params.restart ) {
        if (params.multiple_decomposition) {
            checkpoint.readRegionDistribution( region );
            region.build( params, smpi, vecPatches, false, simWindow->getNmoved() );
        }
        checkpoint.restartAll( vecPatches, region, smpi, params );
    }

    if( params.print_expected_disk_usage ) {
        TITLE( "Expected disk usage (approximate)" );
        vecPatches.checkExpectedDiskUsage( smpi, params, checkpoint );
    }

    // If test mode enable, code stops here
    TITLE( "Keeping or closing the python runtime environment" );
    params.cleanup( smpi );
    delete simWindow;
    PyTools::closePython();
    TITLE( "END TEST MODE" );

    return 0;
}
