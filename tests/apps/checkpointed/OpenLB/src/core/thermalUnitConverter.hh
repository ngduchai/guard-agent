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

#ifndef THERMALUNITCONVERTER_HH
#define THERMALUNITCONVERTER_HH

#include "thermalUnitConverter.h"

// All OpenLB code is contained in this namespace.
namespace olb {

template <typename T, typename DESCRIPTOR, typename ThermalLattice>
void ThermalUnitConverter<T, DESCRIPTOR, ThermalLattice>::print() const
{
  OstreamManager clout(std::cout, "ThermalUnitConverter");
  clout << "----------------- UnitConverter information -----------------" << std::endl;
  clout << "-- Parameters:" << std::endl;
  clout << "Resolution:                                 N=                              " << this->getResolution() << std::endl;
  clout << "Lattice velocity:                           latticeU=                       " << this->getCharLatticeVelocity() << std::endl;
  clout << "Lattice relaxation frequency:               omega=                          " << this->getLatticeRelaxationFrequency() << std::endl;
  clout << "Lattice relaxation time:                    tau=                            " << this->getLatticeRelaxationTime() << std::endl;
  clout << "Thermal Lattice relaxation frequency:       omega_AD=                       " << this->getLatticeThermalRelaxationFrequency() << std::endl;
  clout << "Thermal Lattice relaxation time:            tau_AD=                         " << this->getLatticeThermalRelaxationTime() << std::endl;
  clout << "Characteristical length(m):                 charL=                          " << this->getCharPhysLength() << std::endl;
  clout << "Characteristical speed(m/s):                charU=                          " << this->getCharPhysVelocity() << std::endl;
  clout << "Phys. kinematic viscosity(m^2/s):           charNu=                         " << this->getPhysViscosity() << std::endl;
  clout << "Phys. density(kg/m^d):                      charRho=                        " << this->getPhysDensity() << std::endl;
  clout << "Characteristical pressure(N/m^2):           charPressure=                   " << this->getCharPhysPressure() << std::endl;
  clout << "Reynolds number:                            reynoldsNumber=                 " << this->getReynoldsNumber() << std::endl;

  clout << "-------------------------------------------------------------" << std::endl;

  clout << "----------------- ThermalUnitConverter information -----------------" << std::endl;
  clout << "-- Parameters:" << std::endl;
  clout << "Phys. Delta X(m):                           physDeltaX=                     " << this->getPhysDeltaX() << std::endl;
  clout << "Phys. Delta T(s):                           physDeltaT=                     " << this->getPhysDeltaT() << std::endl;
  clout << "Characteristical pressure(N/m^2):           charPressure=                   " << this->getCharPhysPressure() << std::endl;
  clout << "Phys. Thermal Conductivity(W/m/K):          physThermalConductivity=        " << this->getThermalConductivity() << std::endl;
  clout << "Phys. specific Heat Capacity(J/kg/K):       physSpecificHeatCapacity=       " << this->getPhysSpecificHeatCapacity() << std::endl;
  clout << "Phys. Thermal Expasion Coefficent(K^-1):    physThermalExpansionCoefficent= " << this->getPhysThermalExpansionCoefficient() << std::endl;
  clout << "Characteristical Phys. low Temperature(K):  charPhysLowTemperature=         " << this->getCharPhysLowTemperature() << std::endl;
  clout << "Characteristical Phys. high Temperature(K): charPhysHighTemperature=        " << this->getCharPhysHighTemperature() << std::endl;
  clout << "Prandtl number:                             prandtlNumber=                  " << this->getPrandtlNumber() << std::endl;
  clout << "Rayleigh number:                            rayleighNumber=                 " << this->getRayleighNumber() << std::endl;


  clout << "-------------------------------------------------------------" << std::endl;

  clout << "----------------- Conversion factors:-----------------" << std::endl;
  clout << "Voxel length(m):                            physDeltaX=                     " << this->getConversionFactorLength() << std::endl;
  clout << "Time step(s):                               physDeltaT=                     " << this->getConversionFactorTime() << std::endl;
  clout << "Velocity factor(m/s):                       physVelocity=                   " << this->getConversionFactorVelocity() << std::endl;
  clout << "Density factor(kg/m^3):                     physDensity=                    " << this->getConversionFactorDensity() <<  std::endl;
  clout << "Mass factor(kg):                            physMass=                       " << this->getConversionFactorMass() << std::endl;
  clout << "Viscosity factor(m^2/s):                    physViscosity=                  " << this->getConversionFactorViscosity() << std::endl;
  clout << "Force factor(N):                            physForce=                      " << this->getConversionFactorForce() << std::endl;
  clout << "Pressure factor(N/m^2):                     physPressure=                   " << this->getConversionFactorPressure() << std::endl;

  clout << "-------------------------------------------------------------" << std::endl;

  clout << "----------------- ThermalConversion factors:-----------------" << std::endl;
  clout << "Temperature(K):                             temperature=                    " << this->getConversionFactorTemperature() << std::endl;
  clout << "Thermal Diffusity(m^2/s):                   physThermalDiffusity=           " << this->getConversionFactorThermalDiffusivity() << std::endl;
  clout << "specific Heat Capacity(J/kg):               physSpecificHeatCapacity=       " << this->getConversionFactorSpecificHeatCapacity() << std::endl;
  clout << "Thermal Coductivity(W/m/K):                 physThermalConductivity=        " << this->getConversionFactorThermalConductivity() <<  std::endl;
  clout << "HeatFlux(W):                                physHeatFlux=                   " << this->getConversionFactorHeatFlux() << std::endl;

  clout << "-------------------------------------------------------------" << std::endl;
}

}

#endif
