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

#ifndef RADIATIVEUNITCONVERTER_H
#define RADIATIVEUNITCONVERTER_H


#include <fstream>
#include "io/ostreamManager.h"
#include "core/unitConverter.h"
#include "core/singleton.h"
#include "utilities/omath.h"

namespace olb {

double getThetaRefracted(double const& thetaIncident, double const& refractiveRelative);
double getFresnelFunction(double const& theta, double const& refractiveRelative);
double R_phi_diff (double const& theta, double const& refractiveRelative);
double R_j_diff (double const& theta, double const& refractiveRelative);
double getRefractionFunction(const double& refractiveRelative);
double getRefractionFunction(const double& refractiveRelative);
double getPartialBBCoefficient(double const& latticeDiffusionCoefficient, double const& relativeRefractiveIndex );

// forward declaration
template<typename T, typename DESCRIPTOR> struct RadiativeUnitConverter;

// wrapper for above function
template <typename T, typename DESCRIPTOR>
double getPartialBBCoefficient(RadiativeUnitConverter<T,DESCRIPTOR> const& converter)
{
  return getPartialBBCoefficient( converter.getLatticeDiffusion(), converter.getRefractiveRelative() );
};

// wrapper for above function
template <typename T, typename DESCRIPTOR>
double getRefractionFunction(RadiativeUnitConverter<T,DESCRIPTOR> const& converter)
{
  return getRefractionFunction(converter.getRefractiveRelative());
};

template <typename T, typename DESCRIPTOR>
struct RadiativeUnitConverter : public UnitConverterFromResolutionAndRelaxationTime<T,DESCRIPTOR> {
  /** Documentation of constructor:
    *   \param resolution   is number of voxel per 1 meter
    *   \param latticeRelaxationTime    see class UnitConverterFromResolutionAndRelaxationTime
    *   \param physAbsorption   physical absorption in 1/meter
    *   \param physScattering   physical scattering in 1/meter
    */
  RadiativeUnitConverter( int resolution, T latticeRelaxationTime, T physAbsorption, T physScattering, T anisotropyFactor=0, T charPhysLength=1, T refractiveMedia=1, T refractiveAmbient=1 )
    : UnitConverterFromResolutionAndRelaxationTime<T, DESCRIPTOR>( resolution, latticeRelaxationTime, charPhysLength, /*visc*/ 1./(3*(physAbsorption+physScattering)), T(1), T(1) )
  {
    this->_physAbsorption = physAbsorption;
    this->_physScattering = physScattering;
    this->_anisotropyFactor = anisotropyFactor;
    this->_extinction = physAbsorption+physScattering;
    this->_scatteringAlbedo = physScattering/(physAbsorption+physScattering);
    this->_physDiffusion = 1.0 / (3.0*(physAbsorption+physScattering));
    this->_effectiveAttenuation = util::sqrt(3*physAbsorption*(physAbsorption+physScattering));
    this->_refractiveRelative = refractiveMedia/refractiveAmbient;
    this->_latticeAbsorption = physAbsorption*this->getConversionFactorLength();
    this->_latticeScattering = physScattering*this->getConversionFactorLength();
    this->_latticeDiffusion = this->_physDiffusion/this->getConversionFactorLength();
  }

  void print(std::ostream& fout) const override;

  using UnitConverter<T,DESCRIPTOR>::print;

};

template <typename T, class DESCRIPTOR>
void RadiativeUnitConverter<T, DESCRIPTOR>::print(std::ostream& clout) const
{
  clout << "----------------- UnitConverter information -----------------" << std::endl;
  clout << "-- Parameters:" << std::endl;
  clout << "Resolution:                       N=              " << this->getResolution() << std::endl;
  clout << "Lattice relaxation frequency:     omega=          " << this->getLatticeRelaxationFrequency() << std::endl;
  clout << "Lattice relaxation time:          tau=            " << this->getLatticeRelaxationTime() << std::endl;
  clout << "Characteristical length(m):       charL=          " << this->getCharPhysLength() << std::endl;
  clout << "Phys. density(kg/m^d):            charRho=        " << this->getPhysDensity() << std::endl;
  clout << "Phys. absorption(1/m):            mu_a=           " << this->getPhysAbsorption() << std::endl;
  clout << "Phys. scattering(1/m):            mu_s=           " << this->getPhysScattering() << std::endl;
  clout << "Extinction(1/m):                  mu_t=           " << this->getExtinction() << std::endl;
  clout << "Effective attenuation(1/m):       mu_eff=         " << this->getEffectiveAttenuation() << std::endl;
  clout << "Phys. diffusion(m):               D=              " << this->getPhysDiffusion() << std::endl;
  clout << "Single scattering albedo:         albedo=         " << this->getScatteringAlbedo() << std::endl;
  clout << "Anisotropy factor:                g=              " << this->getAnisotropyFactor() << std::endl;

  clout << std::endl;
  clout << "Lattice diffusion:                D^*=            " << this->getLatticeDiffusion() << std::endl;
  clout << "Lattice absorption:               absorption=     " << this->getLatticeAbsorption() << std::endl;
  clout << "Lattice scattering:               scattering=     " << this->getLatticeScattering() << std::endl;
  clout << "Lattice sink:                     sink=           " << 3./8.*this->getLatticeAbsorption()*(this->getLatticeScattering()+this->getLatticeAbsorption()) << std::endl;
  clout << "C_R: " << getRefractionFunction(this->getRefractiveRelative()) << std::endl;
  clout << "r_F: " << getPartialBBCoefficient(this->getLatticeDiffusion(),this->getRefractiveRelative()) << std::endl;

  clout << std::endl;
  clout << "-- Conversion factors:" << std::endl;
  clout << "Voxel length(m):                  physDeltaX=     " << this->getConversionFactorLength() << std::endl;
  clout << "Time step(s):                     physDeltaT=     " << this->getConversionFactorTime() << std::endl;
  clout << "Density factor(kg/m^3):           physDensity=    " << this->getConversionFactorDensity() <<  std::endl;
  clout << "-------------------------------------------------------------" << std::endl;
}

/// Documentation of implemented functions found in 5.2.2 Biomedical Optics, Principles and Imaging; Wang 2007
double getThetaRefracted(double const& thetaIncident, double const& refractiveRelative)
{
  double thetaRefracted = M_PI/2.;
  if ( refractiveRelative * util::sin(thetaIncident) < 1 ) {
    thetaRefracted = util::asin( refractiveRelative * util::sin(thetaIncident));  // eq.(5.118)
  }
  return thetaRefracted;
};

double getFresnelFunction(double const& theta, double const& refractiveRelative)
{
  double thetaRefracted = getThetaRefracted(theta, refractiveRelative);
  double rf_1 = 0.5 * util::pow((refractiveRelative * util::cos(thetaRefracted) - util::cos(theta)) /
                                (refractiveRelative * util::cos(thetaRefracted) + util::cos(theta)), 2.);
  double rf_2 = 0.5 * util::pow((refractiveRelative * util::cos(theta) - util::cos(thetaRefracted)) /
                                (refractiveRelative * util::cos(theta) + util::cos(thetaRefracted)), 2.);
  return rf_1 + rf_2;   // eq.(5.115)
};

double R_phi_diff (double const& theta, double const& refractiveRelative)
{
  return 2. * util::sin(theta) * util::cos(theta) * getFresnelFunction(theta,refractiveRelative);
};

double R_j_diff (double const& theta, double const& refractiveRelative)
{
  return 3. * util::sin(theta) * util::pow(util::cos(theta),2.) * getFresnelFunction(theta,refractiveRelative);
};

double getRefractionFunction(const double& refractiveRelative)
{
  int N = 10000.0;
  double h = (M_PI / 2.) /double(N);
  double R_phi = 0.0;
  double R_j = 0.0;
  for (int i = 0; i < N; i++) {
    R_phi += h*(R_phi_diff(0.5*h + h*i,refractiveRelative));
    R_j   += h*(R_j_diff  (0.5*h + h*i,refractiveRelative));
  }
  double R_eff = (R_phi + R_j) / (2 - R_phi + R_j);     // eq.(5.112)
  return (1 + R_eff) / (1 - R_eff);                     // eq.(5.111)    C_R = (1 + R_eff) / (1 - R_eff);
};

double getPartialBBCoefficient(double const& latticeDiffusionCoefficient, double const& relativeRefractiveIndex )
{
  double C_R = getRefractionFunction( relativeRefractiveIndex );
  return 2 - 2/(4*latticeDiffusionCoefficient*C_R +1);
};


}  // namespace olb

#endif
