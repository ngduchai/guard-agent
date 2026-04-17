/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Liam Sauterleute, Fedor Bukreev
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

#ifndef K_EPSILON_RANS_DYNAMICS_H
#define K_EPSILON_RANS_DYNAMICS_H

#include "core/operator.h"

namespace olb {


/// Coupling between Navier-Stokes and k-epsilon lattices for standard and RNG k-epsilon
/// https://www.cfd-online.com/Wiki/RNG_k-epsilon_model
template<typename T>
struct URANSKE{
  static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;

  struct USE_RNG_MODEL : public descriptors::TYPED_FIELD_BASE<int,1> { };
  struct VISC : public descriptors::FIELD_BASE<1> { };
  struct D_T : public descriptors::FIELD_BASE<1> { };
  struct D_X : public descriptors::FIELD_BASE<1> { };

  using parameters = meta::list<USE_RNG_MODEL,VISC,D_T,D_X>;

  template <typename CELLS, typename PARAMETERS>
  void apply(CELLS& cells, PARAMETERS& parameters) any_platform
   {
    using DESCRIPTOR = typename CELLS::template value_t<names::NavierStokes>::descriptor_t;
    using DESCRIPTOR_KE = typename CELLS::template value_t<names::TurbKineticEnergy>::descriptor_t;

    auto cellNS = cells.template get<names::NavierStokes>();

    /// Velocity coupling
    auto u = cells.template get<names::TurbKineticEnergy>().template getField<descriptors::VELOCITY>();
    T rho, pi[util::TensorVal<DESCRIPTOR>::n] { };
    cells.template get<names::NavierStokes>().computeAllMomenta(rho, u.data(), pi);
    cells.template get<names::TurbKineticEnergy>().template setField<descriptors::VELOCITY>(u);
    cells.template get<names::DissipationRate>().template setField<descriptors::VELOCITY>(u);

    T C1 = 1.44;
    T C2 = 1.92;
    T Cmu = 0.09;
    T invSigmaK = 1.0;
    T invSigmaE = 0.76923;
    T eta0 = 4.38;
    T beta = 0.012;
    T kappa = 0.4187;
    T kinVisc = parameters.template get<VISC>();
    T dT = parameters.template get<D_T>();
    T dX = parameters.template get<D_X>();
    T k = cells.template get<names::TurbKineticEnergy>().computeRho();
    T epsilon = cells.template get<names::DissipationRate>().computeRho();
    T porosity = cellNS.template getField<descriptors::POROSITY>();
    T convVisc = dX*dX/dT;
    T convK = dX*dX/dT/dT;
    T convVel = dX/dT;
    T zero = 0.;
    bool is_num = true;


    T turbVisc = Cmu*k*k/epsilon;
    if(std::isnan(turbVisc) || std::isinf(turbVisc)) turbVisc = 0;
    T tau_turb_K = (kinVisc + turbVisc*invSigmaK)/convVisc * descriptors::invCs2<T,DESCRIPTOR_KE>() + 0.5;
    T tau_turb_E = (kinVisc + turbVisc*invSigmaE)/convVisc * descriptors::invCs2<T,DESCRIPTOR_KE>() + 0.5;
    T tau_turb_RANS = (kinVisc + turbVisc)/convVisc * descriptors::invCs2<T,DESCRIPTOR>() + 0.5;
    T tau_mod = (kinVisc + turbVisc)/convVisc * descriptors::invCs2<T,DESCRIPTOR_KE>() + 0.5;
    auto& cellNSE = cells.template get<names::NavierStokes>();
    T piNeqNormSqr= lbm<DESCRIPTOR>::computePiNeqNormSqr(cellNSE);
    T termS = util::sqrt(2.*piNeqNormSqr) * 1./(2.*tau_mod)*descriptors::invCs2<T,DESCRIPTOR_KE>();
    //cells.template get<names::DissipationRate>().template setField<descriptors::SCALAR>(termS/dT);
    T turbKinEnergyProduction = turbVisc/convVisc*termS*termS;
    T eta = termS/dT * k / epsilon;

    const int useRNGModel = parameters.template get<USE_RNG_MODEL>();
    if(useRNGModel) C2 += Cmu*eta*eta*eta*(1. - eta/eta0)/(1. + beta*eta*eta*eta);

    /// Source Terms
    T sourceK = turbKinEnergyProduction*convK - epsilon*dT;
    T sourceE = C1*epsilon/k*turbKinEnergyProduction*convK - C2*epsilon*epsilon/k*dT;

    if(std::isnan(k) || std::isinf(k)) {is_num = false; k = T(1e-10); cells.template get<names::TurbKineticEnergy>().defineRho(k);}
    if(std::isnan(epsilon) || std::isinf(epsilon)) {is_num = false; epsilon = T(1e-10); cells.template get<names::DissipationRate>().defineRho(epsilon);}
    if(std::isnan(sourceK) || std::isinf(sourceK)) sourceK = 0;
    if(std::isnan(sourceE) || std::isinf(sourceE)) sourceE = 0;

    if(-sourceK < k && -sourceE < epsilon){
      if( (Cmu * (k+sourceK) * (k+sourceK) / (epsilon+sourceE))/convVisc < 2.0 && is_num && k >= 0 && epsilon >= 0 && turbVisc >= 0 && porosity == T(1)){
        cells.template get<names::TurbKineticEnergy>().template setField<descriptors::SOURCE>(sourceK);
        cells.template get<names::DissipationRate>().template setField<descriptors::SOURCE>(sourceE);

        /// Modification of the relaxation times
        cells.template get<names::NavierStokes>().template setField<descriptors::OMEGA>(T{1} / (tau_turb_RANS));
        cells.template get<names::TurbKineticEnergy>().template setField<descriptors::OMEGA>(T{1} / (tau_turb_K));
        cells.template get<names::DissipationRate>().template setField<descriptors::OMEGA>(T{1} / (tau_turb_E));
        //cells.template get<names::TurbKineticEnergy>().template setField<descriptors::SCALAR>(T(0));
      }else{
        cells.template get<names::TurbKineticEnergy>().template setField<descriptors::SOURCE>(T{0});
        cells.template get<names::DissipationRate>().template setField<descriptors::SOURCE>(T{0});
        cells.template get<names::NavierStokes>().template setField<descriptors::OMEGA>(T{1} / ((kinVisc/convVisc + 2.)* descriptors::invCs2<T,DESCRIPTOR>() + 0.5));
        cells.template get<names::TurbKineticEnergy>().template setField<descriptors::OMEGA>(T{1} / ((kinVisc/convVisc + 2.)* descriptors::invCs2<T,DESCRIPTOR_KE>() + 0.5));
        cells.template get<names::DissipationRate>().template setField<descriptors::OMEGA>(T{1} / ((kinVisc/convVisc + 2.)* descriptors::invCs2<T,DESCRIPTOR_KE>() + 0.5));
        //cells.template get<names::TurbKineticEnergy>().template setField<descriptors::SCALAR>(T(2000));
      }
    }else{
      cells.template get<names::TurbKineticEnergy>().template setField<descriptors::SOURCE>(T{0});
      cells.template get<names::DissipationRate>().template setField<descriptors::SOURCE>(T{0});
      cells.template get<names::TurbKineticEnergy>().defineRho(zero);
      cells.template get<names::DissipationRate>().defineRho(zero);
      cells.template get<names::NavierStokes>().template setField<descriptors::OMEGA>(T{1} / (kinVisc/convVisc * descriptors::invCs2<T,DESCRIPTOR>() + 0.5));
      cells.template get<names::TurbKineticEnergy>().template setField<descriptors::OMEGA>(T{1} / (kinVisc/convVisc * descriptors::invCs2<T,DESCRIPTOR_KE>() + 0.5));
      cells.template get<names::DissipationRate>().template setField<descriptors::OMEGA>(T{1} / (kinVisc/convVisc * descriptors::invCs2<T,DESCRIPTOR_KE>() + 0.5));
      //cells.template get<names::TurbKineticEnergy>().template setField<descriptors::SCALAR>(T(3000));
    }

    if(porosity >= 0.01 && porosity <= 0.99){
      cells.template get<names::DissipationRate>().template setField<descriptors::SOURCE>(T{0});
      if( k < T(0)) k = T(1.e-10);
      T epsWall = util::pow(Cmu,3./4.)*util::pow(k,3./2.)/kappa/(dX);
      cells.template get<names::DissipationRate>().defineRho(epsWall);
      cells.template get<names::DissipationRate>().template setField<descriptors::OMEGA>(T{1} / (kinVisc/convVisc * descriptors::invCs2<T,DESCRIPTOR_KE>() + 0.5)); //turbVisc -> 0 in wandnähe
  }


// https://www.afs.enea.it/project/neptunius/docs/fluent/html/th/node99.htm
// Wall BC for k and eps

    Vector<int,3> normal(0.,0.,0.);
    bool wall = true;
    Vector<T,3> wallVel(0.,0.,0.);
    int NBcount = 0;
    if(porosity >= T(1)){
      for(int iPop = 1; iPop < descriptors::D3Q7<>::q; iPop++) {
        T porosityNB = cellNS.neighbor(descriptors::c<descriptors::D3Q7<>>(iPop)).template getField<descriptors::POROSITY>();
        if(porosityNB <= T(0.5)) {
          normal = normal - descriptors::c<descriptors::D3Q7<>>(iPop);
          auto velNB = cells.template get<names::TurbKineticEnergy>().template getField<descriptors::VELOCITY>();
          cells.template get<names::NavierStokes>().computeU(velNB.data());
          wallVel = wallVel + velNB;
          NBcount++;
        }
        // if(porosityNB == T(0.5)) wall = false;
      }
      if(util::norm<DESCRIPTOR::d>(normal) != T(0) && wall) {
        cells.template get<names::DissipationRate>().template setField<descriptors::SOURCE>(T{0});
        if( k < T(0)) k = T(1.e-10);
        T epsWall = util::pow(Cmu,3./4.)*util::pow(k,3./2.)/kappa/(dX);
        cells.template get<names::DissipationRate>().defineRho(epsWall);
        cells.template get<names::DissipationRate>().template setField<descriptors::OMEGA>(T{1} / (kinVisc/convVisc * descriptors::invCs2<T,DESCRIPTOR>() + 0.5)); //turbVisc -> 0 in wandnähe
        normal = T(1)/util::norm<DESCRIPTOR::d>(normal) * normal;
        u = u*convVel;
        wallVel = wallVel/NBcount;
        wallVel = wallVel*convVel;
        auto uTang = u - (u*normal)*normal;
        auto wallVelTang = wallVel - (wallVel*normal)*normal;
        //cells.template get<names::TurbKineticEnergy>().template setField<descriptors::SCALAR>(util::norm<DESCRIPTOR::d>(wallVelTang)); //set flag to check if only wall cells are effected

        T tauW = kinVisc*util::norm<DESCRIPTOR::d>(wallVelTang - uTang)/(dX);
        T turbKinEnergyProductionBC = tauW*tauW/kappa/(dX)/util::sqrt(k);
        cells.template get<names::TurbKineticEnergy>().template setField<descriptors::SOURCE>(turbKinEnergyProductionBC*dT - epsWall*dT);
      }
    }
   }
};

}


#endif
