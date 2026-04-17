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

#ifndef MULTIPHASEUNITCONVERTER_H
#define MULTIPHASEUNITCONVERTER_H

#include <math.h>
#include "io/ostreamManager.h"
#include "core/util.h"
#include "io/xmlReader.h"
#include "core/unitConverter.h"

namespace olb {

/** Conversion between physical and lattice units, as well as discretization for multiple component lattices.
* Be aware of the nomenclature:
* We distingish between physical (dimensioned) and lattice (dimensionless) values.
* A specific conversion factor maps the two different scopes,
* e.g. __physLength = conversionLength * latticeLength__
*
* For the basic units of length L, time T, mass M, particle number N and temperature theta,
* 5 elemental conversion factors are deduced from EoS parameters a,b and R, molar mass M and surface tension sigma.
* For multiple components, the conversion factors are computed for the lightest condensable component.
*/
template <typename T, typename DESCRIPTOR>
struct MultiPhaseUnitConverter : public UnitConverter<T, DESCRIPTOR> {
  MultiPhaseUnitConverter(
    std::size_t resolution,
    T charPhysLength,
    T charPhysVelocity,
    T physViscosity,
    T physEoSa,
    T latticeEoSa,
    T physEoSb,
    T physMolarMass,
    T physSurfaceTension,
    T charPhysTemperature,
    T charPhysPressure )
    : UnitConverter<T, DESCRIPTOR>(
        (charPhysLength/resolution),
        (charPhysLength/resolution)*util::pow(physEoSa/latticeEoSa, -0.5)*util::pow(physEoSb*10.5/1., 0.5)*util::pow(physMolarMass*1, 0.5),
        charPhysLength,
        charPhysVelocity,
        physViscosity,
        physMolarMass*1/(physEoSb*10.5/1.),
        charPhysPressure)
  {
    this->_conversionEoSa = physEoSa/latticeEoSa;
    this->_conversionEoSb = physEoSb*10.5/1.;
    this->_conversionMolarMass = physMolarMass*1;
    this->_conversionSurfaceTension = this->_conversionLength*this->_conversionEoSa*util::pow(this->_conversionEoSb.value(), -2);
    this->_conversionTemperature = this->_conversionEoSa/this->_conversionEoSb/this->_conversionGasConstant;
    this->_physEoSav = physEoSa;
    this->_physEoSbv = physEoSb;
    this->_physMolarMass = physMolarMass;
    this->_physSurfaceTension = physSurfaceTension;
    this->_charPhysTemperature = charPhysTemperature;
    this->_latticeSurfaceTension = physSurfaceTension / this->_conversionSurfaceTension;
  };

  using UnitConverter<T,DESCRIPTOR>::print;

  void print(std::ostream& clout) const override;
};

/** Conversion between physical and lattice units, as well as discretization for multiple component lattices.
* Be aware of the nomenclature:
* We distingish between physical (dimensioned) and lattice (dimensionless) values.
* A specific conversion factor maps the two different scopes,
* e.g. __physLength = conversionLength * latticeLength__
*
* For the basic units of length L, time T, mass M, particle number N and temperature theta,
* 5 elemental conversion factors are deduced from EoS parameters a,b and R, molar mass M and surface tension sigma.
* For multiple components, the conversion factors are computed for the lightest condensable component.
*/
template <typename T, typename DESCRIPTOR>
struct MultiPhaseUnitConverterFromRelaxationTime : public UnitConverter<T, DESCRIPTOR> {
  MultiPhaseUnitConverterFromRelaxationTime(
    std::size_t resolution,
    T latticeRelaxationTime,
    T latticeDensity,
    T charPhysLength,
    T physViscosity,
    T physDensity,
    T charPhysPressure = 0 ) : UnitConverter<T, DESCRIPTOR>(
        (charPhysLength/resolution),
        (latticeRelaxationTime - 0.5) / descriptors::invCs2<T,DESCRIPTOR>() * util::pow((charPhysLength/resolution),2) / physViscosity,
        charPhysLength,
        0,
        physViscosity,
        (physDensity/latticeDensity),
        charPhysPressure)
  {
    this->_conversionSurfaceTension =
        this->_conversionDensity *
        this->_conversionViscosity * this->_conversionViscosity /
        this->_conversionLength;
    this->_conversionChemicalPotential = this->_conversionVelocity * this->_conversionVelocity;
  }

  using UnitConverter<T,DESCRIPTOR>::print;

  void print(std::ostream& clout) const override;

};

}

#endif
