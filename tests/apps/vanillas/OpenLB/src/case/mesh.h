/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Adrian Kummerlaender
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

#ifndef CASE_MESH_H
#define CASE_MESH_H

#include "parametersD.h"
#include "io/stlReader.h"

namespace olb {

namespace parameters {

struct STL_PATH : public descriptors::TYPED_FIELD_BASE<std::string,1> { };
struct STL_SCALING : public descriptors::FIELD_BASE<1> { };
struct STL_RAY_MODE : public descriptors::TYPED_FIELD_BASE<RayMode,1> {
  template <typename T, typename DESCRIPTOR>
  static constexpr auto getInitialValue() {
    return Vector<RayMode,1>{RayMode::Robust};
  }
};

struct DECOMPOSITION_STRATEGY : public descriptors::TYPED_FIELD_BASE<std::string,1> { };
struct MESH_PADDING : public descriptors::TYPED_FIELD_BASE<std::size_t,1> {
  template <typename T, typename DESCRIPTOR>
  static constexpr auto getInitialValue() {
    return Vector<std::size_t,1>{1};
  }
};
struct DECOMPOSITION_MULTIPLIER : public descriptors::TYPED_FIELD_BASE<std::size_t,1> {
  template <typename T, typename DESCRIPTOR>
  static constexpr auto getInitialValue() {
    return Vector<std::size_t,1>{1};
  }
};

}

template <typename T, unsigned D>
class Mesh {
private:
  std::unique_ptr<CuboidDecomposition<T,D>> _decomposition;
  std::unique_ptr<LoadBalancer<T>> _balancer;
  std::optional<unsigned> _overlap;

  /// Arbitrary indicators related to the mesh
  std::unordered_map<std::string, std::shared_ptr<IndicatorF<T,D>>> _indicators;

public:
  template <typename V, typename DESCRIPTOR>
  static Mesh fromSTL(ParametersD<V,DESCRIPTOR>& params) {
    using namespace parameters;
    std::shared_ptr<STLreader<T>> stlI(new STLreader<T>(
      params.template get<STL_PATH>(),
      params.template get<PHYS_DELTA_X>(),
      params.template get<STL_SCALING>(),
      params.template get<STL_RAY_MODE>()));
    IndicatorLayer3D<T> extendedDomain(*stlI,   params.template get<MESH_PADDING>()
                                              * params.template get<PHYS_DELTA_X>());
    Mesh mesh(extendedDomain,
              params.template get<PHYS_DELTA_X>(),
              singleton::mpi().getSize() * params.template get<DECOMPOSITION_MULTIPLIER>(),
              params.template get<DECOMPOSITION_STRATEGY>());
    mesh.addIndicator(params.template get<STL_PATH>(), stlI);
    mesh.setOverlap(params.template get<parameters::OVERLAP>());
    return mesh;
  }

  Mesh(std::unique_ptr<CuboidDecomposition<T, D>> decomposition,
       std::unique_ptr<LoadBalancer<T>> balancer)
    : _decomposition(std::move(decomposition)),
      _balancer(std::move(balancer))
  {
    OLB_PRECONDITION(_decomposition);
    OLB_PRECONDITION(_balancer);
  }

  template <typename... ARGS>
  explicit Mesh(ARGS&&... args)
    : _decomposition(new CuboidDecomposition<T,D>(std::forward<ARGS>(args)...)),
      _balancer(new HeuristicLoadBalancer<T>(*_decomposition))
  { }

  CuboidDecomposition<T,D>& getCuboidDecomposition() {
    return *_decomposition;
  }

  LoadBalancer<T>& getLoadBalancer() {
    return *_balancer;
  }

  void setOverlap(unsigned overlap) {
    _overlap = overlap;
  }

  unsigned getOverlap() const {
    if (_overlap) {
      return *_overlap;
    } else {
      throw std::logic_error("Mesh overlap not specified");
    }
  }

  T getDeltaX() const {
    return _decomposition->getDeltaX();
  }

  /// Stores indicator under name
  void addIndicator(std::string name, std::shared_ptr<IndicatorF<T,D>> indicatorF) {
    _indicators[name] = indicatorF;
  }

  /// Return indicator by name
  std::shared_ptr<IndicatorF<T,D>> getIndicator(std::string name) {
    return _indicators.at(name);
  }

  /// Return previously read STL
  std::shared_ptr<STLreader<T>> getSTL(std::string path) {
    return std::static_pointer_cast<STLreader<T>>(getIndicator(path));
  }

};

}

#endif
