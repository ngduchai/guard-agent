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

#ifndef LinEla_UNITCONVERTER_H
#define LinEla_UNITCONVERTER_H

#include "unitConverter.h"

namespace olb {

template <typename T, typename DESCRIPTOR>
struct LinElaUnitConverter : public UnitConverter<T, DESCRIPTOR> {
  LinElaUnitConverter(
    T physDeltaX,
    T physDeltaT,
    T charPhysLength,
    T charPhysDisplacement,
    T youngsModulus,
    T poissonRatio,
    T dampingFactor)
    : UnitConverter<T, DESCRIPTOR>(
      physDeltaX,
      physDeltaT,
      charPhysLength,
      charPhysDisplacement,
      youngsModulus,
      poissonRatio,
      dampingFactor)
  {
    this->_charPhysDisplacement = charPhysDisplacement;
    this->_epsilon              = physDeltaX / charPhysLength;
    this->_charPhysTime         = physDeltaT / (physDeltaX * physDeltaX / (charPhysLength * charPhysLength));
    this->_youngsModulus        = youngsModulus  * physDeltaT / (physDeltaX * physDeltaX * dampingFactor);
    this->_bulkModulus          = (youngsModulus / (2. * (1. - poissonRatio)))  * physDeltaT / (physDeltaX * physDeltaX * dampingFactor); // K
    this->_shearModulus         = (youngsModulus / (2. * (1. + poissonRatio))) * physDeltaT / (physDeltaX * physDeltaX * dampingFactor); // dynamic viscosity in fluid dynamics
    this->_lambda               = (youngsModulus * poissonRatio / (1. - poissonRatio * poissonRatio)) * physDeltaT / (physDeltaX * physDeltaX * dampingFactor);
    this->_poissonRatio         = poissonRatio;
    this->_dampingFactor        = dampingFactor; // Kappa
  };

  void print(std::ostream& clout) const override;

  using UnitConverter<T,DESCRIPTOR>::print;

};

template <typename T, class DESCRIPTOR>
void LinElaUnitConverter<T, DESCRIPTOR>::print(std::ostream& clout) const
{
  clout << "----------------- UnitConverter information -----------------" << std::endl;
  clout << "-- Parameters:" << std::endl;
  clout << "Resolution:                           N=              " << this->getResolution() << std::endl;
  clout << "Characteristical length(m):           charL=          " << this->getCharPhysLength() << std::endl;
  clout << "Characteristical time(s):             charT=          " << this->getCharPhysTime() << std::endl;
  clout << "Characteristical displacement (m/s):  charU=          " << this->getCharPhysDisplacement() << std::endl;
  clout << "Smallness Parameter:              epsilon=        " << this->getEpsilon() << std::endl;
  clout << std::endl;

  clout << std::endl;
  clout << "-- Conversion factors:" << std::endl;
  clout << "Voxel length(m):                  physDeltaX=     " << this->getConversionFactorLength() << std::endl;
  clout << "Time step(s):                     physDeltaT=     " << this->getConversionFactorTime() << std::endl;
  clout << "Shear modulus mue (Phys): "                         << this->getPhysShearModulus() << std::endl;
  clout << "Shear modulus mue (Lattice): "                      << this->getLatticeShearModulus() << std::endl;
  clout << "Bulk modulus K (Lattice): "                         << this->getLatticeBulkModulus() << std::endl;
  clout << "Bulk modulus K (Phys): "                            << this->getPhysBulkModulus() << std::endl;
  clout << "Youngs modulus E (Phys): "                          << this->getPhysYoungsModulus() << std::endl;
  clout << "Youngs modulus E (Lattice): "                       << this->getLatticeYoungsModulus() << std::endl;
  clout << "Lambda (Phys): "                                    << this->getPhysLambda() << std::endl;
  clout << "Lambda (Lattice): "                                 << this->getLatticeLambda() << std::endl;
  clout << "Damping factor Kappa (Lattice): "                   << this->getDampingFactor() << std::endl;
  clout << "-------------------------------------------------------------" << std::endl;
}

}

#endif
