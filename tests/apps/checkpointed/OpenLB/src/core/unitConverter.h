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

#ifndef CORE_UNITCONVERTER_H
#define CORE_UNITCONVERTER_H

#include "utilities/omath.h"
#include "io/ostreamManager.h"
#include "core/util.h"
#include "io/xmlReader.h"
#include "descriptor/fields.h"
#include "utilities/optionalValue.h"

// known design issues
//    1. How can we prevent abuse of constructur by mixing up parameters?
//    2. physical problems may have different names for viscosity, e.g. diffusity,  temperature conductivity
//    4. Feedback about stability or comment the chosen discretization
//    5. Explain why Desctiptor as template
//    6. Is it worth to introduce invConversionDensity to avoid division


namespace olb {

namespace fields {

namespace converter {

struct PHYS_VELOCITY : public descriptors::FIELD_BASE<1> {
  template <typename T, typename DESCRIPTOR,typename FIELD>
  static constexpr auto isValid(FieldD<T,DESCRIPTOR,FIELD> value) {
    return value >= 0;
  }
};
struct PHYS_FORCE : public descriptors::FIELD_BASE<1> {
  template <typename T, typename DESCRIPTOR,typename FIELD>
  static constexpr auto isValid(FieldD<T,DESCRIPTOR,FIELD> value) {
    return value >= 0;
  }
};
struct PHYS_LENGTH : public descriptors::FIELD_BASE<1> {
  template <typename T, typename DESCRIPTOR,typename FIELD>
  static constexpr auto isValid(FieldD<T,DESCRIPTOR,FIELD> value) {
    return value > 0;
  }
 };
struct PHYS_DELTA_X : public descriptors::FIELD_BASE<1> {
  template <typename T, typename DESCRIPTOR,typename FIELD>
  static constexpr auto isValid(FieldD<T,DESCRIPTOR,FIELD> value) {
    return value > 0;
  }
};
struct PHYS_DELTA_T : public descriptors::FIELD_BASE<1> {
  template <typename T, typename DESCRIPTOR,typename FIELD>
  static constexpr auto isValid(FieldD<T,DESCRIPTOR,FIELD> value) {
    return value > 0;
  }
};
struct PHYS_PRESSURE : public descriptors::FIELD_BASE<1> {
  template <typename T, typename DESCRIPTOR,typename FIELD>
  static constexpr auto isValid(FieldD<T,DESCRIPTOR,FIELD> value) {
    return value >= 0;
  }
};

struct LATTICE_TIME : public descriptors::FIELD_BASE<1> {
  template <typename T, typename DESCRIPTOR,typename FIELD>
  static constexpr auto isValid(FieldD<T,DESCRIPTOR,FIELD> value) {
    return value >= 0;
  }
};

struct LATTICE_VISCOSITY : public descriptors::FIELD_BASE<1> { };

}

}

template <typename T>
class UnitConverterBase {
public:
  virtual ~UnitConverterBase() = default;

  virtual void print() const = 0;
  virtual void print(std::ostream& fout) const = 0;
  virtual void write(std::string const& fileName = "unitConverter") const = 0;

  /// return resolution
  int getResolution(  ) const
  {
    return _resolution;
  }
  /// return relaxation time in lattice units
  T getLatticeRelaxationTime(  ) const
  {
    return _latticeRelaxationTime;
  }
  /// return relaxation frequency in lattice units
  T getLatticeRelaxationFrequency(  ) const
  {
    return 1./_latticeRelaxationTime;
  }
  /// return relaxation frequency in lattice units computed from given physical diffusivity in __m^2 / s__
  template <typename DESCRIPTOR_>
  T getLatticeRelaxationFrequencyFromDiffusivity( const T physDiffusivity ) const
  {
    return 1.0 / ( physDiffusivity / _conversionViscosity * descriptors::invCs2<T,DESCRIPTOR_>() + 0.5 );
  }
  /// return characteristic length in physical units
  T getCharPhysLength(  ) const
  {
    return _charPhysLength;
  }
  /// return characteristic velocity in physical units
  T getCharPhysVelocity(  ) const
  {
    return _charPhysVelocity;
  }
  /// return characteristic velocity in lattice units
  T getCharLatticeVelocity(  ) const
  {
    return _charLatticeVelocity;
  }
  /// return characteristic CFL number
  T getCharCFLnumber(  ) const
  {
    return _charLatticeVelocity;
  }
  /// return viscosity in physical units
  T getPhysViscosity(  ) const
  {
    return _physViscosity;
  }
  /// return density in physical units
  T getPhysDensity(  ) const
  {
    return _physDensity;
  }
  /// return characteristic pressure in physical units
  T getCharPhysPressure(  ) const
  {
    return _charPhysPressure;
  }
  /// return Reynolds number
  T getReynoldsNumber(  ) const
  {
    return _charPhysVelocity * _charPhysLength / _physViscosity;

    // Power law
    // Calculation according to Metzner and Reed (1955): 10.1002/aic.690010409
    //return util::pow(this->_charPhysVelocity, T{2} - _powerLawIndex) * util::pow(this->_charPhysLength, _powerLawIndex)
    // / _physConsistencyCoeff;
  }
  /// return Mach number
  T getMachNumber() const
  {
    return getCharLatticeVelocity() * util::sqrt(_invCs2.value());
  }
  /// return Knudsen number
  virtual T getKnudsenNumber(  ) const
  {
    // This calculates the lattice Knudsen number.
    // See e.g. (7.22) in "The Lattice Boltzmann Method: Principles and Practice" [kruger2017lattice].
    return getMachNumber() / getReynoldsNumber();

    // ADE unit converter
    //return this->getMachNumber()/getPecletNumber();
  }
  /// conversion from lattice to  physical length
  T getPhysLength( int latticeLength ) const
  {
    return _conversionLength * latticeLength;
  }
  /// conversion from physical to lattice length, returns number of voxels for given physical length
  int getLatticeLength( T physLength ) const
  {
    return int( physLength / _conversionLength + 0.5 );
  }
  /// access (read-only) to private member variable
  T getConversionFactorLength() const
  {
    return _conversionLength;
  }
  /// returns grid spacing (voxel length) in __m__
  T getPhysDeltaX() const
  {
    return _conversionLength;
  }

  /// conversion from lattice to  physical time
  T getPhysTime( size_t latticeTime ) const
  {
    return _conversionTime * latticeTime;
  }
  /// conversion from physical to lattice time
  size_t getLatticeTime( T physTime ) const
  {
    return size_t(physTime / _conversionTime + 0.5);
  }
  /// access (read-only) to private member variable
  T getConversionFactorTime() const
  {
    return _conversionTime;
  }
  /// returns time spacing (timestep length) in __s__
  T getPhysDeltaT() const
  {
    return _conversionTime;
  }

  /// conversion from lattice to  physical velocity
  T getPhysVelocity( T latticeVelocity ) const
  {
    return _conversionVelocity * latticeVelocity;
  }
  /// conversion from physical to lattice velocity
  T getLatticeVelocity( T physVelocity ) const
  {
    return physVelocity / _conversionVelocity;
  }
  /// conversion from physical to lattice velocity
  template <unsigned D>
  Vector<T,D> getLatticeVelocity(Vector<T,D> physU) const
  {
    return Vector<T,D>([&](std::size_t iD) -> T {
      return this->getLatticeVelocity(physU[iD]);
    });
  }
  /// access (read-only) to private member variable
  T getConversionFactorVelocity() const
  {
    return _conversionVelocity;
  }

  /// conversion from lattice to  physical density
  T getPhysDensity( T latticeDensity ) const
  {
    return _conversionDensity * latticeDensity;
  }
  /// conversion from physical to lattice density
  T getLatticeDensity( T physDensity ) const
  {
    return physDensity / _conversionDensity;
  }
  T getLatticeDensityFromPhysPressure( T physPressure ) const
  {
    return getLatticePressure(physPressure) * _invCs2 + 1.0;
  }
  /// access (read-only) to private member variable
  T getConversionFactorDensity() const
  {
    return _conversionDensity;
  }

  /// conversion from lattice to  physical mass
  T getPhysMass( T latticeMass ) const
  {
    return _conversionMass * latticeMass;
  }
  /// conversion from physical to lattice mass
  T getLatticeMass( T physMass ) const
  {
    return physMass / _conversionMass;
  }
  /// access (read-only) to private member variable
  T getConversionFactorMass() const
  {
    return _conversionMass;
  }

  /// conversion from lattice to  physical viscosity
  T getPhysViscosity( T latticeViscosity ) const
  {
    return _conversionViscosity * latticeViscosity;
  }
  /// conversion from physical to lattice viscosity
  T getLatticeViscosity(  ) const
  {
    return _physViscosity / _conversionViscosity;
  }
  /// access (read-only) to private member variable
  T getConversionFactorViscosity() const
  {
    return _conversionViscosity;
  }

  /// conversion from lattice to  physical force
  T getPhysForce( T latticeForce ) const
  {
    return _conversionForce * latticeForce;
  }
  /// conversion from lattice to  physical force vector
  template <unsigned D>
  Vector<T,D> getPhysForce(Vector<T,D> latticeForce) const
  {
    return Vector<T,D>([&](std::size_t iD) -> T {
      return this->getPhysForce(latticeForce[iD]);
    });
  }
  /// conversion from physical to lattice force
  T getLatticeForce( T physForce ) const
  {
    return physForce / _conversionForce;
  }
  /// access (read-only) to private member variable
  T getConversionFactorForce() const
  {
    return _conversionForce;
  }

  /// conversion from lattice to  physical torque
  T getPhysTorque ( T latticeTorque ) const
  {
    return _conversionTorque * latticeTorque;
  }
  /// conversion from lattice to  physical force vector
  template <unsigned D>
  Vector<T,D> getPhysTorque(Vector<T,D> latticeTorque) const
  {
    return Vector<T,D>([&](std::size_t iD) -> T {
      return this->getPhysTorque(latticeTorque[iD]);
    });
  }
  /// conversion from physical to lattice torque
  T getLatticeTorque( T physTorque ) const
  {
    return physTorque / _conversionTorque;
  }
  /// access (read-only) to private member variable
  T getConversionFactorTorque() const
  {
    return _conversionTorque;
  }

  /// conversion from lattice to  physical pressure
  T getPhysPressure( T latticePressure ) const
  {
    return _conversionPressure * latticePressure + _charPhysPressure;
  }
  /// conversion from physical to lattice pressure
  T getLatticePressure( T physPressure ) const
  {
    return ( physPressure - _charPhysPressure ) / _conversionPressure;
  }
  /// access (read-only) to private member variable
  T getConversionFactorPressure() const
  {
    return _conversionPressure;
  }

  // from thermalUnitConverter
  /// return thermal relaxation time in lattice units
  T getLatticeThermalRelaxationTime(  ) const
  {
    return _latticeThermalRelaxationTime;
  };
  /// return thermal relaxation frequency in lattice units
  T getLatticeThermalRelaxationFrequency(  ) const
  {
    return 1.0 / _latticeThermalRelaxationTime;
  };

  /// return characteristic low temperature in physical units
  T getCharPhysLowTemperature(  ) const
  {
    return _charPhysLowTemperature;
  };
  /// return characteristic high temperature in physical units
  T getCharPhysHighTemperature(  ) const
  {
    return _charPhysHighTemperature;
  };
  /// return characteristic temperature difference in physical units
  T getCharPhysTemperatureDifference(  ) const
  {
    return _charPhysTemperatureDifference;
  };
  /// return thermal expansion coefficient in physical units
  T getPhysThermalExpansionCoefficient(  ) const
  {
    return _physThermalExpansionCoefficient;
  };
  /// return thermal diffusivity in physical units
  T getPhysThermalDiffusivity(  ) const
  {
    return _physThermalDiffusivity;
  };
  /// return specific heat capacity in physical units
  T getPhysSpecificHeatCapacity(  ) const
  {
    return _physSpecificHeatCapacity;
  };
  /// return thermal conductivity in physical units
  T getThermalConductivity(  ) const
  {
    return _physThermalConductivity;
  };

  /// conversion from lattice to physical temperature
  T getPhysTemperature( T latticeTemperature ) const
  {
    return _conversionTemperature * (latticeTemperature - 0.5) + _charPhysLowTemperature;
  };
  /// conversion from physical to lattice temperature
  T getLatticeTemperature( T physTemperature ) const
  {
    return (physTemperature - _charPhysLowTemperature) / _conversionTemperature + 0.5;
  };

  /// conversion from lattice to physical thermal diffusivity
  T getPhysThermalDiffusivity( T latticeThermalDiffusivity ) const
  {
    return _conversionThermalDiffusivity * latticeThermalDiffusivity;
  };
  /// conversion from physical to lattice thermal diffusivity
  T getLatticeThermalDiffusivity( T physThermalDiffusivity ) const
  {
    return physThermalDiffusivity / _conversionThermalDiffusivity;
  };
  /// access (read-only) to private member variable
  T getConversionFactorThermalDiffusivity() const
  {
    return _conversionThermalDiffusivity;
  };


  /// conversion from lattice to physical specific heat capacity
  T getPhysSpecificHeatCapacity( T latticeSpecificHeatCapacity ) const
  {
    return _conversionSpecificHeatCapacity * latticeSpecificHeatCapacity;
  };
  /// conversion from physical to lattice specific heat capacity
  T getLatticeSpecificHeatCapacity( T physSpecificHeatCapacity ) const
  {
    return physSpecificHeatCapacity / _conversionSpecificHeatCapacity;
  };
  /// access (read-only) to private member variable
  T getConversionFactorSpecificHeatCapacity() const
  {
    return _conversionSpecificHeatCapacity;
  };

  /// conversion from lattice to physical thermal  conductivity
  T getPhysThermalConductivity( T latticeThermalConductivity ) const
  {
    return _conversionThermalConductivity * latticeThermalConductivity;
  };
  /// conversion from physical to lattice thermal  conductivity
  T getLatticeThermalConductivity( T physThermalConductivity ) const
  {
    return physThermalConductivity / _conversionThermalConductivity;
  };
  /// access (read-only) to private member variable
  T getConversionFactorThermalConductivity() const
  {
    return _conversionThermalConductivity;
  };

  /// conversion from lattice to physical heat flux
  T getPhysHeatFlux( T latticeHeatFlux ) const
  {
    return _conversionHeatFlux * latticeHeatFlux;
  };
  /// conversion from physical to lattice heat flux
  T getLatticeHeatFlux( T physHeatFlux ) const
  {
    return physHeatFlux / _conversionHeatFlux;
  };
  /// access (read-only) to private member variable
  T getConversionFactorHeatFlux() const
  {
    return _conversionHeatFlux;
  };
  T getPrandtlNumber() const
  {
    return this->_physViscosity/_physThermalDiffusivity;
  };
  T getRayleighNumber() const
  {
    return 9.81 * _physThermalExpansionCoefficient/this->_physViscosity/_physThermalDiffusivity * (_charPhysHighTemperature - _charPhysLowTemperature) * util::pow(this->_charPhysLength.value(),3);
  };

  // from multiPhaseUnitConverter
  /// return characteristic temperature in physical units
  T getCharPhysTemperature(  ) const {
    return _charPhysTemperature;
  };
  /// return equation of state parameter a in physical units
  T getPhysEoSa(  ) const {
    return _physEoSa;
  };
  /// return equation of state parameter b in physical units
  T getPhysEoSb(  ) const {
    return _physEoSb;
  };
  /// return molar mass in physical units
  T getPhysMolarMass(  ) const {
    return _physMolarMass;
  };
  /// return surface tension in physical units
  T getPhysSurfaceTension(  ) const {
    return _physSurfaceTension;
  };
  /// return characteristic temperature in physical units
  T getPhysTemperature(  ) const {
    return _charPhysTemperature;
  };
  /// access (read-only) to private member variable
  T getConversionFactorEoSa() const {
    return _conversionEoSa;
  };
  /// access (read-only) to private member variable
  T getConversionFactorEoSb() const {
    return _conversionEoSb;
  };
  /// access (read-only) to private member variable
  T getConversionFactorMolarMass() const {
    return _conversionMolarMass;
  };
  /// access (read-only) to private member variable
  T getConversionFactorGasConstant() const {
    return _conversionGasConstant;
  };
  /// access (read-only) to private member variable
  T getConversionFactorSurfaceTension() const {
    return _conversionSurfaceTension;
  };
  /// access (read-only) to private member variable
  T getConversionFactorTemperature(  ) const {
    return _conversionTemperature;
  };
  /// return lattice surface tension for parameter fitting
  T getLatticeSurfaceTension(  ) const {
    return _latticeSurfaceTension;
  };
  /// access (read-only) to private member variable
  T getConversionFactorChemicalPotential() const {
    return _conversionChemicalPotential;
  };
  /// compute relaxation time from physical viscosity
  T computeRelaxationTimefromPhysViscosity(T userViscosity) const {
    return 0.5 + _invCs2 *
                 userViscosity / this->_conversionViscosity;
  };
  /// compute lattice surface tension from physical one
  T computeLatticeSurfaceTension(T userSurfaceTension) const {
    return userSurfaceTension / this->_conversionSurfaceTension;
  };
  /// compute Reynolds from kinematic viscosity
  T computeReynolds(T userVelocity, T userLength, T userViscosity) const {
    return userVelocity * userLength / userViscosity;
  };
  /// compute Weber
  T computeWeber(T userVelocity, T userLength, T userSurfaceTension) const {
    return userLength * userVelocity * userVelocity / userSurfaceTension;
  };

  //from powerLawUnitConverter
  /// return consistency coefficient in physical units
  T getPhysConsistencyCoeff( ) const {
    return _physConsistencyCoeff;
  }
  /// conversion from lattice to  physical consistency coefficient
  T getPhysConsistencyCoeff( T latticeConsistencyCoeff ) const {
    return _conversionConsistencyCoeff * latticeConsistencyCoeff;
  }
  /// conversion from physical to lattice consistency coefficient
  T getLatticeConsistencyCoeff(  ) const {
    return _physConsistencyCoeff / _conversionConsistencyCoeff;
  }
  /// access (read-only) to private member variable
  T getConversionFactorConsistencyCoeff() const {
    return _conversionConsistencyCoeff;
  }
  /// access (read-only) to private member variable
  T getPowerLawIndex() const {
    return _powerLawIndex;
  }

  // from adeUnitConverter
  /// return thermal relaxation time in lattice units
  T getLatticeAdeRelaxationTime() const {
    return _latticeAdeRelaxationTime;
  };
  /// return thermal relaxation frequency in lattice units
  T getLatticeAdeRelaxationFrequency() const {
    return 1.0 / _latticeAdeRelaxationTime;
  };
  T getPhysDiffusivity() const {
    return _physDiffusivity;
  }
  T getLatticeDiffusivity() const {
    return _physDiffusivity / _conversionDiffusivity ;
  }
  T getConversionFactorDiffusivity() const {
    return _conversionDiffusivity;
  }
  T getPecletNumber() const {
    return getCharPhysVelocity()  * getCharPhysLength() / getPhysDiffusivity();
  };

  // from adsorptionUnitConverter
  /// conversion factor to convert particle density from lattice units to kg/m^3
  T getConversionFactorParticleDensity() const {
    return _particleConcentrationAdsorption;
  }
  T getPhysParticleConcentration(T c) const {
    return c * _particleConcentrationAdsorption;
  }
  T getPhysConcentration(T c) const {
    return c * this->getConversionFactorDensity();
  }
  T getPhysLoading(T Cq) const {
    return Cq * _particleConcentrationAdsorption;
  }
  T getSchmidtNumber() const {
    return getPhysViscosity() / getPhysDiffusivity();
  };
  T getFourierNumber() const {
    return getPhysDiffusivity() * getPhysDeltaT() / getPhysDeltaX() / getPhysDeltaX();
  };

  // from radiativeUnitConverter
  T getPhysAbsorption() const {
    return _physAbsorption;
  };
  T getPhysScattering() const {
    return _physScattering;
  };
  T getAnisotropyFactor() const {
    return _anisotropyFactor;
  };
  T getExtinction() const {
    return _extinction;
  };
  T getScatteringAlbedo() const {
    return _scatteringAlbedo;
  };
  T getPhysDiffusion() const {
    return _physDiffusion;
  };
  T getEffectiveAttenuation() const {
    return _effectiveAttenuation;
  };
  T getLatticeAbsorption() const {
    return _latticeAbsorption;
  };
  T getLatticeScattering() const {
    return _latticeScattering;
  };
  T getLatticeDiffusion() const {
    return _latticeDiffusion;
  };
  T getRefractiveRelative() const {
    return _refractiveRelative;
  };

  // from LinElaUnitConverter
  T getCharPhysDisplacement( ) const {
    return _charPhysDisplacement;
  }
  T getLatticeShearModulus( ) const {
    return _shearModulus;
  };
  T getPhysShearModulus( ) const {
    return _shearModulus * (_conversionLength * _conversionLength * _dampingFactor) / _conversionTime;
  };
  T getLatticeBulkModulus( ) const {
    return _bulkModulus;
  };
  T getPhysBulkModulus( ) const {
    return _bulkModulus * (_conversionLength * _conversionLength * _dampingFactor) / _conversionTime;
  };
  T getLatticeLambda( ) const {
    return _lambda;
  };
  T getPhysLambda( ) const {
    return _lambda * (_conversionLength * _conversionLength * _dampingFactor) / _conversionTime;
  };
  T getLatticeYoungsModulus() const {
    return _youngsModulus;
  };
  T getEpsilon() const {
    return _epsilon;
  };
  T getCharPhysTime() const {
    return _charPhysTime;
  };
  T getPhysYoungsModulus() const {
    return _youngsModulus * (_conversionLength * _conversionLength * _dampingFactor) / _conversionTime;
  };
  T getDampingFactor() const {
    return _dampingFactor;
  };
  T getPoissonRatio() const {
    return _poissonRatio;
  };

protected:
  OptionalValue<T> _invCs2;

  // conversion factors
  OptionalValue<T> _conversionLength;      // m
  OptionalValue<T> _conversionTime;        // s
  OptionalValue<T> _conversionVelocity;    // m / s
  OptionalValue<T> _conversionDensity;     // kg / m^3
  OptionalValue<T> _conversionMass;        // kg
  OptionalValue<T> _conversionViscosity;   // m^2 / s
  OptionalValue<T> _conversionForce;       // kg m / s^2
  OptionalValue<T> _conversionTorque;      // kg m^2 / s^2
  OptionalValue<T> _conversionPressure;    // kg / m s^2

  // physical units, e.g characteristic or reference values
  OptionalValue<T> _charPhysLength;        // m
  OptionalValue<T> _charPhysVelocity;      // m / s
  OptionalValue<T> _physViscosity;         // m^2 / s
  OptionalValue<T> _physDensity;           // kg / m^3
  OptionalValue<T> _charPhysPressure;      // kg / m s^2

  // lattice units, discretization parameters
  OptionalValue<std::size_t> _resolution;
  OptionalValue<T> _latticeRelaxationTime;
  OptionalValue<T> _charLatticeVelocity;   //

  // conversion factors
  OptionalValue<T> _conversionTemperature; // K
  OptionalValue<T> _conversionThermalDiffusivity; // m^2 / s
  OptionalValue<T> _conversionSpecificHeatCapacity; // J / kg K = m^2 / s^2 K
  OptionalValue<T> _conversionThermalConductivity; // W / m K = kg m / s^3 K
  OptionalValue<T> _conversionHeatFlux; // W / m^2 = kg / s^3

  // physical units, e.g characteristic or reference values
  OptionalValue<T> _charPhysLowTemperature; // K
  OptionalValue<T> _charPhysHighTemperature; // K
  OptionalValue<T> _charPhysTemperatureDifference; // K
  OptionalValue<T> _physThermalExpansionCoefficient; // 1 / K
  OptionalValue<T> _physThermalDiffusivity; // m^2 / s
  OptionalValue<T> _physSpecificHeatCapacity; // J / kg K = m^2 / s^2 K
  OptionalValue<T> _physThermalConductivity; // W / m K = kg m / s^3 K

  // lattice units, discretization parameters
  OptionalValue<T> _latticeThermalRelaxationTime; // -

  // ADE lattice units
  OptionalValue<T> _physDiffusivity;
  OptionalValue<T> _conversionDiffusivity;
  OptionalValue<T> _latticeAdeRelaxationTime;

  // MultiPhase conversion factors
  OptionalValue<T> _conversionEoSa;                      // kg m^5 / s^2 mol^2
  OptionalValue<T> _conversionEoSb;                      // m^3 / mol
  OptionalValue<T> _conversionMolarMass;                 // kg / mol
  OptionalValue<T> _conversionGasConstant = T{8.314462618}; // J / mol K = kg m^2 / s^2 mol K
  OptionalValue<T> _conversionSurfaceTension;            // J / m^2 = kg / s^2
  OptionalValue<T> _physEoSa;                            // kg m^5 / s^2 mol^2
  OptionalValue<T> _physEoSb;                            // m^3 / mol
  OptionalValue<T> _physEoSav;
  OptionalValue<T> _physEoSbv;
  OptionalValue<T> _physMolarMass;                       // kg / mol
  OptionalValue<T> _physSurfaceTension;                  // J / m^2 = kg / s^2
  OptionalValue<T> _charPhysTemperature;                 // K
  OptionalValue<T> _latticeSurfaceTension;               // -
  OptionalValue<T> _conversionChemicalPotential;         // J / kg = m^2 / s^2

  // power law conversion factors
  OptionalValue<T> _conversionConsistencyCoeff;          // m^2 s^(n-2)
  OptionalValue<T> _powerLawIndex;
  OptionalValue<T> _physConsistencyCoeff;                // m^2 s^(n-2)

  // adsorption factors
  OptionalValue<T> _physViscosityAdsorption;
  OptionalValue<T> _conversionViscosityAdsorption;
  OptionalValue<T> _particleConcentrationAdsorption;

  // radiative factors
  OptionalValue<T> _physAbsorption;
  OptionalValue<T> _physScattering;
  OptionalValue<T> _anisotropyFactor;
  OptionalValue<T> _extinction;
  OptionalValue<T> _scatteringAlbedo;
  OptionalValue<T> _physDiffusion;
  OptionalValue<T> _effectiveAttenuation;
  OptionalValue<T> _refractiveRelative;
  OptionalValue<T> _latticeAbsorption;
  OptionalValue<T> _latticeScattering;
  OptionalValue<T> _latticeDiffusion;

  // linear elasticity factors
  OptionalValue<T> _charPhysTime;
  OptionalValue<T> _charPhysDisplacement;
  OptionalValue<T> _epsilon;
  OptionalValue<T> _youngsModulus;
  OptionalValue<T> _bulkModulus;
  OptionalValue<T> _shearModulus;
  OptionalValue<T> _lambda;
  OptionalValue<T> _poissonRatio;
  OptionalValue<T> _dampingFactor;

};


/** Conversion between physical and lattice units, as well as discretization.
* Be aware of the nomenclature:
* We distingish between physical (dimensioned) and lattice (dimensionless) values.
* A specific conversion factor maps the two different scopes,
* e.g. __physLength = conversionLength * latticeLength__
*
* For pressure and temperature we first shift the physical values by a characteristic value to asure a lattice pressure and lattice temperature between 0 and 1, e.g. __physPressure - charPhysPressure = conversionPressure * latticePressure__
*
*  \param latticeRelaxationTime   relaxation time, have to be greater than 0.5!
*  - - -
*  \param physViscosity         physical kinematic viscosity in __m^2 / s__
*  \param physDensity           physical density in __kg / m^3__
*  - - -
*  \param conversionLength      conversion factor for length __m__
*  \param conversionTime        conversion factor for time __s__
*  \param conversionMass        conversion factor for mass __kg__
*  - - -
*  \param conversionVelocity    conversion velocity __m / s__
*  \param conversionViscosity   conversion kinematic viscosity __m^2 / s__
*  \param conversionDensity     conversion density __kg / m^3__
*  \param conversionForce       conversion force __kg m / s^2__
*  \param conversionPressure    conversion pressure __kg / m s^2__
*  - - -
*  \param resolution            number of grid points per charPhysLength
*  - - -
*  \param charLatticeVelocity
*/
template <typename T, typename DESCRIPTOR>
struct UnitConverter : public UnitConverterBase<T> {
  /** Documentation of constructor:
    *  \param physDeltaX              spacing between two lattice cells in __m__
    *  \param physDeltaT              time step in __s__
    *  \param charPhysLength          reference/characteristic length of simulation geometry in __m__
    *  \param charPhysVelocity        maximal or highest expected velocity during simulation in __m / s__
    *  \param physViscosity           physical kinematic viscosity in __m^2 / s__
    *  \param physDensity             physical density in __kg / m^3__
    *  \param charPhysPressure        reference/characteristic physical pressure in Pa = kg / m s^2
    */
  UnitConverter( T physDeltaX, T physDeltaT, T charPhysLength, T charPhysVelocity,
                           T physViscosity, T physDensity, T charPhysPressure = 0 )
  {
    this->_invCs2 = descriptors::invCs2<T,DESCRIPTOR>();
    this->_conversionLength = physDeltaX;
    this->_conversionTime = physDeltaT,
    this->_conversionVelocity = this->_conversionLength / this->_conversionTime;
    this->_conversionDensity = physDensity;
    this->_conversionMass = this->_conversionDensity * util::pow(this->_conversionLength.value(), 3);
    this->_conversionViscosity = this->_conversionLength * this->_conversionLength / this->_conversionTime;
    this->_conversionForce = this->_conversionMass * this->_conversionLength / (this->_conversionTime * this->_conversionTime);
    this->_conversionTorque = this->_conversionMass * this->_conversionLength * this->_conversionLength / (this->_conversionTime * this->_conversionTime);
    this->_conversionPressure = this->_conversionForce / util::pow(this->_conversionLength.value(), 2);
    this->_charPhysLength = charPhysLength;
    this->_charPhysVelocity = charPhysVelocity;
    this->_physViscosity = physViscosity;
    this->_physDensity = physDensity;
    this->_charPhysPressure = charPhysPressure;
    this->_resolution = (std::size_t)(this->_charPhysLength / this->_conversionLength + 0.5);
    this->_latticeRelaxationTime = (this->_physViscosity / this->_conversionViscosity * descriptors::invCs2<T,DESCRIPTOR>()) + 0.5;
    this->_charLatticeVelocity = this->_charPhysVelocity / this->_conversionVelocity;
  }

  template <typename _DESCRIPTOR>
  UnitConverter(const UnitConverter<T,_DESCRIPTOR>& rhs) {
    static_cast<UnitConverterBase<T>&>(*this) = static_cast<const UnitConverterBase<T>&>(rhs);
  }

  virtual void print(std::ostream& fout) const;
  virtual void write(std::string const& fileName = "unitConverter") const;

  void print() const;

};

template <typename T, typename DESCRIPTOR>
UnitConverter<T,DESCRIPTOR> convectivelyRefineUnitConverter(
  const UnitConverter<T,DESCRIPTOR>& converter,
  unsigned scale = 2)
{
  const T refinementFactor = T{1} / scale;
  return UnitConverter<T,DESCRIPTOR>(
    converter.getPhysDeltaX() * refinementFactor,
    converter.getPhysDeltaT() * refinementFactor,
    converter.getCharPhysLength(),
    converter.getCharPhysVelocity(),
    converter.getPhysViscosity(),
    converter.getPhysDensity(),
    converter.getCharPhysPressure()
  );
}

/// creator function with data given by a XML file
template <typename T, typename DESCRIPTOR>
UnitConverter<T, DESCRIPTOR>* createUnitConverter(XMLreader const& params);

template <typename T, typename DESCRIPTOR>
struct UnitConverterFromResolutionAndRelaxationTime : public UnitConverter<T, DESCRIPTOR> {
  UnitConverterFromResolutionAndRelaxationTime(
    size_t resolution,
    T latticeRelaxationTime,
    T charPhysLength,
    T charPhysVelocity,
    T physViscosity,
    T physDensity,
    T charPhysPressure = 0) : UnitConverter<T, DESCRIPTOR>(
        (charPhysLength/resolution),
        (latticeRelaxationTime - 0.5) / descriptors::invCs2<T,DESCRIPTOR>() * util::pow((charPhysLength/resolution),2) / physViscosity,
        charPhysLength,
        charPhysVelocity,
        physViscosity,
        physDensity,
        charPhysPressure)
  { }
};

template <typename T, typename DESCRIPTOR>
struct UnitConverterFromResolutionAndLatticeVelocity : public UnitConverter<T, DESCRIPTOR> {
  UnitConverterFromResolutionAndLatticeVelocity(
    size_t resolution,
    T charLatticeVelocity,
    T charPhysLength,
    T charPhysVelocity,
    T physViscosity,
    T physDensity,
    T charPhysPressure = 0) : UnitConverter<T, DESCRIPTOR>(
        (charPhysLength/resolution),
        (charLatticeVelocity / charPhysVelocity * charPhysLength / resolution),
        charPhysLength,
        charPhysVelocity,
        physViscosity,
        physDensity,
        charPhysPressure)
  { }
};

template <typename T, typename DESCRIPTOR>
struct UnitConverterFromRelaxationTimeAndLatticeVelocity : public UnitConverter<T, DESCRIPTOR> {
  UnitConverterFromRelaxationTimeAndLatticeVelocity(
    T latticeRelaxationTime,
    T charLatticeVelocity,
    T charPhysLength,
    T charPhysVelocity,
    T physViscosity,
    T physDensity,
    T charPhysPressure = 0) : UnitConverter<T, DESCRIPTOR>(
        (physViscosity * charLatticeVelocity / charPhysVelocity * descriptors::invCs2<T,DESCRIPTOR>() / (latticeRelaxationTime - 0.5)),
        (physViscosity * charLatticeVelocity * charLatticeVelocity / charPhysVelocity / charPhysVelocity * descriptors::invCs2<T,DESCRIPTOR>() / (latticeRelaxationTime - 0.5)),
        charPhysLength,
        charPhysVelocity,
        physViscosity,
        physDensity,
        charPhysPressure)
  {
  }
};

template<typename T, typename DESCRIPTOR, typename MEMBER, typename... ARGS>
std::unique_ptr<UnitConverter<T,DESCRIPTOR>> createUnitConverter(ARGS&&... args) {
  return std::make_unique<MEMBER>(std::forward<ARGS>(args)...);
}

}

#include "thermalUnitConverter.h"
#include "multiPhaseUnitConverter.h"

#endif
