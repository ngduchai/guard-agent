/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2024 Shota Ito
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

#ifndef CORE_CSE_H
#define CORE_CSE_H

#include <type_traits>

#include "core/expr.h"
#include "optimization/dual.h"

namespace olb {

namespace cse {

/// Generator of the expressions
class SymbolGenerator {
private:
  std::string _symbol = "x";
  unsigned int _count = 0;
public:
  SymbolGenerator() = default;

  std::string next() {
    unsigned int tmp = _count;
    ++_count;
    return _symbol + std::to_string(tmp);
  }
};

/// Helper function to print symbols
std::string symbol(Expr symbol) {
  return "Symbol(\"" + symbol.describe() + "\")";
}

/// Helper function to print symbols
std::string symbol(std::string symbol) {
  return "Symbol(\"" + symbol + "\")";
}

std::string assignment(std::string lhs, std::string rhs) {
  return "Assignment(" + lhs + "," + rhs + ")";
}

template<typename DYNAMICS>
std::stringstream extractExpressionTree() {
  std::stringstream tree;
  using T = Expr;
  using DESCRIPTOR = DYNAMICS::descriptor_t;
  using PARAMETERS = DYNAMICS::parameters;

  // Instatiate a 1x1 BlockLattice with Expr type
  Vector<int,DESCRIPTOR::d> size(1);
  ConcreteBlockLattice<T,DESCRIPTOR,Platform::CPU_SISD> exprLattice(size, 0);
  // This is required as invalid operators for Expr are used in CellStatistics
  exprLattice.setStatisticsEnabled(false);

  // Set dynamics to the cells
  exprLattice.setDynamics(0, meta::id<dynamics::StoreStatisticInField<DYNAMICS>>{});

  // Initialize expressions for the populations
  Vector<int,DESCRIPTOR::d> pos(0);
  auto cell = exprLattice.get(pos);

  for (auto field : introspection::getFieldsAccessedByDynamics<T,DESCRIPTOR,DYNAMICS>()) {
    if (field.name().starts_with("Array<")) {
      field.setPlaceholderExpression(cell);
      std::cout << "NAME: " << field.name() << std::endl;
    }
  }

  // If DUAL dynamics, retrieve also field access from PRIMAL dynamics
  if constexpr (IsDualDynamics<DYNAMICS>) {
    using PRIMAL = typename DYNAMICS::primalDynamics;
    for (auto field : introspection::getFieldsAccessedByDynamics<T,DESCRIPTOR,PRIMAL>()) {
      if (field.name().starts_with("Array<")) {
        field.setPlaceholderExpression(cell);
        std::cout << "NAME: " << field.name() << std::endl;
      }
    }
  }


  for (int iPop=0; iPop < DESCRIPTOR::q; ++iPop) {
    cell[iPop] = T(symbol("cell[" + std::to_string(iPop) + "]"));
  }

  // Retrieve parameters from Dynamics and initialize unique expressions
  std::vector<T> params;
  PARAMETERS::for_each([&](auto field) {
    using FIELD = typename decltype(field)::type;
    FieldD<T,DESCRIPTOR,FIELD> f;
    if (f.d == 1) {
      T expr = T(symbol("parameters.template get<"+std::string(fields::name<FIELD>())+">()"));
      exprLattice.template setParameter<FIELD>(expr);
      params.push_back(expr);
    } else {
      for (unsigned d=0; d < f.d; ++d) {
        f[d] = T(symbol("parameters.template get<"+std::string(fields::name<FIELD>())+">()["+std::to_string(d)+"]"));
        params.push_back(f[d]);
      }
      exprLattice.template setParameter<FIELD>(f);
    }
  });

  // Execute one colliding step to obtain post-collision expressions
  exprLattice.collide();

  tree << "# Dynamics info: \n";
  tree << "collisionO = \"" << fields::name<DYNAMICS>() << "\"\n";

  // Retrieve expressions for the post-collision populations
  tree << "# Expressions of the post-collision populations\n";
  tree << "cell_assignments = [\n";
  for (int iPop=0; iPop < DESCRIPTOR::q; ++iPop) {
    tree << "  " << assignment(symbol("cell["+std::to_string(iPop)+"]"),cell[iPop].describe()) << ",\n";
  }
  tree << "]\n";

  // Retrieve parameter expressions
  tree << "# Expressions of the used parameters\n";
  tree << "params_symbols = [\n";
  for (std::size_t i=0; i < params.size(); ++i) {
    tree << "  " << params[i].describe() << ",\n";
  }
  tree << "]\n";

  // Retrieve expressions for the cell statistics
  tree << "# Expressions of the return values\n";
  tree << "return_assignments = [\n";
  tree << "  " << assignment(symbol("rho"),cell.template getFieldComponent<descriptors::STATISTIC>(0).describe()) << ",\n";
  tree << "  " << assignment(symbol("uSqr"),cell.template getFieldComponent<descriptors::STATISTIC>(1).describe()) << ",\n";
  tree << "]\n";
  return tree;
}

}

}

#endif
