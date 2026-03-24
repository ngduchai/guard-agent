/****************************************************************************
 * Copyright (c) 2018-2020 by the ExaMPM authors                            *
 * All rights reserved.                                                     *
 *                                                                          *
 * This file is part of the ExaMPM library. ExaMPM is distributed under a   *
 * BSD 3-clause license. For the licensing terms see the LICENSE file in    *
 * the top-level directory.                                                 *
 *                                                                          *
 * SPDX-License-Identifier: BSD-3-Clause                                    *
 ****************************************************************************/

#ifndef EXAMPM_SOLVER_HPP
#define EXAMPM_SOLVER_HPP

#include <ExaMPM_BoundaryConditions.hpp>
#include <ExaMPM_Mesh.hpp>
#include <ExaMPM_ProblemManager.hpp>
#include <ExaMPM_TimeIntegrator.hpp>
#include <ExaMPM_TimeStepControl.hpp>

#include <Cabana_Core.hpp>
#include <Kokkos_Core.hpp>

#include <memory>
#include <string>
#include <cstdio>
#include <cstring>

#include <mpi.h>
#include <veloc.h>

namespace ExaMPM
{
//---------------------------------------------------------------------------//
class SolverBase
{
  public:
    virtual ~SolverBase() = default;
    virtual void solve( const double t_final, const int write_freq ) = 0;
};

//---------------------------------------------------------------------------//
template <class MemorySpace, class ExecutionSpace>
class Solver : public SolverBase
{
  public:
    template <class InitFunc>
    Solver( MPI_Comm comm, const Kokkos::Array<double, 6>& global_bounding_box,
            const std::array<int, 3>& global_num_cell,
            const std::array<bool, 3>& periodic,
            const Cabana::Grid::BlockPartitioner<3>& partitioner,
            const int halo_cell_width, const InitFunc& create_functor,
            const int particles_per_cell, const double bulk_modulus,
            const double density, const double gamma, const double kappa,
            const double delta_t, const double gravity,
            const BoundaryCondition& bc )
        : _dt( delta_t )
        , _time( 0.0 )
        , _step( 0 )
        , _gravity( gravity )
        , _bc( bc )
        , _halo_min( 3 )
    {
        _mesh = std::make_shared<Mesh<MemorySpace>>(
            global_bounding_box, global_num_cell, periodic, partitioner,
            halo_cell_width, _halo_min, comm );

        _bc.min = _mesh->minDomainGlobalNodeIndex();
        _bc.max = _mesh->maxDomainGlobalNodeIndex();

        _pm = std::make_shared<ProblemManager<MemorySpace>>(
            ExecutionSpace(), _mesh, create_functor, particles_per_cell,
            bulk_modulus, density, gamma, kappa );

        MPI_Comm_rank( comm, &_rank );
    }

    //---------------------------------------------------------------------------//
    // VeloC file-based checkpoint: write step, time, dt, and all particle data
    //---------------------------------------------------------------------------//
    void writeCheckpoint( int version )
    {
        // Begin checkpoint phase (collective)
        if ( VELOC_Checkpoint_begin( "exampm", version ) != VELOC_SUCCESS )
        {
            if ( _rank == 0 )
                std::cerr << "VeloC: Checkpoint_begin failed\n";
            VELOC_Checkpoint_end( 0 );
            return;
        }

        // Get the routed file path
        char veloc_file[VELOC_MAX_NAME];
        if ( VELOC_Route_file( "exampm_ckpt.dat", veloc_file ) != VELOC_SUCCESS )
        {
            if ( _rank == 0 )
                std::cerr << "VeloC: Route_file failed\n";
            VELOC_Checkpoint_end( 0 );
            return;
        }

        int valid = 1;
        FILE* fp = std::fopen( veloc_file, "wb" );
        if ( fp != nullptr )
        {
            // Write step, time, dt
            if ( std::fwrite( &_step, sizeof( int ), 1, fp ) != 1 )
                valid = 0;
            if ( std::fwrite( &_time, sizeof( double ), 1, fp ) != 1 )
                valid = 0;
            if ( std::fwrite( &_dt, sizeof( double ), 1, fp ) != 1 )
                valid = 0;

            // Write number of particles
            std::size_t num_p = _pm->numParticle();
            if ( std::fwrite( &num_p, sizeof( std::size_t ), 1, fp ) != 1 )
                valid = 0;

            if ( num_p > 0 && valid )
            {
                // Get particle slices and create host mirrors
                // Member 0: affine [3][3] = 9 doubles per particle
                auto aff = _pm->get( Location::Particle(), Field::Affine() );
                // Member 1: velocity [3] = 3 doubles per particle
                auto vel = _pm->get( Location::Particle(), Field::Velocity() );
                // Member 2: position [3] = 3 doubles per particle
                auto pos = _pm->get( Location::Particle(), Field::Position() );
                // Member 3: mass = 1 double per particle
                auto mass = _pm->get( Location::Particle(), Field::Mass() );
                // Member 4: volume = 1 double per particle
                auto vol = _pm->get( Location::Particle(), Field::Volume() );
                // Member 5: J = 1 double per particle
                auto j_det = _pm->get( Location::Particle(), Field::J() );

                // Write particle data one by one (safe for any memory layout)
                for ( std::size_t p = 0; p < num_p && valid; ++p )
                {
                    // Affine 3x3
                    for ( int d0 = 0; d0 < 3; ++d0 )
                        for ( int d1 = 0; d1 < 3; ++d1 )
                        {
                            double val = aff( p, d0, d1 );
                            if ( std::fwrite( &val, sizeof( double ), 1, fp ) != 1 )
                                valid = 0;
                        }
                    // Velocity 3
                    for ( int d = 0; d < 3; ++d )
                    {
                        double val = vel( p, d );
                        if ( std::fwrite( &val, sizeof( double ), 1, fp ) != 1 )
                            valid = 0;
                    }
                    // Position 3
                    for ( int d = 0; d < 3; ++d )
                    {
                        double val = pos( p, d );
                        if ( std::fwrite( &val, sizeof( double ), 1, fp ) != 1 )
                            valid = 0;
                    }
                    // Mass
                    {
                        double val = mass( p );
                        if ( std::fwrite( &val, sizeof( double ), 1, fp ) != 1 )
                            valid = 0;
                    }
                    // Volume
                    {
                        double val = vol( p );
                        if ( std::fwrite( &val, sizeof( double ), 1, fp ) != 1 )
                            valid = 0;
                    }
                    // J
                    {
                        double val = j_det( p );
                        if ( std::fwrite( &val, sizeof( double ), 1, fp ) != 1 )
                            valid = 0;
                    }
                }
            }
            std::fclose( fp );
        }
        else
        {
            valid = 0;
        }

        VELOC_Checkpoint_end( valid );
    }

    //---------------------------------------------------------------------------//
    // VeloC file-based restart: read step, time, dt, and all particle data
    // Returns true if restart succeeded.
    //---------------------------------------------------------------------------//
    bool tryRestart()
    {
        int v = VELOC_Restart_test( "exampm", 0 );
        if ( v <= 0 )
            return false;

        if ( _rank == 0 )
            std::printf( "VeloC: Restarting from checkpoint version %d\n", v );

        if ( VELOC_Restart_begin( "exampm", v ) != VELOC_SUCCESS )
        {
            VELOC_Restart_end( 0 );
            return false;
        }

        char veloc_file[VELOC_MAX_NAME];
        if ( VELOC_Route_file( "exampm_ckpt.dat", veloc_file ) != VELOC_SUCCESS )
        {
            VELOC_Restart_end( 0 );
            return false;
        }

        int valid = 1;
        FILE* fp = std::fopen( veloc_file, "rb" );
        if ( fp != nullptr )
        {
            // Read step, time, dt
            if ( std::fread( &_step, sizeof( int ), 1, fp ) != 1 )
                valid = 0;
            if ( std::fread( &_time, sizeof( double ), 1, fp ) != 1 )
                valid = 0;
            if ( std::fread( &_dt, sizeof( double ), 1, fp ) != 1 )
                valid = 0;

            // Read number of particles
            std::size_t num_p = 0;
            if ( std::fread( &num_p, sizeof( std::size_t ), 1, fp ) != 1 )
                valid = 0;

            if ( valid )
            {
                // Resize the particle list to hold the checkpointed particles
                _pm->resizeParticles( num_p );

                if ( num_p > 0 )
                {
                    auto aff = _pm->get( Location::Particle(), Field::Affine() );
                    auto vel = _pm->get( Location::Particle(), Field::Velocity() );
                    auto pos = _pm->get( Location::Particle(), Field::Position() );
                    auto mass = _pm->get( Location::Particle(), Field::Mass() );
                    auto vol = _pm->get( Location::Particle(), Field::Volume() );
                    auto j_det = _pm->get( Location::Particle(), Field::J() );

                    for ( std::size_t p = 0; p < num_p && valid; ++p )
                    {
                        // Affine 3x3
                        for ( int d0 = 0; d0 < 3; ++d0 )
                            for ( int d1 = 0; d1 < 3; ++d1 )
                            {
                                double val;
                                if ( std::fread( &val, sizeof( double ), 1, fp ) != 1 )
                                    valid = 0;
                                else
                                    aff( p, d0, d1 ) = val;
                            }
                        // Velocity 3
                        for ( int d = 0; d < 3; ++d )
                        {
                            double val;
                            if ( std::fread( &val, sizeof( double ), 1, fp ) != 1 )
                                valid = 0;
                            else
                                vel( p, d ) = val;
                        }
                        // Position 3
                        for ( int d = 0; d < 3; ++d )
                        {
                            double val;
                            if ( std::fread( &val, sizeof( double ), 1, fp ) != 1 )
                                valid = 0;
                            else
                                pos( p, d ) = val;
                        }
                        // Mass
                        {
                            double val;
                            if ( std::fread( &val, sizeof( double ), 1, fp ) != 1 )
                                valid = 0;
                            else
                                mass( p ) = val;
                        }
                        // Volume
                        {
                            double val;
                            if ( std::fread( &val, sizeof( double ), 1, fp ) != 1 )
                                valid = 0;
                            else
                                vol( p ) = val;
                        }
                        // J
                        {
                            double val;
                            if ( std::fread( &val, sizeof( double ), 1, fp ) != 1 )
                                valid = 0;
                            else
                                j_det( p ) = val;
                        }
                    }
                }
            }
            std::fclose( fp );
        }
        else
        {
            valid = 0;
        }

        VELOC_Restart_end( valid );

        if ( valid && _rank == 0 )
            std::printf( "VeloC: Restored step=%d time=%f dt=%e num_particles=%zu\n",
                         _step, _time, _dt, _pm->numParticle() );

        return ( valid != 0 );
    }

    void solve( const double t_final, const int write_freq ) override
    {
        // Attempt VeloC restart
        bool restarted = tryRestart();

        if ( !restarted )
        {
            // Output initial state (fresh start only).
            outputParticles();
        }

        while ( _time < t_final )
        {
            if ( 0 == _rank && 0 == _step % write_freq )
                printf( "Time %f / %f\n", _time, t_final );

            // Fixed timestep is guaranteed only when sufficently low dt
            // does not violate the CFL condition (otherwise user-set dt is
            // really a max_dt).
            _dt = timeStepControl( _mesh->localGrid()->globalGrid().comm(),
                                   ExecutionSpace(), *_pm, _dt );

            TimeIntegrator::step( ExecutionSpace(), *_pm, _dt, _gravity, _bc );

            _pm->communicateParticles( _halo_min );

            _time += _dt;
            _step++;

            // Output particles periodically.
            if ( 0 == ( _step ) % write_freq )
                outputParticles();

            // VeloC checkpoint every write_freq steps (aligns with output)
            if ( 0 == ( _step ) % write_freq )
                writeCheckpoint( _step );
        }
    }

    void outputParticles()
    {
        // Prefer HDF5 output over Silo. Only output if one is enabled.
#ifdef Cabana_ENABLE_HDF5
        Cabana::Experimental::HDF5ParticleOutput::HDF5Config h5_config;
        Cabana::Experimental::HDF5ParticleOutput::writeTimeStep(
            h5_config, "particles", _mesh->localGrid()->globalGrid().comm(),
            _step, _time, _pm->numParticle(),
            _pm->get( Location::Particle(), Field::Position() ),
            _pm->get( Location::Particle(), Field::Velocity() ),
            _pm->get( Location::Particle(), Field::J() ) );
#else
#ifdef Cabana_ENABLE_SILO
        Cabana::Grid::Experimental::SiloParticleOutput::writeTimeStep(
            "particles", _mesh->localGrid()->globalGrid(), _step, _time,
            _pm->get( Location::Particle(), Field::Position() ),
            _pm->get( Location::Particle(), Field::Velocity() ),
            _pm->get( Location::Particle(), Field::J() ) );
#else
        if ( _rank == 0 )
            std::cout << "No particle output enabled in Cabana. Add "
                         "Cabana_REQUIRE_HDF5=ON or Cabana_REQUIRE_SILO=ON to "
                         "the Cabana build if needed.";
#endif
#endif
    }

  private:
    double _dt;
    double _time;
    int _step;
    double _gravity;
    BoundaryCondition _bc;
    int _halo_min;
    std::shared_ptr<Mesh<MemorySpace>> _mesh;
    std::shared_ptr<ProblemManager<MemorySpace>> _pm;
    int _rank;
};

//---------------------------------------------------------------------------//
// Creation method.
template <class InitFunc>
std::shared_ptr<SolverBase>
createSolver( const std::string& exec_space, MPI_Comm comm,
              const Kokkos::Array<double, 6>& global_bounding_box,
              const std::array<int, 3>& global_num_cell,
              const std::array<bool, 3>& periodic,
              const Cabana::Grid::BlockPartitioner<3>& partitioner,
              const int halo_cell_width, const InitFunc& create_functor,
              const int particles_per_cell, const double bulk_modulus,
              const double density, const double gamma, const double kappa,
              const double delta_t, const double gravity,
              const BoundaryCondition& bc )
{
    if ( 0 == exec_space.compare( "serial" ) ||
         0 == exec_space.compare( "Serial" ) ||
         0 == exec_space.compare( "SERIAL" ) )
    {
#ifdef KOKKOS_ENABLE_SERIAL
        return std::make_shared<
            ExaMPM::Solver<Kokkos::HostSpace, Kokkos::Serial>>(
            comm, global_bounding_box, global_num_cell, periodic, partitioner,
            halo_cell_width, create_functor, particles_per_cell, bulk_modulus,
            density, gamma, kappa, delta_t, gravity, bc );
#else
        throw std::runtime_error( "Serial Backend Not Enabled" );
#endif
    }
    else if ( 0 == exec_space.compare( "openmp" ) ||
              0 == exec_space.compare( "OpenMP" ) ||
              0 == exec_space.compare( "OPENMP" ) )
    {
#ifdef KOKKOS_ENABLE_OPENMP
        return std::make_shared<
            ExaMPM::Solver<Kokkos::HostSpace, Kokkos::OpenMP>>(
            comm, global_bounding_box, global_num_cell, periodic, partitioner,
            halo_cell_width, create_functor, particles_per_cell, bulk_modulus,
            density, gamma, kappa, delta_t, gravity, bc );
#else
        throw std::runtime_error( "OpenMP Backend Not Enabled" );
#endif
    }
    else if ( 0 == exec_space.compare( "cuda" ) ||
              0 == exec_space.compare( "Cuda" ) ||
              0 == exec_space.compare( "CUDA" ) )
    {
#ifdef KOKKOS_ENABLE_CUDA
        return std::make_shared<
            ExaMPM::Solver<Kokkos::CudaSpace, Kokkos::Cuda>>(
            comm, global_bounding_box, global_num_cell, periodic, partitioner,
            halo_cell_width, create_functor, particles_per_cell, bulk_modulus,
            density, gamma, kappa, delta_t, gravity, bc );
#else
        throw std::runtime_error( "CUDA Backend Not Enabled" );
#endif
    }
    else if ( 0 == exec_space.compare( "hip" ) ||
              0 == exec_space.compare( "Hip" ) ||
              0 == exec_space.compare( "HIP" ) )
    {
#ifdef KOKKOS_ENABLE_HIP
        return std::make_shared<ExaMPM::Solver<Kokkos::Experimental::HIPSpace,
                                               Kokkos::Experimental::HIP>>(
            comm, global_bounding_box, global_num_cell, periodic, partitioner,
            halo_cell_width, create_functor, particles_per_cell, bulk_modulus,
            density, gamma, kappa, delta_t, gravity, bc );
#else
        throw std::runtime_error( "HIP Backend Not Enabled" );
#endif
    }
    else
    {
        throw std::runtime_error( "invalid backend" );
        return nullptr;
    }
}

//---------------------------------------------------------------------------//

} // end namespace ExaMPM

#endif // end EXAMPM_SOLVER_HPP
