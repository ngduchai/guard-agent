/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2024 Tim Bingert, Luiz Eduardo Czelusniak
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

//This file contains all inlet and outlet boundary conditions of phase field models
//This boundary only contains free floating functions

#ifndef PHASE_FIELD_INLET_OUTLET_3D_H
#define PHASE_FIELD_INLET_OUTLET_3D_H

#include "setBoundary.h"
#include "phaseFieldInletOutlet.h"
#include "zouHeDynamics.h"
#include "dynamics/freeEnergyDynamics.h"

namespace olb {

/*

///Initialising the setConvectivePhaseFieldBoundary function on the superLattice domain in 3d
template<typename T, typename DESCRIPTOR>
void setConvectivePhaseFieldBoundary(SuperLattice<T, DESCRIPTOR>& sLattice, SuperGeometry<T,3>& superGeometry, int material)
{
  setConvectivePhaseFieldBoundary<T,DESCRIPTOR>(sLattice, superGeometry.getMaterialIndicator(material));
}

///Initialising the setConvectivePhaseFieldBoundary function on the superLattice domain
template<typename T, typename DESCRIPTOR>
void setConvectivePhaseFieldBoundary(SuperLattice<T, DESCRIPTOR>& sLattice, FunctorPtr<SuperIndicatorF3D<T>>&& indicator)
{
  OstreamManager clout(std::cout, "setConvectivePhaseFieldBoundary");

  for (int iCloc = 0; iCloc < sLattice.getLoadBalancer().size(); iCloc++) {
    setConvectivePhaseFieldBoundary<T,DESCRIPTOR>(sLattice.getBlock(iCloc), indicator->getBlockIndicatorF(iCloc));
  }
  /// Adds needed Cells to the Communicator _commBC in SuperLattice
  int _overlap = 1;
  {
    auto& communicator = sLattice.getCommunicator(stage::PostCollide());
    communicator.template requestField<descriptors::POPULATION>();

    SuperIndicatorBoundaryNeighbor<T,DESCRIPTOR::d> neighborIndicator(std::forward<decltype(indicator)>(indicator), _overlap);
    communicator.requestOverlap(_overlap, neighborIndicator);
    communicator.exchangeRequests();
  }
}

/// Set ConvectivePhaseFieldBoundary for any indicated cells inside the block domain
template<typename T, typename DESCRIPTOR>
void setConvectivePhaseFieldBoundary(BlockLattice<T,DESCRIPTOR>& block, BlockIndicatorF3D<T>& indicator)
{
  using namespace boundaryhelper;
  const auto& blockGeometryStructure = indicator.getBlockGeometry();
  const int margin = 1;
  std::vector<int> discreteNormal(4,0);
  blockGeometryStructure.forSpatialLocations([&](auto iX, auto iY, auto iZ) {
    if (blockGeometryStructure.getNeighborhoodRadius({iX, iY, iZ}) >= margin && indicator(iX, iY, iZ)) {
      discreteNormal = blockGeometryStructure.getStatistics().getType(iX, iY, iZ);
      if ((abs(discreteNormal[1]) + abs(discreteNormal[2]) + abs(discreteNormal[3])) == 1) {
        block.addPostProcessor(
          typeid(stage::PostCollide), {iX,iY,iZ},
          promisePostProcessorForNormal<T,DESCRIPTOR,FlatConvectivePhaseFieldPostProcessorA3D>(
            Vector<int,3>(discreteNormal.data() + 1)));
        block.addPostProcessor(
          typeid(stage::PostStream), {iX,iY,iZ},
          promisePostProcessorForNormal<T,DESCRIPTOR,FlatConvectivePhaseFieldPostProcessorB3D>(
            Vector<int,3>(discreteNormal.data() + 1)));
        block.template defineDynamics<NoCollideDynamicsExternalVelocity>({iX, iY, iZ});
      } else {
        throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
      }
    }
  });
}

///Initialising the setNeumannPhaseFieldBoundary function on the superLattice domain in 3d
template<typename T, typename DESCRIPTOR>
void setNeumannPhaseFieldBoundary(SuperLattice<T, DESCRIPTOR>& sLattice, SuperGeometry<T,3>& superGeometry, int material)
{
  setNeumannPhaseFieldBoundary<T,DESCRIPTOR>(sLattice, superGeometry.getMaterialIndicator(material));
}

///Initialising the setNeumannPhaseFieldBoundary function on the superLattice domain
template<typename T, typename DESCRIPTOR>
void setNeumannPhaseFieldBoundary(SuperLattice<T, DESCRIPTOR>& sLattice, FunctorPtr<SuperIndicatorF3D<T>>&& indicator)
{
  OstreamManager clout(std::cout, "setNeumannPhaseFieldBoundary");

  for (int iCloc = 0; iCloc < sLattice.getLoadBalancer().size(); iCloc++) {
    setNeumannPhaseFieldBoundary<T,DESCRIPTOR>(sLattice.getBlock(iCloc), indicator->getBlockIndicatorF(iCloc));
  }
  /// Adds needed Cells to the Communicator _commBC in SuperLattice
  int _overlap = 1;
  {
    auto& communicator = sLattice.getCommunicator(stage::PostCollide());
    communicator.template requestField<descriptors::POPULATION>();

    SuperIndicatorBoundaryNeighbor<T,DESCRIPTOR::d> neighborIndicator(std::forward<decltype(indicator)>(indicator), _overlap);
    communicator.requestOverlap(_overlap, neighborIndicator);
    communicator.exchangeRequests();
  }
}

/// Set setNeumannPhaseFieldBoundary for any indicated cells inside the block domain
template<typename T, typename DESCRIPTOR>
void setNeumannPhaseFieldBoundary(BlockLattice<T,DESCRIPTOR>& block, BlockIndicatorF3D<T>& indicator)
{
  using namespace boundaryhelper;
  const auto& blockGeometryStructure = indicator.getBlockGeometry();
  const int margin = 1;
  std::vector<int> discreteNormal(4,0);
  blockGeometryStructure.forSpatialLocations([&](auto iX, auto iY, auto iZ) {
    if (blockGeometryStructure.getNeighborhoodRadius({iX, iY, iZ}) >= margin && indicator(iX, iY, iZ)) {
      discreteNormal = blockGeometryStructure.getStatistics().getType(iX, iY, iZ);
      if ((abs(discreteNormal[1]) + abs(discreteNormal[2]) + abs(discreteNormal[3])) == 1) {
        block.addPostProcessor(
          typeid(stage::PostCollide), {iX,iY,iZ},
          promisePostProcessorForNormal<T,DESCRIPTOR,FlatNeumannPhaseFieldPostProcessorA3D>(
            Vector<int,3>(discreteNormal.data() + 1)));
        block.addPostProcessor(
          typeid(stage::PostStream), {iX,iY,iZ},
          promisePostProcessorForNormal<T,DESCRIPTOR,FlatNeumannPhaseFieldPostProcessorB3D>(
            Vector<int,3>(discreteNormal.data() + 1)));
        block.template defineDynamics<NoCollideDynamicsExternalVelocity>({iX, iY, iZ});
      } else {
        throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
      }
    }
  });
}

namespace boundary {

template <concepts::BaseType T, concepts::LatticeDescriptor DESCRIPTOR, typename MixinDynamics>
requires (DESCRIPTOR::d == 3)
struct IncompressibleZouHeVelocity<T,DESCRIPTOR,MixinDynamics> {

using value_t = T;
using descriptor_t = DESCRIPTOR;

CellDistance getNeighborhoodRadius() {
  return 2;
}

std::optional<DynamicsPromise<T,DESCRIPTOR>> getDynamics(DiscreteNormalType type,
                                                         DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::DirectionOrientationMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      IncZouHeDynamics,MixinDynamics,momenta::IncDirichletVelocityBoundaryTuple
    >::construct(n);

  case DiscreteNormalType::ExternalCorner:
    return meta::id<typename MixinDynamics::template exchange_momenta<
      momenta::FixedVelocityBoundaryTuple
    >>();

  case DiscreteNormalType::InternalCorner:
    return boundaryhelper::PlainMixinDynamicsForNormalMomenta<T,DESCRIPTOR,
      CombinedRLBdynamics,MixinDynamics,momenta::InnerCornerVelocityTuple3D
    >::construct(n);

  case DiscreteNormalType::ExternalEdge:
    return meta::id<typename MixinDynamics::template exchange_momenta<
      momenta::FixedVelocityBoundaryTuple
    >>();

  case DiscreteNormalType::InternalEdge:
    return boundaryhelper::PlainMixinDynamicsForNormalSpecialMomenta<T,DESCRIPTOR,
      CombinedRLBdynamics,MixinDynamics,momenta::InnerEdgeVelocityTuple3D
    >::construct(n);

  default:
    return std::nullopt;
  }
}

std::optional<PostProcessorPromise<T,DESCRIPTOR>> getPostProcessor(DiscreteNormalType type,
                                                                   DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::ExternalCorner:
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,OuterVelocityCornerProcessor3D>(n);
  case DiscreteNormalType::ExternalEdge:
    return boundaryhelper::promisePostProcessorForNormalSpecial<T,DESCRIPTOR,OuterVelocityEdgeProcessor3D>(n);
  default:
    return std::nullopt;
  }
}

};

template <concepts::BaseType T, concepts::LatticeDescriptor DESCRIPTOR, typename MixinDynamics>
requires (DESCRIPTOR::d == 3)
struct IncompressibleZouHePressure<T,DESCRIPTOR,MixinDynamics> {

using value_t = T;
using descriptor_t = DESCRIPTOR;

CellDistance getNeighborhoodRadius() {
  return 1;
}

std::optional<DynamicsPromise<T,DESCRIPTOR>> getDynamics(DiscreteNormalType type,
                                                         DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::DirectionOrientationMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      IncZouHeDynamics,MixinDynamics,momenta::IncDirichletPressureBoundaryTuple
    >::construct(n);

  default:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return std::nullopt;
  }
}

std::optional<PostProcessorPromise<T,DESCRIPTOR>> getPostProcessor(DiscreteNormalType type,
                                                                   DiscreteNormal<DESCRIPTOR> n) {
  return std::nullopt;
}

};

template <concepts::BaseType T, concepts::LatticeDescriptor DESCRIPTOR, typename MixinDynamics>
requires (DESCRIPTOR::d == 3)
struct IncompressibleLocalPressure<T,DESCRIPTOR,MixinDynamics> {

using value_t = T;
using descriptor_t = DESCRIPTOR;

CellDistance getNeighborhoodRadius() {
  return 1;
}

std::optional<DynamicsPromise<T,DESCRIPTOR>> getDynamics(DiscreteNormalType type,
                                                         DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::PlainMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      CombinedIRLBdynamics,MixinDynamics,momenta::IncRegularizedPressureBoundaryTuple
    >::construct(n);

  default:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return std::nullopt;
  }
}

std::optional<PostProcessorPromise<T,DESCRIPTOR>> getPostProcessor(DiscreteNormalType type,
                                                                   DiscreteNormal<DESCRIPTOR> n) {
  return std::nullopt;
}

};

template <concepts::BaseType T, concepts::LatticeDescriptor DESCRIPTOR, typename MixinDynamics>
requires (DESCRIPTOR::d == 3)
struct FreeEnergyVelocity<T,DESCRIPTOR,MixinDynamics> {

using value_t = T;
using descriptor_t = DESCRIPTOR;

CellDistance getNeighborhoodRadius() {
  return 1;
}

std::optional<DynamicsPromise<T,DESCRIPTOR>> getDynamics(DiscreteNormalType type,
                                                         DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::PlainMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      CombinedRLBdynamics,MixinDynamics,momenta::RegularizedVelocityBoundaryTuple
      >::construct(n);

  case DiscreteNormalType::ExternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::PlainMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      CombinedRLBdynamics,MixinDynamics,momenta::RegularizedVelocityBoundaryTuple
      >::construct(n);

  case DiscreteNormalType::InternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::PlainMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      CombinedRLBdynamics,MixinDynamics,momenta::RegularizedVelocityBoundaryTuple
      >::construct(n);

  default:
    return std::nullopt;
  }
}

std::optional<PostProcessorPromise<T,DESCRIPTOR>> getPostProcessor(DiscreteNormalType type,
                                                                   DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,FreeEnergyInletMomentum3D>(n);

  case DiscreteNormalType::ExternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,FreeEnergyInletMomentum3D>(n);

  case DiscreteNormalType::InternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,FreeEnergyInletMomentum3D>(n);

  default:
    return std::nullopt;
  }
}

};

template <concepts::BaseType T, concepts::LatticeDescriptor DESCRIPTOR, typename MixinDynamics>
requires (DESCRIPTOR::d == 3)
struct FreeEnergyPressure<T,DESCRIPTOR,MixinDynamics> {

using value_t = T;
using descriptor_t = DESCRIPTOR;

CellDistance getNeighborhoodRadius() {
  return 1;
}

std::optional<DynamicsPromise<T,DESCRIPTOR>> getDynamics(DiscreteNormalType type,
                                                         DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::PlainMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      CombinedRLBdynamics,MixinDynamics,momenta::RegularizedPressureBoundaryTuple
      >::construct(n);

  case DiscreteNormalType::ExternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::PlainMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      CombinedRLBdynamics,MixinDynamics,momenta::RegularizedPressureBoundaryTuple
      >::construct(n);

  case DiscreteNormalType::InternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::PlainMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      CombinedRLBdynamics,MixinDynamics,momenta::RegularizedPressureBoundaryTuple
      >::construct(n);

  default:
    return std::nullopt;
  }
}

std::optional<PostProcessorPromise<T,DESCRIPTOR>> getPostProcessor(DiscreteNormalType type,
                                                                   DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,FreeEnergyInletMomentum3D>(n);

  case DiscreteNormalType::ExternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,FreeEnergyInletMomentum3D>(n);

  case DiscreteNormalType::InternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,FreeEnergyInletMomentum3D>(n);

  default:
    return std::nullopt;
  }
}

};

template <concepts::BaseType T, concepts::LatticeDescriptor DESCRIPTOR, typename MixinDynamics>
requires (DESCRIPTOR::d == 3)
struct FreeEnergyPressureConvective<T,DESCRIPTOR,MixinDynamics> {

using value_t = T;
using descriptor_t = DESCRIPTOR;

CellDistance getNeighborhoodRadius() {
  return 1;
}

std::optional<DynamicsPromise<T,DESCRIPTOR>> getDynamics(DiscreteNormalType type,
                                                         DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::PlainMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      CombinedRLBdynamics,MixinDynamics,momenta::RegularizedPressureBoundaryTuple
      >::construct(n);

  case DiscreteNormalType::ExternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::PlainMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      CombinedRLBdynamics,MixinDynamics,momenta::RegularizedPressureBoundaryTuple
      >::construct(n);

  case DiscreteNormalType::InternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::PlainMixinDynamicsForDirectionOrientationMomenta<T,DESCRIPTOR,
      CombinedRLBdynamics,MixinDynamics,momenta::RegularizedPressureBoundaryTuple
      >::construct(n);

  default:
    return std::nullopt;
  }
}

std::optional<PostProcessorPromise<T,DESCRIPTOR>> getPostProcessor(DiscreteNormalType type,
                                                                   DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,FreeEnergyOutletMomentum3D>(n);

  case DiscreteNormalType::ExternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,FreeEnergyOutletMomentum3D>(n);

  case DiscreteNormalType::InternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,FreeEnergyOutletMomentum3D>(n);

  default:
    return std::nullopt;
  }
}

};

template <concepts::BaseType T, concepts::LatticeDescriptor DESCRIPTOR>
requires (DESCRIPTOR::d == 3)
struct FreeEnergyOrderParameter<T,DESCRIPTOR> {

using value_t = T;
using descriptor_t = DESCRIPTOR;

CellDistance getNeighborhoodRadius() {
  return 1;
}

std::optional<DynamicsPromise<T,DESCRIPTOR>> getDynamics(DiscreteNormalType type,
                                                         DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::DirectionOrientationDynamics<T,DESCRIPTOR,FreeEnergyInletOutletDynamics>
    ::construct(n);

  case DiscreteNormalType::ExternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return std::nullopt;

  case DiscreteNormalType::InternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return std::nullopt;

  default:
    return std::nullopt;
  }
}

std::optional<PostProcessorPromise<T,DESCRIPTOR>> getPostProcessor(DiscreteNormalType type,
                                                                   DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,FreeEnergyInletOrderParameter3D>(n);

  case DiscreteNormalType::ExternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return std::nullopt;

  case DiscreteNormalType::InternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return std::nullopt;

  default:
    return std::nullopt;
  }
}

};

template <concepts::BaseType T, concepts::LatticeDescriptor DESCRIPTOR>
requires (DESCRIPTOR::d == 3)
struct FreeEnergyOrderParameterConvective<T,DESCRIPTOR> {

using value_t = T;
using descriptor_t = DESCRIPTOR;

CellDistance getNeighborhoodRadius() {
  return 1;
}

std::optional<DynamicsPromise<T,DESCRIPTOR>> getDynamics(DiscreteNormalType type,
                                                         DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::DirectionOrientationDynamics<T,DESCRIPTOR,FreeEnergyInletOutletDynamics>
    ::construct(n);

  case DiscreteNormalType::ExternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return std::nullopt;

  case DiscreteNormalType::InternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return std::nullopt;

  default:
    return std::nullopt;
  }
}

std::optional<PostProcessorPromise<T,DESCRIPTOR>> getPostProcessor(DiscreteNormalType type,
                                                                   DiscreteNormal<DESCRIPTOR> n) {
  switch (type) {
  case DiscreteNormalType::Flat:
    return boundaryhelper::promisePostProcessorForNormal<T,DESCRIPTOR,FreeEnergyOutletOrderParameter3D>(n);

  case DiscreteNormalType::ExternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return std::nullopt;

  case DiscreteNormalType::InternalCorner:
    throw std::runtime_error("No valid discrete normal found. This BC is not suited for curved walls.");
    return std::nullopt;

  default:
    return std::nullopt;
  }
}

};

}

*/

}

#endif
