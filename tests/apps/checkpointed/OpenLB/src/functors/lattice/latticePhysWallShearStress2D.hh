/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2019 Albert Mink, Mathias J. Krause, Lukas Baron,
 *  2020 Stephan Simonis
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

#ifndef LATTICE_PHYS_WALL_SHEAR_STRESS_2D_HH
#define LATTICE_PHYS_WALL_SHEAR_STRESS_2D_HH

#include <vector>
#include "utilities/omath.h"
#include <limits>

#include "latticePhysWallShearStress2D.h"
#include "dynamics/lbm.h"
#include "geometry/superGeometry.h"
#include "indicator/superIndicatorF2D.h"
#include "blockBaseF2D.h"
#include "functors/genericF.h"
#include "functors/analytical/analyticalF.h"
#include "functors/analytical/indicator/indicatorF2D.h"
#include "communication/mpiManager.h"

namespace olb {

template<typename T, typename DESCRIPTOR>
SuperLatticePhysWallShearStress2D<T, DESCRIPTOR>::SuperLatticePhysWallShearStress2D(
  SuperLattice<T, DESCRIPTOR>& sLattice, SuperGeometry<T,2>& superGeometry,
  const int material, const UnitConverter<T,DESCRIPTOR>& converter,
  IndicatorF2D<T>& indicator)
  : SuperLatticePhysF2D<T, DESCRIPTOR>(sLattice, converter, 1),
    _superGeometry(superGeometry), _material(material)
{
  this->getName() = "physWallShearStress";
  const int maxC = this->_sLattice.getLoadBalancer().size();
  this->_blockF.reserve(maxC);
  for (int iC = 0; iC < maxC; iC++) {
    this->_blockF.emplace_back(
      new BlockLatticePhysWallShearStress2D<T, DESCRIPTOR>(
        this->_sLattice.getBlock(iC),
        _superGeometry.getBlockGeometry(iC),
        _material,
        this->_converter,
        indicator)
    );
  }
}

template <typename T, typename DESCRIPTOR>
BlockLatticePhysWallShearStress2D<T,DESCRIPTOR>::BlockLatticePhysWallShearStress2D(
  BlockLattice<T,DESCRIPTOR>& blockLattice,
  BlockGeometry<T,2>& blockGeometry,
  int material,
  const UnitConverter<T,DESCRIPTOR>& converter,
  IndicatorF2D<T>& indicator)
  : BlockLatticePhysF2D<T,DESCRIPTOR>(blockLattice,converter,1),
    _blockGeometry(blockGeometry), _material(material)
{
  this->getName() = "physWallShearStress";
  const T scaling = this->_converter.getConversionFactorLength() * 0.1;
  const T omega = 1. / this->_converter.getLatticeRelaxationTime();
  const T dt = this->_converter.getConversionFactorTime();
  _physFactor = -omega * descriptors::invCs2<T,DESCRIPTOR>() / dt * this->_converter.getPhysDensity() * this->_converter.getPhysViscosity();

  std::vector<int> discreteNormalOutwards(3, 0);

  const int nx = _blockGeometry.getNx();
  const int ny = _blockGeometry.getNy();

  _discreteNormal.resize(nx);
  _normal.resize(nx);

  for (int iX = 0; iX < nx; iX++) {
    _discreteNormal[iX].resize(ny);
    _normal[iX].resize(ny);

    for (int iY = 0; iY < ny; iY++) {
      _discreteNormal[iX][iY].resize(2);
      _normal[iX][iY].resize(2);

      if (_blockGeometry.getMaterial({iX, iY}) == _material) {
        discreteNormalOutwards = _blockGeometry.getStatistics().getType(iX, iY);

        _discreteNormal[iX][iY][0] = -discreteNormalOutwards[1];
        _discreteNormal[iX][iY][1] = -discreteNormalOutwards[2];

        Vector<T,2> physR{};
        _blockGeometry.getPhysR(physR, {iX, iY});
        Vector<T,2> origin(physR);
        Vector<T,2> direction(-_discreteNormal[iX][iY][0] * scaling,
                              -_discreteNormal[iX][iY][1] * scaling);
        Vector<T,2> normal(0.,0.);

        indicator.normal(normal, origin, direction);

        T normMag = norm(normal); // [PROTECTION]
        if (normMag < 1e-12 || std::isnan(normMag)) {
          _normal[iX][iY][0] = T(0);
          _normal[iX][iY][1] = T(0);
        } else {
          normal /= normMag;
          _normal[iX][iY][0] = normal[0];
          _normal[iX][iY][1] = normal[1];
        }
      }
    }
  }
}

template <typename T, typename DESCRIPTOR>
bool BlockLatticePhysWallShearStress2D<T,DESCRIPTOR>::operator() (T output[], const int input[])
{
  output[0] = T();

  const int iX = input[0], iY = input[1];

  if (iX < 0 || iY < 0 ||
      iX >= (int)_discreteNormal.size() ||
      iY >= (int)_discreteNormal[iX].size()) {
#ifdef OLB_DEBUG
    std::cout << "Invalid index access in WSS functor.\n";
#endif
    return true;
  }

  if (_blockGeometry.getMaterial({iX, iY}) == _material) {

    T rho = this->_blockLattice.get(iX + _discreteNormal[iX][iY][0],
                                    iY + _discreteNormal[iX][iY][1]).computeRho();

    T stress[3];
    this->_blockLattice.get(iX + _discreteNormal[iX][iY][0],
                            iY + _discreteNormal[iX][iY][1]).computeStress(stress);

    T normalX = _normal[iX][iY][0];
    T normalY = _normal[iX][iY][1];

    T traction[2];
    traction[0] = _physFactor / rho * (stress[0] * normalX + stress[1] * normalY);
    traction[1] = _physFactor / rho * (stress[1] * normalX + stress[2] * normalY);

    T tractionNormal = traction[0] * normalX + traction[1] * normalY;
    T tractionNormalComponent[2] = {tractionNormal * normalX, tractionNormal * normalY};

    T WSS[2];
    WSS[0] = traction[0] - tractionNormalComponent[0];
    WSS[1] = traction[1] - tractionNormalComponent[1];

    output[0] = util::sqrt(WSS[0]*WSS[0] + WSS[1]*WSS[1]);

    if (std::isnan(output[0])) output[0] = T(0);  // [PROTECTION]

    return true;
  }

  return true;
}

} // namespace olb

#endif
