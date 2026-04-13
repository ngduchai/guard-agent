/* This file is part of the Palabos library.
 *
 * The Palabos softare is developed since 2011 by FlowKit-Numeca Group Sarl
 * (Switzerland) and the University of Geneva (Switzerland), which jointly
 * own the IP rights for most of the code base. Since October 2019, the
 * Palabos project is maintained by the University of Geneva and accepts
 * source code contributions from the community.
 *
 * Contact:
 * Jonas Latt
 * Computer Science Department
 * University of Geneva
 * 7 Route de Drize
 * 1227 Carouge, Switzerland
 * jonas.latt@unige.ch
 *
 * The most recent release of Palabos can be downloaded at
 * <https://palabos.unige.ch/>
 *
 * The library Palabos is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * The library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
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

#define USE_ACC

#ifdef USE_ACC
#define MULTIBLOCK AcceleratedLattice3D
#else
#define MULTIBLOCK MultiBlockLattice3D
#endif

#include "palabos3D.h"
#include "palabos3D.hh"
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

// Custom facet to format numbers with apostrophes as thousand separators
class ApostropheSeparator : public std::numpunct<char> {
protected:
    virtual char do_thousands_sep() const
    {
        return '\'';
    }
    virtual std::string do_grouping() const
    {
        return "\03";
    }
};

typedef float T;
#define DESCRIPTOR D3Q19Descriptor  // Change this line to modify the lattice

string dynName = "BGK";                     // Change this line to modify the collision model
const int COLLMODEL = CollisionModel::BGK;  // Change this line to modify the collision model
constexpr bool applyWeakScaling = false;

//////// A functional, used to get the dynamics
template <typename T, template <typename U> class Descriptor>
Dynamics<T, Descriptor> *getDynamics(string &dynName, T &omega)
{
    Dynamics<T, Descriptor> *dyn;
    if (dynName == "BGK") {  // BGK with second-order equilibrium
        dyn = new BGKdynamics<T, Descriptor>(omega);
    } else if (dynName == "TRT")
    {  // Collision based on two-relaxation-time model proposed by Ginzburg et al.
        dyn = new TRTdynamics<T, Descriptor>(omega);
    } else if (dynName == "RM")
    {  // Collision based on raw moment space (equivalent to Complete_BGK if SRT and D3Q27)
        dyn = new RMdynamics<T, Descriptor>(omega);
    } else if (dynName == "HM")
    {  // Collision based on Hermite moment space (equivalent to Complete_BGK if SRT and D3Q27)
        dyn = new HMdynamics<T, Descriptor>(omega);
    } else if (dynName == "CM")
    {  // Collision based on central moment space (equivalent to Complete_BGK if SRT and D3Q27)
        dyn = new CMdynamics<T, Descriptor>(omega);
    } else if (dynName == "CHM") {  // Collision based on central Hermite moment space
                                    // (equivalent to Complete_BGK if SRT and D3Q27)
        dyn = new CHMdynamics<T, Descriptor>(omega);
    } else if (dynName == "K") {  // Collision based on cumulant space
        dyn = new Kdynamics<T, Descriptor>(omega);
    } else if (dynName == "GH") {  // Collision based on Gauss-Hermite quadrature (HM with weighted
                                   // scalar product, equivalent to Complete_BGK if SRT and D3Q27)
        dyn = new GHdynamics<T, Descriptor>(omega);
    } else if (dynName == "RR") {  // Recursive regularization of populations (equivalent to
                                   // Complete_Regularized_BGK if SRT and D3Q27)
        dyn = new RRdynamics<T, Descriptor>(omega);
    } else {
        pcout << "Error: Dynamics name does not exist, please choose among BGK, TRT, RM, HM, CM, "
                 "CHM, K, GH and RR."
              << std::endl;
        exit(-1);
    }

    return dyn;
}

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
    MULTIBLOCK<T, DESCRIPTOR> &lattice, const plint nx, const plint ny, const plint nz, const T u0)
{
    // Initialize the simulation domain.
    initializeAtEquilibrium(
        lattice, lattice.getBoundingBox(), TGVInitialVelocityField<T>(nx, ny, nz, u0));

    // Call initialize to get the lattice ready for the simulation.
    lattice.initialize();
}

//////// Post processing & Data outputs
/// Write 3D fields (physical units) into a VTK file.
void writeVTK(MULTIBLOCK<T, DESCRIPTOR> &lattice, T dx, T dt, plint iter)
{
    VtkImageOutput3D<T> vtkOut(createFileName("vtk", iter, 6), dx);
    vtkOut.writeData<3, T>(*computeVelocity(lattice), "velocity", dx / dt);
    // // Below are additional fields you might want to output
    // vtkOut.writeData<T>(*computeVelocityNorm(lattice), "machNorm", 1.0/sqrt(DESCRIPTOR<T>::cs2));
    // vtkOut.writeData<T>(*computeDensity(lattice), "density", 1.0);
    // vtkOut.writeData<3,T>(*computeVorticity(*computeVelocity(lattice)), "vorticity", (T)1/dt);
}

/// Compute the kinetic energy averaged over the whole domain.
auto computeAvgKinEnergy(MULTIBLOCK<T, DESCRIPTOR> &lattice)
{
    unique_ptr<MultiScalarField3D<T>> kinEnergy = computeKineticEnergy(lattice);
    return computeAverageAcc(*kinEnergy);
}

/// Compute the enstrophy averaged over the whole domain.
/// Computation based on 2nd, 4th, 6th and 8th order finite difference approximations.
auto computeAvgEnstrophy(
    MULTIBLOCK<T, DESCRIPTOR> &lattice, MultiTensorField3D<T, 3> &velocity,
    MultiTensorField3D<T, 3> &vorticity8, MultiScalarField3D<T> &vorticity8NormSqr)
{
    // // 2nd-order FD computation of enstrophy
    // unique_ptr<MultiTensorField3D<T,3>> velocity = computeVelocity(lattice);
    // unique_ptr<MultiTensorField3D<T,3>> vorticity = computeVorticity(*velocity);
    // unique_ptr<MultiScalarField3D<T>> vorticityNorm = computeNorm(*vorticity);
    // unique_ptr<MultiScalarField3D<T>> enstrophy =
    //     multiply((T)0.5, *multiply(*vorticityNorm,*vorticityNorm) );

    // // 4th-order FD computation of enstrophy
    // unique_ptr<MultiTensorField3D<T,3>> vorticity4 = computeVorticityOrderFour(*velocity);
    // unique_ptr<MultiScalarField3D<T>> vorticity4Norm = computeNorm(*vorticity4);
    // unique_ptr<MultiScalarField3D<T>> enstrophy4 =
    //     multiply((T)0.5, *multiply(*vorticity4Norm,*vorticity4Norm) );

    // // 6th-order FD computation of enstrophy
    // unique_ptr<MultiTensorField3D<T,3>> vorticity6 = computeVorticityOrderSix(*velocity);
    // unique_ptr<MultiScalarField3D<T>> vorticity6Norm = computeNorm(*vorticity6);
    // unique_ptr<MultiScalarField3D<T>> enstrophy6 =
    //     multiply((T)0.5, *multiply(*vorticity6Norm,*vorticity6Norm) );

    // // 8th-order FD computation of enstrophy
    // unique_ptr<MultiTensorField3D<T,3>> vorticity8 = computeVorticityOrderEight(*velocity);
    // unique_ptr<MultiScalarField3D<T>> vorticity8Norm = computeNorm(*vorticity8);
    // unique_ptr<MultiScalarField3D<T>> enstrophy8 =
    //     multiply((T)0.5, *multiply(*vorticity8Norm,*vorticity8Norm) );

    // return
    // make_tuple(computeAverageAcc(*enstrophy),computeAverageAcc(*enstrophy4),computeAverageAcc(*enstrophy6),computeAverageAcc(*enstrophy8));

    computeVelocity(lattice, velocity, lattice.getBoundingBox());

    computeBulkVorticityOrderEightAcc(velocity, vorticity8);
    computeNormSqrAcc(vorticity8, vorticity8NormSqr);
    return (T)0.5 * computeAverageAcc(vorticity8NormSqr);

    // unique_ptr<MultiTensorField3D<T, 3> > velocity = computeVelocity(lattice);
    // unique_ptr<MultiTensorField3D<T, 3> > vorticity8 = computeVorticityOrderEight(*velocity);
    // unique_ptr<MultiScalarField3D<T> > vorticity8Norm = computeNorm(*vorticity8);
    // unique_ptr<MultiScalarField3D<T> > enstrophy8 =
    // multiply((T)0.5, *multiply(*vorticity8Norm, *vorticity8Norm));

    // return computeAverageAcc(*enstrophy8);
}

/// Write all parameters in a log file.
void writeLogFile(
    string &dynName, plint &reg, plint &bulkVisco, T &Re, T &Ma, T &soundSpeed, plint &N, plint &nx,
    plint &ny, plint &nz, T &dx, T &dt, T &u0, T &nu, T &tau, T &omega, T &tc)
{
    plb_ofstream fout("tmp/log.dat");

    if (sizeof(T) == sizeof(float))
        fout << "Running Taylor Green vortex using single precision" << endl << endl;
    else
        fout << "Running Taylor Green vortex using single precision" << endl << endl;

    fout << " //=========== LBM Parameters ============// " << endl;
    fout << "   Lattice  -->           "
         << "D3Q" << DESCRIPTOR<T>::q << endl;
    if (bulkVisco == 1 && (dynName != "BGK" || dynName != "TRT")) {
        if (reg == 1) {
            fout << "   Dynamics --> " << dynName << " (regularized with increased bulk viscosity)"
                 << endl;
        } else {
            fout << "   Dynamics --> " << dynName << " (with increased bulk viscosity)" << endl;
        }
    } else if (reg == 1 && (dynName != "BGK" || dynName != "TRT")) {
        fout << "   Dynamics --> " << dynName << " (regularized)" << endl;
    } else {
        fout << "   Dynamics --> " << dynName << endl;
    }
    fout << endl;

    fout << " //========= Physical Parameters =========// " << endl;
    fout << " Flow properties (dimensionless):    " << endl;
    fout << "   Re = " << Re << endl;
    fout << "   Ma = " << Ma << endl;
    fout << " Flow properties (physical units):    " << endl;
    fout << "   nu = " << nu * dx * dx / dt << " [m2/s]" << endl;
    fout << "   c  = " << soundSpeed << " [m/s]" << endl;
    fout << "   u0 = " << Ma * ::sqrt(DESCRIPTOR<T>::cs2) * dx / dt << " [m/s]" << endl;
    fout << "   tc = " << tc * dt << " [s]" << endl;
    fout << " Geometry (physical units):    " << endl;
    fout << "   lx = " << nx * dx << " [m]" << endl;
    fout << "   ly = " << ny * dx << " [m]" << endl;
    fout << "   lz = " << nz * dx << " [m]" << endl;
    fout << endl;

    fout << " //======== Numerical Parameters =========// " << endl;
    fout << " Numerical discretization (physical units):    " << endl;
    fout << "   dx = " << dx << " [m]" << endl;
    fout << "   dt = " << dt << " [s]" << endl;
    fout << " Geometry (LB units):    " << endl;
    fout << "   nx = " << nx << endl;
    fout << "   ny = " << ny << endl;
    fout << "   nz = " << nz << endl;
    fout << " Flow properties (LB units):    " << endl;
    fout << "   nuLB = " << nu << endl;
    fout << "   u0LB = " << Ma * ::sqrt(DESCRIPTOR<T>::cs2) << endl;
    fout << "   tcLB = " << round(tc) << " (" << tc << ")" << endl;
    fout << " Collision parameters (LB units):    " << endl;
    fout << "   tau = " << tau << endl;
    fout << "   omega = " << omega << endl;
    fout << endl;

    fout << " //======== Simulation parameters ========// " << endl;
    fout << "   output= "
         << "tmp" << endl;
    fout << "   tAdim = "
         << "20"
         << " * tc" << endl;
    fout << "         = " << (plint)(20 * tc) * dt << " [s]" << endl;
    fout << "         = " << (plint)(20 * tc) << " [iterations]" << endl;
    fout << "   vtsT  = "
         << "5"
         << " * tc" << endl;
    fout << "         = " << (plint)(5 * tc) * dt << " [s]" << endl;
    fout << "         = " << (plint)(5 * tc) << " [iterations]" << endl;
}

// Return a new clock for the current time, for benchmarking.
auto restartClock()
{
    return make_pair(high_resolution_clock::now(), 0);
}

// Compute the time elapsed since a starting point, and the corresponding
// performance of the code in Mega Lattice site updates per second (MLups).
T printMlups(plint clock_iter, plint nelem)
{
    T elapsed = global::timer("tgv").stop();
    T mlups = static_cast<T>(nelem * clock_iter) / elapsed * 1.e-6;

    pcout << "Benchmark result: " << setprecision(4) << mlups << " MLUPS" << endl;
    pcout << endl;
    return mlups;
}

// Run a regression test for a specific pre-recorded value
// of the average kinetic energy.
void runRegression(T energy, plint iT, string dynName, int N, T Re, int sizeofT)
{
    T reference_energy = 0.;
    if (dynName == "RR" && (int)Re == 1600 && N == 256 && iT == 200 && sizeofT == sizeof(float)) {
        reference_energy = 827.9800415039;
    } else if (
        dynName == "BGK" && (int)Re == 1600 && N == 256 && iT == 200 && sizeofT == sizeof(float)) {
        reference_energy = 838.2340698242;
    } else {
        pcout << "No regression value provided for your parameter set." << endl;
        return;
    }

    // if (dynName == "TRT" && (int)Re == 1600) reference_energy = 104.7253828509;
    // else if (dynName == "RM" || dynName == "HM" || dynName == "CM" || dynName == "CHM" && (int)Re
    // == 1600) reference_energy = 104.725421212; else if (dynName == "K" && (int)Re == 1600)
    // reference_energy = 104.725421212; else if (dynName == "GH" && (int)Re == 1600)
    // reference_energy = 104.7254276103; else if (dynName == "RR" && (int)Re == 1600)
    // reference_energy = 104.725421212;
    pcout << "Regression test at iteration " << iT << ": Average energy = " << setprecision(13)
          << energy;
    if (fabs(energy - reference_energy) < 1.e-10) {
        pcout << ": OK" << endl;
    } else {
        pcout << ": FAILED" << endl;
        pcout << "Expected the value " << reference_energy << endl;
    }
}

//////// MAIN PROGRAM
int main(int argc, char *argv[])
{
    plbInit(&argc, &argv);
    defaultMultiBlockPolicy3D().toggleBlockingCommunication(true);
    pcout << "Number of MPI threads: " << global::mpi().getSize() << endl;

    if (argc != 7) {
        pcout << argc << std::endl;
        pcout << "Error! Wrong number of parameters." << std::endl;
        pcout << "Syntax: " << (std::string)global::argv(0) << " Re Ma N Reg Bulk Bench"
              << std::endl;
        pcout << "Example: " << (std::string)global::argv(0) << " 1600 0.2 128 0 0 0" << std::endl;
        exit(1);
    }

    //////// Collision model
    plint reg = atoi(argv[4]);        // 1 to equilibriate high-order moments, 0 otherwise
    plint bulkVisco = atoi(argv[5]);  // 1 to increase bulk viscosity, 0 otherwise

    //////// Benchmark parameters
    bool regression = false;
    bool benchmark = (bool)atoi(argv[6]);
    plint bench_ini_iter = 100;
    plint bench_max_iter = 200;

    //////// Simulation domain parameters
    plint N = atoi(argv[3]);
    plint nx = N;
    plint ny = N;
    plint nz = N;
    // if (applyWeakScaling) {
    // nz *= global::mpi().getSize();
    //}

    //////// Dimensionless parameters
    T Ma = atof(argv[2]);               // Mach number
    T cs = ::sqrt(DESCRIPTOR<T>::cs2);  // Sound speed in LB units
    T u0 = Ma * cs;                     // Velocity in LB units
    T Ntgv = T(N) / ((T)2. * M_PI);     // The normalized size of the domain is 2*pi in paper,
                                        // but here we used 1 instead, hence the normalization
    T tc = (T)(Ntgv / u0);              // Convective time in iterations
    T Re = atof(argv[1]);               // Reynolds number
    T nu = (u0 * Ntgv) / Re;            // Kinematic viscosity in LB units
    T tau = nu / DESCRIPTOR<T>::cs2;    // Relaxation time in LB units
    T omega = 1. / (tau + 0.5);         // Relaxation frequency in LB units

    //////// Numerical parameters and sound speed

    ///// Convective scaling based on an arbitrary velocity of 1 [m/s]
    // T dx = 0.01;                                // Space step in physical units [m]
    // T dt = dx * u0;                             // Time step in physical units [s] based on the
    // convective scaling
    //                                             //   this is different than imposing dt with the
    //                                             speed of sound!!!
    //                                             //   Instead, here we assume that u_phy = 1 [m/s]
    // T soundSpeed = cs*(dx/dt);                  // Sound speed obtained with u_phy = 1 [m/s]

    ///// Acoustic scaling based on the speed of sound for air at 1013.25 hPa and 20°C
    T soundSpeed = 340.;            // Sound speed in physical units [m/s]
    T dx = 0.01;                    // Space step in physical units [m]
    T dt = dx * (cs / soundSpeed);  // Time step in physical units [s] based on the acoustic scaling

    ///// Output directory
    global::directories().setOutputDir("tmp/");

    ///// Simulation maximal time, and output frequency (in terms of iterations).
    plint vtkTout = 0 * tc;
    plint statsTout = 0.2 * tc;
    plint tmax =
        benchmark ? bench_max_iter
                  : (plint)20 * tc + 1;  // If benchmark mode, we only run bench_max_iter iterations

    // Print the simulation parameters to the terminal.
    if (benchmark)
        pcout << "Taylor-Green vortex, benchmark mode" << endl;
    else
        pcout << "Taylor-Green vortex, production mode" << endl;

    if (sizeof(T) == sizeof(float))
        pcout << "Running single precision" << endl;
    else
        pcout << "Running double precision" << endl;
    pcout << "Lattice D3Q" << DESCRIPTOR<T>::q << endl;

    long totalCells = nx * ny * nz;
    stringstream ss;
    ss.imbue(locale(locale(), new ApostropheSeparator));
    ss << totalCells;
    pcout << "Size = {" << nx << ", " << ny << ", " << nz << "} = " << ss.str() << endl;

    // pcout << "Size = {" << nx << ", " << ny << ", " << nz << "} = " << nx*ny*nz << endl;

    if (bulkVisco == 1 && (dynName != "BGK" || dynName != "TRT")) {
        if (reg == 1) {
            pcout << "Collision = " << dynName << " (regularized with increased bulk viscosity)"
                  << endl;
        } else {
            pcout << "Collision = " << dynName << " (with increased bulk viscosity)" << endl;
        }
    } else if (reg == 1 && (dynName != "BGK" || dynName != "TRT")) {
        pcout << "Collision = " << dynName << " (regularized)" << endl;
    } else {
        pcout << "Collision = " << dynName << endl;
    }
    pcout << "Re = " << Re << endl;
    pcout << "Ma = " << Ma << endl;
    pcout << "omega = " << omega << endl;
    pcout << "u0 = " << u0 << endl;
    if (benchmark)
        pcout << "Now running " << bench_ini_iter << " warm-up iterations." << endl;
    else
        pcout << "max_t = " << tmax << endl;

#ifdef USE_CUDA_MALLOC
    pcout << "Using CUDA Malloc" << endl;
#endif

    ///// Generate the dynamics.
    Dynamics<T, DESCRIPTOR> *dyn = getDynamics<T, DESCRIPTOR>(dynName, omega);
    ///// Generate and initialize relaxation parameters for MRT approaches.
    Array<T, DESCRIPTOR<T>::numRelaxationTimes> relaxMatrix;
    for (int i = 0; i < DESCRIPTOR<T>::numRelaxationTimes; ++i)
        relaxMatrix[i] = omega;
    if (bulkVisco == 1)
        relaxMatrix[DESCRIPTOR<T>::numRelaxationTimes - 1] =
            1.;  // relaxation frequency for the bulk viscosity
    if (reg == 1) {
        for (int iReg = 2; iReg < DESCRIPTOR<T>::numRelaxationTimes - 1; ++iReg)
            relaxMatrix[iReg] = 1.;  // equilibration of high-order moments
    }
    if (dynName == "RM") {
        RMdynamics<T, DESCRIPTOR>::allOmega = relaxMatrix;
    } else if (dynName == "HM") {
        HMdynamics<T, DESCRIPTOR>::allOmega = relaxMatrix;
    } else if (dynName == "CM") {
        CMdynamics<T, DESCRIPTOR>::allOmega = relaxMatrix;
    } else if (dynName == "CHM") {
        CHMdynamics<T, DESCRIPTOR>::allOmega = relaxMatrix;
    } else if (dynName == "K") {
        Kdynamics<T, DESCRIPTOR>::allOmega = relaxMatrix;
    } else if (dynName == "GH") {
        GHdynamics<T, DESCRIPTOR>::allOmega = relaxMatrix;
    } else if (dynName == "RR") {
        RRdynamics<T, DESCRIPTOR>::allOmega = relaxMatrix;
    }

    ///// Generate the lattice for the given dynamics.
    MULTIBLOCK<T, DESCRIPTOR> lattice(nx, ny, nz, dyn);

    lattice.toggleInternalStatistics(false);

    ///// Initialization from analytical profiles
    simulationSetup(lattice, nx, ny, nz, u0);

    // Set periodic boundaries (MUST BE AFTER simulationSetup()!!!).
    lattice.periodicity().toggleAll(true);

    ///// Initial state is saved
    if (!regression && !benchmark && vtkTout != 0) {
        writeVTK(lattice, dx, dt, 0);
    }

    ///// Output stats (kinetic energy and enstrophy)
    plb_ofstream statsOut("tmp/stats.dat");
    // statsOut << "iT/tc  kinEnergyAdim  enstr2Adim  enstr4Adim  enstr6Adim  enstr8Adim" << endl;
    statsOut << "iT/tc  kinEnergyAdim  enstr8Adim" << endl;
    T previous_energy = numeric_limits<T>::max();

    ///// Output all parameters in a log file
    writeLogFile(
        dynName, reg, bulkVisco, Re, Ma, soundSpeed, N, nx, ny, nz, dx, dt, u0, nu, tau, omega, tc);

    // Reset the clock.
    global::timer("tgv").start();
    plint clock_iter = 0;

    int envelopeWidth = 4;
    unique_ptr<MultiTensorField3D<T, 3>> velocity =
        generateMultiTensorField<T, 3>((MultiBlock3D &)lattice, envelopeWidth);
    velocity->periodicity().toggleAll(true);
    unique_ptr<MultiTensorField3D<T, 3>> vorticity8 =
        generateMultiTensorField<T, 3>((MultiBlock3D &)lattice, 1);
    unique_ptr<MultiScalarField3D<T>> vorticity8NormSqr =
        generateMultiScalarField<T>((MultiBlock3D &)lattice, 1);

    ///// Main loop over time iterations.
    plint iT = 0;
    for (iT = 0; iT < tmax; ++iT) {
        ///// Output stats.
        if (!regression && !benchmark && ((iT == 0) || (iT % statsTout == 0) || (iT == tmax))) {
            T kinEnergy = computeAvgKinEnergy(lattice);
            T kinEnergyAdim = kinEnergy / (0.5 * u0 * u0);

            // auto [enstr2,enstr4,enstr6,enstr8] = computeAvgEnstrophy(lattice);
            // T enstr2Adim = enstr2*(nx*nx)/(0.5*u0*u0);
            // T enstr4Adim = enstr4*(nx*nx)/(0.5*u0*u0);
            // T enstr6Adim = enstr6*(nx*nx)/(0.5*u0*u0);
            // T enstr8Adim = enstr8*(nx*nx)/(0.5*u0*u0);

            // statsOut << iT/tc << " "
            //          << kinEnergyAdim << " "
            //          << enstr2Adim    << " "
            //          << enstr4Adim    << " "
            //          << enstr6Adim    << " "
            //          << enstr8Adim    << endl;

            auto enstr8 = computeAvgEnstrophy(lattice, *velocity, *vorticity8, *vorticity8NormSqr);
            T enstr8Adim = enstr8 * (nx * nx) / (0.5 * u0 * u0);

            statsOut << iT / tc << " " << kinEnergyAdim << " " << enstr8Adim << endl;

            //// Stability test based on the decrease of the kinetic energy.
            // The kinetic energy should be smaller than its initial value (weak condition)
            if (iT == 0)
                previous_energy = kinEnergy;
            if ((iT > (int)(0.01 * tc)) && !(kinEnergy < previous_energy)) {
                pcout << "Catastrophic error: energy has increased or is NaN!" << endl;
                return 1;
            }
            pcout << "At iT/tc = " << iT / tc << " --> energy = " << kinEnergy << endl;
            printMlups(statsTout, nx * ny * nz);
            global::timer("tgv").restart();
        }

        ///// Output VTK files.
        if (!regression && !benchmark && vtkTout != 0
            && ((iT == 0) || (iT % vtkTout == 0) || (iT == tmax))) {
            pcout << "Writing VTK file at iteration = " << iT << endl;
            writeVTK(lattice, dx, dt, iT);
        }

        ///// Lattice Boltzmann iteration step.
#ifdef USE_ACC
        //// The command below compiles all collision model kernels,
        //// hence avoiding user typos but it is also less efficient
        // lattice.collideAndStream();

        // This only compiles required collision models
        lattice.collideAndStream(CollisionKernel<T, DESCRIPTOR, COLLMODEL>());
#else
        lattice.collideAndStream();
#endif

        if (benchmark && iT == bench_ini_iter) {
            pcout << "Now running " << bench_max_iter - bench_ini_iter << " benchmark iterations."
                  << endl;
            global::timer("tgv").restart();
            clock_iter = 0;
        }

        ++clock_iter;
    }
    statsOut.close();
    if (benchmark) {
        printMlups(clock_iter, nx * ny * nz);
        // Check energy is not NaN
        T kinEnergy = computeAvgKinEnergy(lattice);
        if (isnan(kinEnergy)) {
            cout << "Simulation was unstable --> Invalid benchmark!!!" << endl;
        } else {
            cout << "Energy check is OK --> Energy = " << kinEnergy << endl;
        }
    }

    if (regression) {
        T kinEnergy = nx * ny * nz * computeAvgKinEnergy(lattice);
        runRegression(kinEnergy, iT, dynName, N, Re, sizeof(T));
    }

    return 0;
}
