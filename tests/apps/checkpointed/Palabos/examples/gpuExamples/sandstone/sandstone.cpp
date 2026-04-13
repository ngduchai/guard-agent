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
 * Flow through a porous sandstone. Benchmark case for the Palabos
 * project "From CPU to GPU in 80 days".
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
using namespace std;

typedef double T;
#define DESCRIPTOR descriptors::D3Q19Descriptor

int main(int argc, char *argv[])
{
    plbInit(&argc, &argv);
    defaultMultiBlockPolicy3D().toggleBlockingCommunication(true);

    bool regression = false;  // Run a regression test at the end of the simulation ?
    bool benchmark = false;   // Run in benchmark mode ?
    bool useAcceleratedLattice = true;
    bool writeSTL = false;
    bool imposePressureGradient = false;
    T rhoIn = (T)1.001;
    T rhoOut = (T)0.999;

    // Output VTK files go to this directory
    global::directories().setOutputDir("./tmp/");

    // You must download the geometry file of the Berea sandstone (see address provided in the
    // error message below)
    string data_fname("Berea.ascii");

    int prod_max_iter = 1'000'000;  // Total number of iterations in production mode
    int bench_ini_iter = 1000;      // Number of warm-up iterations in benchmark mode
    int bench_max_iter = 2000;      // Total number of iterations in benchmark mode
    int vtkIter = 500'000;          // Frequency of VTK file output in production mode
    int permIter = 1'000;  // Frequency at which permeability is provided, in production mode
    int statIter =
        10'000;  // Frequency at which flow and pressure values are computed, in production mode

    int data_nx = 0.;  // Dimensions of the geometry in the provided data file
    int data_ny = 0.;
    int data_nz = 0.;

    int nx = 400;  // Dimensions of the geometry extract on which the simulation is run
    int ny = 400;
    int nz = 400;

    T ulb = 0.;  // Velocity in lattice units

    if (global::argc() == 1) {
        pcout << "No arguments provided, running with standard parameters. For other parameters, "
                 "use this syntax: "
              << std::endl;
        pcout << (std::string)global::argv(0) << " ulb nx ny nz" << std::endl;
        pcout << "(if ulb is 0, a pressure gradient is applied instead of a flow)" << std::endl;
    } else {
        try {
            if (global::argc() != 5) {
                throw PlbIOException("Wrong number of arguments.");
            }
            global::argv(1).read(ulb);
            global::argv(2).read(nx);
            global::argv(3).read(ny);
            global::argv(4).read(nz);
        } catch (PlbIOException &except) {
            pcout << except.what() << std::endl;
            pcout << "Error in the provided parameters. The syntax is: " << std::endl;
            pcout << (std::string)global::argv(0) << " ulb nx ny nz" << std::endl;
            pcout << "(if ulb is 0, a pressure gradient is applied instead of a flow)" << std::endl;
            return -1;
        }
    }
    if (ulb == 0) {
        imposePressureGradient = true;
    }
#ifdef USE_CUDA_MALLOC
    pcout << "Using CUDA Malloc" << endl;
#endif

    int maxIter = benchmark ? bench_max_iter : prod_max_iter;

    int buffer = 40;  // Size of the buffer layer in the inlet and outlet zone

    T nuPhys = 1.e-3;      // Kinematic viscosity in physical units (e.g. m^2/s)
    T tau_original = 1.0;  // LB relaxation time
    T tau = 0.5 + 0.01 * (tau_original - 0.5);
    T rho0 = 1000.;  // Density (material constant, kg/m^3)

    T dx = 1.0;  // Cell spacing in physical units (e.g. m), will be properly computed
    T dt = 1.0;  // Discrete time step in physical units (e.g. s), will be properly computed

    T nu_lb = 1. / 3. * (tau - 0.5);  // Viscosity in LB units

    pcout << "Running simulation in ";
    if (benchmark) {
        pcout << "benchmark";
    } else {
        pcout << "production";
    }
    pcout << " mode on a " << nx + 2 * buffer << " x " << ny << " x " << nz << " domain." << endl;

    pcout << "Boundary condition: ";
    if (imposePressureGradient) {
        pcout << "pressure" << endl;
    } else {
        pcout << "velocity" << endl;
    }

    pcout << "Precision: ";
    if (sizeof(T) == 4) {
        pcout << " single" << endl;
    } else {
        pcout << " double" << endl;
    }

    pcout << "ulb = " << ulb << endl;
    pcout << "tau = " << tau << endl;

    plb_ifstream datafile(data_fname.c_str());

    pcout << "Reading porous media data file." << endl;
    if (datafile.is_open()) {
        datafile >> data_nx >> data_ny >> data_nz >> dx;
        global::mpi().bCast(&data_nx, 1);
        global::mpi().bCast(&data_ny, 1);
        global::mpi().bCast(&data_nz, 1);
        global::mpi().bCast(&dx, 1);
        dt = nu_lb / nuPhys * dx * dx;
        pcout << "Cell spacing: " << dx << endl;
        pcout << "Reading data file of size " << data_nx << " x " << data_ny << " x " << data_nz
              << endl;
    } else {
        pcout << "File could not be opened: " << data_fname << endl;
        pcout
            << "You can obtain the geometry of the Berea sandstone on the Web site of the Imperial "
               "College London: https://doi.org/10.6084/m9.figshare.1153794.v2"
            << endl;
        pcout << "You should then convert the .raw file to a .ascii file using the provided Python "
                 "script."
              << endl;
        return -1;
    }

    // First, the full geometry is read into a scalar field
    MultiScalarField3D<int> data_geometry(data_nx, data_ny, data_ny);
    datafile >> data_geometry;

    if (writeSTL) {
        pcout << "Writing STL" << endl;
        auto float_geometry = copyConvert<int, float>(data_geometry);
        auto smooth_geometry = lbmSmoothen<float, DESCRIPTOR>(
            *lbmSmoothen<float, DESCRIPTOR>(*float_geometry, float_geometry->getBoundingBox()),
            float_geometry->getBoundingBox());

        std::vector<float> isoLevels;
        isoLevels.push_back(0.2);

        typedef TriangleSet<float>::Triangle Triangle;
        std::vector<Triangle> triangles;
        isoSurfaceMarchingCube(
            triangles, *smooth_geometry, isoLevels, smooth_geometry->getBoundingBox().enlarge(-1));
        {
            TriangleSet<float> triangleSet(triangles);
            triangleSet.scale(dx);
            triangleSet.writeBinarySTL("berea.stl");
        }
        pcout << "Writing STL: done" << endl;
    }

    // Then, a reduced data field is created which includes only the geometry
    // extract for the simulation, plus a buffer zone
    MultiScalarField3D<int> geometry(nx + 2 * buffer, ny, nz);
    geometry.periodicity().toggleAll(true);

    pcout << "Distributing the geometry extract over the porous media domain." << endl;
    // Copy the geometry extract from the old to the new scalar field
    // If the domain is larger than the geometry, this procedure copies multiple patches.
    int offset_x = 0;
    for (int iX = 0; iX <= nx / data_nx; ++iX, offset_x += data_nx) {
        int lx = iX < nx / data_nx ? data_nx : nx % data_nx;
        int offset_y = 0;
        for (int iY = 0; iY <= ny / data_ny; ++iY, offset_y += data_ny) {
            int ly = iY < ny / data_ny ? data_ny : ny % data_ny;
            int offset_z = 0;
            for (int iZ = 0; iZ <= nz / data_nz; ++iZ, offset_z += data_nz) {
                int lz = iZ < nz / data_nz ? data_nz : nz % data_nz;
                copy(
                    data_geometry, Box3D(0, lx - 1, 0, ly - 1, 0, lz - 1), geometry,
                    Box3D(
                        buffer + offset_x, buffer + offset_x + lx - 1, offset_y, offset_y + ly - 1,
                        offset_z, offset_z + lz - 1));
            }
        }
    }

    pcout << "Setting up the data on the CPU." << endl;
    // Set up the lattice, use TRT dynamics (otherwise, the permeability is viscosity dependent)
    MultiBlockLattice3D<T, DESCRIPTOR> lattice(
        nx + 2 * buffer, ny, nz, new TRTdynamics<T, DESCRIPTOR>(1. / tau));
    lattice.periodicity().toggleAll(true);

    const int SOLID_FLAG = 1;
    defineDynamics(
        lattice, geometry, lattice.getBoundingBox(), new BounceBack<T, DESCRIPTOR>, SOLID_FLAG);
    plint numberOfBB =
        count(lattice, lattice.getBoundingBox(), [](Cell<T, DESCRIPTOR> const &cell) -> bool {
            return cell.getDynamics().getId() == BounceBack<T, DESCRIPTOR> {}.getId();
        });

    double porosity = 1. - (double)numberOfBB / ((double)nx * (double)ny * (double)nz);
    pcout << "porosity = " << porosity << endl;

    // Create velocity boundaries on the inlet and the outlet, to impose a constant flow
    Box3D inlet(0, 0, 0, ny - 1, 0, nz - 1);
    int xMax = nx - 1 + 2 * buffer;
    Box3D outlet(xMax, xMax, 0, ny - 1, 0, nz - 1);
    auto boundaryCondition = createDynamicsBasedLocalBoundaryCondition3D<T, DESCRIPTOR>();
    if (imposePressureGradient) {
        boundaryCondition->addPressureBoundary0N(inlet, lattice);
        boundaryCondition->addPressureBoundary0P(outlet, lattice);
        setBoundaryDensity(lattice, inlet, rhoIn);
        setBoundaryDensity(lattice, outlet, rhoOut);
    } else {
        boundaryCondition->addVelocityBoundary0N(inlet, lattice);
        boundaryCondition->addVelocityBoundary0P(outlet, lattice);
        setBoundaryVelocity(lattice, inlet, Array<T, 3>(ulb, 0., 0.));
        setBoundaryVelocity(lattice, outlet, Array<T, 3>(ulb, 0., 0.));
    }

    // Initialize by setting the inflow and outflow velocity everywhere
    initializeAtEquilibrium(
        lattice, lattice.getBoundingBox(), (T)1., Array<T, 3>(ulb, (T)0., (T)0.));

    auto computePermeability = [&](auto &lattice) {
        auto density = computeDensity(lattice);
        Box3D inletBuffer(0, buffer - 1, 0, ny - 1, 0, nz - 1);
        Box3D outletBuffer(nx + buffer, nx + 2 * buffer - 1, 0, ny - 1, 0, nz - 1);
        T rhoIn_ = useAcceleratedLattice ? computeAverageAcc(*density, inletBuffer)
                                         : computeAverage(*density, inletBuffer);
        T rhoOut_ = useAcceleratedLattice ? computeAverageAcc(*density, outletBuffer)
                                          : computeAverage(*density, outletBuffer);
        T deltaP = 1. / 3. * (rhoIn_ - rhoOut_);

        return ulb * nu_lb * nx / deltaP * dx * dx;
    };

    auto computePermeabilityFromFlow = [&](auto &lattice) {
        auto velocity = computeVelocity(lattice);
        Box3D inletBuffer(0, buffer - 1, 0, ny - 1, 0, nz - 1);
        Box3D outletBuffer(nx + buffer, nx + 2 * buffer - 1, 0, ny - 1, 0, nz - 1);
        Box3D porousDomain(buffer, nx + buffer - 1, 0, ny - 1, 0, nz - 1);
        Array<T, 3> uIn = useAcceleratedLattice ? computeAverageAcc(*velocity, inletBuffer)
                                                : computeAverage(*velocity, inletBuffer);
        Array<T, 3> uOut = useAcceleratedLattice ? computeAverageAcc(*velocity, outletBuffer)
                                                 : computeAverage(*velocity, outletBuffer);
        Array<T, 3> uBulk = useAcceleratedLattice ? computeAverageAcc(*velocity, porousDomain)
                                                  : computeAverage(*velocity, porousDomain);
        T deltaP = 1. / 3. * (rhoIn - rhoOut);
        T ulb_ = uBulk[0];
        return ulb_ * nu_lb * nx / deltaP * dx * dx;
    };

    auto computeDensities = [&](auto &lattice) {
        auto density = computeDensity(lattice);
        Box3D inletBuffer(0, buffer - 1, 0, ny - 1, 0, nz - 1);
        Box3D outletBuffer(nx + buffer, nx + 2 * buffer - 1, 0, ny - 1, 0, nz - 1);
        Box3D porousDomain(buffer, nx + buffer - 1, 0, ny - 1, 0, nz - 1);
        T rhoIn_ = useAcceleratedLattice ? computeAverageAcc(*density, inletBuffer)
                                         : computeAverage(*density, inletBuffer);
        T rhoOut_ = useAcceleratedLattice ? computeAverageAcc(*density, outletBuffer)
                                          : computeAverage(*density, outletBuffer);
        T rhoBulk_ = useAcceleratedLattice ? computeAverageAcc(*density, porousDomain)
                                           : computeAverage(*density, porousDomain);

        pcout << "In (Inlet/Outlet/Bulk) region, rho = (";
        pcout << setprecision(8) << rhoIn_ << ", ";
        pcout << setprecision(8) << rhoOut_ << ", ";
        pcout << setprecision(8) << rhoBulk_ << ")" << endl;
    };

    auto computeVelocities = [&](auto &lattice) {
        auto velocity = computeVelocityComponent(lattice, 0);
        Box3D inletBuffer(0, buffer - 1, 0, ny - 1, 0, nz - 1);
        Box3D outletBuffer(nx + buffer, nx + 2 * buffer - 1, 0, ny - 1, 0, nz - 1);
        Box3D porousDomain(buffer, nx + buffer - 1, 0, ny - 1, 0, nz - 1);
        T uIn_ = useAcceleratedLattice ? computeAverageAcc(*velocity, inletBuffer)
                                       : computeAverage(*velocity, inletBuffer);
        T uOut_ = useAcceleratedLattice ? computeAverageAcc(*velocity, outletBuffer)
                                        : computeAverage(*velocity, outletBuffer);
        T uBulk_ = useAcceleratedLattice ? computeAverageAcc(*velocity, porousDomain)
                                         : computeAverage(*velocity, porousDomain);

        pcout << "In (Inlet/Outlet/Bulk) region, ux = (";
        pcout << setprecision(8) << uIn_ << ", ";
        pcout << setprecision(8) << uOut_ << ", ";
        pcout << setprecision(8) << uBulk_ << ")" << endl;
    };

    auto writeVTK = [&](auto &lattice, int iT) {
        VtkImageOutput3D<T> vtkOut(createFileName("vtk", iT, 6), dx);
        vtkOut.writeData<int>(*copyConvert<int, T>(geometry), "geometry");
        vtkOut.writeData<3, T>(*computeVelocity(lattice), "velocity", dx / dt);
        vtkOut.writeData<T>(
            *add((T)-1., *computeDensity(lattice)), "pressure", dx * dx / (dt * dt) / (T)3. * rho0);
    };

    // Reset the clock
    global::timer("sandstone").start();
    plint clock_iter = 0;

    // pcout << std::endl << "Here is what the \"collideAndStream\" command should look like: " <<
    // std::endl; showTemplateArguments(lattice); pcout << std::endl;

    pcout << "Setting up the data on the GPU." << endl;
    AcceleratedLattice3D<T, DESCRIPTOR> *accLattice = nullptr;
    if (useAcceleratedLattice) {
        accLattice = new AcceleratedLattice3D<T, DESCRIPTOR>(lattice);
        // Activate the following line to use the accelerated lattice in OpenMP mode (multi-threaded
        // CPU).
        // accLattice->setExecutionMode(ExecutionMode::openmp);
    }

    if (benchmark) {
        pcout << "Now running " << bench_ini_iter << " warm-up iterations." << endl;
    } else {
        pcout << "Starting simulation" << endl;
    }
    for (int iT = 0; iT <= maxIter; ++iT) {
        if (!benchmark && iT % vtkIter == 0 && iT > 0) {
            pcout << "Writing data into a VTK file" << endl;
            if (useAcceleratedLattice) {
                writeVTK(*accLattice, iT);
            } else {
                writeVTK(lattice, iT);
            }
            pcout << "End writing VTK." << endl;
        }
        if (!benchmark && iT % permIter == 0) {
            T permeability {};
            if (imposePressureGradient) {
                permeability = useAcceleratedLattice ? computePermeabilityFromFlow(*accLattice)
                                                     : computePermeabilityFromFlow(lattice);
            } else {
                permeability = useAcceleratedLattice ? computePermeability(*accLattice)
                                                     : computePermeability(lattice);
            }
            pcout << "At iteration " << iT << ", permeability = " << setprecision(10)
                  << permeability << " m2 = " << setprecision(10) << permeability * 1.01325e15
                  << " mD" << endl;
        }
        if (!benchmark && iT % statIter == 0) {
            if (useAcceleratedLattice) {
                computeDensities(*accLattice);
                computeVelocities(*accLattice);
            } else {
                computeDensities(lattice);
                computeVelocities(lattice);
            }
        }

        if (benchmark && iT == bench_ini_iter) {
            pcout << "Starting " << maxIter - bench_ini_iter << " benchmark iterations." << endl;
            global::timer("sandstone").restart();
            clock_iter = 0;
        }
        if (useAcceleratedLattice) {
            if (imposePressureGradient) {
                accLattice->collideAndStream(
                    CollisionKernel<
                        T, DESCRIPTOR, CollisionModel::NoDynamics, CollisionModel::TRT,
                        CollisionModel::BounceBack,
                        CollisionModel::Boundary_RegularizedDensity_0_1__TRT,
                        CollisionModel::Boundary_RegularizedDensity_0_M1__TRT>());
            } else {
                accLattice->collideAndStream(
                    CollisionKernel<
                        T, DESCRIPTOR, CollisionModel::NoDynamics, CollisionModel::TRT,
                        CollisionModel::BounceBack,
                        CollisionModel::Boundary_RegularizedVelocity_0_1__TRT,
                        CollisionModel::Boundary_RegularizedVelocity_0_M1__TRT>());
            }
        } else {
            lattice.collideAndStream();
        }
        ++clock_iter;
    }
    pcout << "Simulation ended." << endl;

    // Print program performance in MLUPS
    double elapsed = global::timer("sandstone").stop();
    double mlups =
        static_cast<double>(lattice.getBoundingBox().nCells() * clock_iter) / elapsed * 1.e-6;
    pcout << "Performance: " << setprecision(4) << mlups << " MLUPS" << endl;
    pcout << endl;

    // If so required, execute a regression test
    if (regression) {
        double reference_permeability = 1.0;
        if (nx == 128 && ny == 128 && nz == 128 && sizeof(T) == sizeof(float) && maxIter == 2000) {
            reference_permeability = 3.517730220328e-11;
        } else if (
            nx == 400 && ny == 400 && nz == 400 && sizeof(T) == sizeof(float) && maxIter == 2000) {
            reference_permeability = 8.906846787893e-11;
        }
        T permeability =
            useAcceleratedLattice ? computePermeability(*accLattice) : computePermeability(lattice);
        if (reference_permeability == 1.0) {
            pcout << "Permeability = " << setprecision(13) << permeability << endl;
        } else {
            pcout << "Regression test with permeability = " << setprecision(13) << permeability;
            if (std::fabs(permeability - reference_permeability) < 1.e-10) {
                pcout << ": OK" << endl;
            } else {
                pcout << ": FAILED" << endl;
                pcout << "Expected the value " << reference_permeability << endl;
            }
        }
    }

    delete boundaryCondition;
    delete accLattice;
    return 0;
}
