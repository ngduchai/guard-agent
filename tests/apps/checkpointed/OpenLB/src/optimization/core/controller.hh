/*  This file is part of the OpenLB library
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

#ifndef CONTROLLER_HH
#define CONTROLLER_HH

#include "controller.h"

namespace olb {

namespace opti {

template <typename T>
std::optional<std::vector<T>> Controller<T>::applyProjection() {
  if (!_projection) {
    return std::nullopt;
  }

  std::vector<T> projectedControls;
  for (auto element : _controls) {
    projectedControls.emplace_back(_projection->project(element));
  }
  return projectedControls;
}

template <typename T>
std::optional<std::vector<T>> Controller<T>::applyInverseProjection() {
  if (!_projection) {
    return std::nullopt;
  }

  std::vector<T> projectedControls;
  for (auto element : _controls) {
    projectedControls.emplace_back(_projection->inverse(element));
  }
  return projectedControls;
}

template <typename T>
std::optional<std::vector<T>> Controller<T>::applyDerivativeProjection() {
  if (!_projection) {
    return std::nullopt;
  }

  std::vector<T> projectedControls;
  for (auto element : _controls) {
    projectedControls.emplace_back(_projection->derivative(element));
  }
  return projectedControls;
}

template <typename T>
void Controller<T>::set(const std::vector<T>& control) {
  _controls.resize(control.size());
  std::copy(control.begin(), control.end(), _controls.begin());
}

template <typename T>
template <typename FIELD, typename DESCRIPTOR>
void Controller<T>::set(SuperGeometry<T,DESCRIPTOR::d>& geometry, std::vector<int>&& materials, SuperLattice<T,DESCRIPTOR>& sLattice) {
  _designDomain = geometry.getMaterialIndicator(std::move(materials));
  _controls = getSerializedFromField<FIELD>(sLattice, getIndicator<DESCRIPTOR::d>());
  if (auto projected = applyInverseProjection()) {
    _controls = *projected;
  }
}

template <typename T>
template <typename FIELD, typename DESCRIPTOR>
void Controller<T>::set(SuperGeometry<T,DESCRIPTOR::d>& geometry, int material, SuperLattice<T,DESCRIPTOR>& sLattice) {
  set<FIELD,DESCRIPTOR>(geometry, std::vector<int>{material}, sLattice);
}

template <typename T>
template <typename FIELD, typename DESCRIPTOR>
void Controller<T>::setUpdatedControlsOnField(SuperLattice<T,DESCRIPTOR>& sLattice) {
  if (auto projected = applyProjection()) {
    setFieldFromSerialized<FIELD>(*projected, sLattice, getIndicator<DESCRIPTOR::d>());
  } else {
    setFieldFromSerialized<FIELD>(_controls, sLattice, getIndicator<DESCRIPTOR::d>());
  }
}

template <typename T>
template <typename FIELD, typename DESCRIPTOR>
void Controller<T>::setUpdatedProjectionDerivativesOnField(SuperLattice<T,DESCRIPTOR>& sLattice) {
  if (auto derivatives = applyDerivativeProjection()) {
    setFieldFromSerialized<FIELD>(*derivatives, sLattice, getIndicator<DESCRIPTOR::d>());
  } else {
    throw std::runtime_error("No Projection set.");
  }
}

template <typename T>
template <typename PROJECTION, typename... ARGS>
void Controller<T>::setProjection(ARGS&&... args) {
  _projection = std::make_unique<PROJECTION>(std::forward<ARGS...>(args)...);
}

template<typename T>
bool Controller<T>::checkProjection() {
  if (_projection) {
    return true;
  } else {
    return false;
  }
}

template <typename T>
template <typename DESCRIPTOR>
SuperIndicatorF<T,DESCRIPTOR::d>& Controller<T>::getDesignDomain() {
  if (!getIndicator<DESCRIPTOR::d>()) {
    throw std::runtime_error("Indicator for design domain not defined.");
  }
  return *(getIndicator<DESCRIPTOR::d>());
}

template<typename T>
std::vector<T>& Controller<T>::get() {
  return _controls;
}

template<typename T>
const std::vector<T>& Controller<T>::get() const {
  return _controls;
}

template<typename T>
T& Controller<T>::operator[] (std::size_t index) {
  return _controls[index];
}

template<typename T>
const T& Controller<T>::operator[] (std::size_t index) const {
  return _controls[index];
}

template<typename T>
std::size_t Controller<T>::size() const {
  return _controls.size();
}

} // namespace opti

} // namepsace olb

#endif
