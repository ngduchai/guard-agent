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
 * Simulation of a 3D Rayleigh-Taylor instability, which describes a symmetry breakdown,
 * as a heavy fluid, initially located on top of a light one, starts penetrating the
 * latter. This is an illutration of the Shan/Chen multi-component model. Note that the
 * single-component multi-phase model is also implemented in Palabos, and a corresponding
 * sample program is provided. Also, note that the multi-component model can be used to
 * couple more than two phases, using the same approach as the one shown here.
 *
 *  This is a benchmark case for the Palabos project "From CPU to GPU in 80 days".
 *  Project page: https://palabos.unige.ch/community/cpu-gpu-80-days/
 *  Performance measurements:
 *https://docs.google.com/spreadsheets/d/1ROJbPlLKqX9JxO408S4BEFkzK1XLbxiimUdd4XaIJ8c/edit?usp=sharing
 *
 **/

#include "palabos3D.h"
#include "palabos3D.hh"
#include <cstdlib>
#include <iostream>
#include <random>

using namespace plb;
using namespace std;

typedef float T;
// Use a grid which additionally to the f's stores three variables for
//   the external force term.
#define DESCRIPTOR descriptors::ForcedShanChenD3Q19Descriptor

/// Initial condition: heavy fluid on top, light fluid on bottom.
/** This functional is going to be used as an argument to the function "applyIndexed",
 *  to setup the initial condition. For efficiency reasons, this approach should
 *  always be preferred over explicit space loops in end-user codes.
 */

template <typename T, template <typename U> class Descriptor>
class BubbleInitializer : public OneCellIndexedWithRandFunctional3D<T, Descriptor> {
public:
    BubbleInitializer(bool buoyantFluid_, T bubbleRadius, vector<array<int, 3>> bubblePos_) :
        buoyantFluid(buoyantFluid_),
        bubbleRadiusSqr(bubbleRadius * bubbleRadius),
        bubblePos(bubblePos_)
    { }
    BubbleInitializer<T, Descriptor> *clone() const
    {
        return new BubbleInitializer<T, Descriptor>(*this);
    }
    virtual void execute(plint iX, plint iY, plint iZ, T rand_val, Cell<T, Descriptor> &cell) const
    {
        T almostNoFluid = 1.e-4;
        Array<T, 3> zeroVelocity(0., 0., 0.);

        bool insideBubble = false;
        for (int i = 0; i < (int)bubblePos.size(); ++i) {
            int dx = iX - bubblePos[i][0];
            int dy = iY - bubblePos[i][1];
            int dz = iZ - bubblePos[i][2];
            int dSqr = dx * dx + dy * dy + dz * dz;
            if ((T)dSqr < bubbleRadiusSqr) {
                insideBubble = true;
            }
        }
        T rho = (T)1;
        if (buoyantFluid) {
            if (insideBubble) {
                rho = (T)1;
            } else {
                rho = almostNoFluid;
            }
        } else {
            if (insideBubble) {
                rho = almostNoFluid;
            } else {
                rho = (T)1;
            }
        }
        iniCellAtEquilibrium(cell, rho, zeroVelocity);
    }

private:
    bool buoyantFluid;
    T bubbleRadiusSqr;
    vector<array<int, 3>> bubblePos;
};

void bubbleSetup(
    MultiBlockLattice3D<T, DESCRIPTOR> &buoyantFluid,
    MultiBlockLattice3D<T, DESCRIPTOR> &displacedFluid, T rhoOnBuoyant, T rhoOnDisplaced, T force0,
    T force, T bubbleRadius, vector<array<int, 3>> bubblePos)
{
    // The setup is: periodicity along horizontal direction, bounce-back on top
    // and bottom. The upper half is initially filled with fluid 1 + random noise,
    // and the lower half with fluid 2. Only fluid 1 experiences a forces,
    // directed downwards.
    plint nx = buoyantFluid.getNx();
    plint ny = buoyantFluid.getNy();
    plint nz = buoyantFluid.getNz();

    // Bounce-back on left wall
    defineDynamics(
        buoyantFluid, Box3D(0, 0, 0, ny - 1, 0, nz - 1),
        new BounceBack<T, DESCRIPTOR>(rhoOnBuoyant));
    defineDynamics(
        displacedFluid, Box3D(0, 0, 0, ny - 1, 0, nz - 1),
        new BounceBack<T, DESCRIPTOR>(rhoOnDisplaced));
    // Bounce-back on right wall
    defineDynamics(
        buoyantFluid, Box3D(nx - 1, nx - 1, 0, ny - 1, 0, nz - 1),
        new BounceBack<T, DESCRIPTOR>(rhoOnBuoyant));
    defineDynamics(
        displacedFluid, Box3D(nx - 1, nx - 1, 0, ny - 1, 0, nz - 1),
        new BounceBack<T, DESCRIPTOR>(rhoOnDisplaced));
    // Bounce-back on front wall
    defineDynamics(
        buoyantFluid, Box3D(0, nx - 1, 0, ny - 1, 0, 0),
        new BounceBack<T, DESCRIPTOR>(rhoOnBuoyant));
    defineDynamics(
        displacedFluid, Box3D(0, nx - 1, 0, ny - 1, 0, 0),
        new BounceBack<T, DESCRIPTOR>(rhoOnDisplaced));
    // Bounce-back on back wall
    defineDynamics(
        buoyantFluid, Box3D(0, nx - 1, 0, ny - 1, nz - 1, nz - 1),
        new BounceBack<T, DESCRIPTOR>(rhoOnBuoyant));
    defineDynamics(
        displacedFluid, Box3D(0, nx - 1, 0, ny - 1, nz - 1, nz - 1),
        new BounceBack<T, DESCRIPTOR>(rhoOnDisplaced));
    // Bounce-back on bottom wall (where the light fluid is, initially).
    defineDynamics(
        buoyantFluid, Box3D(0, nx - 1, 0, 0, 0, nz - 1),
        new BounceBack<T, DESCRIPTOR>(rhoOnBuoyant));
    defineDynamics(
        displacedFluid, Box3D(0, nx - 1, 0, 0, 0, nz - 1),
        new BounceBack<T, DESCRIPTOR>(rhoOnDisplaced));
    // Bounce-back on top wall (where the heavy fluid is, initially).
    defineDynamics(
        buoyantFluid, Box3D(0, nx - 1, ny - 1, ny - 1, 0, nz - 1),
        new BounceBack<T, DESCRIPTOR>(rhoOnDisplaced));
    defineDynamics(
        displacedFluid, Box3D(0, nx - 1, ny - 1, ny - 1, 0, nz - 1),
        new BounceBack<T, DESCRIPTOR>(rhoOnBuoyant));

    applyIndexed(
        buoyantFluid, Box3D(0, nx - 1, 0, ny - 1, 0, nz - 1),
        new BubbleInitializer<T, DESCRIPTOR>(true, bubbleRadius, bubblePos));
    applyIndexed(
        displacedFluid, Box3D(0, nx - 1, 0, ny - 1, 0, nz - 1),
        new BubbleInitializer<T, DESCRIPTOR>(false, bubbleRadius, bubblePos));

    // Let's have gravity acting on the heavy fluid only. This represents a situation
    //   where the molecular mass of the light species is very small, and thus the
    //   action of gravity on this species is negligible.
    int Y0 = ny / 2 - 10;
    int Y1 = ny / 2 + 30;
    int deltaY = Y1 - Y0;
    setExternalVector(
        buoyantFluid, Box3D(0, nx - 1, 0, Y0, 0, nz - 1),
        DESCRIPTOR<T>::ExternalField::forceBeginsAt, Array<T, 3>(0., force0, 0.));
    for (int iY = Y0; iY <= Y1; ++iY) {
        T f = force0 + (T)(iY - Y0) / (T)deltaY * (force - force0);
        setExternalVector(
            buoyantFluid, Box3D(0, nx - 1, iY, iY, 0, nz - 1),
            DESCRIPTOR<T>::ExternalField::forceBeginsAt, Array<T, 3>(0., f, 0.));
    }
    setExternalVector(
        buoyantFluid, Box3D(0, nx - 1, Y1, ny - 1, 0, nz - 1),
        DESCRIPTOR<T>::ExternalField::forceBeginsAt, Array<T, 3>(0., force, 0.));
    setExternalVector(
        displacedFluid, Box3D(0, nx - 1, 0, ny - 1, 0, nz - 1),
        DESCRIPTOR<T>::ExternalField::forceBeginsAt, Array<T, 3>(0., 0., 0.));

    displacedFluid.initialize();
    buoyantFluid.initialize();
}

template <class LATTICE>
void writePpms(LATTICE &buoyantFluid, LATTICE &displacedFluid, plint iT)
{
    const plint nx = buoyantFluid.getNx();
    const plint ny = buoyantFluid.getNy();
    const plint nz = buoyantFluid.getNz();
    Box3D slice(0, nx - 1, 0, ny - 1, nz / 2, nz / 2);

    ImageWriter<T> imageWriter("leeloo");
    imageWriter.writeScaledPpm(
        createFileName("rho_heavy_", iT, 6), *computeDensity(buoyantFluid, slice));
    imageWriter.writeScaledPpm(
        createFileName("rho_light_", iT, 6), *computeDensity(displacedFluid, slice));
}

template <class LATTICE>
void writeVTK(LATTICE &lattice1, LATTICE &lattice2, MultiScalarField3D<T> &geometry, int iT)
{
    VtkImageOutput3D<T> vtkOut(createFileName("vtk", iT, 6), 1.0);
    pcout << "Writing geometry " << endl;
    vtkOut.writeData<T>(geometry, "geometry", 1.0);
    pcout << "Writing velocity " << endl;
    vtkOut.writeData<T>(*computeNorm(*computeVelocity(lattice2)), "velocity", 1.0);
    pcout << "Writing density " << endl;
    vtkOut.writeData<T>(*computeDensity(lattice1), "density1", 1.0);
};

template <typename T, template <typename U> class Descriptor>
class CountOccupiedNodesFunctional3D : public ReductiveBoxProcessingFunctional3D_A<T, Descriptor> {
public:
    CountOccupiedNodesFunctional3D(T threshold_);
    virtual void process(Box3D domain, AtomicAcceleratedLattice3D<T, Descriptor> &lattice);
    virtual CountOccupiedNodesFunctional3D<T, Descriptor> *clone() const;
    virtual void getTypeOfModification(std::vector<modif::ModifT> &modified) const
    {
        modified[0] = modif::nothing;
    }
    plint getNumNodes() const;

private:
    T threshold;
    plint numNodesId;
};

template <typename T, template <typename U> class Descriptor>
CountOccupiedNodesFunctional3D<T, Descriptor>::CountOccupiedNodesFunctional3D(T threshold_) :
    threshold(threshold_), numNodesId(this->getStatistics().subscribeSum())
{ }

template <typename T, template <typename U> class Descriptor>
void CountOccupiedNodesFunctional3D<T, Descriptor>::process(
    Box3D domain, AtomicAcceleratedLattice3D<T, Descriptor> &lattice)
{
    T sumNodes = lattice.transform_reduce(
        domain, (T)0, std::plus<T>(),
        [&lattice, threshold = threshold](
            plint i, plint iX, plint iY, plint iZ, int collisionModel) {
            if (collisionModel == CollisionModel::BounceBack) {
                return (T)0.;
            } else {
                Array<T, Descriptor<T>::q> f;
                lattice.pullPop(i, f);
                T rhoBar =
                    momentTemplatesImpl<T, typename Descriptor<T>::BaseDescriptor>::get_rhoBar(f);
                T rho = Descriptor<T>::fullRho(rhoBar);
                return rho > threshold ? (T)1. : (T)0.;
            }
        });
    this->getStatistics().gatherSum(numNodesId, (double)sumNodes);
}

template <typename T, template <typename U> class Descriptor>
CountOccupiedNodesFunctional3D<T, Descriptor>
    *CountOccupiedNodesFunctional3D<T, Descriptor>::clone() const
{
    return new CountOccupiedNodesFunctional3D<T, Descriptor>(*this);
}

template <typename T, template <typename U> class Descriptor>
plint CountOccupiedNodesFunctional3D<T, Descriptor>::getNumNodes() const
{
    double doubleSum = this->getStatistics().getSum(numNodesId);
    return (plint)util::roundToInt(doubleSum);
}

template <typename T, template <typename U> class Descriptor>
plint countOccupiedNodes(AcceleratedLattice3D<T, Descriptor> &lattice, Box3D domain, T threshold)
{
    CountOccupiedNodesFunctional3D<T, Descriptor> functional(threshold);
    applyProcessingFunctional(functional, domain, lattice);
    return functional.getNumNodes();
}

template <typename T, template <typename U> class Descriptor>
plint countOccupiedNodes(AcceleratedLattice3D<T, Descriptor> &lattice, T threshold)
{
    return countOccupiedNodes(lattice, lattice.getBoundingBox(), threshold);
}

int main(int argc, char *argv[])
{
    plbInit(&argc, &argv);
    defaultMultiBlockPolicy3D().toggleBlockingCommunication(true);

    global::directories().setOutputDir("./tmp/");

    bool regression = false;  // Run a regression test at the end of the simulation ?
    bool benchmark = true;    // Run in benchmark mode ?
    bool useAcceleratedLattice = true;

    const T omegaBuoyant = 1.0;
    const T omegaDisplaced = 1.0;

    // Parameters of a large program run
    // plint nx   = 300;
    // plint ny   = 800;
    // plint nz   = 200;

    plint nx = 150;
    plint ny = 400;
    plint nz = 100;

    const T G = 2.0;     // Interaction strength
    T force0 = 0.00003;  // Buoyancy force applied outside the porous media
    T force = 0.002;     // Buoyancy force applied in the porous media

    const plint bench_ini_iter = 250;
    const plint saveIter = 800;
    const plint statIter = 400;

    if (global::argc() == 1) {
        pcout << "No arguments provided, running with standard parameters. For other parameters, "
                 "use this syntax: "
              << std::endl;
        pcout << (std::string)global::argv(0) << " benchmark(1/0) nx ny nz" << std::endl;
    } else {
        try {
            if (global::argc() != 5) {
                throw PlbIOException("Wrong number of arguments.");
            }
            int intBenchmarkMode;
            global::argv(1).read(intBenchmarkMode);
            benchmark = intBenchmarkMode ? true : false;
            global::argv(2).read(nx);
            global::argv(3).read(ny);
            global::argv(4).read(nz);
        } catch (PlbIOException &except) {
            pcout << except.what() << std::endl;
            pcout << "Error in the provided parameters. The syntax is: " << std::endl;
            pcout << (std::string)global::argv(0) << " benchmark(1/0) nx ny nz" << std::endl;
            return -1;
        }
    }
#ifdef USE_CUDA_MALLOC
    pcout << "Using CUDA Malloc" << endl;
#endif

    bool production = !benchmark;  // Run in production mode ?
    const plint maxIter = production ? 200'000 : 500;

    // The buffer is the area, without porous media, in which the bubbles are placed originally.
    int bufferSize = ny / 2;

    // Generate the bubble positions at random locations.
    T bubbleRadius = 20.0;
    vector<array<int, 3>> bubblePos;

    random_device dev;
    mt19937 rng(dev());
    rng.seed(42);
    uniform_int_distribution<std::mt19937::result_type> distx(
        (int)bubbleRadius / 2, nx - 1 - (int)bubbleRadius / 2);
    uniform_int_distribution<std::mt19937::result_type> distz(
        (int)bubbleRadius / 2, nz - 1 - (int)bubbleRadius / 2);

    int numBubblesX = nx / 60;
    int numBubblesY = ny / 80;
    int numBubblesZ = nz / 60;
    int bubbleDeltaY = ny / numBubblesY;
    for (int iX = 0; iX < numBubblesX; ++iX) {
        for (int iY = 0; iY < numBubblesY / 2; ++iY) {
            for (int iZ = 0; iZ < numBubblesZ; ++iZ) {
                int posY = iY * bubbleDeltaY + bubbleDeltaY / 2;

                int posX = distx(rng);
                int posZ = distz(rng);

                bubblePos.push_back({posX, posY, posZ});
            }
        }
    }

    MultiBlockLattice3D<T, DESCRIPTOR> *buoyantFluid = new MultiBlockLattice3D<T, DESCRIPTOR>(
        nx, ny, nz, new ExternalMomentBGKdynamics<T, DESCRIPTOR>(omegaBuoyant));
    buoyantFluid->toggleInternalStatistics(false);
    MultiBlockLattice3D<T, DESCRIPTOR> *displacedFluid = new MultiBlockLattice3D<T, DESCRIPTOR>(
        nx, ny, nz, new ExternalMomentBGKdynamics<T, DESCRIPTOR>(omegaDisplaced));
    displacedFluid->toggleInternalStatistics(false);

    // Make x- and z-directions periodic.
    buoyantFluid->periodicity().toggle(0, false);
    buoyantFluid->periodicity().toggle(1, false);
    buoyantFluid->periodicity().toggle(2, false);
    displacedFluid->periodicity().toggle(0, false);
    displacedFluid->periodicity().toggle(1, false);
    displacedFluid->periodicity().toggle(2, false);

    T rhoOnDisplaced =
        0.;  // Fictitious density experienced by the partner fluid on a Bounce-Back node.
    T rhoOnBuoyant =
        0.;  // Fictitious density experienced by the partner fluid on a Bounce-Back node.

    // Store a pointer to all lattices (two in the present application) in a vector to
    //   create the Shan/Chen coupling therm. The heavy fluid being at the first place
    //   in the vector, the coupling term is going to be executed at the end of the call
    //   to collideAndStream() or stream() for the heavy fluid.
    vector<MultiBlockLattice3D<T, DESCRIPTOR> *> blockLattices;
    blockLattices.push_back(buoyantFluid);
    blockLattices.push_back(displacedFluid);

    // The argument "constOmegaValues" to the Shan/Chen processor is optional,
    //   and is used for efficiency reasons only. It tells the data processor
    //   that the relaxation times are constant, and that their inverse must be
    //   computed only once.
    std::vector<T> constOmegaValues;
    constOmegaValues.push_back(omegaBuoyant);
    constOmegaValues.push_back(omegaDisplaced);
    plint processorLevel = 1;
    integrateProcessingFunctional(
        new ShanChenMultiComponentProcessor3D<T, DESCRIPTOR>(G, constOmegaValues),
        Box3D(0, nx - 1, 1, ny - 2, 0, nz - 1), blockLattices, processorLevel);

    bubbleSetup(
        *buoyantFluid, *displacedFluid, rhoOnBuoyant, rhoOnDisplaced, force0, force, bubbleRadius,
        bubblePos);

    string data_fname("Berea.ascii");
    plb_ifstream datafile(data_fname.c_str());
    pcout << "Reading porous media data file." << endl;
    int data_nx, data_ny, data_nz;
    T dx;
    if (datafile.is_open()) {
        datafile >> data_nx >> data_ny >> data_nz >> dx;
        global::mpi().bCast(&data_nx, 1);
        global::mpi().bCast(&data_ny, 1);
        global::mpi().bCast(&data_nz, 1);
        global::mpi().bCast(&dx, 1);
        // dt = nu_lb / nuPhys * dx * dx;
        pcout << "Cell spacing: " << dx << endl;
        pcout << "Reading data file of size " << data_nx << " x " << data_ny << " x " << data_nz
              << endl;
    } else {
        pcout << "File could not be opened: " << data_fname << endl;
        pcout
            << "You can obtain the geometry of the Berea sandstone on the Web site of the Imperial "
               "College London: https://imperialcollegelondon.app.box.com/v/ImagesICPSC2007"
            << endl;
        pcout << "We also provide a mirrored copy here: "
                 "https://www.dropbox.com/s/6mf545fva4e7hf2/Berea.ascii?dl=0"
              << endl;
        return -1;
    }
    // First, the full geometry is read into a scalar field
    MultiScalarField3D<int> *data_geometry = new MultiScalarField3D<int>(data_nx, data_ny, data_ny);
    datafile >> *data_geometry;

    MultiScalarField3D<int> *geometry = new MultiScalarField3D<int>(nx, ny, nz);
    geometry->periodicity().toggleAll(true);

    pcout << "Distributing the geometry extract over the porous media domain." << endl;
    // Copy the geometry extract from the old to the new scalar field
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
                    *data_geometry, Box3D(0, lx - 1, 0, ly - 1, 0, lz - 1), *geometry,
                    Box3D(
                        offset_x, offset_x + lx - 1, offset_y, offset_y + ly - 1, offset_z,
                        offset_z + lz - 1));
            }
        }
    }
    delete data_geometry;

    pcout << "Converting geometry" << endl;
    MultiScalarField3D<T> floatGeometry(*geometry);
    copy<int, T>(*geometry, floatGeometry, geometry->getBoundingBox());

    pcout << "Initializing geometry on CPU" << endl;
    // Set the bounce-back nodes from the geometry data
    const int SOLID_FLAG = 1;
    const int FLUID_FLAG = 0;

    Box3D porousDomain(0, nx - 1, bufferSize, ny - 1, 0, nz - 1);
    Box3D lowerDomain(0, nx - 1, 0, bufferSize - 1, 0, nz - 1);

    setToConstant(*geometry, lowerDomain, FLUID_FLAG);
    setToConstant(*geometry, Box3D(0, nx - 1, 0, ny - 1, 0, 0), SOLID_FLAG);
    setToConstant(*geometry, Box3D(0, nx - 1, 0, ny - 1, nz - 1, nz - 1), SOLID_FLAG);

    plint numFluidNodes = porousDomain.nCells() - computeSum(*geometry, porousDomain);
    pcout << "Number for fluid nodes: " << numFluidNodes << endl;
    pcout << "Porosity: " << (T)numFluidNodes / (T)porousDomain.nCells() * 100 << "%" << endl;

    defineDynamics(
        *buoyantFluid, *geometry, porousDomain, new BounceBack<T, DESCRIPTOR>(rhoOnBuoyant),
        SOLID_FLAG);
    defineDynamics(
        *displacedFluid, *geometry, porousDomain, new BounceBack<T, DESCRIPTOR>(rhoOnDisplaced),
        SOLID_FLAG);

    delete geometry;
    geometry = nullptr;

    AcceleratedLattice3D<T, DESCRIPTOR> *accBuoyantFluid = nullptr;
    AcceleratedLattice3D<T, DESCRIPTOR> *accDisplacedFluid = nullptr;

    if (useAcceleratedLattice) {
        pcout << "Creating GPU data" << endl;
        accBuoyantFluid = new AcceleratedLattice3D<T, DESCRIPTOR>(*buoyantFluid);
        accDisplacedFluid = new AcceleratedLattice3D<T, DESCRIPTOR>(*displacedFluid);

        vector<AcceleratedLattice3D<T, DESCRIPTOR> *> acceleratedBlockLattices;
        acceleratedBlockLattices.push_back(accBuoyantFluid);
        acceleratedBlockLattices.push_back(accDisplacedFluid);
        static const int numSpecies = 2;
        integrateProcessingFunctional(
            new ShanChenMultiComponentAccelerated3D<T, DESCRIPTOR, numSpecies>(G, constOmegaValues),
            Box3D(0, nx - 1, 1, ny - 2, 0, nz - 1), acceleratedBlockLattices, processorLevel);
        // delete buoyantFluid;
        // buoyantFluid = nullptr;
        // delete displacedFluid;
        // displacedFluid = nullptr;
    }

    /*
    std::map<int, std::string> nameOfDynamics;
    auto dynField = extractDynamicsChain(buoyantFluid, nameOfDynamics);
    pcout << "Dynamics map:" << endl;
    for (auto iter = nameOfDynamics.begin(); iter != nameOfDynamics.end(); ++iter) {
        pcout << iter->first << ": " << iter->second << endl;
    }
    pcout << endl;
    */

    if (benchmark) {
        pcout << "Now running " << bench_ini_iter << " warm-up iterations." << endl;
    } else {
        pcout << "Starting simulation" << endl;
    }

    // Reset the clock.
    global::timer("rayleighTaylor").start();
    plint clock_iter = 0;

    // Main loop over time iterations.
    for (plint iT = 0; iT < maxIter; ++iT) {
        if (production && iT % saveIter == 0) {
            if (useAcceleratedLattice) {
                // writePpms(*accBuoyantFluid, *accDisplacedFluid, iT);
                pcout << "Writing VTKs at iteration " << iT << endl;
                writeVTK(*accBuoyantFluid, *accDisplacedFluid, floatGeometry, iT);
                pcout << "End writing VTKs" << endl;
            } else {
                // writePpms(buoyantFluid, displacedFluid, iT);
                writeVTK(*buoyantFluid, *displacedFluid, floatGeometry, iT);
            }
        }

        if (benchmark && iT == bench_ini_iter) {
            pcout << "Now running " << maxIter - bench_ini_iter << " benchmark iterations." << endl;
            global::timer("rayleighTaylor").restart();
            clock_iter = 0;
        }
        if (useAcceleratedLattice) {
            accDisplacedFluid->collideAndStream(CollisionKernel<
                                                T, DESCRIPTOR, CollisionModel::BGK_ExternalMoment,
                                                CollisionModel::BounceBack>());
            accBuoyantFluid->collideAndStream(CollisionKernel<
                                              T, DESCRIPTOR, CollisionModel::BGK_ExternalMoment,
                                              CollisionModel::BounceBack>());
        } else {
            // Time iteration for the light fluid.
            displacedFluid->collideAndStream();
            buoyantFluid->collideAndStream();
        }

        if (production && iT % statIter == 0) {
            if (useAcceleratedLattice) {
                pcout << "Average energy fluid one = "
                      << computeAverage<T>(*computeKineticEnergy(*accBuoyantFluid));
                pcout << ", average energy fluid two = "
                      << computeAverage<T>(*computeKineticEnergy(*accDisplacedFluid)) << endl;

                plint numOccupiedNodes = countOccupiedNodes(*accBuoyantFluid, porousDomain, (T)0.5);
                pcout << "Number of buoyant fluid cells in porous media: " << numOccupiedNodes
                      << endl;
                T saturation = (T)numOccupiedNodes / (T)numFluidNodes;
                pcout << "Saturation: " << saturation * 100 << "%" << endl;
            } else {
                pcout << "Average energy fluid one = "
                      << computeAverage<T>(*computeKineticEnergy(*buoyantFluid));
                pcout << ", average energy fluid two = "
                      << computeAverage<T>(*computeKineticEnergy(*displacedFluid)) << endl;
            }
        }
        ++clock_iter;
    }

    // Print program performance in MLUPS
    double elapsed = global::timer("rayleighTaylor").stop();
    double mlups = static_cast<double>((nx * ny * nz) * clock_iter) / elapsed * 1.e-6;
    pcout << "Performance: " << setprecision(4) << mlups << " MLUPS" << endl;
    pcout << endl;

    // If so required, execute a regression test
    if (regression) {
        double reference_energy = -1.0;
        if (nx == 225 && ny == 75 && nz == 225 && sizeof(T) == sizeof(float) && maxIter == 200) {
            reference_energy = 0.001526529202238;
        } else if (
            nx == 625 && ny == 188 && nz == 625 && sizeof(T) == sizeof(float) && maxIter == 500) {
            reference_energy = 0.001539794146083;
        }
        T energy = 0.;
        if (useAcceleratedLattice) {
            energy = computeAverage<T>(*computeKineticEnergy(*accBuoyantFluid))
                     + computeAverage<T>(*computeKineticEnergy(*accDisplacedFluid));
        } else {
            energy = computeAverage<T>(*computeKineticEnergy(*buoyantFluid))
                     + computeAverage<T>(*computeKineticEnergy(*displacedFluid));
        }
        pcout << "Regression test with energy = " << setprecision(13) << energy;
        if (std::fabs(energy - reference_energy) < 1.e-10) {
            pcout << ": OK" << endl;
        } else {
            pcout << ": FAILED" << endl;
            pcout << "Expected the value " << reference_energy << endl;
        }
    }

    return 0;
}
