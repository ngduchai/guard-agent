/*  Lattice Boltzmann sample, written in C++, using the OpenLB
 *  library
 *
 *  Copyright (C) 2006, 2007, 2012, 2025 Jonas Latt, Mathias J. Krause,
 *  Louis Kronberg, Christian Vorwerk, Bastian Schäffauer, Yuji (Sam) Shimojima
 *  E-mail contact: info@openlb.net
 *  The most recent release of OpenLB can be downloaded at
 *  <http://www.openlb.net/>
 *
 *  This program is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU General Public License
 *  as published by the Free Software Foundation; either version 2
 *  of the License, or (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public
 *  License along with this program; if not, write to the Free
 *  Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 *  Boston, MA  02110-1301, USA.
 */

/* bstep2d.cpp:
 * The implementation of a backward facing step. It is furthermore
 * shown how to use checkpointing to save the state of the
 * simulation regularly.
 * The geometry of the step is based on the experiment described in
 * [Armaly, B.F., Durst, F., Pereira, J. C. F. and Schönung, B. Experimental
 * and theoretical investigation of backward-facing step flow. 1983.
 * J. Fluid Mech., vol. 127, pp. 473-496, DOI: 10.1017/S0022112083002839]
 */

#include <olb.h>
#include <fstream>
using namespace olb;
using namespace olb::names;

// === Step 1: Declarations ===
using MyCase = Case<NavierStokes, Lattice<double, descriptors::D2Q9<>>>;

namespace olb::parameters {

struct PHYS_LENGTH_OF_STEP : public descriptors::FIELD_BASE<1> {};
struct PHYS_HEIGHT_OF_STEP : public descriptors::FIELD_BASE<1> {};

} // namespace olb::parameters

/// @brief Create a simulation mesh, based on user-specific geometry
/// @return An instance of Mesh, which keeps the relevant information
Mesh<MyCase::value_t, MyCase::d> createMesh(MyCase::ParametersD& parameters)
{
  using T = MyCase::value_t;
  // setup channel
  const Vector                     extendChannel = parameters.get<parameters::DOMAIN_EXTENT>();
  const Vector                     originChannel(0, 0);
  std::shared_ptr<IndicatorF2D<T>> channel = std::make_shared<IndicatorCuboid2D<T>>(extendChannel, originChannel);
  // setup step
  const T lengthStep = parameters.get<parameters::PHYS_LENGTH_OF_STEP>(); // length of step in meter
  const T heightStep = parameters.get<parameters::PHYS_HEIGHT_OF_STEP>(); // height of step in meter

  const Vector                     extendStep(lengthStep, heightStep);
  const Vector                     originStep(0, 0);
  std::shared_ptr<IndicatorF2D<T>> step = std::make_shared<IndicatorCuboid2D<T>>(extendStep, originStep);

  const T physDeltaX = parameters.get<parameters::PHYS_CHAR_LENGTH>() / parameters.get<parameters::RESOLUTION>();

  Mesh<T, MyCase::d> mesh(*(channel - step), physDeltaX, singleton::mpi().getSize());
  mesh.setOverlap(parameters.get<parameters::OVERLAP>());
  return mesh;
}

/// @brief Set material numbers for different parts of the domain
/// @param myCase The Case instance which keeps the simulation data
/// @note The material numbers will be used to assign physics to lattice nodes
void prepareGeometry(MyCase& myCase)
{
  OstreamManager clout(std::cout, "prepareGeometry");
  clout << "Prepare Geometry ..." << std::endl;
  using T          = MyCase::value_t;
  auto& parameters = myCase.getParameters();
  auto& sGeometry  = myCase.getGeometry();
  // Parameters for the simulation setup

  // setup channel
  const Vector                     extendChannel = parameters.get<parameters::DOMAIN_EXTENT>();
  const Vector                     originChannel(0, 0);
  std::shared_ptr<IndicatorF2D<T>> channel = std::make_shared<IndicatorCuboid2D<T>>(extendChannel, originChannel);

  // setup step
  const T lengthStep = parameters.get<parameters::PHYS_LENGTH_OF_STEP>(); // length of step in meter
  const T heightStep = parameters.get<parameters::PHYS_HEIGHT_OF_STEP>(); // height of step in meter

  const Vector                     extendStep(lengthStep, heightStep);
  const Vector                     originStep(0, 0);
  std::shared_ptr<IndicatorF2D<T>> step = std::make_shared<IndicatorCuboid2D<T>>(extendStep, originStep);

  const T physDeltaX = parameters.get<parameters::PHYS_CHAR_LENGTH>() / parameters.get<parameters::RESOLUTION>();
  // material numbers from zero to 2 inside geometry defined by indicator
  sGeometry.rename(0, 2, channel - step);
  sGeometry.rename(2, 1, {1, 1});
  const T      lengthChannel = parameters.get<parameters::DOMAIN_EXTENT>()[0];
  const T      heightChannel = parameters.get<parameters::DOMAIN_EXTENT>()[1];
  const T      heightInlet   = heightChannel - heightStep;
  Vector<T, 2> extendBC_out((T)0.0 + (T)1.0 * physDeltaX, heightChannel);
  Vector<T, 2> extendBC_in((T)0.0, heightInlet);
  Vector<T, 2> originBC_out(lengthChannel - (T)1.0 * physDeltaX, 0);
  Vector<T, 2> originBC_in((T)0.0, heightStep);

  IndicatorCuboid2D<T> inflow(extendBC_in, originBC_in);
  // Set material number for inflow
  sGeometry.rename(2, 3, 1, inflow);

  IndicatorCuboid2D<T> outflow(extendBC_out, originBC_out);
  // Set material number for outflow
  sGeometry.rename(2, 4, 1, outflow);

  // Removes all not needed boundary voxels outside the surface
  sGeometry.clean();
  // Removes all not needed boundary voxels inside the surface
  sGeometry.innerClean();
  sGeometry.checkForErrors();
  sGeometry.getStatistics().print();
  clout << "Prepare Geometry ... OK" << std::endl;
}

/// @brief Set lattice dynamics
/// @param myCase The Case instance which keeps the simulation data
void prepareLattice(MyCase& myCase)
{
  OstreamManager clout(std::cout, "prepareLattice");
  clout << "Prepare Lattice ..." << std::endl;

  using T = MyCase::value_t;

  auto& sGeometry  = myCase.getGeometry();
  auto& parameters = myCase.getParameters();
  auto& sLattice   = myCase.getLattice(NavierStokes {});
  using DESCRIPTOR = MyCase::descriptor_t_of<NavierStokes>;
  {
    using namespace olb::parameters;
    sLattice.setUnitConverter<UnitConverterFromResolutionAndRelaxationTime<T, DESCRIPTOR>>(
        parameters.get<RESOLUTION>(),       // resolution
        parameters.get<LATTICE_RELAXATION_TIME>(),  // relaxation time
        parameters.get<PHYS_CHAR_LENGTH>(), // charPhysLength: reference length of simulation geometry
        parameters.get<
            PHYS_CHAR_VELOCITY>(), // charPhysVelocity: maximal/highest expected velocity during simulation in __m / s__
        parameters.get<PHYS_CHAR_VISCOSITY>(), // physViscosity: physical kinematic viscosity in __m^2 / s__
        parameters.get<PHYS_CHAR_DENSITY>()    // physDensity: physical density in __kg / m^3__
    );
  }
  const auto& converter = sLattice.getUnitConverter();

  // Prints the converter log as console output
  converter.print();
  // Writes the converter log in a file
  converter.write("bstep2d");

  auto bulkIndicator = sGeometry.getMaterialIndicator({1, 3, 4});

  // Material=1 -->bulk dynamics
  // Material=3 -->bulk dynamics (inflow)
  // Material=4 -->bulk dynamics (outflow)
  dynamics::set<BGKdynamics>(sLattice, bulkIndicator);
  // Material=2 -->bounce back
  boundary::set<boundary::BounceBack>(sLattice, sGeometry, 2);

  //if boundary conditions are chosen to be local
  boundary::set<boundary::LocalVelocity>(sLattice, sGeometry, 3);
  boundary::set<boundary::LocalPressure>(sLattice, sGeometry, 4);

  //if boundary conditions are chosen to be interpolated
  // boundary::set<boundary::InterpolatedVelocity>(sLattice, sGeometry, 3);
  // boundary::set<boundary::InterpolatedPressure>(sLattice, sGeometry, 4);

  clout << "Prepare Lattice ... OK" << std::endl;
}

/// Set initial condition for primal variables (velocity and density)
/// @param myCase The Case instance which keeps the simulation data
/// @note Be careful: initial values have to be set using lattice units
void setInitialValues(MyCase& myCase)
{
  OstreamManager clout(std::cout, "Initialization");
  clout << "lattice initialization ..." << std::endl;
  using T         = MyCase::value_t;
  auto& sLattice  = myCase.getLattice(NavierStokes {});
  const T omega = sLattice.getUnitConverter().getLatticeRelaxationFrequency();
  sLattice.setParameter<descriptors::OMEGA>(omega);

  // Make the lattice ready for simulation
  sLattice.initialize();
  clout << "Initialization ... OK" << std::endl;
}

// Generates a slowly increasing inflow for the first iTMaxStart timesteps
void setTemporalValues(MyCase& myCase, std::size_t iT)
{
  OstreamManager clout(std::cout, "setTemporalValues");
  using T = MyCase::value_t;

  auto&   sLattice   = myCase.getLattice(NavierStokes {});
  auto&   converter  = sLattice.getUnitConverter();
  auto&   sGeometry  = myCase.getGeometry();
  auto&   parameters = myCase.getParameters();
  const T maxPhysT   = parameters.get<parameters::MAX_PHYS_T>();

  // time for smooth start-up
  std::size_t iTmaxStart = converter.getLatticeTime(maxPhysT * 0.2);
  std::size_t iTupdate   = 100;

  if (iT % iTupdate == 0 && iT <= iTmaxStart) {
    // Smooth start curve, sinus
    // SinusStartScale<T,std::size_t> StartScale(iTmaxStart, (T)1);
    // Smooth start curve, polynomial
    PolynomialStartScale<T, std::size_t> StartScale(iTmaxStart, T(1));
    // Creates and sets the Poiseuille inflow profile using functors
    std::size_t iTvec[1] = {iT};
    T           frac[1]  = {};
    StartScale(frac, iTvec);
    T               maxVelocity   = converter.getCharPhysVelocity() * (T)3.0 / (T)2.0 * frac[0];
    T               distance2Wall = converter.getPhysDeltaX() / (T)2.0;
    Poiseuille2D<T> poiseuilleU(sGeometry, 3, maxVelocity, distance2Wall);
    // define physical speed on inflow
    momenta::setVelocity(sLattice, sGeometry.getMaterialIndicator(3), poiseuilleU);

    sLattice.setProcessingContext<Array<momenta::FixedVelocityMomentumGeneric::VELOCITY>>(
        ProcessingContext::Simulation);
  }
}

void getResults(MyCase& myCase, std::size_t iT, util::Timer<MyCase::value_t> &timer)
{
  OstreamManager clout(std::cout, "getResults");
  using T = MyCase::value_t;
  auto&          parameters    = myCase.getParameters();
  const T        heightChannel = parameters.get<parameters::DOMAIN_EXTENT>()[1];
  const T        heightStep    = parameters.get<parameters::PHYS_HEIGHT_OF_STEP>(); // height of step in meter
  const T        lengthStep    = parameters.get<parameters::PHYS_LENGTH_OF_STEP>(); // length of step in meter
  const T        heightInlet   = heightChannel - heightStep;
  auto&          sLattice      = myCase.getLattice(NavierStokes {});
  auto&          converter     = sLattice.getUnitConverter();
  auto&          sGeometry     = myCase.getGeometry();

  // instantiate reusable functors
  SuperPlaneIntegralFluxVelocity2D<T> velocityFlux(sLattice, converter, sGeometry,
                                                   {lengthStep / (T)2.0, heightInlet / (T)2.0}, {(T)0.0, (T)1.0});

  SuperPlaneIntegralFluxPressure2D<T> pressureFlux(sLattice, converter, sGeometry,
                                                   {lengthStep / (T)2.0, heightInlet / (T)2.0}, {(T)0.0, (T)1.0});
  SuperVTMwriter2D<T>                 vtmWriter("bstep2d");

  if (iT == 0) {
    // Writes geometry, cuboid no. and rank no. to file system
    SuperLatticeCuboid2D cuboid(sLattice);
    SuperLatticeRank2D   rank(sLattice);
    vtmWriter.write(cuboid);
    vtmWriter.write(rank);
    vtmWriter.createMasterFile();
  }

  // Writes every 0.1 simulated
  if (iT % converter.getLatticeTime(0.1) == 0) {
    sLattice.setProcessingContext(ProcessingContext::Evaluation);

    velocityFlux.print();
    pressureFlux.print();

    // write to terminal
    timer.update(iT);
    timer.printStep();
    // Lattice statistics console output
    sLattice.getStatistics().print(iT, converter.getPhysTime(iT));
  }

  if (iT % converter.getLatticeTime(0.2) == 0) {
    SuperLatticePhysVelocity2D velocity(sLattice, converter);
    SuperLatticePhysPressure2D pressure(sLattice, converter);
    vtmWriter.addFunctor(velocity);
    vtmWriter.addFunctor(pressure);
    // write vtk to file system
    vtmWriter.write(iT);
    using T = MyCase::value_t_of<NavierStokes>;
    SuperEuklidNorm2D     normVel(velocity);
    BlockReduction2D2D<T> planeReduction(normVel, 1200, BlockDataSyncMode::ReduceOnly);
    // write output as JPEG
    heatmap::plotParam<T> jpeg_Param;
    jpeg_Param.maxValue       = converter.getCharPhysVelocity() * 3. / 2.;
    jpeg_Param.minValue       = 0.0;
    jpeg_Param.fullScreenPlot = true;
    heatmap::write(planeReduction, iT, jpeg_Param);
  }

  // Saves lattice data (checkpoint every 5000 iterations)
  if (iT % 5000 == 0 && iT > 0) {
    clout << "Checkpointing the system at t=" << iT << std::endl;
    sLattice.save( "bstep2d.checkpoint" );
    // Save iteration number for restart
    std::ofstream iterFile("bstep2d.checkpoint.iter");
    iterFile << iT;
    iterFile.close();
  }
}

void simulate(MyCase& myCase)
{
  OstreamManager clout(std::cout, "Time marching");


  using T = MyCase::value_t;
  auto&          parameters = myCase.getParameters();
  auto&          sLattice   = myCase.getLattice(NavierStokes {});
  const T        maxPhysT   = parameters.get<parameters::MAX_PHYS_T>();
  util::Timer<T> timer(sLattice.getUnitConverter().getLatticeTime(maxPhysT),
                       myCase.getGeometry().getStatistics().getNvoxel());
  clout << "starting simulation..." << std::endl;

  // Try to load checkpoint for restart
  std::size_t startIter = 0;
  if (sLattice.load("bstep2d.checkpoint")) {
    // Read saved iteration number
    std::ifstream iterFile("bstep2d.checkpoint.iter");
    if (iterFile.good()) {
      iterFile >> startIter;
      startIter++; // resume from next iteration
    }
    clout << "Loaded checkpoint, resuming from iteration " << startIter << std::endl;
  }

  timer.start();

  for (std::size_t iT = startIter; iT < sLattice.getUnitConverter().getLatticeTime(maxPhysT); ++iT) {

    setTemporalValues(myCase, iT);

    sLattice.collideAndStream();

    getResults(myCase, iT, timer);
  }

  sLattice.setProcessingContext(ProcessingContext::Evaluation);
  timer.stop();
  timer.printSummary();
}

int main(int argc, char* argv[])
{
  initialize(&argc, &argv);
  /// === Step 2: Set Parameters ===
  MyCase::ParametersD myCaseParameters;
  {
    using namespace olb::parameters;
    myCaseParameters.set<RESOLUTION>(20);
    myCaseParameters.set<LATTICE_RELAXATION_TIME>(0.518);
    myCaseParameters.set<PHYS_LENGTH_OF_STEP>(0.2);
    myCaseParameters.set<PHYS_HEIGHT_OF_STEP>(0.0049);
    myCaseParameters.set<PHYS_CHAR_VELOCITY>(1.0);
    myCaseParameters.set<PHYS_CHAR_VISCOSITY>(1.0 / 19230.76923);
    myCaseParameters.set<PHYS_CHAR_DENSITY>(1.0);
    myCaseParameters.set<DOMAIN_EXTENT>({0.7, 0.0101});
    myCaseParameters.set<PHYS_CHAR_LENGTH>([&]{return 2.0 *
          (myCaseParameters.get<DOMAIN_EXTENT>()[1] - myCaseParameters.get<PHYS_HEIGHT_OF_STEP>());});
    myCaseParameters.set<MAX_PHYS_T>(2.0);
  }
  myCaseParameters.fromCLI(argc, argv);

  /// === Step 3: Create Mesh ===
  Mesh mesh = createMesh(myCaseParameters);
  /// === Step 4: Create Case ===
  MyCase myCase(myCaseParameters, mesh);

  /// === Step 5: Prepare Geometry ===
  prepareGeometry(myCase);

  /// === Step 6: Prepare Lattice ===
  prepareLattice(myCase);

  /// === Step 7: Definition of Initial, Boundary Values, and Fields ===
  setInitialValues(myCase);

  /// === Step 8: Simulate ===
  simulate(myCase);

  return 0;
}
