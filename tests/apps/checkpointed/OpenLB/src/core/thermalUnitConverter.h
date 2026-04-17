/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2017 Max Gaedtke, Albert Mink
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
 * Unit conversion handling -- header file.
 */

#ifndef THERMALUNITCONVERTER_H
#define THERMALUNITCONVERTER_H

#include <math.h>
#include "io/ostreamManager.h"
#include "core/util.h"
#include "io/xmlReader.h"
#include "core/unitConverter.h"

namespace olb {

/** Conversion between physical and lattice units, as well as discretization specialized for thermal applications with boussinesq approximation.
* Be aware of the nomenclature:
* We distingish between physical (dimensioned) and lattice (dimensionless) values.
* A specific conversion factor maps the two different scopes,
* e.g. __physLength = conversionLength * latticeLength__
*
* For pressure and temperature we first shift the physical values by a characteristic value to asure a lattice pressure and between 0 and 1, e.g. __physPressure - charPhysPressure = conversionPressure * latticePressure__. For the temperature we set lattice values between 0.5 and 1.5 by __latticeTemperature = (physTemperature - charPhysLowTemperature) / conversionTemperature + 0.5 with conversionTemperature = charPhysHighTemperature - charPhysLowTemperature = charPhysTemperatureDifference
*
* TODO: Extend documentation for ThermalUnitConverter
*/
template <typename T, typename DESCRIPTOR, typename ThermalLattice>
struct ThermalUnitConverter : public UnitConverter<T, DESCRIPTOR> {
  ThermalUnitConverter(
    T physDeltaX,
    T physDeltaT,
    T charPhysLength,
    T charPhysVelocity,
    T physViscosity,
    T physDensity,
    T physThermalConductivity,
    T physSpecificHeatCapacity,
    T physThermalExpansionCoefficient,
    T charPhysLowTemperature,
    T charPhysHighTemperature,
    T charPhysPressure = 0 )
    : UnitConverter<T, DESCRIPTOR>(
        physDeltaX, physDeltaT, charPhysLength, charPhysVelocity,
        physViscosity, physDensity, charPhysPressure)
  {
    this->_conversionTemperature = charPhysHighTemperature - charPhysLowTemperature;
    this->_conversionThermalDiffusivity = this->_conversionViscosity;
    this->_conversionSpecificHeatCapacity = this->_conversionVelocity * this->_conversionVelocity / this->_conversionTemperature;
    this->_conversionThermalConductivity = this->_conversionForce / this->_conversionTime / this->_conversionTemperature;
    this->_conversionHeatFlux = this->_conversionMass / util::pow(this->_conversionTime.value(), 3);
    this->_charPhysLowTemperature = charPhysLowTemperature;
    this->_charPhysHighTemperature = charPhysHighTemperature;
    this->_charPhysTemperatureDifference = charPhysHighTemperature - charPhysLowTemperature;
    this->_physThermalExpansionCoefficient = physThermalExpansionCoefficient;
    this->_physThermalDiffusivity = physThermalConductivity / (physDensity * physSpecificHeatCapacity);
    this->_physSpecificHeatCapacity = physSpecificHeatCapacity;
    this->_physThermalConductivity = physThermalConductivity;
    this->_latticeThermalRelaxationTime = (this->_physThermalDiffusivity / this->_conversionThermalDiffusivity * descriptors::invCs2<T,ThermalLattice>()) + 0.5;
  }

  /// nice terminal output for conversion factors, characteristical and physical data
  void print() const override;

};

}  // namespace olb

#endif
