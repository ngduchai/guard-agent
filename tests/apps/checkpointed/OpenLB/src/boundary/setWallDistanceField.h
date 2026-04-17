/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Fedor Bukreev, Michael Grinschewski
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
#ifndef SETWALLDISTANCEFIELD
#define SETWALLDISTANCEFIELD

#include "core/util.h"
#include "../functors/primitive/getSurfaceVector.h"
namespace olb{

template<typename T, typename DESCRIPTOR, typename FIELD>
void setWallDistanceField(SuperLattice<T, DESCRIPTOR>& sLattice,
                     FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& boundaryIndicator,
                     IndicatorF<T,DESCRIPTOR::d>* indicatorAnalyticalBoundary = nullptr,
                     int accuracy = 128) any_platform
{
  int _overlap = 3;

  auto& load = sLattice.getLoadBalancer();
  for (int iC=0; iC < load.size(); ++iC) {
    setWallDistanceField<T,DESCRIPTOR,FIELD>(sLattice.getBlock(iC),
                                  (boundaryIndicator->getBlockIndicatorF(iC)).getBlockGeometry(),
                                  boundaryIndicator->getBlockIndicatorF(iC),
                                  indicatorAnalyticalBoundary,
                                  accuracy);
  }
  addPoints2CommBC<T,DESCRIPTOR>(sLattice, std::forward<decltype(boundaryIndicator)>(boundaryIndicator), _overlap);
}

template<typename T, typename DESCRIPTOR, typename FIELD>
void setWallDistanceField(BlockLattice<T,DESCRIPTOR>& block,
                           BlockGeometry<T,DESCRIPTOR::d>& blockGeometry,
                           BlockIndicatorF<T,DESCRIPTOR::d>& boundaryIndicator,
                           IndicatorF<T,DESCRIPTOR::d>* indicatorAnalyticalBoundary = nullptr,
                           int nSamplingPoints = 128) any_platform
{
  // Defining boundary distance y1 and distance to exchange location y2 in wall normal direction for every boundary cell
  block.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> latticeR) {
    // Check if cell is solid cell
    if (boundaryIndicator(latticeR)) {
      for (int iPop=1; iPop < DESCRIPTOR::q; ++iPop) {
        Vector<T,DESCRIPTOR::d> latticeR2(latticeR + descriptors::c<DESCRIPTOR>(iPop));
        if (blockGeometry.getNeighborhoodRadius(latticeR2) >= 1) {
          if (blockGeometry.isInside(latticeR2)) {
          Vector<T,DESCRIPTOR::d> y1;
            // check if neighbor is fluid cell
            if(indicatorAnalyticalBoundary){
              T physDeltaX = blockGeometry.getDeltaR();
              Vector<T,DESCRIPTOR::d> physR;
              blockGeometry.getPhysR(physR, latticeR2);
              y1 = getSurfaceVector<T,DESCRIPTOR>(physDeltaX, indicatorAnalyticalBoundary, physR, nSamplingPoints);
            }
            else{
              y1 = getSurfaceVector<T,DESCRIPTOR>(boundaryIndicator, latticeR2);
            }
            block.get(latticeR2).template setField<FIELD>(y1);
          }
        }
      }
    }
  });
}
} // namespace
#endif

