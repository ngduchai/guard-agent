/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2024 Fedor Bukreev, Adrian Kummerländer
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

#ifndef CRYSTAL_COLLISION
#define CRYSTAL_COLLISION

#include "boundary/bouzidiFields.h"

namespace olb {

namespace collision {
  struct CrystalCollision {
  using parameters = typename meta::list<descriptors::OMEGA>;

  static std::string getName() {
    return "CrystalCollision";
  }

  template <typename DESCRIPTOR, typename MOMENTA, typename EQUILIBRIUM>
  struct type {

    using MomentaF = typename MOMENTA::template type<DESCRIPTOR>;
    using EquilibriumF = typename EQUILIBRIUM::template type<DESCRIPTOR,MOMENTA>;

    static constexpr bool is_vectorizable = false;

    template <typename CELL, typename PARAMETERS, typename V=typename CELL::value_t>
    CellStatistic<V> apply(CELL& cell, PARAMETERS& parameters) any_platform {
      V crystal = cell.template getField<descriptors::CRYSTLAYER>();
      if(crystal < V(0.5)){
        const V omega = parameters.template get<descriptors::OMEGA>();
        V rho, u[DESCRIPTOR::d];
        MomentaF().computeRhoU(cell, rho, u);
        V uSqr = lbm<DESCRIPTOR>::bgkCollision(cell, rho, u, omega);
        const auto force = cell.template getField<descriptors::FORCE>();
        V rho1 = V(1.);
        lbm<DESCRIPTOR>::addExternalForce(cell, rho1, u, omega, force);
        V newRho{};
        Vector<V,DESCRIPTOR::d> newU;
        typename momenta::Crystal<MOMENTA>::template type<DESCRIPTOR>().computeRhoU(cell, newRho, newU);
        cell.template setField<descriptors::MOMENTA_DENSITY>(newRho);
        cell.template setField<descriptors::MOMENTA_VELOCITY>(newU);
        return {rho, uSqr};
      }else{
        auto normal = cell.template getFieldPointer<descriptors::NORMAL>();
        int reflectionPop[DESCRIPTOR::q];
        int mirrorDirection0;
        int mirrorDirection1;
        int mirrorDirection2;
        int NX(normal[0]);
        int NY(normal[1]);
        int NZ(normal[2]);
        int mult = 0;
        if((NX*NX + NY*NY + NZ*NZ) != 0){
          mult = 2 / (NX*NX + NY*NY + NZ*NZ);
        }
        reflectionPop[0] =0;
        for (int iPop = 1; iPop < DESCRIPTOR::q; iPop++) {
          reflectionPop[iPop] = 0;
          // iPop are the directions which pointing into the fluid, discreteNormal is pointing outwarts
          int scalarProduct = descriptors::c<DESCRIPTOR>(iPop,0)*NX + descriptors::c<DESCRIPTOR>(iPop,1)*NY + descriptors::c<DESCRIPTOR>(iPop,2)*NZ;
          if ( scalarProduct < 0) {
            // bounce back for the case discreteNormalX = discreteNormalY = discreteNormalZ = 1, that is mult=0
            if (mult == 0) {
              mirrorDirection0 = -descriptors::c<DESCRIPTOR>(iPop,0);
              mirrorDirection1 = -descriptors::c<DESCRIPTOR>(iPop,1);
              mirrorDirection2 = -descriptors::c<DESCRIPTOR>(iPop,2);
            }
            else {
              mirrorDirection0 = descriptors::c<DESCRIPTOR>(iPop,0) - mult*scalarProduct*NX;
              mirrorDirection1 = descriptors::c<DESCRIPTOR>(iPop,1) - mult*scalarProduct*NY;
              mirrorDirection2 = descriptors::c<DESCRIPTOR>(iPop,2) - mult*scalarProduct*NZ;
            }

            // run through all lattice directions and look for match of direction
            for (int i = 1; i < DESCRIPTOR::q; i++) {
              if (descriptors::c<DESCRIPTOR>(i,0)==mirrorDirection0
                  && descriptors::c<DESCRIPTOR>(i,1)==mirrorDirection1
                  && descriptors::c<DESCRIPTOR>(i,2)==mirrorDirection2) {
                reflectionPop[iPop] = i;
                break;
              }
            }
          }
        }
        for (int iPop = 1; iPop < DESCRIPTOR::q ; ++iPop) {
          if (reflectionPop[iPop]!=0) {
            //do reflection
            cell[iPop] = cell[reflectionPop[iPop]];
          }
        }
        return {-1, -1};
      }
    };
  };
};
}

namespace dynamics {

struct ExposeCrystalMomenta {
  static std::string getName() {
    return "ExposeCrystalMomenta";
  }

  template <typename DESCRIPTOR, typename MOMENTA>
  using combined_momenta = typename momenta::Crystal<MOMENTA>::template type<DESCRIPTOR>;

  template <typename DESCRIPTOR, typename MOMENTA, typename EQUILIBRIUM>
  using combined_equilibrium = typename EQUILIBRIUM::template type<DESCRIPTOR,MOMENTA>;

  template <typename DESCRIPTOR, typename MOMENTA, typename EQUILIBRIUM, typename COLLISION>
  using combined_collision = typename COLLISION::template type<DESCRIPTOR,MOMENTA,EQUILIBRIUM>;

  template <typename DESCRIPTOR, typename MOMENTA, typename EQUILIBRIUM, typename COLLISION>
  using combined_parameters = typename COLLISION::parameters;
};

}
}
#endif
