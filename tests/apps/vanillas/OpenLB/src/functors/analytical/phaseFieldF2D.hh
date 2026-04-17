/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2024 Tim Bingert
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

#ifndef ANALYTICAL_PHASE_FIELD_F_2D_HH
#define ANALYTICAL_PHASE_FIELD_F_2D_HH

#include<vector>
#include<cmath>
#include<string>

#include "phaseFieldF2D.h"
#include "functors/genericF.h"
#include "analyticalF.h"
#include "functors/lattice/superBaseF2D.h"
#include "geometry/superGeometry.h"

#include "core/superLattice2D.h"
#include "utilities/vectorHelpers.h"  // for normalize


namespace olb {

template <typename T>
CircularInterface2D<T>::CircularInterface2D(std::vector<T> center, T radius, T interfaceWidth, T factor, bool bubble) : AnalyticalF2D<T,T>(1)
{
  this->getName() = "CircularInterface2D";
  _center.resize(2);
  for (int i = 0; i < 2; ++i) {
    _center[i] = center[i];
  }
  _interfaceWidth = interfaceWidth;
  _radius = radius;
  _factor = factor;
  _bubble = bubble;
}

template <typename T>
bool CircularInterface2D<T>::operator()(T output[], const T x[])
{
  T distToCenter2 = util::pow(_center[0]-x[0], 2) + util::pow(_center[1]-x[1], 2);
  T d = util::sqrt(distToCenter2) - _radius;
  if (_bubble) output[0] = T(_factor*(1.+tanh(2*d/_interfaceWidth))/2.);
  else output[0] = T(_factor*(1.-tanh(2*d/_interfaceWidth))/2.);
  return true;
}


template <typename T>
LaplacePressure2D<T>::LaplacePressure2D(std::vector<T> center, T radius, T interfaceWidth, T surfaceTension) : AnalyticalF2D<T,T>(1)
{
  this->getName() = "LaplacePressure2D";
  _center.resize(2);
  for (int i = 0; i < 2; ++i) {
    _center[i] = center[i];
  }
  _interfaceWidth = interfaceWidth;
  _radius = radius;
  _surfaceTension = surfaceTension;
}

template <typename T>
bool LaplacePressure2D<T>::operator()(T output[], const T x[])
{
  T distToCenter2 = util::pow(_center[0]-x[0], 2) + util::pow(_center[1]-x[1], 2);
  T d = util::sqrt(distToCenter2) - _radius;
  T tanh_d = tanh(2*d/_interfaceWidth);
  output[0] = _surfaceTension/(_radius*4)*tanh_d*(tanh_d*tanh_d-3.);
  return true;
}


template <typename T>
ShiftedLaplacePressure2D<T>::ShiftedLaplacePressure2D(std::vector<T> center, T radius, T interfaceWidth, T surfaceTension, T pressureShift): AnalyticalF2D<T,T>(1)
{
  this->getName() = "ShiftedLaplacePressure2D";
  _center.resize(2);
  for (int i = 0; i < 2; ++i) {
    _center[i] = center[i];
  }
  _interfaceWidth = interfaceWidth;
  _radius = radius;
  _surfaceTension = surfaceTension;
  _pressureShift = pressureShift;
}

template <typename T>
bool ShiftedLaplacePressure2D<T>::operator()(T output[], const T x[])
{
  T distToCenter2 = util::pow(_center[0]-x[0], 2) + util::pow(_center[1]-x[1], 2);
  T d = util::sqrt(distToCenter2) - _radius;
  T tanh_d = tanh(2*d/_interfaceWidth);
  output[0] = _surfaceTension/(_radius*4)*tanh_d*(tanh_d*tanh_d-3.) + _pressureShift;
  return true;
}


template <typename T>
LayeredPoiseuilleSharp2D<T>::LayeredPoiseuilleSharp2D(std::vector<T> axisPoint, std::vector<T> axisDirection, T h_phys, T h_lat, T g, T mu_l, T mu_g): AnalyticalF2D<T,T>(2)
{
  this->getName() = "LayeredPoiseuilleSharp2D";
  _axisPoint.resize(2);
  _axisDirection.resize(2);
  for (int i = 0; i < 2; ++i) {
    _axisPoint[i] = axisPoint[i];
    _axisDirection[i] = axisDirection[i];
  }
  _h_phys = h_phys;
  _h_lat = h_lat;
  _g = g;
  _mu_l = mu_l;
  _mu_g = mu_g;
}

template <typename T>
bool LayeredPoiseuilleSharp2D<T>::operator()(T output[], const T x[])
{
  T d = -_axisDirection[1]*(x[0] - _axisPoint[0]) + _axisDirection[0]*(x[1] - _axisPoint[1]);
  T mu_sum = _mu_g+_mu_l;
  T mu_rel = (_mu_g-_mu_l)/mu_sum;
  if ( d >= -_h_phys && d <= 0  ) {
    output[0] = _g*_h_lat*_h_lat/2./_mu_l*_axisDirection[0]*(-util::pow(d/_h_phys,2)-d/_h_phys*mu_rel+2.*_mu_l/mu_sum);
    output[1] = _g*_h_lat*_h_lat/2./_mu_l*_axisDirection[1]*(-util::pow(d/_h_phys,2)-d/_h_phys*mu_rel+2.*_mu_l/mu_sum);
  } else if ( d > 0 && d <= _h_phys ) {
    output[0] = _g*_h_lat*_h_lat/2./_mu_g*_axisDirection[0]*(-util::pow(d/_h_phys,2)-d/_h_phys*mu_rel+2.*_mu_g/mu_sum);
    output[1] = _g*_h_lat*_h_lat/2./_mu_g*_axisDirection[1]*(-util::pow(d/_h_phys,2)-d/_h_phys*mu_rel+2.*_mu_g/mu_sum);
  } else {
    output[0] = T();
    output[1] = T();
  }
  return true;
}

template <typename T, typename DESCRIPTOR>
IncompressibleEquilibriumPopulations2D<T, DESCRIPTOR>::IncompressibleEquilibriumPopulations2D(FunctorPtr<AnalyticalF2D<T,T>> density, FunctorPtr<AnalyticalF2D<T,T>> pressure, FunctorPtr<AnalyticalF2D<T,T>> velocity): AnalyticalF2D<T,T>(DESCRIPTOR::q)
  , _density{std::move(density)}, _pressure{std::move(pressure)}, _velocity{std::move(velocity)}
{
}

template <typename T, typename DESCRIPTOR>
bool IncompressibleEquilibriumPopulations2D<T, DESCRIPTOR>::operator()(T output[], const T input[])
{
  T d;
  T p;
  T v [2];
  this->_density(&d, input);
  this->_pressure(&p, input);
  this->_velocity(v, input);

  for(int iPop = 0; iPop < DESCRIPTOR::q; ++iPop){
    output[iPop] = olb::equilibrium<DESCRIPTOR>::mpincompressible(iPop, d, v, p);
  }

  return true;
}

template <typename T, typename DESCRIPTOR>
FirstOrderEquilibriumPopulations2D<T, DESCRIPTOR>::FirstOrderEquilibriumPopulations2D(FunctorPtr<AnalyticalF2D<T,T>> density, FunctorPtr<AnalyticalF2D<T,T>> velocity): AnalyticalF2D<T,T>(DESCRIPTOR::q)
  , _density{std::move(density)}, _velocity{std::move(velocity)}
{

}

template <typename T, typename DESCRIPTOR>
bool FirstOrderEquilibriumPopulations2D<T, DESCRIPTOR>::operator()(T output[], const T input[])
{
  T d;
  T v [2];
  this->_density(&d, input);
  this->_velocity(v, input);

  for(int iPop = 0; iPop < DESCRIPTOR::q; ++iPop){
    output[iPop] = olb::equilibrium<DESCRIPTOR>::firstOrder(iPop, d, v);
  }

  return true;
}


} // end namespace olb
#endif
