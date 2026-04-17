/*  Lattice Boltzmann sample, written in C++, using the OpenLB
 *  library
 *
 *  Copyright (C) 2025 Shota Ito
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

#ifndef REGULARIZATION_F_H
#define REGULARIZATION_F_H

namespace olb {

namespace functors {

/// Computes the physical velocity
template <typename CONTROLS>
struct TikhonovRegularizationF {
  using parameters_t = meta::list<parameters::REG_ALPHA>;
  using result_t = opti::REGULARIZATION;
  using fields_t = meta::list<CONTROLS>;

  template <typename CELL, typename PARAMETERS>
  auto compute(CELL& cell, PARAMETERS& parameters) any_platform {
    using V = typename CELL::value_t;
    using DESCRIPTOR = typename CELL::descriptor_t;
    const V regAlpha = parameters.template get<parameters::REG_ALPHA>();

    Vector controls = cell.template getField<CONTROLS>();
    FieldD<V,DESCRIPTOR,result_t> regularization{};
    for (std::size_t iDim=0; iDim<CONTROLS::template size<DESCRIPTOR>(); ++iDim) {
      regularization += util::fabs(controls[iDim]);
    }
    regularization *= regAlpha;
    return regularization;
  }
};

}

}

#endif
