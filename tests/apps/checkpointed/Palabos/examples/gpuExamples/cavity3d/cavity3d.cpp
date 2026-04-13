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
 * Lid-driven cavity flow. Benchmark case for the Palabos project "From CPU to GPU in 80 days".
 * Project page: https://palabos.unige.ch/community/cpu-gpu-80-days/
 * Performance measurements:
 *https://docs.google.com/spreadsheets/d/1ROJbPlLKqX9JxO408S4BEFkzK1XLbxiimUdd4XaIJ8c/edit?usp=sharing
 *
 **/

#include "palabos3D.h"
#include "palabos3D.hh"
#include <memory>
#include <iostream>
#include <fstream>
using namespace plb;
using namespace plb::descriptors;
using namespace std;

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
#define DESCRIPTOR D3Q27Descriptor  // Change this line to modify the lattice
//////// Collision model
string dynName = "RR";                     // Change this line to modify the collision model
const int COLLMODEL = CollisionModel::RR;  // Change this line to modify the collision model
const int COLLMODEL_HWBB =
    CollisionModel::HalfwayBounceBack__RR;  // Change this line to modify the collision model

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
        pcout << "Error: Dynamics name does not exist, please choose among BGK, RM, HM, CM, "
                 "CHM, K, GH and RR."
              << endl;
        exit(-1);
    }

    return dyn;
}

/// Run a regression test for a specific pre-recorded value of the average kinetic energy.
void runRegression(T energy, plint iT, string dynName, int nx, int ny, int nz, T Re, T Ma)
{
    double reference_energy = 1.;
    if (nx == 256 && ny == 256 && nz == 256 && sizeof(T) == sizeof(float) && Re == (T)100.
        && Ma == (T)0.1 && DESCRIPTOR<T>::q == 19 && dynName == "BGK" && (int)iT == 200)
    {
        reference_energy = 2.077663702948e-05;
    } else if (nx == 256 && ny == 256 && nz == 256 && sizeof(T) == sizeof(float) && (int)iT == 200)
    {
        pcout << std::boolalpha << (Re == (T)100.) << endl;
        pcout << std::boolalpha << (Ma == (T)0.1) << endl;
        pcout << std::boolalpha << ((int)iT == 200) << endl;
        pcout << std::boolalpha << (DESCRIPTOR<T>::q == 19) << endl;
        reference_energy = 8.446989340882e-06;
    } else if (nx == 400 && ny == 400 && nz == 400 && sizeof(T) == sizeof(float) && (int)iT == 200)
    {
        reference_energy = 6.913718607393e-06;
    } else if (nx == 420 && ny == 420 && nz == 420 && sizeof(T) == sizeof(float) && (int)iT == 200)
    {
        reference_energy = 6.761440090486e-06;
    } else if (nx == 500 && ny == 500 && nz == 500 && sizeof(T) == sizeof(float) && (int)iT == 200)
    {
        reference_energy = 6.241020855668e-06;
    } else if (nx == 600 && ny == 600 && nz == 600 && sizeof(T) == sizeof(float) && (int)iT == 2000)
    {
        reference_energy = 1.630528640817e-05;
    } else {
        pcout << "No regression value provided for your parameter set." << endl;
        return;
    }

    pcout << "Regression test at iteration " << iT << ": Average energy = " << setprecision(13)
          << energy;
    if (fabs(energy - reference_energy) < 1.e-10) {
        pcout << ": OK" << endl;
    } else {
        pcout << ": FAILED" << endl;
        pcout << "Expected the value " << reference_energy << endl;
    }
}

/// Initialization.
class IniCavityFunctional3D : public BoxProcessingFunctional3D_L<T, DESCRIPTOR> {
public:
    IniCavityFunctional3D(Box3D const &fullDomain_, Array<T, 3> const &u_) :
        fullDomain(fullDomain_), u(u_)
    { }
    virtual void process(Box3D domain, BlockLattice3D<T, DESCRIPTOR> &lattice)
    {
        Box3D innerDomain = fullDomain.enlarge(-1);
        Dot3D relativeOffset = lattice.getLocation();
        for (plint iX = domain.x0; iX <= domain.x1; ++iX) {
            plint absX = iX + relativeOffset.x;
            for (plint iY = domain.y0; iY <= domain.y1; ++iY) {
                plint absY = iY + relativeOffset.y;
                for (plint iZ = domain.z0; iZ <= domain.z1; ++iZ) {
                    plint absZ = iZ + relativeOffset.z;

                    if (!contained(absX, absY, absZ, innerDomain)) {
                        HalfwayBounceBack<T, DESCRIPTOR> *dynamics =
                            new HalfwayBounceBack<T, DESCRIPTOR>(
                                lattice.get(iX, iY, iZ).getDynamics().clone());
                        for (plint iPop = 0; iPop < DESCRIPTOR<T>::q; ++iPop) {
                            plint nextX = absX + DESCRIPTOR<T>::c[iPop][0];
                            plint nextY = absY + DESCRIPTOR<T>::c[iPop][1];
                            plint nextZ = absZ + DESCRIPTOR<T>::c[iPop][2];
                            if (contained(nextX, nextY, nextZ, fullDomain)) {
                                dynamics->getData(iPop) = numeric_limits<T>::signaling_NaN();
                            } else {
                                if (nextZ > fullDomain.z1) {
                                    dynamics->setVelocity(iPop, u);
                                } else {
                                    dynamics->setVelocity(iPop, Array<T, 3>(0., 0., 0.));
                                }
                            }
                        }
                        lattice.attributeDynamics(iX, iY, iZ, dynamics);
                    }
                }
            }
        }
    }

    virtual IniCavityFunctional3D *clone() const
    {
        return new IniCavityFunctional3D(*this);
    }

    virtual void getTypeOfModification(vector<modif::ModifT> &modified) const
    {
        modified[0] = modif::dataStructure;
    }

private:
    Box3D fullDomain;
    Array<T, 3> u;
};

/// Compute the kinetic energy averaged over the whole domain.
template <class LATTICE>
auto computeAveragedKinEnergy(LATTICE &lattice)
{
    unique_ptr<MultiScalarField3D<T> > kinEnergy = computeKineticEnergy(lattice);
    return computeAverageAcc(*kinEnergy);
}

/// Add the current velocity components to previous ones for time averaging.
template <class LATTICE>
void addVelocityFieldToAvg(LATTICE &lattice, MultiTensorField3D<T, 3> &avgVelocityField)
{
    unique_ptr<MultiTensorField3D<T, 3> > velocity = computeVelocity(lattice);
    avgVelocityField = *add(avgVelocityField, *velocity);
}

/// Write all parameters in a log file.
void writeLogFile(
    string &dynName, plint &reg, plint &bulkVisco, T &Re, T &Ma, T &soundSpeed, plint &nx,
    plint &ny, plint &nz, T &dx, T &dt, T &u0, T &nu, T &tau, T &omega, T &tc, T &maxIter,
    T &vtkIter, T &statIter, T &startAvgIter, T &avgIter)
{
    plb_ofstream fout("tmp/log.dat");

    if (sizeof(T) == sizeof(float))
        fout << "Running lid-driven cavity using single precision" << endl << endl;
    else
        fout << "Running lid-driven cavity using single precision" << endl << endl;

    fout << " //=========== LBM Parameters ============// " << endl;
    fout << "   Lattice  -->           "
         << "D3Q" << DESCRIPTOR<T>::q << endl;
    if (bulkVisco == 1 and dynName != "BGK") {
        if (reg == 1) {
            fout << "   Dynamics --> " << dynName << " (regularized with increased bulk viscosity)"
                 << endl;
        } else {
            fout << "   Dynamics --> " << dynName << " (with increased bulk viscosity)" << endl;
        }
    } else if (reg == 1 and dynName != "BGK") {
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
    fout << "       output = "
         << "tmp" << endl;
    fout << "      maxIter = " << int(maxIter / tc) << " * tc" << endl;
    fout << "              = " << int(maxIter) * dt << " [s]" << endl;
    fout << "              = " << int(maxIter) << " [iterations]" << endl;
    fout << "      vtkIter = " << int(vtkIter / tc) << " * tc" << endl;
    fout << "              = " << int(vtkIter) * dt << " [s]" << endl;
    fout << "              = " << int(vtkIter) << " [iterations]" << endl;
    fout << "     statIter = " << int(statIter / tc) << " * tc" << endl;
    fout << "              = " << int(statIter) * dt << " [s]" << endl;
    fout << "              = " << int(statIter) << " [iterations]" << endl;
    fout << " startAvgIter = " << int(startAvgIter / tc) << " * tc" << endl;
    fout << "              = " << int(startAvgIter) * dt << " [s]" << endl;
    fout << "              = " << int(startAvgIter) << " [iterations]" << endl;
    fout << "      avgIter = " << int(avgIter / tc) << " * tc" << endl;
    fout << "              = " << int(avgIter) * dt << " [s]" << endl;
    fout << "              = " << int(avgIter) << " [iterations]" << endl;
}

// Compute the time elapsed since a starting point, and the corresponding
// performance of the code in Mega Lattice site updates per second (MLups).
T printMlups(plint clock_iter, plint nelem)
{
    T elapsed = global::timer("cavity").stop();
    T mlups = static_cast<T>(nelem * clock_iter) / elapsed * 1.e-6;

    pcout << "Benchmark result: " << setprecision(4) << mlups << " MLUPS" << endl;
    pcout << endl;
    return mlups;
}

int main(int argc, char *argv[])
{
    plbInit(&argc, &argv);
    defaultMultiBlockPolicy3D().toggleBlockingCommunication(true);

    bool useAccelerated = true;  // Use accelerated lattice (for GPU execution) ?

    // Output VTK files go to this directory
    global::directories().setOutputDir("./tmp/");

    pcout << "Number of MPI threads: " << global::mpi().getSize() << endl;

    T maxIter = 2000;   // Total number of iterations
    T vtkIter = 10000;  // Frequency of VTK file output in production mode
    T statIter = 1000;  // Frequency at which stats are outputed, in production mode
    T startAvgIter =
        40000;  // Iteration at which the velocity field starts being averaged, in production mode
    T avgIter = 1000;  // Frequency at which the velocity field is averaged, in production mode

    int default_nx = 600;
    int default_ny = 600;
    int default_nz = 600;

    plint nx = default_nx;
    plint ny = default_ny;
    plint nz = default_nz;

    T Re = 100.;
    T Ma = 0.1;

    plint reg = 0;        // 1 to equilibriate high-order moments, 0 otherwise
    plint bulkVisco = 0;  // 1 to increase bulk viscosity, 0 otherwise

    try {
        if (global::argc() != 9) {
            throw PlbIOException("Wrong number of arguments.");
        }
        nx = atoi(argv[1]);
        ny = atoi(argv[2]);
        nz = atoi(argv[3]);
        Re = atof(argv[4]);
        Ma = atof(argv[5]);
    } catch (PlbIOException &except) {
        pcout << except.what() << endl;
        pcout << "Error! Wrong number of parameters." << endl;
        pcout << "Syntax:  " << (string)global::argv(0) << "  nx  ny  nz    Re  Ma Reg Bulk Bench"
              << endl;
        pcout << "Example: " << (string)global::argv(0) << " 128 128 128   100 0.1 0 0 0 (BGK)"
              << endl;
        pcout << "         " << (string)global::argv(0) << " 256 256 256  1000 0.1 0 0 0 (BGK)"
              << endl;
        pcout << "         " << (string)global::argv(0) << " 256 256 256  3200 0.1 0 0 0 (BGK)"
              << endl;
        pcout << "         " << (string)global::argv(0) << " 400 400 400 10000 0.1 0 1 0 (RR)"
              << endl;
        return -1;
    }

    //////// Collision model
    reg = atoi(argv[6]);        // 1 to equilibriate high-order moments, 0 otherwise
    bulkVisco = atoi(argv[7]);  // 1 to increase bulk viscosity, 0 otherwise

    //////// Benchmark parameters
    bool regression = false;
    bool benchmark = (bool)atoi(argv[8]);
    bool production = !benchmark;
    plint bench_ini_iter = 100;
    plint bench_max_iter = 200;

    //////// Dimensionless parameters
    T cs = ::sqrt(DESCRIPTOR<T>::cs2);  // Sound speed in LB units
    T u0 = Ma * cs;                     // Velocity in LB units
    T tc = ((T)nx / u0);                // Convective time in iterations
    T nu = (u0 * (T)nx) / Re;           // Kinematic viscosity in LB units
    T tau = nu / DESCRIPTOR<T>::cs2;    // Relaxation time in LB units
    T omega = 1. / (tau + 0.5);         // Relaxation frequency in LB units

    //////// Numerical parameters and sound speed

    ///// Convective scaling based on an arbitrary velocity of 1 [m/s]
    // T dx = 0.01;                                // Space step in physical units [m]
    // T dt = dx * u0;                            // Time step in physical units [s] based on the
    // convective scaling
    //                                             //   this is different than imposing dt with the
    //                                             speed of sound!!!
    //                                             //   Instead, here we assume that u_phy = 1 [m/s]
    // T soundSpeed = cs*(dx/dt);                  // Sound speed obtained with u_phy = 1 [m/s]

    ///// Acoustic scaling based on the speed of sound for air at 1013.25 hPa and 20°C
    T soundSpeed = 340.;            // Sound speed in physical units [m/s]
    T dx = 0.01;                    // Space step in physical units [m]
    T dt = dx * (cs / soundSpeed);  // Time step in physical units [s] based on the acoustic scaling

    if (production) {
        // By default, the simulation goes on for a million iterations AND no averaging
        maxIter = (T)1000000.;
        avgIter = (T)0. * tc;  // No averaging
        if ((int)Re == 1000)
        {  // Steady state so no need to modify maxIter because of the convergence criterion
            vtkIter = (T)10. * tc;
            statIter = (T)1. * tc;
            startAvgIter = (T)50. * tc;
            avgIter = (T)0. * tc;      // Steady state so no need for averaging
        } else if ((int)Re == 3200) {  // Laminar unsteady
            vtkIter = (T)10. * tc;
            statIter = (T)1. * tc;
            startAvgIter = (T)50. * tc;
            maxIter = (T)250. * tc;
            avgIter = (T)1. * tc;
        } else if ((int)Re == 10000) {  // Turbulent unsteady
            vtkIter = (T)100. * tc;
            statIter = (T)1. * tc;
            startAvgIter = (T)150. * tc;
            maxIter = (T)500. * tc;
            avgIter = (T)0.1 * tc;
        }
    }

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
    MultiBlockLattice3D<T, DESCRIPTOR> lattice(nx, ny, nz, dyn);
    lattice.periodicity().toggleAll(true);
    applyProcessingFunctional(
        new IniCavityFunctional3D(lattice.getBoundingBox(), Array<T, 3>(u0, 0., 0.)),
        lattice.getBoundingBox(), lattice);
    lattice.periodicity().toggleAll(false);

    pcout << "Executing a ";
    if (benchmark) {
        pcout << "benchmark ";
    } else {
        pcout << "production ";
    }
#ifdef USE_CUDA_MALLOC
    pcout << "\nUsing CUDA Malloc" << endl;
#endif
    long totalCells = nx * ny * nz;
    stringstream ss;
    ss.imbue(locale(locale(), new ApostropheSeparator));
    ss << totalCells;
    pcout << "Size = {" << nx << ", " << ny << ", " << nz << "} = " << ss.str() << endl;

    pcout << " //=========== LBM Parameters ============// " << endl;
    pcout << "   Lattice  -->           "
          << "D3Q" << DESCRIPTOR<T>::q << endl;
    if (bulkVisco == 1 and dynName != "BGK") {
        if (reg == 1) {
            pcout << "   Dynamics --> " << dynName << " (regularized with increased bulk viscosity)"
                  << endl;
        } else {
            pcout << "   Dynamics --> " << dynName << " (with increased bulk viscosity)" << endl;
        }
    } else if (reg == 1 and dynName != "BGK") {
        pcout << "   Dynamics --> " << dynName << " (regularized)" << endl;
    } else {
        pcout << "   Dynamics --> " << dynName << endl;
    }
    pcout << " //========= Physical Parameters =========// " << endl;
    pcout << " Flow properties (dimensionless):    " << endl;
    pcout << "   Re = " << Re << endl;
    pcout << "   Ma = " << Ma << endl;
    pcout << " Flow properties (LB units):    " << endl;
    pcout << "   nuLB = " << nu << endl;
    pcout << "   u0LB = " << Ma * ::sqrt(DESCRIPTOR<T>::cs2) << endl;
    pcout << "   tcLB = " << round(tc) << " (" << tc << ")" << endl;
    pcout << " Collision parameters (LB units):    " << endl;
    pcout << "   tau   = " << tau << endl;
    pcout << "   omega = " << omega << endl;
    pcout << " Output data information:    " << endl;
    pcout << "      maxIter = " << int(maxIter / tc) << " * tc (" << int(maxIter) << " iterations)"
          << endl;
    pcout << "      vtkIter = " << int(vtkIter / tc) << " * tc (" << int(vtkIter) << " iterations)"
          << endl;
    pcout << "     statIter = " << int(statIter / tc) << " * tc (" << int(statIter)
          << " iterations)" << endl;
    pcout << " startAvgIter = " << int(startAvgIter / tc) << " * tc (" << int(startAvgIter)
          << " iterations)" << endl;
    pcout << "      avgIter = " << std::fixed << std::setprecision(1) << int(avgIter / tc)
          << " * tc (" << int(avgIter) << " iterations)" << endl;
    pcout << endl;

    // Output all parameters in a log file
    writeLogFile(
        dynName, reg, bulkVisco, Re, Ma, soundSpeed, nx, ny, nz, dx, dt, u0, nu, tau, omega, tc,
        maxIter, vtkIter, statIter, startAvgIter, avgIter);

    // Initialize by setting the inflow and outflow velocity everywhere
    initializeAtEquilibrium(
        lattice, lattice.getBoundingBox(), (T)1., Array<T, 3>((T)0., (T)0., (T)0.));

    auto writeVTK = [&](auto &lattice, int iT) {
        VtkImageOutput3D<T> vtkOut(createFileName("vtk", iT, 6), dx);
        vtkOut.writeData<3, T>(*computeVelocity(lattice), "velocity", dx / dt);
        const T rho0 = 1.0;
        vtkOut.writeData<T>(
            *add((T)-1., *computeDensity(lattice)), "pressure",
            dx * dx / (dt * dt) / DESCRIPTOR<T>::cs2 * rho0);
    };

    // Reset the clock
    global::timer("cavity").start();
    plint clock_iter = 0;

    // pcout << endl << "Here is what the \"collideAndStream\" command should look like: " << endl;
    // showTemplateArguments(lattice);
    // pcout << endl;

    pcout << "Creating accelerated lattice" << endl;
    AcceleratedLattice3D<T, DESCRIPTOR> *accLattice = nullptr;
    if (useAccelerated) {
        accLattice = new AcceleratedLattice3D<T, DESCRIPTOR>(lattice);
    }

    if (benchmark) {
        pcout << "Now running " << bench_ini_iter << " warm-up iterations." << endl;
    } else {
        pcout << "Starting simulation" << endl;
    }

    T avEnergyPrev = 0.;
    if (production && Re < 2000) {
        T avEnergy = useAccelerated ? computeAveragedKinEnergy(*accLattice)
                                    : computeAveragedKinEnergy(lattice);
        T conv = abs(avEnergy - avEnergyPrev) / abs(avEnergy);
        avEnergyPrev = avEnergy;
    }

    unique_ptr<MultiTensorField3D<T, 3> > avgVelocityField;
    T numAvg = 0;

    for (int iT = 0; iT < (int)maxIter; ++iT) {
        //// VTK output
        if (production && fabs(fmod(iT, vtkIter)) < 1 && iT > 0) {
            pcout << "Writing data into a VTK file" << endl;
            useAccelerated ? writeVTK(*accLattice, iT) : writeVTK(lattice, iT);
        }

        //// Velocity field averaging
        if (production && iT == (int)startAvgIter && (int)avgIter != 0) {
            pcout << "At t = " << setw(5) << setfill(' ') << fixed << setprecision(1) << (T)iT / tc
                  << "tc (iter " << iT << "): beginning of velocity field averaging " << endl;
            useAccelerated ? avgVelocityField = computeVelocity(*accLattice)
                           : avgVelocityField = computeVelocity(lattice);
            numAvg += 1;
        }
        if (production && fabs(fmod(iT, avgIter)) < 1 && iT > (int)startAvgIter
            && (int)avgIter != 0) {
            pcout << "At t = " << setw(5) << setfill(' ') << fixed << setprecision(1) << (T)iT / tc
                  << "tc (iter " << iT << "):  velocity field averaging " << endl;
            useAccelerated ? addVelocityFieldToAvg(*accLattice, *avgVelocityField)
                           : addVelocityFieldToAvg(lattice, *avgVelocityField);
            numAvg += 1;
        }

        //// Stats output
        if (production && fabs(fmod(iT, statIter)) < 1 && iT > 0) {
            T avEnergy = useAccelerated ? computeAveragedKinEnergy(*accLattice)
                                        : computeAveragedKinEnergy(lattice);
            T conv = abs(avEnergy - avEnergyPrev) / abs(avEnergy);
            pcout << "At t = " << setw(5) << setfill(' ') << fixed << setprecision(1) << (T)iT / tc
                  << "tc (iter " << iT << "):  conv = " << scientific << conv << endl;
            avEnergyPrev = avEnergy;
            if (isnan(conv)) {
                pcout << "Catastrophic error: energy has increased or is NaN!" << endl;
                return 1;
            }
            //// Output the converged velocity field
            if (conv < 1e-6 && Re < 2000) {
                pcout << endl << "Writing data into a VTK file after convergence" << endl;
                useAccelerated ? writeVTK(*accLattice, iT) : writeVTK(lattice, iT);
                break;
            }
        }

        //// Benchmark
        if (benchmark && iT == bench_ini_iter) {
            pcout << "Now running " << bench_max_iter - bench_ini_iter << " benchmark iterations."
                  << endl;
            global::timer("cavity").restart();
            clock_iter = 0;
        }

        //// Collide & Stream
        if (useAccelerated) {
            accLattice->collideAndStream(
                CollisionKernel<T, DESCRIPTOR, COLLMODEL, COLLMODEL_HWBB>());
        } else {
            lattice.collideAndStream();
        }

        ++clock_iter;
    }

    //// Output average velocity fields for unsteady simulations
    if (production && avgIter != 0) {
        pcout << "Outputing the averaged velocity field (averaged " << (int)numAvg << " times)"
              << endl;
        VtkImageOutput3D<T> vtkOut("vtk_avg", dx);
        vtkOut.writeData<3, T>(*multiply((T)1. / numAvg, *avgVelocityField), "velocity", dx / dt);
    }

    //// Print program performance in MLUPS
    if (!production) {
        printMlups(clock_iter, lattice.getBoundingBox().nCells());
        // Check energy is not NaN
        T energy = useAccelerated ? computeAveragedKinEnergy(*accLattice)
                                  : computeAveragedKinEnergy(lattice);
        if (isnan(energy)) {
            cout << "Simulation was unstable --> Invalid benchmark!!!" << endl;
        } else {
            cout << "Energy check is OK --> Energy = " << energy << endl;
        }
    }

    //// Execute a regression test
    if (regression) {
        T energy = useAccelerated ? computeAveragedKinEnergy(*accLattice)
                                  : computeAveragedKinEnergy(lattice);
        runRegression(energy, maxIter, dynName, nx, ny, nz, Re, Ma);
    }

    delete accLattice;
    return 0;
}
