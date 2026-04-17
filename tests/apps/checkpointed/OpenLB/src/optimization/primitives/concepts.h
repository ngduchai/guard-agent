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

#ifndef PRIMITIVE_CONCEPTS_H
#define PRIMITIVE_CONCEPTS_H

#include "core/concepts.h"

namespace olb {

namespace concepts {

template <typename PARAMETER_LIST>
concept ParameterList = requires () {
  requires std::is_base_of_v<meta::list_base, PARAMETER_LIST>;
};

template <typename FIELD_LIST>
concept FieldList = requires () {
  requires std::is_base_of_v<meta::list_base, FIELD_LIST>;
};

template <typename FUNCTOR>
concept PrimitiveFunctor = requires() {
  // FUNCTOR::parameters is a valid list of used parameters
  requires ParameterList<typename FUNCTOR::parameters_t>;
  // FUNCTOR::result_t is a valid field type
  requires Field<typename FUNCTOR::result_t>;
  // FUNCTOR provide a compute method
};

template <typename FUNCTOR>
concept DifferentiableFunctor = requires() {
  // Needs to be a primitive functor
  requires PrimitiveFunctor<FUNCTOR>;
  // FUNCTOR::fields is a valid list of used fields
  // This is necessary as the AD-cell needs all primal data
  requires FieldList<typename FUNCTOR::fields_t>;
};

//template <typename DYNAMICS>
//concept DifferentiableDynamics = requires () {
  // TODO: This requires refactoring of all dynamics
  // but is requires to omit the necessiry to put all
  // accessed fields in the DESCRIPTOR when one uses
  // adjoint optimization in OpenLB.

  // requires FieldList<typename DYNAMICS::fields>;
//};

}

}

#endif
