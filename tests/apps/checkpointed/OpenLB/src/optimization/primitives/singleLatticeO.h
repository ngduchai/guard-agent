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

#ifndef SINGLE_LATTICE_O_H
#define SINGLE_LATTICE_O_H

#include "core/superLatticeCoupling.h"

namespace olb {

/// Wrapper class for SuperLatticeCoupling with only a single lattice instance
/// in order to allow operator executions with seperated ParameterD instances.
template <typename OPERATOR>
struct SingleLatticeO {
  static constexpr OperatorScope scope = OPERATOR::scope;
  using parameters = typename OPERATOR::parameters;

  template <typename CELLS> requires (OPERATOR::scope == OperatorScope::PerCell)
  void apply(CELLS& cells) any_platform {
    OPERATOR().apply(cells.template get<names::Lattice1>());
  }
  template <typename CELLS, typename PARAMETERS> requires (OPERATOR::scope == OperatorScope::PerCellWithParameters)
  void apply(CELLS& cells, PARAMETERS& parameters) any_platform {
    OPERATOR().apply(cells.template get<names::Lattice1>(), parameters);
  }
  template <typename BLOCKS> requires (OPERATOR::scope == OperatorScope::PerBlock)
  void setup(BLOCKS& blocks) any_platform {
    OPERATOR().setup(blocks.template get<names::Lattice1>());
  }
  template <typename BLOCKS> requires (OPERATOR::scope == OperatorScope::PerBlock)
  void apply(BLOCKS& blocks) any_platform {
    OPERATOR().apply(blocks.template get<names::Lattice1>());
  }
  template <typename BLOCKS, typename PARAMETERS> requires (OPERATOR::scope == OperatorScope::PerBlockWithParameters)
  void setup(BLOCKS& blocks, PARAMETERS& parameters) any_platform {
    OPERATOR().setup(blocks.template get<names::Lattice1>(), parameters);
  }
  template <typename BLOCKS, typename PARAMETERS> requires (OPERATOR::scope == OperatorScope::PerBlockWithParameters)
  void apply(BLOCKS& blocks, PARAMETERS& parameters) any_platform {
    OPERATOR().apply(blocks.template get<names::Lattice1>(), parameters);
  }
};

template <typename OPERATOR, typename T, typename DESCRIPTOR>
auto makeSingleLatticeO(SuperLattice<T,DESCRIPTOR>& lattice) {
  return std::make_unique<SuperLatticeCoupling<SingleLatticeO<OPERATOR>,
                                               meta::map<names::Lattice1,
                                               descriptors::VALUED_DESCRIPTOR<T,DESCRIPTOR>>>>
    (SingleLatticeO<OPERATOR>(), names::Lattice1(), lattice);
}

}

#endif
