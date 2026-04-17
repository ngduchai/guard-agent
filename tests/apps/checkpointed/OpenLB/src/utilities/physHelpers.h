/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Fedor Bukreev
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

/** \file
 * Physical helpers for EOS parameters calculation.
 */

#ifndef PHYSHELPERS_H
#define PHYSHELPERS_H

#include "omath.h"

namespace olb {

namespace physConstants {

template<typename T>
const T avogadroNumber() any_platform
{
  return 6.02214076e23;
}

template<typename T>
const T boltzmannConstant() any_platform
{
  return 1.380649e-23;
}

template<typename T>
const T faradayConstant() any_platform
{
  return 96485.33;
}

template<typename T>
const T universalGasConst() any_platform
{
  return 8.31446261815324;
}

template<typename T>
const T elementaryCharge() any_platform
{
  return 1.602177e-19;
}


}

namespace util {

template<typename T>
T molecularMass( T molarMass) any_platform
{
  return molarMass/physConstants::avogadroNumber<T>();
}

template<typename T>
T idealGasDensity( T molarMass, T pressure, T temperature) any_platform
{
  T mass = molarMass/physConstants::avogadroNumber<T>();
  return mass*pressure/physConstants::boltzmannConstant<T>()/temperature;
}

template<typename T>
T thermalSpeed( T molarMass, T temperature) any_platform
{
  return util::sqrt(3*physConstants::universalGasConst<T>()*temperature/molarMass);
}

template<typename T>
T gasDynamicViscosity( T molarMass, T pressure, T temperature, T kineticDiameter) any_platform
{
  T sigma = std::numbers::pi*kineticDiameter*kineticDiameter;
  return 2./3./util::sqrt(std::numbers::pi)*util::sqrt(molarMass*physConstants::universalGasConst<T>()*temperature)/sigma/physConstants::avogadroNumber<T>();
}

template<typename T>
T meanFreePath( T molarMass, T pressure, T temperature, T viscosity) any_platform
{
  T mass = util::molecularMass(molarMass);
  return viscosity/pressure * util::sqrt(std::numbers::pi*physConstants::boltzmannConstant<T>()*temperature/2./mass);
}

template<typename T>
T debyeLength( T dielectricC, T valence, T temperature, T concentration) any_platform
{
  return util::sqrt(dielectricC*physConstants::boltzmannConstant<T>()*temperature/T(2)/physConstants::elementaryCharge<T>()/physConstants::elementaryCharge<T>()/valence/valence/concentration/physConstants::avogadroNumber<T>());
}

}
}

#endif