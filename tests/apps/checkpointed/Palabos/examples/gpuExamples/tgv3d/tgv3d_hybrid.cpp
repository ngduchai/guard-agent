/* This file is part of the Palabos library.
 * Copyright (C) 2009 Jonas Latt
 * E-mail contact: jonas@lbmethod.org
 * The most recent release of Palabos can be downloaded at
 * <http://www.lbmethod.org/palabos/>
 *
 * The library Palabos is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * The library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/** \file
 * Taylor-Green vortex.
 * This benchmark case for the Palabos project "From CPU to GPU in 80 days" was added by Christophe
 *Coreixas. Project page: https://palabos.unige.ch/community/cpu-gpu-80-days/ Performance
 *measurements:
 *https://docs.google.com/spreadsheets/d/1ROJbPlLKqX9JxO408S4BEFkzK1XLbxiimUdd4XaIJ8c/edit?usp=sharing
 *
 **/

#include "palabos3D.h"
#include "palabos3D.hh"  // include full template code
#include <vector>
#include <cmath>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <algorithm>
#include <chrono>
#include "omp.h"

using namespace plb;
using namespace plb::descriptors;
using namespace std;
using namespace std::chrono;

typedef float T;
#define DESCRIPTOR D3Q19Descriptor

//////// A functional, used to initialize the simulation
template <typename T>
class TGVInitialVelocityField {
public:
    TGVInitialVelocityField(plint const &nx_, plint const &ny_, plint const &nz_, T const &u0_) :
        nx(nx_), ny(ny_), nz(nz_), u0(u0_)
    { }

    void operator()(plint iX, plint iY, plint iZ, T &rho, Array<T, 3> &u) const
    {
        T rho0 = 1.0;
        T U0 = u0;
        T pi = M_PI;

        T x = (T)2. * pi * (iX - nx / 2.) / T(nx);
        T y = (T)2. * pi * (iY - ny / 2.) / T(ny);
        T z = (T)2. * pi * (iZ - nz / 2.) / T(nz);

        rho = rho0
              * (1.
                 + U0 * U0 / (16. * DESCRIPTOR<T>::cs2) * (cos(2. * x) + cos(2. * y))
                       * (cos(2. * z) + 2.));
        u[0] = U0 * sin(x) * cos(y) * cos(z);
        u[1] = -U0 * cos(x) * sin(y) * cos(z);
        u[2] = 0.;
    }

private:
    plint nx;
    plint ny;
    plint nz;
    T u0;
};

//////// Initialize the simulation
void simulationSetup(
    MultiBlockLattice3D<T, DESCRIPTOR> &lattice, const plint nx, const plint ny, const plint nz,
    const T u0)
{
    // Set periodic boundaries.
    lattice.periodicity().toggleAll(true);

    // Initialize the simulation domain.
    initializeAtEquilibrium(
        lattice, lattice.getBoundingBox(), TGVInitialVelocityField<T>(nx, ny, nz, u0));

    // Call initialize to get the lattice ready for the simulation.
    lattice.initialize();
}

//////// Post processing & Data outputs
/// Write 3D fields (physical units) into a VTK file.
void writeVTK(MultiBlockLattice3D<T, DESCRIPTOR> &lattice, T dx, T dt, plint iter)
{
    VtkStructuredImageOutput3D<T> vtkOut(createFileName("vtk", iter, 6), dx);
    vtkOut.writeData<float>(
        *computeVelocityNorm(lattice), "machNorm", 1.0 / std::sqrt(DESCRIPTOR<T>::cs2));
    vtkOut.writeData<float>(*computeDensity(lattice), "density", 1.0);
    vtkOut.writeData<3, float>(*computeVelocity(lattice), "velocity", dx / dt);
    vtkOut.writeData<3, float>(
        *computeBulkVorticity(*computeVelocity(lattice)), "vorticity", (T)1 / dt);
}

/// Compute the compressible kinetic energy averaged over the whole domain.
/// (accounts for density variations)
auto computeAveragedCompressibleKinEnergy(MultiBlockLattice3D<T, DESCRIPTOR> &lattice)
{
    unique_ptr<MultiScalarField3D<T> > density = computeDensity(lattice);
    unique_ptr<MultiScalarField3D<T> > velocityNorm = computeVelocityNorm(lattice);
    unique_ptr<MultiScalarField3D<T> > kinEnergy =
        multiply(0.5, *multiply(*density, *multiply(*velocityNorm, *velocityNorm)));
    return computeAverage(*kinEnergy);
}

/// Compute the kinetic energy averaged over the whole domain.
auto computeAveragedKinEnergy(MultiBlockLattice3D<T, DESCRIPTOR> &lattice)
{
    unique_ptr<MultiScalarField3D<T> > kinEnergy = computeKineticEnergy(lattice);
    return computeAverage(*kinEnergy);
}

/// Compute the enstrophy averaged over the whole domain.
auto computeAveragedEnstrophy(MultiBlockLattice3D<T, DESCRIPTOR> &lattice)
{
    unique_ptr<MultiTensorField3D<T, 3> > velocity = computeVelocity(lattice);
    unique_ptr<MultiTensorField3D<T, 3> > vorticity = computeBulkVorticity(*velocity);
    unique_ptr<MultiScalarField3D<T> > vorticityNorm = computeNorm(*vorticity);
    unique_ptr<MultiScalarField3D<T> > enstrophy =
        multiply(0.5, *multiply(*vorticityNorm, *vorticityNorm));
    return computeAverage(*enstrophy);
}

/// Compute the RMS kinetic energy averaged over the whole domain.
auto computeRMSkinEnergy(MultiBlockLattice3D<T, DESCRIPTOR> &lattice)
{
    unique_ptr<MultiScalarField3D<T> > velocityNorm = computeVelocityNorm(lattice);
    unique_ptr<MultiScalarField3D<T> > kinEnergy =
        multiply(0.5, *multiply(*velocityNorm, *velocityNorm));
    T averagedKinEnergy = computeAverage(*kinEnergy);
    subtractInPlace(*kinEnergy, averagedKinEnergy);
    multiplyInPlace(*kinEnergy, *kinEnergy);
    return std::sqrt(computeAverage(*kinEnergy));
}

/// Compute the RMS enstrophy averaged over the whole domain.
auto computeRMSenstrophy(MultiBlockLattice3D<T, DESCRIPTOR> &lattice)
{
    unique_ptr<MultiTensorField3D<T, 3> > velocity = computeVelocity(lattice);
    unique_ptr<MultiTensorField3D<T, 3> > vorticity = computeBulkVorticity(*velocity);
    unique_ptr<MultiScalarField3D<T> > vorticityNorm = computeNorm(*vorticity);
    unique_ptr<MultiScalarField3D<T> > enstrophy =
        multiply(0.5, *multiply(*vorticityNorm, *vorticityNorm));
    T averagedEns = computeAverage(*enstrophy);
    subtractInPlace(*enstrophy, averagedEns);
    multiplyInPlace(*enstrophy, *enstrophy);
    return std::sqrt(computeAverage(*enstrophy));
}

/// Write all parameters in a log file.
void writeLogFile(
    T &Re, T &Ma, T &soundSpeed, plint &N, plint &nx, plint &ny, plint &nz, T &dx, T &dt, T &u0,
    T &nu, T &tau, T &omega, T &tc)
{
    plb_ofstream fout("tmp/log.dat");
    fout << " //=========== LBM Parameters ============// " << std::endl;
    fout << "   Lattice  -->           "
         << "D3Q19" << std::endl;
    fout << "   Dynamics -->           "
         << "BGK_Ma2" << std::endl;
    fout << std::endl;

    fout << " //========= Physical Parameters =========// " << std::endl;
    fout << " Flow properties (dimensionless):    " << std::endl;
    fout << "   Re = " << Re << std::endl;
    fout << "   Ma = " << Ma << std::endl;
    fout << " Flow properties (physical units):    " << std::endl;
    fout << "   nu = " << nu * dx * dx / dt << " [m2/s]" << std::endl;
    fout << "   c  = " << soundSpeed << " [m/s]" << std::endl;
    fout << "   u0 = " << Ma * ::sqrt(DESCRIPTOR<T>::cs2) * dx / dt << " [m/s]" << std::endl;
    fout << "   tc = " << tc * dt << " [s]" << std::endl;
    fout << " Geometry (physical units):    " << std::endl;
    fout << "   lx = " << nx * dx << " [m]" << std::endl;
    fout << "   ly = " << ny * dx << " [m]" << std::endl;
    fout << "   lz = " << nz * dx << " [m]" << std::endl;
    fout << std::endl;

    fout << " //======== Numerical Parameters =========// " << std::endl;
    fout << " Numerical discretization (physical units):    " << std::endl;
    fout << "   dx = " << dx << " [m]" << std::endl;
    fout << "   dt = " << dt << " [s]" << std::endl;
    fout << " Geometry (LB units):    " << std::endl;
    fout << "   N  = " << N << " (resolution)" << std::endl;
    fout << "   nx = " << nx << std::endl;
    fout << "   ny = " << ny << std::endl;
    fout << "   nz = " << nz << std::endl;
    fout << " Flow properties (LB units):    " << std::endl;
    fout << "   nuLB = " << nu << std::endl;
    fout << "   u0LB = " << Ma * ::sqrt(DESCRIPTOR<T>::cs2) << std::endl;
    fout << "   tcLB = " << round(tc) << " (" << tc << ")" << std::endl;
    fout << " Collision parameters (LB units):    " << std::endl;
    fout << "   tau = " << tau << std::endl;
    fout << "   omega = " << omega << std::endl;
    fout << std::endl;

    fout << " //======== Simulation parameters ========// " << std::endl;
    fout << "   output= "
         << "tmp" << std::endl;
    fout << "   tAdim = "
         << "20"
         << " * tc" << std::endl;
    fout << "         = " << (plint)(20 * tc) * dt << " [s]" << std::endl;
    fout << "         = " << (plint)(20 * tc) << " [iterations]" << std::endl;
    fout << "   vtsT  = "
         << "5"
         << " * tc" << std::endl;
    fout << "         = " << (plint)(5 * tc) * dt << " [s]" << std::endl;
    fout << "         = " << (plint)(5 * tc) << " [iterations]" << std::endl;
}

// Return a new clock for the current time, for benchmarking.
auto restartClock()
{
    return make_pair(high_resolution_clock::now(), 0);
}

// Compute the time elapsed since a starting point, and the corresponding
// performance of the code in Mega Lattice site updates per second (MLups).
double printMlups(plint clock_iter, plint nelem)
{
    double elapsed = global::timer("tgv").stop();
    double mlups = static_cast<double>(nelem * clock_iter) / elapsed * 1.e-6;

    pcout << "Benchmark result: " << setprecision(4) << mlups << " MLUPS" << endl;
    pcout << endl;
    return mlups;
}

// Run a regression test for a specific pre-recorded value
// of the average kinetic energy.
void runRegression(double energy, plint iT)
{
    double reference_energy = 104.7253828509;
    pcout << "Regression test at iteration " << iT << ": Average energy = " << setprecision(13)
          << energy;
    if (std::fabs(energy - reference_energy) < 1.e-10) {
        pcout << ": OK" << endl;
    } else {
        pcout << ": FAILED" << endl;
        pcout << "Expected the value " << reference_energy << endl;
        throw runtime_error("Regression test failed.");
    }
}

//////// MAIN PROGRAM
int main(int argc, char *argv[])
{
    plbInit(&argc, &argv);

    //////// Benchmark parameters
    bool regression = false;
    bool benchmark = true;
    plint bench_ini_iter = 1000;
    plint bench_max_iter = 2000;

    //////// Simulation domain parameters
    plint N = 128;
    plint nx = N;
    plint ny = N;
    plint nz = N;

    //////// Dimensionless parameters
    T u0 = 0.02;                        // velocity in LB units
    T cs = ::sqrt(DESCRIPTOR<T>::cs2);  // Sound speed in LB units
    T Ma = u0 / cs;                     // Mach number
    T Ntgv = N / (2. * M_PI);           // The normalized size of the domain is 2*pi in paper,
                                        // but here we used 1 instead, hence the normalization
    T tc = (T)(Ntgv / u0);              // Convective time in iterations
    T Re = 1600.;                       // Reynolds number
    T nu = (u0 * Ntgv) / Re;            // Kinematic viscosity in LB units
    T tau = nu / DESCRIPTOR<T>::cs2;    // Relaxation time in LB units
    T omega = 1. / (tau + 0.5);         // Relaxation frequency in LB units

    //////// Numerical parameters and sound speed
    T dx = 0.01;     // Space step in physical units [m]
    T dt = dx * u0;  // Time step in physical units [s] based on the convective scaling
                     //   this is different than imposing dt with the speed of sound!!!
                     //   Instead, here we assume that u_phy = 1 [m/s]
    T soundSpeed = cs * (dx / dt);  // Sound speed obtained with u_phy = 1 [m/s]

    ///// Output directory
    global::directories().setOutputDir("tmp/");

    ///// Simulation maximal time, and output frequency (in terms of iterations).
    plint vtsTout = 5 * tc;
    plint tmax =
        benchmark ? bench_max_iter
                  : (plint)20 * tc + 1;  // If benchmark mode, we only run bench_max_iter iterations
    tmax = regression ? 151 : tmax;      // If regression mode, we override the number of iterations

    // Print the simulation parameters to the terminal.
    if (regression) {
        pcout << "Taylor-Green vortex, regression mode" << endl;
    } else if (benchmark) {
        pcout << "Taylor-Green vortex, benchmark mode" << endl;
    } else {
        pcout << "Taylor-Green vortex, production mode" << endl;
    }
    pcout << "Size = {" << nx << ", " << ny << ", " << nz << "}" << endl;
    pcout << "Re = " << Re << endl;
    pcout << "omega = " << omega << endl;
    pcout << "u0 = " << u0 << endl;
    if (benchmark) {
        pcout << "Now running " << bench_ini_iter << " warm-up iterations." << endl;
    } else {
        pcout << "max_t = " << tmax << endl;
    }

#ifdef USE_CUDA_MALLOC
    pcout << "Using CUDA Malloc" << endl;
#endif

    ///// Generate the dynamics and the corresponding lattice from the .xml file.
    Dynamics<T, DESCRIPTOR> *dyn = new BGKdynamics<T, DESCRIPTOR>(omega);
    MultiBlockLattice3D<T, DESCRIPTOR> lattice(nx, ny, nz, dyn);

    lattice.toggleInternalStatistics(false);

    ///// Initialization from analytical profiles
    simulationSetup(lattice, nx, ny, nz, u0);

    ///// Initial state is saved
    writeVTK(lattice, dx, dt, 0);

    ///// Output stats (kinetic energy and enstrophy)
    plb_ofstream statsOut("tmp/stats.dat");
    T previous_energy = std::numeric_limits<T>::max();

    ///// Output all parameters in a log file
    writeLogFile(Re, Ma, soundSpeed, N, nx, ny, nz, dx, dt, u0, nu, tau, omega, tc);

    // Reset the clock.
    global::timer("tgv").start();

    plint clock_iter = 0;

    AcceleratedLattice3D<T, DESCRIPTOR> accLattice(lattice);

    ///// Main loop over time iterations.
    for (plint iT = 0; iT < tmax; ++iT) {
        // The regression case has been registered at a resolution of N=128 after 150 iterations.
        // This test should be executed at every code change.
        if (regression && N == 128 && iT == 150) {
            accLattice.writeBack(lattice);
            T kinEnergy = nx * ny * nz * computeAveragedKinEnergy(lattice);
            // T kinEnergy = computeAveragedKinEnergy(lattice);
            runRegression(kinEnergy, iT);
        }

        if (!regression && !benchmark) {
            accLattice.writeBack(lattice);
            T kinEnergy = computeAveragedKinEnergy(lattice);
            T kinEnergyAdim = kinEnergy / (0.5 * u0 * u0);
            T RMSkinEnergy = computeRMSkinEnergy(lattice);
            T RMSkinEnergyAdim = RMSkinEnergy / kinEnergy;

            T enstrophy = computeAveragedEnstrophy(lattice);
            T enstrophyAdim = enstrophy * (nx * nx) / (0.5 * u0 * u0);
            T RMSenstrophy = computeRMSenstrophy(lattice);
            T RMSenstrophyAdim = RMSenstrophy / enstrophy;

            statsOut << iT / tc << " " << kinEnergy << " " << kinEnergyAdim << " " << RMSkinEnergy
                     << " " << RMSkinEnergyAdim << " " << enstrophy << " " << enstrophyAdim << " "
                     << RMSenstrophy << " " << RMSenstrophyAdim << std::endl;

            ///// Stability test based on the decrease of the kinetic energy.
            // The kinetic energy should be smaller than its initial value (weak condition)
            if (iT == 0)
                previous_energy = kinEnergy;
            if ((iT > (int)(0.01 * tc)) && !(kinEnergy < previous_energy)) {
                pcout << "Catastrophic error: energy has increased or is NaN!" << std::endl;
                return 1;
            }
        }

        if (benchmark && iT == bench_ini_iter) {
            pcout << "Now running " << bench_max_iter - bench_ini_iter << " benchmark iterations."
                  << endl;
            global::timer("tgv").restart();
            clock_iter = 0;
        }

        ///// Lattice Boltzmann iteration step.
        accLattice.collideAndStream();

        ///// Output.
        if (!regression && !benchmark && iT % vtsTout == 0) {
            accLattice.writeBack(lattice);
            pcout << "Writing VTS file at iteration = " << iT << std::endl;
            writeVTK(lattice, dx, dt, iT);
        }
        ++clock_iter;
    }
    statsOut.close();
    if (benchmark) {
        printMlups(clock_iter, nx * ny * nz);
    }

    return 0;
}
