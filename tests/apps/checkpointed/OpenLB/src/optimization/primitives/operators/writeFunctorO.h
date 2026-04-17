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

#ifndef WRITE_FUNCTOR_O_H
#define WRITE_FUNCTOR_O_H

#include <core/operator.h>
#include "../singleLatticeO.h"

namespace olb {

namespace operators {

/// Operator which evaluate a functor and write its results into the passed field
template <concepts::PrimitiveFunctor FUNCTOR, typename TO>
struct WriteFunctorO {
  static constexpr OperatorScope scope = OperatorScope::PerCellWithParameters;
  using parameters = FUNCTOR::parameters_t;

  int getPriority() const {
   return 0;
  }

  template <typename CELL, typename PARAMETERS>
  void apply(CELL& cell, PARAMETERS& parameters) any_platform
  {
    cell.template setField<TO>(FUNCTOR{}.compute(cell, parameters));
  }
};

}

// Returns a unique pointer to the SingleLatticeO with the writing operator
template <typename FUNCTOR, typename TO, typename T, typename DESCRIPTOR>
auto makeWriteFunctorO(SuperLattice<T,DESCRIPTOR>& lattice) {
  return makeSingleLatticeO<operators::WriteFunctorO<FUNCTOR,TO>>(lattice);
}

template <typename FUNCTOR, typename TO, typename T, typename DESCRIPTOR>
void writeFunctorTo(SuperLattice<T,DESCRIPTOR>& lattice) {
  auto superLatticeO = makeSingleLatticeO<operators::WriteFunctorO<FUNCTOR,TO>>(lattice);
  superLatticeO->apply();
}

template <typename FUNCTOR, typename TO, typename T, typename DESCRIPTOR>
void writeFunctorTo(SuperLattice<T,DESCRIPTOR>& lattice,
                    FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>&& indicator) {
  auto superLatticeO = makeSingleLatticeO<operators::WriteFunctorO<FUNCTOR,TO>>(lattice);
  superLatticeO->restrictTo(std::forward<FunctorPtr<SuperIndicatorF<T,DESCRIPTOR::d>>>(indicator));
  superLatticeO->apply();
}

}
#endif
