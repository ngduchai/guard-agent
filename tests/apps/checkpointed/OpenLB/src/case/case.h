/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Adrian Kummerlaender, Shota Ito, Julius Jeßberger, Mathias J. Krause
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

#ifndef CASE_CASE_H
#define CASE_CASE_H

#include "mesh.h"
#include "parametersD.h"

#include "core/superLattice.h"

#include "utilities/typeMap.h"
#include "utilities/typeIndexedContainers.h"

#include "setters.h"

namespace olb {

template <typename MAP>
class ConcreteCase {
public:
  // Select first descriptor as reference for value type and dimension (for now)
  using reference_component_t = MAP::values_t::template get<0>;

  // Expose reference value type to use in apps with single lattice
  using value_t = reference_component_t::value_t;
  // Expose reference descriptor type to use in apps with single lattice
  using descriptor_t = reference_component_t::descriptor_t;

  template <typename VALUE_TYPE>
  using exchange_value_t = ConcreteCase<typename MAP::template map_values<
    meta::exchange_value_type<VALUE_TYPE>::template type
  >>;

  using ParametersD = olb::ParametersD<typename reference_component_t::value_t,
                                       typename reference_component_t::descriptor_t>;

private:
  /// Reference to case parameters
  ParametersD& _parameters;

  /// Reference to mesh (shared between multiple cases)
  Mesh<typename reference_component_t::value_t,
       reference_component_t::descriptor_t::d>& _mesh;

  /// Case-specific geometry
  std::unique_ptr<SuperGeometry<typename reference_component_t::value_t,
                                reference_component_t::descriptor_t::d>> _geometry;

  /// Case-specific named components (e.g. lattices, ...)
  utilities::TypeIndexedTuple<typename MAP::template map_values<meta::unique_ptr_to>> _components;

  /// Arbitrary case-specific operators
  std::unordered_map<std::string, std::unique_ptr<ApplicableO>> _operators;

  std::string _name{"ConcreteCase"};

public:
  static constexpr unsigned d = reference_component_t::descriptor_t::d;

  template <typename NAME>
  using value_t_of = MAP::template value<NAME>::value_t;
  template <typename NAME>
  using descriptor_t_of = MAP::template value<NAME>::descriptor_t;

  /// (Re)construct all named components and reset operators
  void constructComponentsFromMesh() {
    /// Necessary due to impending invalidation
    _operators.clear();
    MAP::keys_t::for_each([&](auto name) {
      using COMPONENT = MAP::template value<typename decltype(name)::type>;
      _components.set(name, std::make_unique<COMPONENT>(_mesh));
    });
  }

  ConcreteCase(ParametersD& parameters,
               Mesh<typename reference_component_t::value_t,d>& mesh)
    : _parameters{parameters}
    , _mesh{mesh}
    , _geometry{new SuperGeometry<typename reference_component_t::value_t,
                                  reference_component_t::descriptor_t::d>(
          mesh.getCuboidDecomposition()
        , mesh.getLoadBalancer()
        , mesh.getOverlap())}
    , _components{}
  {
    OstreamManager clout(std::cout, "Case");
    constructComponentsFromMesh();
    clout << std::endl;
    clout << "-- OpenLB Case Components --" << std::endl;
    print(clout);
    clout << std::endl;
    clout << "-- Parameters --" << std::endl;
    _parameters.print(clout);
    clout << std::endl;
  };

  void print(OstreamManager clout={std::cout, "Case"}) const {
    std::size_t nCharName = 0;
    MAP::keys_t::for_each([&](auto name) {
      using NAME = typename decltype(name)::type;
      nCharName = std::max(nCharName, fields::name<NAME>().length());
    });
    MAP::keys_t::for_each([&](auto name) {
      using NAME = typename decltype(name)::type;
      using COMPONENT = MAP::template value<NAME>;
      clout << fields::name<NAME>() << std::string(nCharName - fields::name<NAME>().length(), ' ')
            << " = " << fields::name<COMPONENT>() << std::endl;
    });
  }

  ParametersD& getParameters() {
    return _parameters;
  }

  auto& getMesh() {
    return _mesh;
  }

  auto& getGeometry() {
    return *_geometry;
  }

  /// Returns reference to component of NAME
  template <typename NAME>
  auto& get(NAME) {
    return *_components.template get<NAME>();
  }

  /// Returns reference to lattice of NAME
  template <typename NAME>
  auto& getLattice(NAME name) {
    using T = value_t_of<NAME>;
    using DESCRIPTOR = descriptor_t_of<NAME>;
    // Ensure that component with NAME is actually a lattice
    return static_cast<Lattice<T,DESCRIPTOR>&>(get(name));
  }

  ApplicableO& getOperator(std::string name) {
    return *_operators.at(name);
  }

  template <typename... ARGS>
  auto& setCouplingOperator(std::string name, ARGS&&... args) {
    auto ptr = constructUniqueCoupling(std::forward<ARGS&&>(args)...);
    auto& concrete = *ptr;
    _operators[name].reset(ptr.release());
    return concrete;
  }

  void resetLattices() {
    constructComponentsFromMesh();
  }

  void setName(std::string name) {
    _name = name;
  }

  template <typename NAME>
  bool hasName(NAME) {
    return  (NAME{}.name == _name);
  }
};

template <typename... MAP>
using Case = ConcreteCase<meta::map<MAP...>>;

template <typename T>
struct is_case {
  static constexpr bool value = false;
};

template <typename... MAP>
struct is_case<ConcreteCase<MAP...>> {
  static constexpr bool value = true;
};

template <typename T>
static constexpr bool is_case_v = is_case<T>::value;

}

#endif
