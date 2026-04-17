/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2020 Louis Kronberg, Stephan Simonis
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
 * Unit conversion handling for Advection-Diffusion Problmes -- header file.
 */
#ifndef ADE_UNITCONVERTER_H
#define ADE_UNITCONVERTER_H

#include <math.h>
#include <fstream>
#include <iostream>
#include <unistd.h>

#include "io/ostreamManager.h"
#include "io/fileName.h"

#include "core/util.h"
#include "core/unitConverter.h"
#include "core/singleton.h"


namespace olb {

template <typename T, typename DESCRIPTOR>
struct AdeUnitConverter : public UnitConverter<T,DESCRIPTOR> {
  AdeUnitConverter(
    T physDeltaX,
    T physDeltaT,
    T charPhysLength,
    T charPhysVelocity,
    T physDiffusivity,
    T physDensity)
    : UnitConverter<T,DESCRIPTOR>(physDeltaX, physDeltaT,
                                  charPhysLength, charPhysVelocity,
                                  physDiffusivity, physDensity)
  {
    this->_physDiffusivity = physDiffusivity;
    this->_conversionDiffusivity = physDeltaX * physDeltaX / physDeltaT;
    this->_latticeAdeRelaxationTime = (physDiffusivity / this->_conversionDiffusivity * descriptors::invCs2<T,DESCRIPTOR>()) + 0.5;
  }

  void print(std::ostream& clout) const override;
};

template <typename T, class DESCRIPTOR>
void AdeUnitConverter<T, DESCRIPTOR>::print(std::ostream& clout) const
{
  clout << "----------------- UnitConverter information -----------------" << std::endl;
  clout << "-- Parameters:" << std::endl;
  clout << "Resolution:                       N=              " << this->getResolution() << std::endl;
  clout << "Lattice velocity:                 latticeU=       " << this->getCharLatticeVelocity() << std::endl;
  clout << "Lattice relaxation frequency:     omega=          " << this->getLatticeRelaxationFrequency() << std::endl;
  clout << "Lattice relaxation time:          tau=            " << this->getLatticeRelaxationTime() << std::endl;
  clout << "Characteristical length(m):       charL=          " << this->getCharPhysLength() << std::endl;
  clout << "Characteristical speed(m/s):      charU=          " << this->getCharPhysVelocity() << std::endl;
  clout << "Phys. density(kg/m^d):            charRho=        " << this->getPhysDensity() << std::endl;
  clout << "Peclet Number:                    Pe=             " << this->getPecletNumber() << std::endl;
  clout << "Phys.  diffusivity (m^2/s):       charNu=         " << this->getPhysDiffusivity() << std::endl;
  clout << "Mach number:                      machNumber=     " << this->getMachNumber() << std::endl;
  clout << "Knudsen number:                   knudsenNumber=  " << this->getKnudsenNumber() << std::endl;
  clout << std::endl;

  clout << std::endl;
  clout << "-- Conversion factors:" << std::endl;
  clout << "Voxel length(m):                  physDeltaX=     " << this->getConversionFactorLength() << std::endl;
  clout << "Time step(s):                     physDeltaT=     " << this->getConversionFactorTime() << std::endl;
  clout << "Velocity factor(m/s):             physVelocity=   " << this->getConversionFactorVelocity() << std::endl;
  clout << "Density factor(kg/m^3):           physDensity=    " << this->getConversionFactorDensity() <<  std::endl;
  clout << "Mass factor(kg):                  physMass=       " << this->getConversionFactorMass() << std::endl;
  clout << "Viscosity factor(m^2/s):          physViscosity=  " << this->getConversionFactorViscosity() << std::endl;
  clout << "Force factor(N):                  physForce=      " << this->getConversionFactorForce() << std::endl;
  clout << "Pressure factor(N/m^2):           physPressure=   " << this->getConversionFactorPressure() << std::endl;
  clout << "-------------------------------------------------------------" << std::endl;
}

template <typename T, typename DESCRIPTOR>
struct AdeUnitConverterFromResolutionAndRelaxationTime : public AdeUnitConverter<T, DESCRIPTOR> {
  AdeUnitConverterFromResolutionAndRelaxationTime(
    std::size_t resolution,
    T latticeRelaxationTime,
    T charPhysLength,
    T charPhysVelocity,
    T physDiffusivity,
    T physDensity): AdeUnitConverter<T, DESCRIPTOR>(
        (charPhysLength/resolution),
        (latticeRelaxationTime - 0.5) / descriptors::invCs2<T,DESCRIPTOR>() * util::pow((charPhysLength/resolution),2) / physDiffusivity,
        charPhysLength,
        charPhysVelocity,
        physDiffusivity,
        physDensity)
  { }
};

template <typename T, typename DESCRIPTOR>
struct AdeUnitConverterFromResolutionAndLatticeVelocity : public AdeUnitConverter<T, DESCRIPTOR> {
  AdeUnitConverterFromResolutionAndLatticeVelocity(
    std::size_t resolution,
    T charLatticeVelocity,
    T charPhysLength,
    T charPhysVelocity,
    T physViscosity,
    T physDensity) : AdeUnitConverter<T, DESCRIPTOR>(
        (charPhysLength/resolution),
        (charLatticeVelocity / charPhysVelocity * charPhysLength / resolution),
        charPhysLength,
        charPhysVelocity,
        physViscosity,
        physDensity)
  { }
};

}
#endif
