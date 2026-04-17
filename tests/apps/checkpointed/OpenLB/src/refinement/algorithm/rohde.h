/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Adrian Kummerlaender
 *
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

#ifndef REFINEMENT_ALGORITHM_ROHDE_H
#define REFINEMENT_ALGORITHM_ROHDE_H

namespace olb::refinement::rohde {

struct CoarseToFineO {
  static constexpr refinement::OperatorScope scope = refinement::OperatorScope::PerCellCenteredCoarseCell;

  using parameters = meta::list<>;

  using data = meta::list<fields::refinement::NORMAL>;

  template <typename COARSE_CELL, typename FINE_CELL, typename DATA, typename PARAMETERS>
  void apply(COARSE_CELL& cCell, FINE_CELL& fMother, DATA& data, PARAMETERS& params) any_platform {
    using DESCRIPTOR = typename COARSE_CELL::descriptor_t;

    const Vector<int,DESCRIPTOR::d> normal = data.template getField<fields::refinement::NORMAL>();

    for (unsigned iOrthant=0; iOrthant < (unsigned{1} << DESCRIPTOR::d); ++iOrthant) {
      const Vector<int,DESCRIPTOR::d> o_i([iOrthant](unsigned j) -> int {
        return 2*((iOrthant >> (DESCRIPTOR::d-1-j)) & 1) - 1;
      });
      auto fCell = fMother.child(o_i);
      for (int iPop=1; iPop < DESCRIPTOR::q; ++iPop) {
        if (descriptors::c<DESCRIPTOR>(iPop) * normal <= 0) {
          fCell[iPop] = cCell[iPop];
        }
      }
    }
  }
};

struct FineToCoarseO {
  static constexpr refinement::OperatorScope scope = refinement::OperatorScope::PerCellCenteredCoarseCell;

  using parameters = meta::list<>;

  using data = meta::list<fields::refinement::NORMAL>;

  template <typename COARSE_CELL, typename FINE_CELL, typename DATA, typename PARAMETERS>
  void apply(COARSE_CELL& cCell, FINE_CELL& fMother, DATA& data, PARAMETERS& params) any_platform {
    using DESCRIPTOR = typename COARSE_CELL::descriptor_t;
    const Vector<int,DESCRIPTOR::d> normal = data.template getField<fields::refinement::NORMAL>();

    for (unsigned iPop=1; iPop < DESCRIPTOR::q; ++iPop) {
      if (descriptors::c<DESCRIPTOR>(iPop) * normal > 0) {
        cCell[iPop] = 0;
        for (unsigned iOrthant=0; iOrthant < (unsigned{1} << DESCRIPTOR::d); ++iOrthant) {
          const Vector<int,DESCRIPTOR::d> o_i([iOrthant](unsigned j) -> int {
            return 2*((iOrthant >> (DESCRIPTOR::d-1-j)) & 1) - 1;
          });
          auto fCell = fMother.child(o_i);
          cCell[iPop] += fCell[iPop];
        }
        cCell[iPop] /= (unsigned{1} << DESCRIPTOR::d);
      }
    }
  }
};

template <typename T, typename DESCRIPTOR>
std::unique_ptr<SuperLatticeRefinement<T,DESCRIPTOR>> makeCoupler(
  SuperLattice<T,DESCRIPTOR>& sLatticeCoarse,
  SuperGeometry<T,DESCRIPTOR::d>& sGeometryCoarse,
  SuperLattice<T,DESCRIPTOR>& sLatticeFine,
  SuperGeometry<T,DESCRIPTOR::d>& sGeometryFine,
  FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& fineBulkI)
{
  auto& loadBalancerFine = dynamic_cast<RefinedLoadBalancer<T,DESCRIPTOR::d>&>(
    sLatticeFine.getLoadBalancer());
  auto& cDecompositionFine = sLatticeFine.getCuboidDecomposition();

  SuperIndicatorDomainFrontierDistanceF<T,DESCRIPTOR> frontierI(cDecompositionFine,
                                                                sGeometryFine,
                                                                0);
  SuperIndicatorDomainFrontierDistanceF<T,DESCRIPTOR> insideI(cDecompositionFine,
                                                              sGeometryFine,
                                                              1);
  SuperIndicatorDomainFrontierDistanceF<T,DESCRIPTOR> outsideI(cDecompositionFine,
                                                               sGeometryFine,
                                                               -1);

  auto coupler = std::make_unique<SuperLatticeRefinement<T,DESCRIPTOR>>(
    sLatticeCoarse, sLatticeFine, loadBalancerFine);

  for (int iC = 0; iC < loadBalancerFine.size(); ++iC) {
    auto& cBlock = sLatticeCoarse.getBlock(loadBalancerFine.cloc(iC));
    auto& fBlock = sLatticeFine.getBlock(iC);

    cBlock.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> coarseLatticeR) {
      if (   frontierI.getBlockIndicatorF(iC)(2*coarseLatticeR)
          && fineBulkI->getBlockIndicatorF(iC)(2*coarseLatticeR)
          && cBlock.getNeighborhoodRadius(coarseLatticeR) >= 1) {
        coupler->getBlock(iC).addCellCentered(coarseLatticeR);

        // Bitshift (unsigned{1} << 2) results in 4 orthants for 2D case,
        // (unsigned{1} << 3) will results in 8 orthants for the 3D case
        unsigned int numberOrthants = unsigned{1} << DESCRIPTOR::d;

        for (unsigned iOrthant = 0; iOrthant < numberOrthants; ++iOrthant) {
          Vector<int, DESCRIPTOR::d> offset;
          for (int j = 0; j < DESCRIPTOR::d; ++j) {
            offset[j] = (iOrthant >> (DESCRIPTOR::d - 1 - j)) & 1;
          }
          sLatticeFine.getBlock(iC).template defineDynamics<NoDynamics>(2 * coarseLatticeR + offset);
        }
      }
    });

    cBlock.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> coarseLatticeR) {
      if (   frontierI.getBlockIndicatorF(iC)(2*coarseLatticeR)
          && fineBulkI->getBlockIndicatorF(iC)(2*coarseLatticeR)
          && cBlock.getNeighborhoodRadius(coarseLatticeR) >= 1) {
        if (auto index = coupler->getBlock(iC).getCoarseDataIndex(coarseLatticeR)) {
          auto [type, normal] = computeBoundaryTypeAndNormal(insideI.getBlockIndicatorF(iC), outsideI.getBlockIndicatorF(iC), 2*coarseLatticeR);
          coupler->getBlock(iC).getData()
                               .template getField<fields::refinement::NORMAL>().set(*index, normal);
        } else {
          throw std::logic_error("Invalid cell-centered coupling setup");
        }
      }
    });

    fBlock.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> latticeR) {
      if (fBlock.isPadding(latticeR) && !cDecompositionFine.isInside(
          cDecompositionFine.getPhysR(latticeR.withPrefix(loadBalancerFine.glob(iC))))) {
        fBlock.template defineDynamics<NoDynamics>(latticeR);
      }
    });
  }

  coupler->setProcessingContext(ProcessingContext::Simulation);

  return coupler;
}

}

#endif
