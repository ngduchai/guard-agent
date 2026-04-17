/*  Lattice Boltzmann sample, written in C++, using the OpenLB
 *  library
 *
 *  Copyright (C) 2006, 2007, 2012 Jonas Latt, Mathias J. Krause,
 *  Vojtech Cvrcek, Peter Weisbrod
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

#include <olb.h>

#include "poiseuille_shared.h"

#include <cmath>
#include <iomanip>
#include <fstream>

#include "../unit/helper/framework.h"

#include <gtest/gtest.h>

using namespace olb;

using DESCRIPTOR = descriptors::D2Q9<descriptors::FORCE>;

/// ensure olbInit is called for MPI
::testing::Environment* const foo_env = ::testing::AddGlobalTestEnvironment(new OlbInitTestEnvironment);

// Parameters for the simulation setup
const T lx  = 2.;             // length of the channel
const T ly  = 1.;             // height of the channel
const T Re = 10.;             // Reynolds number
const T maxPhysT = 20.;       // max. simulation time in s, SI unit
const T physInterval = 0.25;  // interval for the convergence check in s
const T residuum = 1e-5;      // residuum for the convergence check

TestParam bgkParams[] = {
  {FlowType::forced, BoundaryType::bounceBack, 11, 1000, 0.232242, 0., 0.00943311, 1},
  {FlowType::forced, BoundaryType::local, 11, 1185, 0.0164571, 0., 0.00949058, 1},
  {FlowType::forced, BoundaryType::interpolated, 11, 1187, 0.0111551, 0., 0.00974589, 1},
  {FlowType::nonForced, BoundaryType::bounceBack, 11, 930, 0.11423416, 0.46332219, 0.38766511, 1},
  {FlowType::nonForced, BoundaryType::local, 11,  887, 0.0249852, 0.0701517, 0.0348407, 1},
  {FlowType::nonForced, BoundaryType::interpolated, 11,  886, 0.0241304, 0.0661456, 0.0304911, 1},
  {FlowType::nonForced, BoundaryType::local, 21, 2735, 0.00672805, 0.0181265, 0.00967376, 1},
  {FlowType::nonForced, BoundaryType::local, 41, 7694, 0.00175806, 0.00461553, 0.00260221, 1}
};

class Poiseuille2DTest : public ::testing::TestWithParam<TestParam> {

};

// Stores geometry information in form of material numbers
template<typename DESCRIPTOR>
void prepareGeometry( UnitConverter<T,DESCRIPTOR> const& converter,
                      SuperGeometry<T,2>& superGeometry, const TestParam& param)
{

  superGeometry.rename( 0,2 );

  superGeometry.rename( 2,1,{1,1} );

  if (param.flowType == FlowType::nonForced) {
    Vector<T,2> extend;
    Vector<T,2> origin;
    T physSpacing = converter.getPhysDeltaX();

    // Set material number for inflow
    extend[1] = ly;
    extend[0] = physSpacing / 2;
    origin[0] -= physSpacing / 4;
    IndicatorCuboid2D<T> inflow( extend, origin );
    superGeometry.rename( 2,3,1,inflow );

    // Set material number for outflow
    origin[0] = lx - physSpacing / 4;
    IndicatorCuboid2D<T> outflow( extend, origin );
    superGeometry.rename( 2,4,1,outflow );
  }

  // Removes all not needed boundary voxels outside the surface
  superGeometry.clean(false);
  // Removes all not needed boundary voxels inside the surface
  superGeometry.innerClean(false);
  superGeometry.checkForErrors(false);
}

// Set up the geometry of the simulation
template<typename DESCRIPTOR>
void prepareLattice( UnitConverter<T,DESCRIPTOR> const& converter,
                     SuperLattice<T, DESCRIPTOR>& sLattice,
                     SuperGeometry<T,2>& superGeometry, const TestParam& param )
{

  const T omega = converter.getLatticeRelaxationFrequency();

  // Material=0 -->do nothing
  sLattice.template defineDynamics<NoDynamics>(superGeometry, 0);

  // Material=1 -->bulk dynamics
  if (param.flowType == FlowType::forced) {
    sLattice.template defineDynamics<ForcedBGKdynamics>(superGeometry, 1);
  } else {
    sLattice.template defineDynamics<BGKdynamics>(superGeometry, 1);
  }

  if (param.boundaryType == BoundaryType::bounceBack) {
    sLattice.template defineDynamics<BounceBack>(superGeometry, 2);
  }
  else {
    if (param.boundaryType == BoundaryType::local) {
      boundary::set<boundary::LocalVelocity>(sLattice, superGeometry, 2);
    }
    else {
      boundary::set<boundary::InterpolatedVelocity>(sLattice, superGeometry, 2);
    }
  }

  if (param.flowType == FlowType::nonForced) {
    if (param.boundaryType == BoundaryType::local) {
      boundary::set<boundary::LocalVelocity>(sLattice, superGeometry, 3);
      boundary::set<boundary::LocalPressure>(sLattice, superGeometry, 4);
    }
    else {
      boundary::set<boundary::InterpolatedVelocity>(sLattice, superGeometry, 3);
      boundary::set<boundary::InterpolatedPressure>(sLattice, superGeometry, 4);
    }
  } else {
    // Material=3 -->bulk dynamics
    // Material=4 -->bulk dynamics
    sLattice.template defineDynamics<ForcedBGKdynamics>(superGeometry, 3);
    sLattice.template defineDynamics<ForcedBGKdynamics>(superGeometry, 4);
  }

  // Initial conditions
  T Lx = converter.getLatticeLength( lx );
  T Ly = converter.getLatticeLength( ly );

  if (param.flowType == FlowType::forced) {
    std::vector<T> poiseuilleForce( 2,T() );
    poiseuilleForce[0] = 8.*converter.getLatticeViscosity()*converter.getCharLatticeVelocity() / ( Ly*Ly );
    AnalyticalConst2D<T,T> force( poiseuilleForce );

    // Initialize force
    sLattice.template defineField<descriptors::FORCE>( superGeometry, 1, force );
    sLattice.template defineField<descriptors::FORCE>( superGeometry, 2, force );
  }
  else {
    T p0 =8.*converter.getLatticeViscosity()*converter.getCharLatticeVelocity()*Lx/( Ly*Ly );
    AnalyticalLinear2D<T,T> rho( -p0/lx*descriptors::invCs2<T,DESCRIPTOR>(), 0, p0*descriptors::invCs2<T,DESCRIPTOR>()+1 );

    T maxVelocity = converter.getCharLatticeVelocity();
    T distance2Wall = converter.getConversionFactorLength();
    Poiseuille2D<T> u( superGeometry, 3, maxVelocity, distance2Wall );

    // Initialize all values of distribution functions to their local equilibrium
    sLattice.defineRhoU( superGeometry, 1, rho, u );
    sLattice.iniEquilibrium( superGeometry, 1, rho, u );
    sLattice.defineRhoU( superGeometry, 2, rho, u );
    sLattice.iniEquilibrium( superGeometry, 2, rho, u );
    sLattice.defineRhoU( superGeometry, 3, rho, u );
    sLattice.iniEquilibrium( superGeometry, 3, rho, u );
    sLattice.defineRhoU( superGeometry, 4, rho, u );
    sLattice.iniEquilibrium( superGeometry, 4, rho, u );
  }

  sLattice.template setParameter<descriptors::OMEGA>(omega);

  // Make the lattice ready for simulation
  sLattice.initialize();
}

// Compute error norms
template<typename DESCRIPTOR>
void error( SuperGeometry<T,2>& superGeometry,
            SuperLattice<T, DESCRIPTOR>& sLattice,
            UnitConverter<T,DESCRIPTOR> const& converter,
            const TestParam& param)
{

  int tmp[]= {int()};
  T result[2]= {T(),T()}, result_tmp[2]= {T(),T()};

  // velocity error
  const T maxVelocity = converter.getCharPhysVelocity();
  const T radius = ly/2.;
  std::vector<T> axisPoint( 2,T() );
  axisPoint[0] = lx/2.;
  axisPoint[1] = ly/2.;
  std::vector<T> axisDirection( 2,T() );
  axisDirection[0] = 1;
  axisDirection[1] = 0;
  Poiseuille2D<T> uSol( axisPoint, axisDirection, maxVelocity, radius );
  SuperLatticePhysVelocity2D<T,DESCRIPTOR> u( sLattice,converter );
  SuperLatticeFfromAnalyticalF2D<T,DESCRIPTOR> uSolLattice( uSol,sLattice );

  SuperL2Norm2D<T> uL2Norm( uSolLattice-u,superGeometry,1 );
  SuperL2Norm2D<T> uSolL2Norm( uSolLattice,superGeometry,1 );
  uL2Norm( result,tmp );
  uSolL2Norm( result_tmp,tmp );
  T velocityErrorL2 = result[0] / result_tmp[0];
  EXPECT_NEAR(velocityErrorL2, param.velocityErrorL2, 1e-6);

  // strainRate error
  PoiseuilleStrainRate2D<T,T,DESCRIPTOR> sSol( converter, ly );
  SuperLatticePhysStrainRate2D<T,DESCRIPTOR> s( sLattice,converter );
  SuperLatticeFfromAnalyticalF2D<T,DESCRIPTOR> sSolLattice( sSol,sLattice );

  SuperL2Norm2D<T> sL2Norm( sSolLattice-s,superGeometry,1 );
  SuperL2Norm2D<T> sSolL2Norm( sSolLattice,superGeometry,1 );
  sL2Norm( result,tmp );
  sSolL2Norm( result_tmp,tmp );
  T strainErrorL2 = result[0] / result_tmp[0];
  EXPECT_NEAR(strainErrorL2, param.strainErrorL2, 1e-6);

  if (param.flowType == FlowType::nonForced) {
    // pressure error
    int Lx = converter.getLatticeLength( lx );
    int Ly = converter.getLatticeLength( ly );
    T p0 = 8.*converter.getLatticeViscosity()*converter.getCharLatticeVelocity()*Lx/double( Ly*Ly );

    AnalyticalLinear2D<T,T> pressureSol( -converter.getPhysPressure( p0 )/lx, 0, converter.getPhysPressure( p0 ) );
    SuperLatticePhysPressure2D<T,DESCRIPTOR> pressure( sLattice,converter );
    SuperLatticeFfromAnalyticalF2D<T,DESCRIPTOR> pressureSolLattice( pressureSol,sLattice );

    SuperL2Norm2D<T> pressureL2Norm( pressureSolLattice-pressure,superGeometry,1 );
    SuperL2Norm2D<T> pressureSolL2Norm( pressureSolLattice,superGeometry,1 );
    pressureL2Norm( result,tmp );
    pressureSolL2Norm( result_tmp,tmp );
    T pressureErrorL2 = result[0] / result_tmp[0];
    EXPECT_NEAR(pressureErrorL2, param.pressureErrorL2, 1e-6);

  }
}

TEST_P(Poiseuille2DTest, testBGK)
{

  // === 1st Step: Initialization ===
  TestParam param = GetParam();

  UnitConverterFromResolutionAndRelaxationTime<T,DESCRIPTOR> const converter(
    param.N,     // resolution: number of voxels per charPhysL
    (T)   0.8,   // latticeRelaxationTime: relaxation time, have to be greater than 0.5!
    (T)   1,     // charPhysLength: reference length of simulation geometry
    (T)   1,     // charPhysVelocity: maximal/highest expected velocity during simulation in __m / s__
    (T)   1./Re, // physViscosity: physical kinematic viscosity in __m^2 / s__
    (T)   1.0    // physDensity: physical density in __kg / m^3__
  );

  // === 2nd Step: Prepare Geometry ===
  Vector<T,2> extend( lx, ly );
  Vector<T,2> origin;
  IndicatorCuboid2D<T> cuboid( extend, origin );

  // Instantiation of a cuboidDecomposition with weights
  CuboidDecomposition2D<T> cuboidDecomposition( cuboid, converter.getConversionFactorLength(), 1 );

  if (param.flowType == FlowType::forced) {
    // Periodic boundaries in x-direction
    cuboidDecomposition.setPeriodicity({ true, false });
  }

  // Instantiation of a loadBalancer
  HeuristicLoadBalancer<T> loadBalancer( cuboidDecomposition );

  // Instantiation of a superGeometry
  SuperGeometry<T,2> superGeometry( cuboidDecomposition, loadBalancer, 2 );

  prepareGeometry<DESCRIPTOR>( converter, superGeometry, param );

  // === 3rd Step: Prepare Lattice ===
  SuperLattice<T,DESCRIPTOR> sLattice( converter, superGeometry );

  // choose boundary condition and prepare lattice
  prepareLattice<DESCRIPTOR>( converter, sLattice, superGeometry, param );

  // === 4th Step: Main Loop with Timer ===
  util::Timer<T> timer( converter.getLatticeTime( maxPhysT ), superGeometry.getStatistics().getNvoxel() );
  util::ValueTracer<T> converge( converter.getLatticeTime( physInterval ), residuum );
  timer.start();

  int iT;
  for ( iT = 0; iT < converter.getLatticeTime( maxPhysT ); ++iT ) {
    if ( converge.hasConverged() ) {
      break;
    }

    // === 5th Step: Definition of Initial and Boundary Conditions ===
    // in this application no boundary conditions have to be adjusted

    // Verify watertightness of dynamics configuration
    std::vector<T> nan(DESCRIPTOR::q, NAN);
    AnalyticalConst2D<T,T> popF( nan );
    sLattice.definePopulations( superGeometry, 0, popF );

    // === 6th Step: Collide and Stream Execution ===
    sLattice.collideAndStream();

    converge.takeValue( sLattice.getStatistics().getAverageEnergy(), false );
  }

  sLattice.setProcessingContext(ProcessingContext::Evaluation);

  EXPECT_EQ(iT, param.iT);
  error<DESCRIPTOR>(superGeometry, sLattice, converter, param);

  timer.stop();
}

INSTANTIATE_TEST_CASE_P(BGKPoiseuille, Poiseuille2DTest,
                        testing::ValuesIn(bgkParams));
