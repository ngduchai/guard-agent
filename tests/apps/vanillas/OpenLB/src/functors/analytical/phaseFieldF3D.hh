/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Tim Bingert
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

#ifndef ANALYTICAL_PHASE_FIELD_F_3D_HH
#define ANALYTICAL_PHASE_FIELD_F_3D_HH

#include<vector>
#include<cmath>
#include<string>

#include "phaseFieldF3D.h"
#include "functors/genericF.h"
#include "analyticalF.h"
#include "functors/lattice/superBaseF3D.h"
#include "geometry/superGeometry.h"

#include "core/superLattice.h"
#include "utilities/vectorHelpers.h"  // for normalize


namespace olb {

template <typename T>
PlanarInterface3D<T>::PlanarInterface3D(Vector<T,3> center, Vector<T,3> direction, T interfaceWidth, T factor) : AnalyticalF3D<T,T>(1)
{
  this->getName() = "PlanarInterface3D";
  for (int i = 0; i < 3; ++i) {
    _center[i] = center[i];
    _direction[i] = direction[i];
  }
  _interfaceWidth = interfaceWidth;
  _factor = factor;
}

template <typename T>
bool PlanarInterface3D<T>::operator()(T output[], const T input[])
{
  Vector<T,3> in{input[0]-_center[0],
                  input[1]-_center[1],
                  input[2]-_center[2]};
  Vector<T,3> n = util::normalize(_direction);
  T d = util::abs(in * n);
  T d_int = util::norm<3>(_direction);

  output[0] = T(_factor*(1.-tanh(2.*(d-d_int)/_interfaceWidth))/2.);
  return true;
}

template <typename T>
SphericalInterface3D<T>::SphericalInterface3D(Vector<T,3> center, T radius, T interfaceWidth, T factor, bool bubble) : AnalyticalF3D<T,T>(1)
{
  this->getName() = "SphericalInterface3D";
  for (int i = 0; i < 3; ++i) {
    _center[i] = center[i];
  }
  _interfaceWidth = interfaceWidth;
  _radius = radius;
  _factor = factor;
  _bubble = bubble;
}

template <typename T>
bool SphericalInterface3D<T>::operator()(T output[], const T x[])
{
  T distToCenter2 = util::pow(_center[0]-x[0], 2) + util::pow(_center[1]-x[1], 2) + util::pow(_center[2]-x[2], 2);
  T d = util::sqrt(distToCenter2) - _radius;
  if (_bubble) output[0] = T(_factor*(1.+tanh(2*d/_interfaceWidth))/2.);
  else output[0] = T(_factor*(1.-tanh(2*d/_interfaceWidth))/2.);
  return true;
}


template <typename T>
LaplacePressure3D<T>::LaplacePressure3D(Vector<T,3> center, T radius, T interfaceWidth, T surfaceTension) : AnalyticalF3D<T,T>(1)
{
  this->getName() = "LaplacePressure3D";
  for (int i = 0; i < 3; ++i) {
    _center[i] = center[i];
  }
  _interfaceWidth = interfaceWidth;
  _radius = radius;
  _surfaceTension = surfaceTension;
}

template <typename T>
bool LaplacePressure3D<T>::operator()(T output[], const T x[])
{
  T distToCenter2 = util::pow(_center[0]-x[0], 2) + util::pow(_center[1]-x[1], 2) + util::pow(_center[2]-x[2], 2);
  T d = util::sqrt(distToCenter2) - _radius;
  T tanh_d = tanh(2*d/_interfaceWidth);
  output[0] = 2.*_surfaceTension/(_radius*4)*tanh_d*(tanh_d*tanh_d-3.);
  return true;
}


template <typename T>
ShiftedLaplacePressure3D<T>::ShiftedLaplacePressure3D(std::vector<T> center, T radius, T interfaceWidth, T surfaceTension, T pressureShift): AnalyticalF3D<T,T>(1)
{
  this->getName() = "ShiftedLaplacePressure3D";
  _center.resize(3);
  for (int i = 0; i < 3; ++i) {
    _center[i] = center[i];
  }
  _interfaceWidth = interfaceWidth;
  _radius = radius;
  _surfaceTension = surfaceTension;
  _pressureShift = pressureShift;
}

template <typename T>
bool ShiftedLaplacePressure3D<T>::operator()(T output[], const T x[])
{
  T distToCenter2 = util::pow(_center[0]-x[0], 2) + util::pow(_center[1]-x[1], 2) + util::pow(_center[2]-x[2], 2);
  T d = util::sqrt(distToCenter2) - _radius;
  T tanh_d = tanh(2*d/_interfaceWidth);
  output[0] = 2.*_surfaceTension/(_radius*4)*tanh_d*(tanh_d*tanh_d-3.) + _pressureShift;
  return true;
}


template <typename T, typename DESCRIPTOR>
IncompressibleEquilibriumPopulations3D<T, DESCRIPTOR>::IncompressibleEquilibriumPopulations3D(FunctorPtr<AnalyticalF3D<T,T>> density, FunctorPtr<AnalyticalF3D<T,T>> pressure, FunctorPtr<AnalyticalF3D<T,T>> velocity): AnalyticalF3D<T,T>(DESCRIPTOR::q)
  , _density{std::move(density)}, _pressure{std::move(pressure)}, _velocity{std::move(velocity)}
{
}

template <typename T, typename DESCRIPTOR>
bool IncompressibleEquilibriumPopulations3D<T, DESCRIPTOR>::operator()(T output[], const T input[])
{
  T d;
  T p;
  T v [3];
  this->_density(&d, input);
  this->_pressure(&p, input);
  this->_velocity(v, input);

  for(int iPop = 0; iPop < DESCRIPTOR::q; ++iPop){
    output[iPop] = olb::equilibrium<DESCRIPTOR>::mpincompressible(iPop, d, v, p);
  }

  return true;
}

template <typename T, typename DESCRIPTOR>
FirstOrderEquilibriumPopulations3D<T, DESCRIPTOR>::FirstOrderEquilibriumPopulations3D(FunctorPtr<AnalyticalF3D<T,T>> density, FunctorPtr<AnalyticalF3D<T,T>> velocity): AnalyticalF3D<T,T>(DESCRIPTOR::q)
  , _density{std::move(density)}, _velocity{std::move(velocity)}
{

}

template <typename T, typename DESCRIPTOR>
bool FirstOrderEquilibriumPopulations3D<T, DESCRIPTOR>::operator()(T output[], const T input[])
{
  T d;
  T v [3];
  this->_density(&d, input);
  this->_velocity(v, input);

  for(int iPop = 0; iPop < DESCRIPTOR::q; ++iPop){
    output[iPop] = olb::equilibrium<DESCRIPTOR>::firstOrder(iPop, d, v);
  }

  return true;
}


} // end namespace olb
#endif
