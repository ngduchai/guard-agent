/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Philipp Spelten
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

/* characteristicBoundaryDynamics.h
* Wissocq, Gauthier, Nicolas Gourdain, Orestis Malaspinas, und Alexandre Eyssartier. „Regularized Characteristic Boundary Conditions for the Lattice-Boltzmann Methods at High Reynolds Number Flows“. Journal of Computational Physics 331 (Februar 2017): 1–18. https://doi.org/10.1016/j.jcp.2016.11.037.
* Adaptation with Zou/He boundary conditions
*/

#ifndef CHARACTERISTIC_POSTPROCESSOR_PRE_COLLIDE_H
#define CHARACTERISTIC_POSTPROCESSOR_PRE_COLLIDE_H

#include <olb.h>

namespace olb {

namespace boundary {

template<typename DESCRIPTOR, int direction, int orientation, concepts::DynamicCell CELL, concepts::Parameters PARAMETERS, typename RHO, typename U>
requires(DESCRIPTOR::d == 3)
static void CharacteristicBoundaryLogicPreCollide(CELL& cell, PARAMETERS& parameters, RHO& rhoDt, U& uDt) any_platform {
  // ### SECOND PART ###
  // This PP is used in Stage::PreCollide for the "Computation of the physical values that must be imposed
  //   at t + 1 to avoid non-physical reflections by the CBC theory using either BL-LODI, CBC-2D or
  //   LS-LODI method. These values are stored to be used in the last step."
  // "last step" ==> see CharacteristicBoundaryLogicPostStream
  // This is non-local

  using V = typename CELL::value_t;
  const V rhoInfty = parameters.template get<descriptors::cbc::RHO_INFTY>();
  const auto uInfty = parameters.template get<descriptors::cbc::U_INFTY>();
  const V T1exact = V(0);  // spacial gradients in y and z considered 0, so T1 is 0
  V T1, T3, T4, T5;

  int normalUp[DESCRIPTOR::d](0),     normalDown[DESCRIPTOR::d](0);
  int normalFront[DESCRIPTOR::d](0),  normalBack[DESCRIPTOR::d](0);
  int normalFluid[DESCRIPTOR::d](0);
  normalFluid[direction] = -orientation;
  // set up which dimensions are implied by "upDown" and "frontBack" (rotating reference frame)
  constexpr int upDown =     (direction+1)%3;
  constexpr int frontBack =  (direction+2)%3;

  normalUp[upDown] = 1; normalDown[upDown] = -1;
  normalFront[frontBack] = 1; normalBack[frontBack] = -1;

  // === CALCULATE PARAMETERS CS, K1, K2 ===
  const V cs2=1./descriptors::invCs2<V,DESCRIPTOR>();
  const V cs=std::sqrt(cs2);
  const V Ma    = parameters.template get<descriptors::cbc::CBC_MA>();
  const V sigma = parameters.template get<descriptors::cbc::CBC_SIGMA>();
  const V L     = parameters.template get<descriptors::cbc::CBC_L>();
  const V K1 = sigma * ( V(1) - std::pow( Ma, V(2) ) ) * cs / L;
  const V K2 = Ma;
  const V dx = 1.;
  const V dy = 2.;
  const V dz = 2.;

  // === GET 1D NEIGHBORS ===
  CELL cellFluid  = cell.neighbor(normalFluid);
  V rhoFluid{}, rhoLocal{},
    uFluid[DESCRIPTOR::d]{}, uLocal[DESCRIPTOR::d]{},
    uDx[DESCRIPTOR::d]{};
  // === GET POST-COLLISION FIELDS ===
  cell.computeRhoU(rhoLocal, uLocal);
  cellFluid.computeRhoU(rhoFluid, uFluid);

  // === CALCULATE PRESSURE AND VELOCITY GRADIENT 1D ===
  V pLocal = cs2*rhoLocal;
  // V rhoDx = (rhoLocal-rhoFluid)/dx;  // will be used only for L2
  V pDx = cs2 * (rhoLocal - rhoFluid) / dx;
  for ( size_t dim=0; dim<DESCRIPTOR::d; dim++ ) {
    uDx[dim] = ( uLocal[dim] - uFluid[dim] ) / dx;
  }

  // === GET 2D NEIGHBORS ===
  V rhoUp{}, rhoUpUp{}, rhoDown{}, rhoDownDown{},
    uUp[DESCRIPTOR::d]{},   uUpUp[DESCRIPTOR::d]{},
    uDown[DESCRIPTOR::d]{}, uDownDown[DESCRIPTOR::d]{},
    pDy{}, uDy[DESCRIPTOR::d]{};
  CELL cellUp         = cell.neighbor(normalUp);
  CELL cellDown       = cell.neighbor(normalDown);
  CELL cellDownDown   = cell.neighbor(normalDown).neighbor(normalDown);
  CELL cellUpUp       = cell.neighbor(normalUp).neighbor(normalUp);
  const bool upCBC    = cellUp.template     getField<fields::cbc::IS_CBC>() == V(1);
  const bool downCBC  = cellDown.template   getField<fields::cbc::IS_CBC>() == V(1);

  // === GET POST-COLLISION FIELDS ===
  // === CALCULATE PRESSURE AND VELOCITY GRADIENT ===
  if ( upCBC && downCBC ) {
    cellUp.computeRhoU(   rhoUp,   uUp);
    cellDown.computeRhoU( rhoDown, uDown);
    // === CENTRAL DIFFERENCES ===
    pDy = cs2 * (rhoUp - rhoDown) / dy;
    for ( size_t dim=0; dim<DESCRIPTOR::d; dim++ ) {
      uDy[dim] = ( uUp[dim] - uDown[dim] ) / dy;
    }
  } else if ( downCBC ) {
    cellDown.computeRhoU( rhoDown, uDown);
    cellDownDown.computeRhoU( rhoDownDown,  uDownDown);
    // === 2nd ORDER FORWARD DIFFERENCES ===
    pDy = cs2 * ( V(3)*rhoLocal - V(4)*rhoDown + rhoDownDown ) / dy;
    for ( size_t dim=0; dim<DESCRIPTOR::d; dim++ ) {
      uDy[dim] = ( V(3)*uLocal[dim] - V(4)*uDown[dim] + uDownDown[dim] ) / dy;
    }
  } else if ( upCBC ) {
    cellUp.computeRhoU(   rhoUp,   uUp);
    cellUpUp.computeRhoU( rhoUpUp,  uUpUp);
    // === 2nd ORDER BACKWARD DIFFERENCES === (/-2)
    pDy = cs2 * ( V(3)*rhoLocal - V(4)*rhoUp + rhoUpUp) / V(-2);
    for ( size_t dim=0; dim<DESCRIPTOR::d; dim++ ) {
      uDy[dim] = ( V(3)*uLocal[dim] - V(4)*uUp[dim] + uUpUp[dim] ) / V(-2);
    }
  }

  // === GET 3D NEIGHBORS ===
  V rhoFront{}, rhoFrontFront{}, rhoBack{}, rhoBackBack{},
    uFront[DESCRIPTOR::d]{}, uFrontFront[DESCRIPTOR::d]{},
    uBack[DESCRIPTOR::d]{}, uBackBack[DESCRIPTOR::d]{},
    pDz{}, uDz[DESCRIPTOR::d]{};
  CELL cellFront      = cell.neighbor(normalFront);
  CELL cellBack       = cell.neighbor(normalBack);
  CELL cellBackBack   = cell.neighbor(normalBack).neighbor(normalBack);
  CELL cellFrontFront = cell.neighbor(normalFront).neighbor(normalFront);
  const bool frontCBC = cellFront.template  getField<fields::cbc::IS_CBC>() == V(1);
  const bool backCBC  = cellBack.template   getField<fields::cbc::IS_CBC>() == V(1);

  // === GET POST-COLLISION FIELDS ===
  // TODO: use fd::centralGradient() and fd::boundaryGradient()
  // === CALCULATE PRESSURE AND VELOCITY GRADIENT ===
  if ( frontCBC && backCBC ) {
    cellFront.computeRhoU(  rhoFront, uFront);
    cellBack.computeRhoU(   rhoBack,  uBack);
    // === CENTRAL DIFFERENCES ===
    pDz = cs2 * (rhoFront - rhoBack) / dz;
    for ( size_t dim=0; dim<DESCRIPTOR::d; dim++ ) {
      uDz[dim] = ( uFront[dim] - uBack[dim] ) / dz;
    }
  } else if ( backCBC ) {
    cellBack.computeRhoU(     rhoBack,      uBack);
    cellBackBack.computeRhoU( rhoBackBack,  uBackBack);
    // === 2nd ORDER FORWARD DIFFERENCES ===
    pDz = cs2 * ( V(3)*rhoLocal - V(4)*rhoBack + rhoBackBack) / dz;
    for ( size_t dim=0; dim<DESCRIPTOR::d; dim++ ) {
      uDz[dim] = ( V(3)*uLocal[dim] - V(4)*uBack[dim] + uBackBack[dim] ) / dz;
    }
  } else if ( frontCBC ) {
    cellFront.computeRhoU(      rhoFront,       uFront);
    cellFrontFront.computeRhoU( rhoFrontFront,  uFrontFront);
    // === 2nd ORDER BACKWARD DIFFERENCES (backwards by dividing by -2) ===
    pDz = cs2 * ( V(3)*rhoLocal - V(4)*rhoFront + rhoFrontFront) / V(-2);
    for ( size_t dim=0; dim<DESCRIPTOR::d; dim++ ) {
      uDz[dim] = ( V(3)*uLocal[dim] - V(4)*uFront[dim] + uFrontFront[dim] ) / V(-2);
    }
  }

  // === TRANSVERSAL WAVES ===
  T1 = - (uLocal[upDown] * pDy  + uLocal[frontBack] * pDz
          + pLocal * (uDy[upDown] + uDz[frontBack])
          - rhoLocal * cs * (uLocal[upDown] * uDy[direction] + uLocal[frontBack] * uDz[direction]));
  T3 = - (uLocal[upDown] * uDy[upDown] + uLocal[frontBack] * uDz[upDown]
            + pDy/(rhoLocal));
  T4 = - (uLocal[upDown] * uDy[frontBack]+ uLocal[frontBack] * uDz[frontBack]
            + pDz/(rhoLocal));
  T5 = - (uLocal[upDown] * pDy + uLocal[frontBack] * pDz
            + pLocal * (uDy[upDown] + uDz[frontBack])
            + rhoLocal * cs * (uLocal[upDown] * uDy[direction] + uLocal[frontBack] * uDz[direction]));

  // === LONGITUDINAL WAVES ===
  V L1, L3, L4, L5;
  if ( parameters.template get<descriptors::cbc::FLOW_DIRECTION>()   ==  direction
    && parameters.template get<descriptors::cbc::FLOW_ORIENTATION>() == -orientation ) {
    // === INFLOW CONDITION ===
    L1 = K1* ( ( cs2*rhoInfty - rhoInfty*cs*uInfty[direction] ) - (cs2*rhoLocal - rhoLocal*cs*uLocal[direction]) ) + T1;
    L3 = T3 + K1*(uInfty[upDown]    - uLocal[upDown]);
    L4 = T4 + K1*(uInfty[frontBack] - uLocal[frontBack]);
    L5 = T5;
  } else {
    // === OUTFLOW CONDITION ===
    // Wissoq: "CBC-2D relaxed"
    L1 = K1*cs2* (rhoLocal-rhoInfty) - K2* (T1-T1exact) + T1;
    L3 = uLocal[direction] * uDx[upDown];
    L4 = uLocal[direction] * uDx[frontBack];
    L5 = ( uLocal[direction] + cs ) * ( pDx + rhoLocal*cs*uDx[direction] );
  }

  // === EXPECTED TIME DERIVATIVES ===
  rhoDt           = ( T5+T1 - (L5+L1) ) / ( V(2)*cs2 );
  uDt[direction]  = ( T5-T1 - (L5-L1) ) / ( V(2)*rhoLocal*cs );
  uDt[upDown]     = T3-L3;
  uDt[frontBack]  = T4-L4;
}

template<typename T, typename DESCRIPTOR, int direction, int orientation>
class CBCPostProcessorPreCollideFlat3D {
public:
  static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;

  using parameters = meta::list<descriptors::cbc::CBC_K1, descriptors::cbc::CBC_K2, descriptors::cbc::CBC_L,
                                descriptors::cbc::CBC_MA, descriptors::cbc::CBC_SIGMA, descriptors::OMEGA,
                                descriptors::cbc::FLOW_DIRECTION, descriptors::cbc::FLOW_ORIENTATION,
                                descriptors::cbc::RHO_INFTY, descriptors::cbc::U_INFTY>;

  int getPriority() const {
    return 0;
  }

  template <concepts::DynamicCell CELL, concepts::Parameters PARAMETERS>
  void apply(CELL& cell, PARAMETERS& parameters) any_platform {

    using V = typename CELL::value_t;
    V rhoLocal, uLocal[DESCRIPTOR::d], rhoDt, uDt[DESCRIPTOR::d](0), rhoNew, uNew[DESCRIPTOR::d](0);
    cell.computeRhoU(rhoLocal, uLocal);

    CharacteristicBoundaryLogicPreCollide<DESCRIPTOR, direction, orientation, CELL, PARAMETERS>(cell, parameters, rhoDt, uDt);

    // === PRESCRIBED VALUES AT x,t+dt ===
    V prevRhoDt   = cell.template getField<fields::cbc::RHO_POST_PP_DT>();
    rhoNew        = rhoLocal + V(1.5)*rhoDt - V(.5)*prevRhoDt;
    auto prevUdt  = cell.template getField<fields::cbc::U_POST_PP_DT>();
    for (size_t iDim=0; iDim<DESCRIPTOR::d; iDim++) {
      uNew[iDim]  = uLocal[iDim] + V(1.5)*uDt[iDim] - V(.5)*prevUdt[iDim];
    }

    // === store calculated values ===
    cell.template setField<fields::cbc::RHO_POST_PP_DT>(rhoDt);
    cell.template setField<fields::cbc::U_POST_PP_DT>(uDt);
    cell.template setField<fields::cbc::RHO_POST_PP>(rhoNew);
    cell.template setField<fields::cbc::U_POST_PP>(uNew);
  };

};

template<typename T, typename DESCRIPTOR, int plane, int normal1, int normal2>
class CBCPostProcessorPreCollideEdge3D {
public:
  static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;

  using parameters = meta::list<descriptors::cbc::CBC_K1, descriptors::cbc::CBC_K2, descriptors::cbc::CBC_L,
                                descriptors::cbc::CBC_MA, descriptors::cbc::CBC_SIGMA, descriptors::OMEGA,
                                descriptors::cbc::FLOW_DIRECTION, descriptors::cbc::FLOW_ORIENTATION,
                                descriptors::cbc::RHO_INFTY, descriptors::cbc::U_INFTY>;

  int getPriority() const {
    return 0;
  }

  template <concepts::DynamicCell CELL, concepts::Parameters PARAMETERS>
  void apply(CELL& cell, PARAMETERS& parameters) any_platform {
    using V = typename CELL::value_t;
    V rhoLocal, uLocal[DESCRIPTOR::d], rhoNew, uNew[DESCRIPTOR::d](0);
    cell.computeRhoU(rhoLocal, uLocal);

    // Define the two normal directions based on the plane
    constexpr int direction1 = (plane+1)%3;
    constexpr int direction2 = (plane+2)%3;

    // Calculate updates for all three directions
    V rhoDt_1, rhoDt_2;
    V uDt_1[DESCRIPTOR::d], uDt_2[DESCRIPTOR::d];
    CharacteristicBoundaryLogicPreCollide<DESCRIPTOR, direction1, normal1, CELL, PARAMETERS>(cell, parameters, rhoDt_1, uDt_1);
    CharacteristicBoundaryLogicPreCollide<DESCRIPTOR, direction2, normal2, CELL, PARAMETERS>(cell, parameters, rhoDt_2, uDt_2);

    // Average the results
    V rhoDt_avg = (rhoDt_1 + rhoDt_2) / V(2);
    V uDt_avg[DESCRIPTOR::d];
    for(size_t i=0; i<DESCRIPTOR::d; ++i) {
      uDt_avg[i] = (uDt_1[i] + uDt_2[i]) / V(2);
    }

    // === PRESCRIBED VALUES AT x,t+dt ===
    V prevRhoDt   = cell.template getField<fields::cbc::RHO_POST_PP_DT>();
    rhoNew        = rhoLocal + V(1.5)*rhoDt_avg - V(.5)*prevRhoDt;
    auto prevUdt  = cell.template getField<fields::cbc::U_POST_PP_DT>();
    for (size_t iDim=0; iDim<DESCRIPTOR::d; iDim++) {
      uNew[iDim]  = uLocal[iDim] + V(1.5)*uDt_avg[iDim] - V(.5)*prevUdt[iDim];
    }

    // === store calculated values ===
    cell.template setField<fields::cbc::RHO_POST_PP_DT>(rhoDt_avg);
    cell.template setField<fields::cbc::U_POST_PP_DT>(uDt_avg);
    cell.template setField<fields::cbc::RHO_POST_PP>(rhoNew);
    cell.template setField<fields::cbc::U_POST_PP>(uNew);
  }
};

template<typename T, typename DESCRIPTOR, int xNormal, int yNormal, int zNormal>
class CBCPostProcessorPreCollideCorner3D {
public:
  static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;

  using parameters = meta::list<descriptors::cbc::CBC_K1, descriptors::cbc::CBC_K2, descriptors::cbc::CBC_L,
                                descriptors::cbc::CBC_MA, descriptors::cbc::CBC_SIGMA, descriptors::OMEGA,
                                descriptors::cbc::FLOW_DIRECTION, descriptors::cbc::FLOW_ORIENTATION,
                                descriptors::cbc::RHO_INFTY, descriptors::cbc::U_INFTY>;

  int getPriority() const {
    return 0;
  }

  template <concepts::DynamicCell CELL, concepts::Parameters PARAMETERS>
  void apply(CELL& cell, PARAMETERS& parameters) any_platform {
    using V = typename CELL::value_t;
    V rhoLocal, uLocal[DESCRIPTOR::d], rhoNew, uNew[DESCRIPTOR::d](0);
    cell.computeRhoU(rhoLocal, uLocal);

    // Calculate updates for all three directions
    V rhoDt_X, rhoDt_Y, rhoDt_Z;
    V uDt_X[DESCRIPTOR::d], uDt_Y[DESCRIPTOR::d], uDt_Z[DESCRIPTOR::d];
    CharacteristicBoundaryLogicPreCollide<DESCRIPTOR, 0, xNormal, CELL, PARAMETERS>(cell, parameters, rhoDt_X, uDt_X);
    CharacteristicBoundaryLogicPreCollide<DESCRIPTOR, 1, yNormal, CELL, PARAMETERS>(cell, parameters, rhoDt_Y, uDt_Y);
    CharacteristicBoundaryLogicPreCollide<DESCRIPTOR, 2, zNormal, CELL, PARAMETERS>(cell, parameters, rhoDt_Z, uDt_Z);

    // Average the results
    V rhoDt_avg = (rhoDt_X + rhoDt_Y + rhoDt_Z) / V(3);
    V uDt_avg[DESCRIPTOR::d];
    for(size_t i=0; i<DESCRIPTOR::d; ++i) {
      uDt_avg[i] = (uDt_X[i] + uDt_Y[i] + uDt_Z[i]) / V(3);
    }

    // === PRESCRIBED VALUES AT x,t+dt ===
    V prevRhoDt   = cell.template getField<fields::cbc::RHO_POST_PP_DT>();
    rhoNew        = rhoLocal + V(1.5)*rhoDt_avg - V(.5)*prevRhoDt;
    auto prevUdt  = cell.template getField<fields::cbc::U_POST_PP_DT>();
    for (size_t iDim=0; iDim<DESCRIPTOR::d; iDim++) {
      uNew[iDim]  = uLocal[iDim] + V(1.5)*uDt_avg[iDim] - V(.5)*prevUdt[iDim];
    }

    // === store calculated values ===
    cell.template setField<fields::cbc::RHO_POST_PP_DT>(rhoDt_avg);
    cell.template setField<fields::cbc::U_POST_PP_DT>(uDt_avg);
    cell.template setField<fields::cbc::RHO_POST_PP>(rhoNew);
    cell.template setField<fields::cbc::U_POST_PP>(uNew);
  }
};

} // namespace boundary
} // namespace olb
#endif // CHARACTERISTIC_POSTPROCESSOR_PRE_COLLIDE_H