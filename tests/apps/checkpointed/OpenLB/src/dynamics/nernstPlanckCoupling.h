/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Fedor Bukreev, Adrian Kummerlaender
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

#ifndef DYNAMICS_NERNST_PLANCK_COUPLING_H
#define DYNAMICS_NERNST_PLANCK_COUPLING_H

#include "core/operator.h"
#include "utilities/physHelpers.h"

namespace olb {

/// Poisson-Nernst-Planck coupling
struct PNPCoupling {
  static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;

  struct DX : public descriptors::FIELD_BASE<1> { };
  struct NPVELCOEFF : public descriptors::FIELD_BASE<1> { };
  struct POISSONCOEFF : public descriptors::FIELD_BASE<1> { };
  struct OMEGA : public descriptors::FIELD_BASE<1> { };

  using parameters = meta::list<DX,NPVELCOEFF,POISSONCOEFF,OMEGA>;

  template <typename CELLS, typename PARAMETERS>
  void apply(CELLS& cells, PARAMETERS& parameters) any_platform {
    using V = typename CELLS::template value_t<names::Concentration0>::value_t;
    using DESCRIPTOR = typename CELLS::template value_t<names::Concentration0>::descriptor_t;

    V dX = parameters.template get<DX>();
    V velCoeff = parameters.template get<NPVELCOEFF>();
    V poissonCoeff = parameters.template get<POISSONCOEFF>();
    V omega = parameters.template get<OMEGA>();

    auto& cellNP = cells.template get<names::Concentration0>();
    auto& cellP = cells.template get<names::Concentration1>();
    auto& cellNP2 = cells.template get<names::Concentration2>();

    V dxPsi = 0.;
    V dyPsi = 0.;
    V dzPsi = 0.;

    for(int iPop = 0; iPop < DESCRIPTOR::q; iPop++){
      dxPsi += descriptors::c<DESCRIPTOR>(iPop, 0) * cellP[iPop];
      dyPsi += descriptors::c<DESCRIPTOR>(iPop, 1) * cellP[iPop];
      dzPsi += descriptors::c<DESCRIPTOR>(iPop, 2) * cellP[iPop];
    }

    dxPsi *= (-1.*omega*descriptors::invCs2<V,DESCRIPTOR>()/dX);
    dyPsi *= (-1.*omega*descriptors::invCs2<V,DESCRIPTOR>()/dX);
    dzPsi *= (-1.*omega*descriptors::invCs2<V,DESCRIPTOR>()/dX);

    V vel[3] ={0.};
    vel[0] -= velCoeff * dxPsi;
    vel[1] -= velCoeff * dyPsi;
    vel[2] -= velCoeff * dzPsi;
    cellNP.template setField<descriptors::VELOCITY>(vel);

    V vel2[3] ={0.};
    vel2[0] += velCoeff * dxPsi;
    vel2[1] += velCoeff * dyPsi;
    vel2[2] += velCoeff * dzPsi;
    cellNP2.template setField<descriptors::VELOCITY>(vel2);

    V concentration = cellNP.computeRho();
    if(util::abs(concentration) > 1.){ concentration = 0.; }
    V concentration2 = cellNP2.computeRho();
    if(util::abs(concentration2) > 1.){ concentration2 = 0.; }
    V poissonSource = poissonCoeff * (concentration - concentration2);
    cellP.template setField<descriptors::SOURCE>(poissonSource);
  }
};

/// Naver-Stokes-Poisson-Nernst-Planck coupling
struct NSPNPCoupling {
  static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;

  struct DX : public descriptors::FIELD_BASE<1> { };
  struct NPVELCOEFF : public descriptors::FIELD_BASE<1> { };
  struct POISSONCOEFF : public descriptors::FIELD_BASE<1> { };
  struct FORCECOEFF : public descriptors::FIELD_BASE<1> { };
  struct DTADE : public descriptors::FIELD_BASE<1> { };
  struct DTNSE : public descriptors::FIELD_BASE<1> { };
  struct OMEGA : public descriptors::FIELD_BASE<1> { };

  using parameters = meta::list<DX,NPVELCOEFF,POISSONCOEFF,FORCECOEFF,DTADE,DTNSE,OMEGA>;

  template <typename CELLS, typename PARAMETERS>
  void apply(CELLS& cells, PARAMETERS& parameters) any_platform {
    using V = typename CELLS::template value_t<names::Concentration0>::value_t;
    using DESCRIPTOR = typename CELLS::template value_t<names::Concentration0>::descriptor_t;

    V dX = parameters.template get<DX>();
    V velCoeff = parameters.template get<NPVELCOEFF>();
    V poissonCoeff = parameters.template get<POISSONCOEFF>();
    V forceCoeff = parameters.template get<FORCECOEFF>();
    V dtADE = parameters.template get<DTADE>();
    V dtNSE = parameters.template get<DTNSE>();
    V omega = parameters.template get<OMEGA>();

    auto& cellNP = cells.template get<names::Concentration0>();
    auto& cellNP2 = cells.template get<names::Concentration1>();
    auto& cellP = cells.template get<names::Temperature>();
    auto& cellNSE = cells.template get<names::NavierStokes>();

    V dxPsi = 0.;
    V dyPsi = 0.;
    V dzPsi = 0.;

    for(int iPop = 0; iPop < DESCRIPTOR::q; iPop++){
      dxPsi += descriptors::c<DESCRIPTOR>(iPop, 0) * cellP[iPop];
      dyPsi += descriptors::c<DESCRIPTOR>(iPop, 1) * cellP[iPop];
      dzPsi += descriptors::c<DESCRIPTOR>(iPop, 2) * cellP[iPop];
    }

    dxPsi *= (-1.*omega*descriptors::invCs2<V,DESCRIPTOR>()/dX);
    dyPsi *= (-1.*omega*descriptors::invCs2<V,DESCRIPTOR>()/dX);
    dzPsi *= (-1.*omega*descriptors::invCs2<V,DESCRIPTOR>()/dX);

    auto vel = cellNP.template getField<descriptors::VELOCITY>();
    cellNSE.computeU(vel.data());
    vel[0] *= dtADE / dtNSE;
    vel[1] *= dtADE / dtNSE;
    vel[2] *= dtADE / dtNSE;

    vel[0] -= velCoeff * dxPsi;
    vel[1] -= velCoeff * dyPsi;
    vel[2] -= velCoeff * dzPsi;
    cellNP.template setField<descriptors::VELOCITY>(vel);

    auto vel2 = cellNP2.template getField<descriptors::VELOCITY>();
    cellNSE.computeU(vel2.data());
    vel2[0] *= dtADE / dtNSE;
    vel2[1] *= dtADE / dtNSE;
    vel2[2] *= dtADE / dtNSE;

    vel2[0] += velCoeff * dxPsi;
    vel2[1] += velCoeff * dyPsi;
    vel2[2] += velCoeff * dzPsi;
    cellNP2.template setField<descriptors::VELOCITY>(vel2);

    V concentration = cellNP.computeRho();
    if(util::abs(concentration) > 1.e5){ concentration = 0.; }
    V concentration2 = cellNP2.computeRho();
    if(util::abs(concentration2) > 1.e5){ concentration2 = 0.; }
    V poissonSource = poissonCoeff * (concentration - concentration2);
    cellP.template setField<descriptors::SOURCE>(poissonSource);

    auto force = cellNSE.template getField<descriptors::FORCE>();
    force = {0.,0.,0.};
    force[0] = forceCoeff * (concentration - concentration2);
    //force[1] = -forceCoeff * (concentration - concentration2) * dyPsi;
    //force[2] = -forceCoeff * (concentration - concentration2) * dzPsi;
    cellNSE.template setField<descriptors::FORCE>(force);
  }
};

struct NSPNPCrystalDynamicCoupling {
  static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;

  struct DX : public descriptors::FIELD_BASE<1> { };
  struct VALENCEH : public descriptors::FIELD_BASE<1> { };
  struct VALENCEP : public descriptors::FIELD_BASE<1> { };
  struct VALENCEC : public descriptors::FIELD_BASE<1> { };
  struct NPVELCOEFFH : public descriptors::FIELD_BASE<1> { };
  struct NPVELCOEFFP : public descriptors::FIELD_BASE<1> { };
  struct NPVELCOEFFC : public descriptors::FIELD_BASE<1> { };
  struct POISSONCOEFF : public descriptors::FIELD_BASE<1> { };
  struct FORCECOEFF : public descriptors::FIELD_BASE<1> { };
  struct DTADE : public descriptors::FIELD_BASE<1> { };
  struct DTNSE : public descriptors::FIELD_BASE<1> { };
  struct OMEGA : public descriptors::FIELD_BASE<1> { };
  struct TAUNSE : public descriptors::FIELD_BASE<1> { };
  struct CRYSTCOEFF : public descriptors::FIELD_BASE<1> { };
  struct CRYSTORDER : public descriptors::FIELD_BASE<1> { };
  struct EQCONST : public descriptors::FIELD_BASE<1> { };
  struct CRYSTMOLARMASS : public descriptors::FIELD_BASE<1> { };
  struct CRYSTDENSITY : public descriptors::FIELD_BASE<1> { };
  struct DESORPCOEFF : public descriptors::FIELD_BASE<1> { };
  struct DESORPEQ : public descriptors::FIELD_BASE<1> { };
  struct CMASS : public descriptors::FIELD_BASE<1> { };
  struct A_ACTIVITY : public descriptors::FIELD_BASE<1> { };
  struct B_ACTIVITY : public descriptors::FIELD_BASE<1> { };
  struct ADIST_ACTIVITY : public descriptors::FIELD_BASE<1> { };
  struct A_NUCL : public descriptors::FIELD_BASE<1> { };
  struct MOLECVOL : public descriptors::FIELD_BASE<1> { };
  struct TEMPERATURE : public descriptors::FIELD_BASE<1> { };

  using parameters = meta::list<DX,VALENCEH,VALENCEP,VALENCEC,NPVELCOEFFH,NPVELCOEFFP,NPVELCOEFFC,POISSONCOEFF,FORCECOEFF,DTADE,DTNSE,OMEGA,TAUNSE,CRYSTCOEFF,CRYSTORDER,EQCONST,CRYSTMOLARMASS,CRYSTDENSITY,DESORPCOEFF,DESORPEQ,CMASS,A_ACTIVITY,B_ACTIVITY,ADIST_ACTIVITY,A_NUCL,MOLECVOL,TEMPERATURE>;

  template <typename CELLS, typename PARAMETERS>
  void apply(CELLS& cells, PARAMETERS& parameters) any_platform {
    using V = typename CELLS::template value_t<names::NavierStokes>::value_t;
    using DESCRIPTOR = typename CELLS::template value_t<names::Concentration0>::descriptor_t;
    using DESCRIPTORNSE = typename CELLS::template value_t<names::NavierStokes>::descriptor_t;

    V dX = parameters.template get<DX>();
    V valenceH = parameters.template get<VALENCEH>();
    V valencePO4 = parameters.template get<VALENCEP>();
    V valenceCa = parameters.template get<VALENCEC>();
    V velCoeffH = parameters.template get<NPVELCOEFFH>();
    V velCoeffPO4 = parameters.template get<NPVELCOEFFP>();
    V velCoeffCa = parameters.template get<NPVELCOEFFC>();
    V poissonCoeff = parameters.template get<POISSONCOEFF>();
    V forceCoeff = parameters.template get<FORCECOEFF>();
    V dtADE = parameters.template get<DTADE>();
    V dtNSE = parameters.template get<DTNSE>();
    V omega = parameters.template get<OMEGA>();
    V tauNSE = parameters.template get<TAUNSE>();
    V crystCoeff = parameters.template get<CRYSTCOEFF>();
    V crystOrder = parameters.template get<CRYSTORDER>();
    V eqConst = parameters.template get<EQCONST>();
    V crystMolarMass = parameters.template get<CRYSTMOLARMASS>();
    V crystDensity = parameters.template get<CRYSTDENSITY>();
    V cMass = parameters.template get<CMASS>();

    //activity coeffs
    V A = parameters.template get<A_ACTIVITY>();
    V B = parameters.template get<B_ACTIVITY>();
    V aDist = parameters.template get<ADIST_ACTIVITY>();

    //nucleation params
    V Acoeff = parameters.template get<A_NUCL>();
    V molecVol = parameters.template get<MOLECVOL>();
    V temperature = parameters.template get<TEMPERATURE>();
    V kBoltzmann = physConstants::boltzmannConstant<V>();

    auto& cellH = cells.template get<names::Concentration0>();
    auto& cellPO4 = cells.template get<names::Concentration1>();
    auto& cellCa = cells.template get<names::Concentration2>();
    auto& cellPoisson = cells.template get<names::Temperature>();
    auto& cellNSE = cells.template get<names::NavierStokes>();

    // calculation of the potential gradient
    Vector<V,DESCRIPTOR::d> dPsi;
    for (int iPop = 1; iPop < DESCRIPTOR::q; iPop++) {
      dPsi += descriptors::c<DESCRIPTOR>(iPop) * cellPoisson[iPop];
    }
    dPsi *= (V(-1)*omega*descriptors::invCs2<V,DESCRIPTOR>()/dX);

    // calculation of the electric velocities for each ion group
    auto nseU = cellNSE.template getField<descriptors::MOMENTA_VELOCITY>();
    {
      auto vel = nseU;
      vel *= dtADE / dtNSE;
      vel -= valenceH * velCoeffH * dPsi;
      cellH.template setField<descriptors::VELOCITY>(vel);
    }

    {
      auto vel2 = nseU;
      vel2 *= dtADE / dtNSE;
      vel2 -= valencePO4 * velCoeffPO4 * dPsi;
      cellPO4.template setField<descriptors::VELOCITY>(vel2);
    }

    {
      auto velCa = nseU;
      velCa *= dtADE / dtNSE;
      velCa -= valenceCa * velCoeffCa * dPsi;
      cellCa.template setField<descriptors::VELOCITY>(velCa);
    }

    // calculation of the source term for the Poisson equation
    V concentrationH = cellH.template getField<descriptors::MOMENTA_DENSITY>();
    if (concentrationH > V(1.e5) || concentrationH < V(0)) { concentrationH = V(0); }
    //V concentrationPO4 = cellPO4.computeRho();
    V concentrationPO4 = cellPO4.template getField<descriptors::MOMENTA_DENSITY>();
    if (concentrationPO4 > V(1.e5) || concentrationPO4 < V(0)) { concentrationPO4 = V(0); }
    //V concentrationCa = cellCa.computeRho();
    V concentrationCa = cellCa.template getField<descriptors::MOMENTA_DENSITY>();
    if (concentrationCa > V(1.e5) || concentrationCa < V(0)) { concentrationCa = V(0); }
    V poissonSource = poissonCoeff * (valenceH * concentrationH + valencePO4 * concentrationPO4 + valenceCa * concentrationCa);
    cellPoisson.template setField<descriptors::SOURCE>(poissonSource);

    // calculation of the electrical driving force for the carrier fluid
    auto force = -forceCoeff * (valenceH * concentrationH + valencePO4 * concentrationPO4 + valenceCa * concentrationCa) * dPsi;
    cellNSE.template setField<descriptors::FORCE>(force);

    // search for boundary cells and computation of the normal for surface tension
    auto surfaceFraction = cellCa.template getFieldPointer<descriptors::CRYSTLAYER>();
    bool isBoundaryCell = false;
    auto normal = cellCa.template getFieldPointer<descriptors::NORMAL>();
    if(surfaceFraction[0] < V(1)) {
      for(int iPop = 1; iPop < DESCRIPTOR::q; iPop++){
        V porNext = cellCa.neighbor(descriptors::c<DESCRIPTOR>(iPop)).template getField<descriptors::CRYSTLAYER>();
        if(porNext >= V(1)){
          isBoundaryCell = true;
          normal += descriptors::c<DESCRIPTOR>(iPop);
        }
      }
    }
    V normalNorm = util::sqrt(normal[0]*normal[0] + normal[1]*normal[1] + normal[2]*normal[2]);
    if(normalNorm != V(0)) {
      normal /= normalNorm;
    }
    cellNSE.template setField<descriptors::NORMAL>(normal);

    if (isBoundaryCell) {
      // computation of ion activity coeffs
      V reactionRate = V(0);
      V desorpRate = V(0);
      V sqrtIonicStrength = util::sqrt(V(0.5) * (concentrationH*valenceH*valenceH + concentrationPO4*valencePO4*valencePO4 + concentrationCa*valenceCa*valenceCa));
      V gamma = util::pow(V(10),V(-1)*A*valencePO4*valencePO4*sqrtIonicStrength/(V(1)+B*aDist*sqrtIonicStrength));
      V gammaWater = util::pow(V(10),V(-1)*A*valenceH*valenceH*sqrtIonicStrength/(V(1)+B*aDist*sqrtIonicStrength));
      V gammaCa = util::pow(V(10),V(-1)*A*valenceCa*valenceCa*sqrtIonicStrength/(V(1)+B*aDist*sqrtIonicStrength));
      V solubility = util::pow(util::pow(concentrationH*gammaWater,V(2))*util::pow(concentrationPO4*gamma,V(6))*util::pow(concentrationCa*gammaCa, V(8))/eqConst, double(1./16.));
      cellCa.template setField<descriptors::SOLUBILITY>(solubility);

      if(solubility > V(1)){
        auto nucleation = cellCa.template getFieldPointer<descriptors::NUCL>();

        // computation of the surface tension
        V rhoNSE = cellNSE.template getField<descriptors::MOMENTA_DENSITY>();
        auto uNSE = cellNSE.template getField<descriptors::MOMENTA_VELOCITY>();
        V uSqr = util::sqrt(uNSE[0]*uNSE[0] + uNSE[1]*uNSE[1] + uNSE[2]*uNSE[2]);
        V pXX = V(0); V pYY = V(0); V pZZ = V(0);
        for (int i = 0; i<DESCRIPTORNSE::q; i++){
          pXX += V(-1)*(V(1) - V(0.5)/tauNSE)*descriptors::c<DESCRIPTORNSE>(i, 0) * descriptors::c<DESCRIPTORNSE>(i, 0) * (cellNSE[i] - equilibrium<DESCRIPTORNSE>::secondOrder(i,rhoNSE,uNSE,uSqr));
          pYY += V(-1)*(V(1) - V(0.5)/tauNSE)*descriptors::c<DESCRIPTORNSE>(i, 1) * descriptors::c<DESCRIPTORNSE>(i, 1) * (cellNSE[i] - equilibrium<DESCRIPTORNSE>::secondOrder(i,rhoNSE,uNSE,uSqr));
          pZZ += V(-1)*(V(1) - V(0.5)/tauNSE)*descriptors::c<DESCRIPTORNSE>(i, 2) * descriptors::c<DESCRIPTORNSE>(i, 2) * (cellNSE[i] - equilibrium<DESCRIPTORNSE>::secondOrder(i,rhoNSE,uNSE,uSqr));
        }
        V surfTension = V(0);
        V num = util::sqrt(normal[0]*normal[0]) + util::sqrt(normal[1]*normal[1]) + util::sqrt(normal[2]*normal[2]);
        surfTension += util::sqrt(normal[0]*normal[0])*(pXX - V(0.5)*(pYY + pZZ));
        surfTension += util::sqrt(normal[1]*normal[1])*(pYY - V(0.5)*(pXX + pZZ));
        surfTension += util::sqrt(normal[2]*normal[2])*(pZZ - V(0.5)*(pYY + pXX));
        if(num != V(0)) surfTension /= num;
        surfTension *= cMass*dX*dX*dX/dtNSE/dtNSE;

        nucleation[0] += isBoundaryCell*Acoeff*dtADE*util::exp(V(-16)*V(3.14)*util::pow(surfTension,V(3))*util::pow(molecVol,V(2))/(V(3)*kBoltzmann*temperature*util::pow(kBoltzmann*temperature*util::log(solubility),V(2))));
         if (nucleation[0] >= V(1)/dX/dX/dX){
          reactionRate = crystCoeff / dX * util::pow( (solubility - V(1)), crystOrder );
          if(V(8)*reactionRate > concentrationCa) reactionRate = V(0);
        }

        V vCrystDt = reactionRate * crystMolarMass / crystDensity;
        surfaceFraction[0] = util::min(surfaceFraction[0] += vCrystDt, V(1));
        cellH.template setField<descriptors::CRYSTLAYER>(surfaceFraction[0]);
        cellPO4.template setField<descriptors::CRYSTLAYER>(surfaceFraction[0]);
        cellNSE.template setField<descriptors::CRYSTLAYER>(surfaceFraction[0]);
      }

      // calculation of the Ca desorption rate
      V desorpCoeff = parameters.template get<DESORPCOEFF>();
      V desorpEq = parameters.template get<DESORPEQ>();
      V dissolubility = V(0);
      if( concentrationH > V(1.e-9) && surfaceFraction[0] < V(0.5) ){
        dissolubility = util::pow(concentrationCa*gammaCa, V(0.83))*util::pow(concentrationH*gammaWater, V(-1.66))/desorpEq;
        desorpRate = util::max(V(0), (V(1)-util::pow(surfaceFraction[0],V(2./3.)))*desorpCoeff/dX * (V(1) - dissolubility));
      }

      if (isBoundaryCell) {
        cellCa.template setField<descriptors::SOURCE>(V(0.83)*desorpRate - V(8)*reactionRate);
      }
      if (concentrationPO4 > V(6)*reactionRate && isBoundaryCell) {
        cellPO4.template setField<descriptors::SOURCE>(V(-6)*reactionRate);
      }
      if (concentrationH > (V(1.66)*desorpRate + V(2)*reactionRate) && isBoundaryCell) {
        cellH.template setField<descriptors::SOURCE>(V(-1.66)*desorpRate - V(2)*reactionRate);
      }
    }
  }
};

}

#endif
