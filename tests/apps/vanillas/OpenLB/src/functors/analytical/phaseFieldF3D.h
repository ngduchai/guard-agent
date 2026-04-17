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

#ifndef ANALYTICAL_PHASE_FIELD_F_3D_H
#define ANALYTICAL_PHASE_FIELD_F_3D_H

#include<vector>
#include<cmath>
#include<string>
#include"math.h"

#include "functors/genericF.h"
#include "analyticalF.h"
#include "core/superLattice.h"

/** \file
  This file contains functors needed to describe multiphase phenomena such
  as interfacial profiles and Young-Laplace pressure fields for initialization
  as well as comparison to analytical solutions.
*/


namespace olb {

/// spherical hyperbolic tangent between values 0 and factor
template <typename T>
class PlanarInterface3D : public AnalyticalF3D<T,T> {
private:
  Vector<T,3> _center;
  Vector<T,3> _direction;
  T _interfaceWidth;
  T _factor;
public:
  PlanarInterface3D(Vector<T,3> center, Vector<T,3> direction, T interfaceWidth, T factor = 1.);
  bool operator() (T output[], const T input[]) override;
};

// spherical hyperbolic tangent between values 0 and factor
template <typename T>
class SphericalInterface3D : public AnalyticalF3D<T,T> {
protected:
  Vector<T,3> _center;
  T _interfaceWidth;
  T _radius;
  T _factor;
  bool _bubble;

public:
  SphericalInterface3D(Vector<T,3> center, T radius, T interfaceWidth, T factor, bool bubble);
  bool operator()(T output[], const T input[]) override;
};

// smooth Young-Laplace pressure over interface
template <typename T>
class LaplacePressure3D : public AnalyticalF3D<T,T> {
protected:
  Vector<T,3> _center;
  T _interfaceWidth;
  T _radius;
  T _surfaceTension;

public:
  LaplacePressure3D(Vector<T,3> center, T radius, T interfaceWidth, T surfaceTension);
  bool operator()(T output[], const T x[]) override;
};

// shifted Young-Laplace pressure over interface
template <typename T>
class ShiftedLaplacePressure3D : public AnalyticalF3D<T,T> {
protected:
  std::vector<T> _center;
  T _interfaceWidth;
  T _radius;
  T _surfaceTension;
  T _pressureShift;

public:
  ShiftedLaplacePressure3D(std::vector<T> center, T radius, T interfaceWidth, T surfaceTension, T pressureShift);
  bool operator()(T output[], const T x[]) override;
};

template <typename T, typename DESCRIPTOR>
class IncompressibleEquilibriumPopulations3D : public AnalyticalF3D<T,T> {
protected:
  FunctorPtr<AnalyticalF3D<T,T>> _density;
  FunctorPtr<AnalyticalF3D<T,T>> _pressure;
  FunctorPtr<AnalyticalF3D<T,T>> _velocity;

public:
  IncompressibleEquilibriumPopulations3D(FunctorPtr<AnalyticalF3D<T,T>> density, FunctorPtr<AnalyticalF3D<T,T>> pressure, FunctorPtr<AnalyticalF3D<T,T>> velocity);
  bool operator()(T output[], const T input[]) override;
};

template <typename T, typename DESCRIPTOR>
class FirstOrderEquilibriumPopulations3D : public AnalyticalF3D<T,T> {
protected:
  FunctorPtr<AnalyticalF3D<T,T>> _density;
  FunctorPtr<AnalyticalF3D<T,T>> _velocity;

public:
  FirstOrderEquilibriumPopulations3D(FunctorPtr<AnalyticalF3D<T,T>> density, FunctorPtr<AnalyticalF3D<T,T>> velocity);
  bool operator()(T output[], const T input[]) override;
};

} // end namespace olb
#endif
