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

#ifndef CONTROLLER_H
#define CONTROLLER_H

#include "projection.h"

namespace olb {

namespace opti {

template <typename T>
class Controller {
private:
  std::vector<T> _controls;
  std::unique_ptr<projection::Base<T>> _projection;
  std::variant<std::unique_ptr<SuperIndicatorF2D<T>>,
               std::unique_ptr<SuperIndicatorF3D<T>>> _designDomain;

  template <unsigned DIM>
  auto& getIndicator() {
    if constexpr (DIM == 2) {
      return std::get<std::unique_ptr<SuperIndicatorF2D<T>>>(_designDomain);
    } else {
      return std::get<std::unique_ptr<SuperIndicatorF3D<T>>>(_designDomain);
    }
  }

  // return controls with applied projection
  std::optional<std::vector<T>> applyProjection();
  std::optional<std::vector<T>> applyInverseProjection();
  std::optional<std::vector<T>> applyDerivativeProjection();

public:
  // Constructor
  explicit Controller(std::vector<T>& controls) :
    _controls(controls)
  { }

  // Default constructor
  Controller() { }

  // setter to overwrite _controls
  void set(const std::vector<T>& control);
  // controls set from an indicated field
  template <typename FIELD, typename DESCRIPTOR>
  void set(SuperGeometry<T,DESCRIPTOR::d>& geometry, std::vector<int>&& materials, SuperLattice<T,DESCRIPTOR>& sLattice);
  template <typename FIELD, typename DESCRIPTOR>
  void set(SuperGeometry<T,DESCRIPTOR::d>& geometry, int material, SuperLattice<T,DESCRIPTOR>& sLattice);

  // update controlled field with the current controls
  template <typename FIELD, typename DESCRIPTOR>
  void setUpdatedControlsOnField(SuperLattice<T,DESCRIPTOR>& sLattice);
  // update the projection derivatives regarding current controls
  template <typename FIELD, typename DESCRIPTOR>
  void setUpdatedProjectionDerivativesOnField(SuperLattice<T,DESCRIPTOR>& sLattice);

  // set control projection
  template <typename PROJECTION, typename... ARGS>
  void setProjection(ARGS&&... args);
  // return if projection is set
  bool checkProjection();

  // getter for design domain
  template <typename DESCRIPTOR>
  SuperIndicatorF<T,DESCRIPTOR::d>& getDesignDomain();

  // getter for accessing _controls
  std::vector<T>& get();
  const std::vector<T>& get() const;
  // index-wise access of _controls
  T& operator[] (std::size_t index);
  const T& operator[] (std::size_t index) const;
  // return size of _controls
  std::size_t size() const;
};

}

}

#endif
