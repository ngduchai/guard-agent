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

#ifndef BOUNDARY_CHARACTERISTIC_H
#define BOUNDARY_CHARACTERISTIC_H

#include "olb.h"
#include "postprocessor/characteristicBoundaryPostProcessorPreCollide.h"
#include "postprocessor/characteristicBoundaryPostProcessorPostStream.h"

namespace olb {

namespace boundary {

/** Boundary condition details:
 *
 * Given name: characteristicBoundary
 *
 * References: Wissoq et al. (2017) doi: 10.1016/j.jcp.2016.11.037
 *
 * Equation: Navier-Stokes
 *
 * Type: onLattice
 *
 * Condition on zeroth moment (pressure): Dirichlet type
 */

template <concepts::BaseType T, concepts::LatticeDescriptor DESCRIPTOR, typename MixinDynamics = BGKdynamics<T,DESCRIPTOR>>
struct Characteristic {
// TODO: Add 2D version

  using value_t = T;
  using descriptor_t = DESCRIPTOR;

  CellDistance getNeighborhoodRadius() {
    return 1;
  }

  std::optional<DynamicsPromise<T,DESCRIPTOR>> getDynamics(DiscreteNormalType type,
                                                          DiscreteNormal<DESCRIPTOR> n) {
    switch (type) {

    // ==== FLAT DYNAMICS
      case DiscreteNormalType::Flat:
        return boundaryhelper::MixinDynamicsExchangeDirectionOrientationMomenta<
                T,
                DESCRIPTOR,
                MixinDynamics, // template <typename,typename,typename> typename DYNAMICS
                momenta::CBCFlatMomentaTuple // template <int,int> typename MOMENTA
              >::construct(n);

      // ==== OUTSIDE CASES
      // fixing velocity to that calculated by PP
      case DiscreteNormalType::ExternalEdge:
      case DiscreteNormalType::ExternalCorner:
        return meta::id<typename MixinDynamics::template exchange_momenta<momenta::CBCoutsideTuple>>{};

      default:
        throw std::runtime_error("Invalid normal type for characteristic boundary dynamics");
        return std::nullopt;
    }
  }

  std::optional<PostProcessorPromise<T,DESCRIPTOR>> getPostProcessorPostStream(DiscreteNormalType type,
                                                                    DiscreteNormal<DESCRIPTOR> n) {
    switch (type) {
    case DiscreteNormalType::Flat:
      return boundaryhelper::promisePostProcessorForDirectionOrientation<
              T,DESCRIPTOR,CBCPostProcessorPostStreamFlat3D
          >(n);
    case DiscreteNormalType::ExternalEdge:
      return boundaryhelper::promisePostProcessorForNormalSpecial<T,DESCRIPTOR,CBCPostProcessorPostStreamEdge3D>(n);
    case DiscreteNormalType::ExternalCorner:
      return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,CBCPostProcessorPostStreamCorner3D>(n);

    default:
      throw std::runtime_error("Invalid normal type for characteristic boundary post stream");
      return std::nullopt;
    }
  }

  std::optional<PostProcessorPromise<T,DESCRIPTOR>> getPostProcessorPreCollide(DiscreteNormalType type,
                                                                    DiscreteNormal<DESCRIPTOR> n) {
    switch (type) {
    case DiscreteNormalType::Flat:
      return boundaryhelper::promisePostProcessorForDirectionOrientation<
              T,DESCRIPTOR,CBCPostProcessorPreCollideFlat3D
          >(n);
    case DiscreteNormalType::ExternalEdge:
      return boundaryhelper::promisePostProcessorForNormalSpecial<T,DESCRIPTOR,CBCPostProcessorPreCollideEdge3D>(n);
    case DiscreteNormalType::ExternalCorner:
      return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,CBCPostProcessorPreCollideCorner3D>(n);

    default:
      throw std::runtime_error("Invalid normal type for characteristic boundary pre collide");
      return std::nullopt;
    }
  }

  std::optional<PostProcessorPromise<T,DESCRIPTOR>> getPostProcessor(DiscreteNormalType type,
                                                                    DiscreteNormal<DESCRIPTOR> n) {
    return std::nullopt;
  }

};

template <concepts::BaseType T, concepts::LatticeDescriptor DESCRIPTOR, concepts::BoundaryCondition BC, typename MixinDynamics = BGKdynamics<T,DESCRIPTOR>>
void setCBC(BlockLattice<T,DESCRIPTOR>& block,
            BlockIndicatorF<T,DESCRIPTOR::d>& boundaryI,
            BlockIndicatorF<T,DESCRIPTOR::d>& fluidI,
            BlockIndicatorF<T,DESCRIPTOR::d>& outsideI)
{
  auto& blockGeometryStructure = boundaryI.getBlockGeometry();
  blockGeometryStructure.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> latticeR) {
    if (   blockGeometryStructure.getNeighborhoodRadius(latticeR) >= util::max(BC().getNeighborhoodRadius(), 1)
        && boundaryI(latticeR)) {
      const auto [normalType, normal] = computeBoundaryTypeAndNormal(fluidI, outsideI, latticeR);
      if (auto dynamics = BC().getDynamics(normalType, normal)) {
        block.defineDynamics( latticeR,
                              std::move(*dynamics));
      }
      if (auto opPreCollide = BC().getPostProcessorPreCollide(normalType, normal)) {
        block.addPostProcessor(typeid(stage::PreCollide),
                                latticeR,
                                std::move(*opPreCollide));
      }
      if (auto opPostStream = BC().getPostProcessorPostStream(normalType, normal)) {
        block.addPostProcessor(typeid(stage::PostStream),
                                latticeR,
                                std::move(*opPostStream));
      }
    }
  });
}

template <concepts::BaseType          T,
          concepts::LatticeDescriptor DESCRIPTOR,
          concepts::BoundaryCondition BC,
          typename                    MixinDynamics = BGKdynamics<T,DESCRIPTOR>>
void setCBC(SuperLattice<T,DESCRIPTOR>& lattice,
            FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& boundaryI,
            FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& fluidI,
            FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& outsideI)
{
  for (int iCloc = 0; iCloc < lattice.getLoadBalancer().size(); ++iCloc) {
    setCBC<T,DESCRIPTOR,BC,MixinDynamics>(  lattice.getBlock(iCloc),
                                            boundaryI->getBlockIndicatorF(iCloc),
                                            fluidI->getBlockIndicatorF(iCloc),
                                            outsideI->getBlockIndicatorF(iCloc));
  }
  SuperIndicatorBoundaryNeighbor<T,DESCRIPTOR::d> neighborIndicator(
    std::forward<decltype(boundaryI)>(boundaryI),
    BC().getNeighborhoodRadius());

  // populations are absolutely required! Otherwise immediate issue at overlap in streaming direction
  auto& communicator = lattice.getCommunicator(stage::PreCollide());
  communicator.template requestField<descriptors::POPULATION>();
  communicator.requestOverlap(BC().getNeighborhoodRadius(), neighborIndicator);
  communicator.exchangeRequests();

  // post pp values are required for correct post stream correction
  auto& communicator2 = lattice.getCommunicator(stage::PostStream());
  communicator2.template requestField<fields::cbc::RHO_POST_PP>();
  communicator2.template requestField<fields::cbc::U_POST_PP>();
  communicator2.requestOverlap(BC().getNeighborhoodRadius(), neighborIndicator);
  communicator2.exchangeRequests();
}

} // namespace boundary
} // namespace olb
#endif // BOUNDARY_CHARACTERISTIC_H
