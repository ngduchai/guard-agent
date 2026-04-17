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

#ifndef OBJECTIVE_F_H
#define OBJECTIVE_F_H

#include "../concepts.h"

namespace olb {

namespace functors {

template <typename FIELD>
struct L2F {

  using parameters_t = meta::list<parameters::DX>;
  using result_t = descriptors::L2_NORM;
  using fields_t = meta::list<>;

  template <typename CELL, typename PARAMETERS>
  auto compute(CELL& cell, PARAMETERS& parameters) any_platform {
    using V = typename CELL::value_t;
    using DESCRIPTOR = typename CELL::descriptor_t;
    V dx = parameters.template get<parameters::DX>();

    FieldD<V,DESCRIPTOR,FIELD> value = cell.template getField<FIELD>();

    FieldD<V,DESCRIPTOR,result_t> norm;
    for (int iDim=0; iDim < value.getDim(); ++iDim) {
      norm[0] += util::pow(value[iDim], 2);
    }
    norm[0] *= util::pow(dx,DESCRIPTOR::d);

    return norm;
  }
};

// Computes "j = 0.5 * (phi - phi_ref)^2 / normalize", used for inverse problems
// FUNCTOR specifies how "phi" is computed in physical units and "phi_ref" is
// provided via fields (could be simulation or external data).
template <concepts::DifferentiableFunctor FUNCTOR>
struct L2DistanceF {

  struct Reference : public FUNCTOR::result_t { };

  using parameters_t = typename FUNCTOR::parameters_t::template include<parameters::NORMALIZE>;
  using result_t = opti::J;
  using fields_t = typename FUNCTOR::fields_t::template include<result_t,
                                                                L2DistanceF<FUNCTOR>::Reference>;

  template <typename CELL, typename PARAMETERS>
  auto compute(CELL& cell, PARAMETERS& parameters) any_platform {
    using V = typename CELL::value_t;
    using DESCRIPTOR = typename CELL::descriptor_t;
    V normalize = parameters.template get<parameters::NORMALIZE>();

    FieldD<V,DESCRIPTOR,typename FUNCTOR::result_t> phi = FUNCTOR{}.compute(cell, parameters);
    FieldD<V,DESCRIPTOR,Reference> phi_ref = cell.template getField<Reference>();

    FieldD<V,DESCRIPTOR,result_t> j;
    for (int iDim=0; iDim < phi.getDim(); ++iDim) {
      j[0] += util::pow(phi[iDim] - phi_ref[iDim], 2);
    }
    j[0] *= 0.5 / normalize;

    return j;
  }
};

}

}

#endif
