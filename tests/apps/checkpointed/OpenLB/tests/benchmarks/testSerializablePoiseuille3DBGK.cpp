/*  Lattice Boltzmann sample, written in C++, using the OpenLB
 *  library
 *
 *  Copyright (C) 2006, 2007, 2012 Jonas Latt, Mathias J. Krause,
 *  Vojtech Cvrcek, Peter Weisbrod, Clara Schragmann
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
#include <iostream>
#include <iomanip>
#include <fstream>

#include "../unit/helper/framework.h"

#include <gtest/gtest.h>

using namespace olb;

using DESCRIPTOR = descriptors::D3Q19<descriptors::FORCE>;

/// ensure olbInit is called for MPI
::testing::Environment* const foo_env = ::testing::AddGlobalTestEnvironment(new OlbInitTestEnvironment);

// Parameters for the simulation setup
const T lx  = 2.;             // length of the channel
const T d  = 1.;              // diameter of the channel
const T r  = 0.5;             // radius of the channel
const T Re = 10.;             // Reynolds number
const T maxPhysT = 20.;       // max. simulation time in s, SI unit
const T physInterval = 0.25;  // interval for the convergence check in s
const T residuum = 1e-5;      // residuum for the convergence check

TestParam bgkParams[] = {
  {FlowType::forced, BoundaryType::bounceBack, 11, 422, 0.158042, 0., 0.168242, 1},
  {FlowType::forced, BoundaryType::local, 11, 317, 0.020342, 0., 0.0165907, 1},
  {FlowType::forced, BoundaryType::interpolated, 11, 303, 0.016909, 0., 0.016009, 1},
  {FlowType::forced, BoundaryType::bouzidi, 11, 294, 0.019703, 0., 0.0232073, 1},
  {FlowType::nonForced, BoundaryType::bounceBack, 11, 621, 0.1284974, 0.40862686, 0.3209910, 1},
  {FlowType::nonForced, BoundaryType::local, 11,  570, 0.05043437, 0.10581659, 0.05099981, 1},
  {FlowType::nonForced, BoundaryType::interpolated, 11, 570, 0.04976679, 0.10483063, 0.04959827, 1},
  {FlowType::nonForced, BoundaryType::bouzidi, 11, 572, 0.056544195, 0.070186678, 0.088491618, 1},
  {FlowType::nonForced, BoundaryType::bouzidi, 21, 1400, 0.01624583, 0.024478267, 0.046465458, 1},
  {FlowType::nonForced, BoundaryType::bouzidi, 41, 4077, 0.00445271, 0.00583554, 0.02117142, 2}
};

class Poiseuille3DTest : public ::testing::TestWithParam<TestParam> {

};

// Stores geometry information in form of material numbers
template<typename DESCRIPTOR>
void prepareGeometry( UnitConverter<T,DESCRIPTOR> const& converter,
                      SuperGeometry<T,3>& superGeometry, const TestParam& param)
{

  Vector<T, 3> C0(-converter.getPhysDeltaX() * 0.2, r, r);
  Vector<T, 3> C1(lx, r, r);
  if (param.flowType == FlowType::forced) {
    C0[0] -= 3.*converter.getPhysDeltaX();
    C1[0] += 3.*converter.getPhysDeltaX();
  }
  IndicatorCylinder3D<T> pipe(C0, C1, r);

  superGeometry.rename(0, 2);

  superGeometry.rename(2, 1, pipe);

  if (param.flowType == FlowType::nonForced) {
    Vector<T, 3> origin(0, r, r);
    Vector<T, 3> extend = origin;

    // Set material number for inflow
    origin[0] = -converter.getPhysDeltaX() * 2;
    extend[0] = converter.getPhysDeltaX() * 2;
    IndicatorCylinder3D<T> inflow(origin, extend, r);
    superGeometry.rename(2, 3, 1, inflow);

    // Set material number for outflow
    origin[0] = lx - 2 * converter.getPhysDeltaX();
    extend[0] = lx + 2 * converter.getPhysDeltaX();
    IndicatorCylinder3D<T> outflow(extend, origin, r);
    superGeometry.rename(2, 4, 1, outflow);
  }

  // Removes all not needed boundary voxels outside the surface
  superGeometry.clean(false);
  // Removes all not needed boundary voxels inside the surface
  superGeometry.innerClean(false);
  superGeometry.checkForErrors(false);
}

// Set up the geometry of the simulation
template<typename DESCRIPTOR>
void prepareLattice(SuperLattice<T, DESCRIPTOR>& sLattice,
                    UnitConverter<T, DESCRIPTOR>const& converter,
                    SuperGeometry<T,3>& superGeometry, const TestParam& param )
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

  Vector<T, 3> C0(0, r, r);
  Vector<T, 3> C1(lx, r, r);

  std::vector<T> origin = { lx, r, r};
  std::vector<T> axis = { 1, 0, 0 };

  CirclePoiseuille3D<T> poiseuilleU(origin, axis, converter.getCharLatticeVelocity(), r);

  if (param.boundaryType == BoundaryType::bounceBack) {
    sLattice.template defineDynamics<BounceBack>(superGeometry, 2);
  }
  else if (param.boundaryType == BoundaryType::bouzidi) {
    sLattice.template defineDynamics<NoDynamics>(superGeometry, 2);

    C0[0] -= 0.5*converter.getPhysDeltaX();
    C1[0] += 0.5*converter.getPhysDeltaX();
    if (param.flowType == FlowType::forced) {
      C0[0] -= 3.*converter.getPhysDeltaX();
      C1[0] += 3.*converter.getPhysDeltaX();
    }
    IndicatorCylinder3D<T> pipe(C0, C1, r);
    setBouzidiBoundary<T,DESCRIPTOR>(sLattice, superGeometry, 2, pipe);
  }
  else {
    if (param.flowType == FlowType::forced) {
      sLattice.template defineDynamics<ForcedBGKdynamics>(superGeometry, 2);
    } else {
      sLattice.template defineDynamics<BGKdynamics>(superGeometry, 2);
    }
    if (param.boundaryType == BoundaryType::local) {
      boundary::set<boundary::LocalVelocity>(sLattice, superGeometry, 2);
    }
    else {
      boundary::set<boundary::InterpolatedVelocity>(sLattice, superGeometry, 2);
    }
  }

  if (param.flowType == FlowType::nonForced) {
    if (param.boundaryType == BoundaryType::bouzidi) {
      sLattice.template defineDynamics<NoDynamics>(superGeometry, 3);
      IndicatorCylinder3D<T> pipe(C0, C1, r);
      setBouzidiBoundary<T,DESCRIPTOR,BouzidiVelocityPostProcessor>(sLattice, superGeometry, 3, pipe);
      setBouzidiVelocity<T,DESCRIPTOR>(sLattice, superGeometry, 3, poiseuilleU);
    }
    else {
      // Material=3 -->bulk dynamics
      if (param.flowType == FlowType::forced) {
        sLattice.template defineDynamics<ForcedBGKdynamics>(superGeometry, 3);
      } else {
        sLattice.template defineDynamics<BGKdynamics>(superGeometry, 3);
      }
      if (param.boundaryType == BoundaryType::local) {
        boundary::set<boundary::LocalVelocity>(sLattice, superGeometry, 3);
      }
      else {
        boundary::set<boundary::InterpolatedVelocity>(sLattice, superGeometry, 3);
      }
    }
    // Material=4 -->bulk dynamics
    if (param.flowType == FlowType::forced) {
      sLattice.template defineDynamics<ForcedBGKdynamics>(superGeometry, 4);
    } else {
      sLattice.template defineDynamics<BGKdynamics>(superGeometry, 4);
    }
    if (param.boundaryType == BoundaryType::local) {
      boundary::set<boundary::LocalPressure>(sLattice, superGeometry, 4);
    }
    else {
      boundary::set<boundary::InterpolatedPressure>(sLattice, superGeometry, 4);
    }
  }

  if (param.flowType == FlowType::forced) {
    // Initial conditions
    T D = converter.getLatticeLength(d);

    std::vector<T> poiseuilleForce(3, T());
    poiseuilleForce[0] = 4. * converter.getLatticeViscosity() * converter.getCharLatticeVelocity() / (D * D / 4. );
    AnalyticalConst3D<T,T> force( poiseuilleForce );

    // Initialize force
    sLattice.template defineField<descriptors::FORCE>( superGeometry, 1, force );
    sLattice.template defineField<descriptors::FORCE>( superGeometry, 2, force );

    AnalyticalConst3D<T, T> rhoF(1);

    sLattice.defineRhoU(superGeometry, 1, rhoF, poiseuilleU);
    sLattice.iniEquilibrium(superGeometry, 1, rhoF, poiseuilleU);
    sLattice.defineRhoU(superGeometry, 2, rhoF, poiseuilleU);
    sLattice.iniEquilibrium(superGeometry, 2, rhoF, poiseuilleU);
  }
  else {
    // Initial conditions
    T p0 = 4. * converter.getPhysViscosity() * converter.getCharPhysVelocity() * lx / (r * r);

    p0 = converter.getLatticePressure(p0);
    AnalyticalLinear3D<T, T> rho(-p0 / lx * descriptors::invCs2<T,DESCRIPTOR>(), 0, 0, p0 * descriptors::invCs2<T,DESCRIPTOR>() + 1);

    std::vector<T> velocity(3, T());
    AnalyticalConst3D<T, T> uF(velocity);

    // Initialize all values of distribution functions to their local equilibrium
    sLattice.defineRhoU(superGeometry, 0, rho, uF);
    sLattice.iniEquilibrium(superGeometry, 0, rho, uF);
    sLattice.defineRhoU(superGeometry, 1, rho, poiseuilleU);
    sLattice.iniEquilibrium(superGeometry, 1, rho, poiseuilleU);
    sLattice.defineRhoU(superGeometry, 2, rho, poiseuilleU);
    sLattice.iniEquilibrium(superGeometry, 2, rho, poiseuilleU);
    sLattice.defineRhoU(superGeometry, 3, rho, poiseuilleU);
    sLattice.iniEquilibrium(superGeometry, 3, rho, poiseuilleU);
    sLattice.defineRhoU(superGeometry, 4, rho, poiseuilleU);
    sLattice.iniEquilibrium(superGeometry, 4, rho, poiseuilleU);
  }

  sLattice.template setParameter<descriptors::OMEGA>(omega);

  sLattice.initialize();
}

// Compute error norms
template<typename DESCRIPTOR>
void error( SuperGeometry<T,3>& superGeometry,
            SuperLattice<T, DESCRIPTOR>& sLattice,
            UnitConverter<T,DESCRIPTOR> const& converter,
            const TestParam& param)
{

  int tmp[]= {int()};
  T result[2]= {T(),T()}, result_tmp[2]= {T(),T()};

  // velocity error
  const T maxVelocity = converter.getCharPhysVelocity();
  std::vector<T> axisPoint = {lx, r, r};
  std::vector<T> axisDirection = { 1, 0, 0 };
  CirclePoiseuille3D<T> uSol(axisPoint, axisDirection, maxVelocity, r);
  SuperLatticePhysVelocity3D<T,DESCRIPTOR> u( sLattice,converter );
  SuperLatticeFfromAnalyticalF3D<T,DESCRIPTOR> uSolLattice( uSol,sLattice );

  SuperL2Norm3D<T> uL2Norm( uSolLattice-u,superGeometry,1 );
  SuperL2Norm3D<T> uSolL2Norm( uSolLattice,superGeometry,1 );
  uL2Norm( result,tmp );
  uSolL2Norm( result_tmp,tmp );
  T velocityErrorL2 = result[0] / result_tmp[0];
  EXPECT_NEAR(velocityErrorL2, param.velocityErrorL2, param.errorFactor * 1e-6);

  // strainRate error
  CirclePoiseuilleStrainRate3D<T, DESCRIPTOR> sSol( converter, r );
  SuperLatticePhysStrainRate3D<T,DESCRIPTOR> s( sLattice,converter );
  SuperLatticeFfromAnalyticalF3D<T,DESCRIPTOR> sSolLattice( sSol,sLattice );

  SuperL2Norm3D<T> sL2Norm( sSolLattice-s,superGeometry,1 );
  SuperL2Norm3D<T> sSolL2Norm( sSolLattice,superGeometry,1 );
  sL2Norm( result,tmp );
  sSolL2Norm( result_tmp,tmp );
  T strainErrorL2 = result[0] / result_tmp[0];
  EXPECT_NEAR(strainErrorL2, param.strainErrorL2, param.errorFactor * 1e-6);

  if (param.flowType == FlowType::nonForced) {
    // pressure error
    T p0 = 4. * converter.getPhysViscosity() * maxVelocity * lx / (r * r);
    AnalyticalLinear3D<T, T> pressureSol(-p0 / lx, 0, 0, p0);
    SuperLatticePhysPressure3D<T, DESCRIPTOR> pressure(sLattice, converter);
    SuperLatticeFfromAnalyticalF3D<T, DESCRIPTOR> pressureSolLattice(pressureSol, sLattice);
    SuperL2Norm3D<T> pressureL2Norm( pressureSolLattice-pressure,superGeometry,1 );
    SuperL2Norm3D<T> pressureSolL2Norm( pressureSolLattice,superGeometry,1 );
    pressureL2Norm( result,tmp );
    pressureSolL2Norm( result_tmp,tmp );
    T pressureErrorL2 = result[0] / result_tmp[0];
    EXPECT_NEAR(pressureErrorL2, param.pressureErrorL2, param.errorFactor * 1e-6);

  }
}

TEST_P(Poiseuille3DTest, testBGK)
{

  // === 1st Step: Initialization ===
  TestParam param = GetParam();

  UnitConverterFromResolutionAndRelaxationTime<T, DESCRIPTOR> const converter(
    param.N,     // resolution: number of voxels per charPhysL
    (T)   0.8,   // latticeRelaxationTime: relaxation time, have to be greater than 0.5!
    (T)   1,     // charPhysLength: reference length of simulation geometry
    (T)   1,     // charPhysVelocity: maximal/highest expected velocity during simulation in __m / s__
    (T)   1./Re, // physViscosity: physical kinematic viscosity in __m^2 / s__
    (T)   1.0    // physDensity: physical density in __kg / m^3__
  );

  // === 2nd Step: Prepare Geometry ===
  Vector<T, 3> C0(0, r, r);
  Vector<T, 3> C1(lx, r, r);
  IndicatorCylinder3D<T> pipe(C0, C1, r);
  IndicatorLayer3D<T> extendedDomain(pipe, converter.getPhysDeltaX());

  //initiatization of the first lattice, running the simulation up to the halfpoint and saving data
  {
    // Instantiation of a cuboidDecomposition with weights
    CuboidDecomposition3D<T> cuboidDecomposition(extendedDomain, converter.getPhysDeltaX(), 1);

    if (param.flowType == FlowType::forced) {
      // Periodic boundaries in x-direction
      cuboidDecomposition.setPeriodicity({ true, false, false });
    }

    // Instantiation of a loadBalancer
    HeuristicLoadBalancer<T> loadBalancer( cuboidDecomposition );

    // Instantiation of a superGeometry
    SuperGeometry<T,3> superGeometry( cuboidDecomposition, loadBalancer, 2 );

    prepareGeometry<DESCRIPTOR>( converter, superGeometry, param );

    // === 3rd Step: Prepare Lattice ===
    SuperLattice<T, DESCRIPTOR> sLattice( converter, superGeometry );


    // choose boundary condition and prepare lattice
    prepareLattice<DESCRIPTOR>( sLattice, converter, superGeometry, param );

    // === 4th Step: Main Loop ===
    util::ValueTracer<T> converge( converter.getLatticeTime( physInterval ), residuum );

    int iT;
    for ( iT = 0; iT < param.iT / 2; ++iT ) {
      sLattice.collideAndStream();

      converge.takeValue( sLattice.getStatistics().getAverageEnergy(), false );
    }

    EXPECT_EQ(iT, param.iT/2);

    sLattice.save("SerializationTest3D");
  }

  //initialization of the second lattice, loading data of the first lattice and continuing the simulation
  {
    // Instantiation of a cuboidDecomposition with weights
    CuboidDecomposition3D<T> cuboidDecomposition(extendedDomain, converter.getPhysDeltaX(), 1);

    if (param.flowType == FlowType::forced) {
      // Periodic boundaries in x-direction
      cuboidDecomposition.setPeriodicity({ true, false, false });
    }

    // Instantiation of a loadBalancer
    HeuristicLoadBalancer<T> loadBalancer( cuboidDecomposition );

    // Instantiation of a superGeometry
    SuperGeometry<T,3> superGeometry( cuboidDecomposition, loadBalancer, 2 );

    prepareGeometry<DESCRIPTOR>( converter, superGeometry, param );

    // === 3rd Step: Prepare Lattice ===
    SuperLattice<T, DESCRIPTOR> sLattice( converter, superGeometry );

    // choose boundary condition and prepare lattice
    prepareLattice<DESCRIPTOR>( sLattice, converter, superGeometry, param );

    sLattice.load("SerializationTest3D");

    // === 4th Step: Main Loop ===
    util::ValueTracer<T> converge( converter.getLatticeTime( physInterval ), residuum );

    int iT;
    for ( iT = param.iT / 2; iT < converter.getLatticeTime( maxPhysT ); ++iT ) {
      if ( converge.hasConverged() ) {
        break;
      }

      sLattice.collideAndStream();

      converge.takeValue( sLattice.getStatistics().getAverageEnergy(), false );
    }

    EXPECT_EQ(iT, param.iT);
    error<DESCRIPTOR>(superGeometry, sLattice, converter, param);
  }

}

INSTANTIATE_TEST_CASE_P(BGKPoiseuille, Poiseuille3DTest,
                        testing::ValuesIn(bgkParams));
