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

#pragma once

namespace olb{
namespace parameters {
    struct BC_INTENSITY : public descriptors::FIELD_BASE<1> { };
}


//======================================================================
// ======== Radiative Transport Boundary PostProcessor ======//
//======================================================================

template<typename T, typename DESCRIPTOR, int discreteNormalX, int discreteNormalY, int discreteNormalZ>
class RtlbmDirectedBoundaryPostProcessor3D{
    public:
    static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;
    using parameters = meta::list<parameters::BC_INTENSITY>;

    int getPriority() const {
        return 0;
    }

    template <typename CELL, typename PARAMETERS>
    void apply(CELL& cell, PARAMETERS& parameters) any_platform{
        const T intensity = parameters.template get<olb::parameters::BC_INTENSITY>();
        for(int iPop = 0; iPop<DESCRIPTOR::q; iPop++){
            const auto c = descriptors::c<DESCRIPTOR>(iPop);
            T k = c[0]*discreteNormalX + c[1]*discreteNormalY + c[2]*discreteNormalZ;
            T norm_c = std::sqrt(c[0]*c[0] + c[1]*c[1] + c[2]*c[2]);
            T norm_n = std::sqrt(discreteNormalX*discreteNormalX + discreteNormalY*discreteNormalY + discreteNormalZ*discreteNormalZ);
            T cos_theta = k / (norm_c * norm_n);
            if (util::nearZero(cos_theta + 1.)) {
                cell[iPop] = (1 - descriptors::t<T,DESCRIPTOR>(0))*intensity - descriptors::t<T,DESCRIPTOR>(iPop);
            } else {
                cell[iPop] = - descriptors::t<T,DESCRIPTOR>(iPop);
            }
        }
    }
};

// Set RtlbmDirectedBoundary for any indicated cells inside the block domain
template<typename T, typename DESCRIPTOR>
void setRtlbmDirectedBoundary(BlockLattice<T,DESCRIPTOR>& _block, BlockIndicatorF3D<T>& indicator)
{
  using namespace boundaryhelper;
  const auto& blockGeometryStructure = indicator.getBlockGeometry();
  std::vector<int> discreteNormal(4,0);
  blockGeometryStructure.forSpatialLocations([&](auto iX, auto iY, auto iZ) {
    if (indicator(iX, iY, iZ)) {
      discreteNormal = blockGeometryStructure.getStatistics().getType(iX, iY, iZ);
      if (discreteNormal[1]!=0 || discreteNormal[2]!=0 || discreteNormal[3]!=0) {
        _block.addPostProcessor(
          typeid(stage::PostCollide), {iX,iY,iZ},
          promisePostProcessorForNormal<T, DESCRIPTOR, RtlbmDirectedBoundaryPostProcessor3D>(
            Vector<int,3>(discreteNormal.data()+1)
          )
        );
        _block.template defineDynamics<NoCollideDynamics>({iX, iY, iZ});
      } else {
        _block.template defineDynamics<BounceBack>({iX, iY, iZ});
      }
    }
  });
};

// Initialising the setRtlbmDirectedBoundary function on the superLattice domain
template<typename T, typename DESCRIPTOR>
void setRtlbmDirectedBoundary(SuperLattice<T, DESCRIPTOR>& sLattice, FunctorPtr<SuperIndicatorF3D<T>>&& indicator)
{
  OstreamManager clout(std::cout, "setRtlbmDirectedBoundary");

  for (int iCloc = 0; iCloc < sLattice.getLoadBalancer().size(); iCloc++) {
    setRtlbmDirectedBoundary<T,DESCRIPTOR>(sLattice.getBlock(iCloc), indicator->getBlockIndicatorF(iCloc));
  }
};

}
