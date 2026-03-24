#include <ExaMPM_BoundaryConditions.hpp>
#include <ExaMPM_Solver.hpp>

#include <Cabana_Core.hpp>

#include <Cabana_Grid.hpp>

#include <Kokkos_Core.hpp>

#include <mpi.h>
#include <veloc.h>

#include <array>
#include <cmath>
#include <cstring>
#include <string>

//---------------------------------------------------------------------------//
// Create the problem setup. The initial geometry is a sphere centered at the
// origin with a radius of 0.25.
struct ParticleInitFunc
{
    double _volume;
    double _mass;

    ParticleInitFunc( const double cell_size, const int ppc,
                      const double density )
        : _volume( cell_size * cell_size * cell_size / ( ppc * ppc * ppc ) )
        , _mass( _volume * density )
    {
    }

    template <class ParticleType>
    KOKKOS_INLINE_FUNCTION bool operator()( const double x[3],
                                            ParticleType& p ) const
    {
        if ( x[0] * x[0] + x[1] * x[1] + x[2] * x[2] < 0.25 * 0.25 )
        {
            // Affine matrix.
            for ( int d0 = 0; d0 < 3; ++d0 )
                for ( int d1 = 0; d1 < 3; ++d1 )
                    Cabana::get<0>( p, d0, d1 ) = 0.0;

            // Velocity
            for ( int d = 0; d < 3; ++d )
                Cabana::get<1>( p, d ) = 0.0;

            // Position
            for ( int d = 0; d < 3; ++d )
                Cabana::get<2>( p, d ) = x[d];

            // Mass
            Cabana::get<3>( p ) = _mass;

            // Volume
            Cabana::get<4>( p ) = _volume;

            // Deformation gradient determinant.
            Cabana::get<5>( p ) = 1.0;

            return true;
        }

        return false;
    }
};

//---------------------------------------------------------------------------//
void freeFall( const double cell_size, const int ppc, const int halo_size,
               const double delta_t, const double t_final, const int write_freq,
               const std::string& exec_space )
{
    // The free fall domain is in a box on [-0.5,0.5] in each dimension.
    Kokkos::Array<double, 6> global_box = { -0.5, -0.5, -0.5, 0.5, 0.5, 0.5 };

    // Compute the number of cells in each direction. The user input must
    // squarely divide the domain.
    std::array<int, 3> global_num_cell = {
        static_cast<int>( 1.0 / cell_size ),
        static_cast<int>( 1.0 / cell_size ),
        static_cast<int>( 1.0 / cell_size ) };

    // All boundaries are periodic to allow the ball to keep falling.
    std::array<bool, 3> periodic = { true, true, true };

    // For simplicity we will only partition in Y.
    int comm_size;
    MPI_Comm_size( MPI_COMM_WORLD, &comm_size );
    std::array<int, 3> ranks_per_dim = { 1, comm_size, 1 };
    Cabana::Grid::ManualBlockPartitioner<3> partitioner( ranks_per_dim );

    // Material properties.
    double bulk_modulus = 5.0e5;
    double density = 1.0e3;
    double gamma = 7.0;
    double kappa = 100.0;

    // Gravity pulls down in z.
    double gravity = 9.81;

    // Periodic everywhere
    ExaMPM::BoundaryCondition bc;
    bc.boundary[0] = ExaMPM::BoundaryType::NONE;
    bc.boundary[1] = ExaMPM::BoundaryType::NONE;
    bc.boundary[2] = ExaMPM::BoundaryType::NONE;
    bc.boundary[3] = ExaMPM::BoundaryType::NONE;
    bc.boundary[4] = ExaMPM::BoundaryType::NONE;
    bc.boundary[5] = ExaMPM::BoundaryType::NONE;

    // Solve the problem.
    auto solver = ExaMPM::createSolver(
        exec_space, MPI_COMM_WORLD, global_box, global_num_cell, periodic,
        partitioner, halo_size, ParticleInitFunc( cell_size, ppc, density ),
        ppc, bulk_modulus, density, gamma, kappa, delta_t, gravity, bc );
    solver->solve( t_final, write_freq );
}

//---------------------------------------------------------------------------//
// Usage:
//   ./FreeFall cell_size parts_per_cell halo_cells dt t_end write_freq exec_space [--veloc-cfg <path>]
//
// The optional --veloc-cfg argument specifies the path to the VeloC
// configuration file. If not provided, defaults to "veloc.cfg" in the
// current working directory.
//---------------------------------------------------------------------------//
int main( int argc, char* argv[] )
{
    MPI_Init( &argc, &argv );

    // --- Parse optional --veloc-cfg argument (before Kokkos::initialize) ---
    std::string veloc_cfg = "veloc.cfg";
    // Scan argv for --veloc-cfg and extract it without disturbing other args
    int new_argc = argc;
    for ( int i = 1; i < argc; ++i )
    {
        if ( std::strcmp( argv[i], "--veloc-cfg" ) == 0 && i + 1 < argc )
        {
            veloc_cfg = argv[i + 1];
            // Shift remaining args down to remove --veloc-cfg and its value
            for ( int j = i; j + 2 < argc; ++j )
                argv[j] = argv[j + 2];
            new_argc -= 2;
            break;
        }
    }
    argc = new_argc;

    // --- Initialize VeloC (BEFORE Kokkos::initialize, per best practice) ---
    VELOC_Init( MPI_COMM_WORLD, veloc_cfg.c_str() );

    Kokkos::initialize( argc, argv );

    // check inputs and write usage
    if ( argc < 8 )
    {
        std::cerr << "Usage: ./FreeFall cell_size parts_per_cell_size "
                     "halo_cells dt t_end write_freq exec_space "
                     "[--veloc-cfg <path>]\n";
        std::cerr << "\nwhere cell_size       edge length of a computational "
                     "cell (domain is unit cube)\n";
        std::cerr
            << "      parts_per_cell  particles per cell in each direction\n";
        std::cerr << "      halo_cells      number of halo cells\n";
        std::cerr << "      dt              time step size\n";
        std::cerr << "      t_end           simulation end time\n";
        std::cerr
            << "      write_freq      number of steps between output files\n";
        std::cerr << "      exec_space      execute with: serial, openmp, "
                     "cuda, hip\n";
        std::cerr << "      --veloc-cfg     (optional) path to VeloC config "
                     "file (default: veloc.cfg)\n";
        std::cerr << "\nfor example: ./FreeFall 0.05 2 0 0.001 1.0 10 serial\n";
        Kokkos::finalize();
        VELOC_Finalize( 0 );
        MPI_Finalize();
        return 0;
    }

    // cell size
    double cell_size = std::atof( argv[1] );

    // particles per cell in a dimension
    int ppc = std::atoi( argv[2] );

    // number of halo cells.
    int halo_size = std::atoi( argv[3] );

    // time step size.
    double delta_t = std::atof( argv[4] );

    // end time.
    double t_final = std::atof( argv[5] );

    // write frequency
    int write_freq = std::atoi( argv[6] );

    // execution space
    std::string exec_space( argv[7] );

    // run the problem.
    freeFall( cell_size, ppc, halo_size, delta_t, t_final, write_freq,
              exec_space );

    Kokkos::finalize();

    VELOC_Finalize( 1 );

    MPI_Finalize();

    return 0;
}

//---------------------------------------------------------------------------//
