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

#ifndef MATH_F_H
#define MATH_F_H

namespace olb {

namespace functors {

/// Computes the physical velocity
template <concepts::DifferentiableFunctor FUNCTOR_1, concepts::PrimitiveFunctor FUNCTOR_2>
struct AddF {
  using parameters_t = meta::merge<typename FUNCTOR_1::parameters_t,
                                 typename FUNCTOR_2::parameters_t>;

  using result_t = FUNCTOR_1::result_t;
  using fields_t = meta::merge<typename FUNCTOR_1::fields_t,
                               typename FUNCTOR_2::fields_t>;

  template <typename CELL, typename PARAMETERS>
  auto compute(CELL& cell, PARAMETERS& parameters) any_platform {
    using V = typename CELL::value_t;
    using DESCRIPTOR = typename CELL::descriptor_t;
    FieldD<V,DESCRIPTOR,typename FUNCTOR_1::result_t> left = FUNCTOR_1{}.compute(cell, parameters);
    FieldD<V,DESCRIPTOR,typename FUNCTOR_2::result_t> right = FUNCTOR_2{}.compute(cell, parameters);
    FieldD<V,DESCRIPTOR,result_t> sum = left + right;
    return sum;
  }
};

template <concepts::DifferentiableFunctor FUNCTOR, unsigned EXPONENT>
struct PowF {
  using parameters_t = typename FUNCTOR::parameters_t;

  using result_t = FUNCTOR::result_t;
  using fields_t = FUNCTOR::fields_t;

  template <typename CELL, typename PARAMETERS>
  auto compute(CELL& cell, PARAMETERS& parameters) any_platform {
    using V = typename CELL::value_t;
    // Require results of the functor to be a scalar
    Vector<V,1> results = FUNCTOR{}.compute(cell, parameters);
    return util::pow(results[0], EXPONENT);
  }
};

}

}

#endif
