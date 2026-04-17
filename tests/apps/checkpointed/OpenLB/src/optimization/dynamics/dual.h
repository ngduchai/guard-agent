/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2012 Mathias J. Krause
 *                2024 Julius Jessberger, Adrian Kummerlaender, Shota Ito
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

#ifndef DUAL_H
#define DUAL_H

#include "optimization/functors/dualLbHelpers.h"

#include "utilities/vectorHelpers.h"
#include "utilities/aDiffTape.h"

// All OpenLB code is contained in this namespace.
namespace olb {

namespace collision {

template <typename PRIMAL>
struct Dual {

template <typename CELL, typename PARAMETERS, typename V=typename CELL::value_t, typename DESCRIPTOR=typename CELL::descriptor_t>
CellStatistic<V> apply(CELL& cell, PARAMETERS& parameters) {
  using Tape = util::ADtape::Tape<V>;
  using ActiveType = util::ADtape::ActiveType<Tape>;
  auto& tape = ActiveType::getTape();

  Vector<int,DESCRIPTOR::d> size(1);
  ConcreteBlockLattice<ActiveType,DESCRIPTOR,Platform::CPU_SISD> adrLattice(size,0);
  adrLattice.setStatisticsEnabled(false);
  cpu::Cell<ActiveType,DESCRIPTOR,Platform::CPU_SISD> adFcell(adrLattice);
  adFcell.template setField<descriptors::POPULATION>(cell.template getField<opti::F>());
  adFcell.template setField<descriptors::FORCE>(cell.template getField<descriptors::FORCE>());
  FieldD<ActiveType,DESCRIPTOR,descriptors::POROSITY> porosity{ cell.template getField<descriptors::POROSITY>() };
  adFcell.template setField<descriptors::POROSITY>(porosity);
  adFcell.template setField<momenta::FixedVelocityMomentumGeneric::VELOCITY>(cell.template getField<momenta::FixedVelocityMomentumGeneric::VELOCITY>());

  auto adParams = parameters.template copyAs<ActiveType>();

  int idFstar[DESCRIPTOR::q];

  for (unsigned iPop=0; iPop < DESCRIPTOR::q; ++iPop) {
    tape.registerInput(adFcell[iPop]);
    idFstar[iPop] = adFcell[iPop].getIdentifier();
  }

  PRIMAL{}.collide(adFcell, adParams);

  for (int iPop=1; iPop <= DESCRIPTOR::q/2; ++iPop) {
    const V cell_iPop = cell[iPop];
    cell[iPop] = cell[descriptors::opposite<DESCRIPTOR>(iPop)];
    cell[descriptors::opposite<DESCRIPTOR>(iPop)] = cell_iPop;
  }

  for (unsigned iPop=0; iPop < DESCRIPTOR::q; ++iPop) {
    tape.registerOutput(adFcell[iPop]);
    adFcell[iPop].gradient() = cell[iPop];
  }

  tape.evaluate();

  for (unsigned iPop=0; iPop < DESCRIPTOR::q; ++iPop) {
    cell[iPop] = tape.gradient(idFstar[iPop]) + cell.template getFieldComponent<opti::DJDF>(iPop);
  }

  tape.reset();

  for (int iPop=1; iPop <= DESCRIPTOR::q/2; ++iPop) {
    const V cell_iPop = cell[iPop];
    cell[iPop] = cell[descriptors::opposite<DESCRIPTOR>(iPop)];
    cell[descriptors::opposite<DESCRIPTOR>(iPop)] = cell_iPop;
  }

  V phi2 {};
  for (int iPop=0; iPop < DESCRIPTOR::q; ++iPop) {
    phi2 += cell[iPop]*cell[iPop];
  }
  return {V(1) + cell[0], phi2};
};

};

}

template <typename DUAL>
concept IsDualDynamics = requires { typename DUAL::primalDynamics; };

template <typename PRIMAL, typename T=typename PRIMAL::value_t, typename DESCRIPTOR=typename PRIMAL::descriptor_t>
struct Dual final : public dynamics::CustomCollision<T,DESCRIPTOR,momenta::BulkTuple> {
  // TODO: Decide which momenta to expose for dual dynamics
  using MomentaF = typename momenta::BulkTuple::template type<DESCRIPTOR>;
  using EquilibriumF = typename PRIMAL::EquilibriumF;
  using parameters = typename PRIMAL::parameters;

  // expose PRIMAL dynamics type
  using primalDynamics = PRIMAL;

  template <typename NEW_T>
  using exchange_value_type = Dual<typename PRIMAL::template exchange_value_type<NEW_T>,NEW_T,DESCRIPTOR>;

  template <typename M>
  using exchange_momenta = Dual<PRIMAL,T,DESCRIPTOR>;

  std::type_index id() override {
    return typeid(Dual);
  }

  AbstractParameters<T,DESCRIPTOR>& getParameters(BlockLattice<T,DESCRIPTOR>& block) override {
    return block.template getData<OperatorParameters<Dual>>();
  }

  template <typename CELL, typename PARAMETERS, typename V=typename CELL::value_t>
  CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) {
    return collision::Dual<PRIMAL>().apply(cell, parameters);
  };

  void computeEquilibrium(ConstCell<T,DESCRIPTOR>& cell, T rho, const T u[DESCRIPTOR::d], T fEq[DESCRIPTOR::q]) const override {
    typename PRIMAL::EquilibriumF().compute(cell, rho, u, fEq);
  };

  std::string getName() const override {
    return "Dual<" + PRIMAL().getName() + ">";
  };

};

} // namespace olb

#endif
