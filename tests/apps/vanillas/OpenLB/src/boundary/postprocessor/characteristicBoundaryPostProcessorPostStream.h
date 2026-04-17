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

#ifndef CHARACTERISTIC_POSTPROCESSOR_POST_STREAM_H
#define CHARACTERISTIC_POSTPROCESSOR_POST_STREAM_H

#include <olb.h>

namespace olb {

namespace boundary {
template<typename T, typename DESCRIPTOR, int direction, int orientation>
class CBCPostProcessorPostStreamFlat3D {
public:
  static constexpr OperatorScope scope = OperatorScope::PerCell;

  int getPriority() const {
    return 0;
  }

  template <concepts::DynamicCell CELL>
  void apply(CELL& cell) any_platform {
    // ### FIRST PART ###
    // This PP is used in Stage::PostStream for the "Correction of the set of populations at the boundary
    //    so that the physical values stored in the first step are imposed by using the Zou/He adaptation
    //    the so-called regularized Bounceback adaptation or the Regularized FD adaptation."
    // Using "Regularized Bounceback (Regularized BB)", p.8
    // This is all local

    using V = typename CELL::value_t;

    // === LOAD PRESCRIBED VALUES FROM PRE-COLLISION POST-PROCESSOR ===
    V     rhoPrev = cell.template getField<fields::cbc::RHO_POST_PP>();
    auto  uPrev   = cell.template getField<fields::cbc::U_POST_PP>();

    // === COMPUTE NON-EQUILIBRIUM PART OF POPULATIONS BASED ON PRE-COLLISION VALUES ===
    V fNeq[DESCRIPTOR::q], fEqB[DESCRIPTOR::q];
    for (int iPop=0; iPop < DESCRIPTOR::q; ++iPop) {
      fEqB[iPop] = equilibrium<DESCRIPTOR>::secondOrder(iPop, rhoPrev, uPrev);
      fNeq[iPop] = cell[iPop] - fEqB[iPop];
    }

    // === COMPUTE f^(1) FROM Wissoq (7) ===
    // F^neq on available populations, opposite otherwise (f^neq is symmetric)
    constexpr auto missingIndices = util::populationsContributingToVelocity<DESCRIPTOR,direction,-orientation>();
    Vector<V,DESCRIPTOR::q> f1{};
    for ( size_t iPop=0; iPop < DESCRIPTOR::q; iPop++ ) {
      f1[iPop] = fNeq[iPop];
    }
    for ( auto e : missingIndices ) {
      f1[e] = fNeq[descriptors::opposite<DESCRIPTOR>(e)];
    }

    // === COMPUTE STRESS TENSOR PI ===
    Vector<Vector<T,DESCRIPTOR::d>,DESCRIPTOR::d> Pi1{};
    for ( size_t iPop=0; iPop < DESCRIPTOR::q; iPop++ ) {
      for ( size_t iDim1=0; iDim1 < DESCRIPTOR::d; iDim1++ ) {
        for ( size_t iDim2=0; iDim2 < DESCRIPTOR::d; iDim2++ ) {
          // todo: can I concat this b/c of unity matrix cs^2*I in Q?
          Pi1[iDim1][iDim2] += descriptors::c<DESCRIPTOR>(iPop,iDim1) * descriptors::c<DESCRIPTOR>(iPop,iDim2) * f1[iPop];
        }
      }
    }
    Vector<Vector<Vector<T,DESCRIPTOR::d>,DESCRIPTOR::d>,DESCRIPTOR::q> Q{};
    for ( size_t iPop=0; iPop < DESCRIPTOR::q; iPop++ ) {
      for ( size_t iDim1=0; iDim1 < DESCRIPTOR::d; iDim1++ ) {
        for ( size_t iDim2=0; iDim2 < DESCRIPTOR::d; iDim2++ ) {
          Q[iPop][iDim1][iDim2] = descriptors::c<DESCRIPTOR>(iPop,iDim1) * descriptors::c<DESCRIPTOR>(iPop,iDim2);
          if ( iDim1 == iDim2 ) Q[iPop][iDim1][iDim2] -= V(1) / descriptors::invCs2<T,DESCRIPTOR>();
        }
      }
    }
    V QPi[DESCRIPTOR::q]{};
    for ( size_t iPop=0; iPop < DESCRIPTOR::q; iPop++ ) {
      for ( size_t iDim1=0; iDim1 < DESCRIPTOR::d; iDim1++ ) {
        for ( size_t iDim2=0; iDim2 < DESCRIPTOR::d; iDim2++ ) {
          QPi[iPop] += Q[iPop][iDim1][iDim2] * Pi1[iDim1][iDim2];
        }
      }
    }
    V wi[DESCRIPTOR::q]{};
    for ( size_t iPop=0; iPop < DESCRIPTOR::q; iPop++ ) {
      wi[iPop] = descriptors::t<V,DESCRIPTOR>(iPop);
    }
    for ( size_t iPop=0; iPop < DESCRIPTOR::q; iPop++ ) {
      f1[iPop] = wi[iPop] / V(2) * descriptors::invCs2<T,DESCRIPTOR>() * QPi[iPop]; // approx, Wissoq (9)
      cell[iPop] = fEqB[iPop] + f1[iPop]; // Wissoq (41), accounting for wi part in f1
    }
    // TODO: set only inbound populations
  };
};

template <typename T, typename DESCRIPTOR, int plane, int normal1, int normal2>
class CBCPostProcessorPostStreamEdge3D : public OuterVelocityEdgeProcessor3D<T,DESCRIPTOR,plane,normal1,normal2> {
public:
  int getPriority() const {
    return 1;
  }
};

template<typename T, typename DESCRIPTOR, int xNormal, int yNormal, int zNormal>
struct CBCPostProcessorPostStreamCorner3D : public OuterVelocityCornerProcessor3D<T,DESCRIPTOR,xNormal,yNormal,zNormal> {
  int getPriority() const {
    // priority is required to give correct values at neighbors
    return 2;
  }
};

} // namespace boundary
} // namespace olb
#endif // CHARACTERISTIC_POSTPROCESSOR_POST_STREAM_H