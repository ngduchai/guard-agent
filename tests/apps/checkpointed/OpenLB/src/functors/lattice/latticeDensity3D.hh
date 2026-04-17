/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2012 Lukas Baron, Tim Dornieden, Mathias J. Krause,
 *  Albert Mink
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

#ifndef LATTICE_DENSITY_3D_HH
#define LATTICE_DENSITY_3D_HH

#include<vector>    // for generic i/o
#include<cmath>     // for lpnorm
#include<math.h>

#include "latticeDensity3D.h"
#include "superBaseF3D.h"
#include "functors/analytical/indicator/indicatorBaseF3D.h"
#include "indicator/superIndicatorF3D.h"
#include "dynamics/lbm.h"  // for computation of lattice rho and velocity
#include "geometry/superGeometry.h"
#include "blockBaseF3D.h"
#include "communication/mpiManager.h"
#include "utilities/vectorHelpers.h"

namespace olb {

template<typename T, typename DESCRIPTOR>
SuperLatticeDensity3D<T, DESCRIPTOR>::SuperLatticeDensity3D(
  SuperLattice<T, DESCRIPTOR>& sLattice) : SuperLatticeF3D<T, DESCRIPTOR>(sLattice, 1)
{
  this->getName() = "density";
  int maxC = this->_sLattice.getLoadBalancer().size();
  this->_blockF.reserve(maxC);
  for (int iC = 0; iC < maxC; iC++) {
    this->_blockF.emplace_back(new BlockLatticeDensity3D<T, DESCRIPTOR>(this->_sLattice.getBlock(iC)));
  }
}

template<typename T, typename DESCRIPTOR>
BlockLatticeDensity3D<T, DESCRIPTOR>::BlockLatticeDensity3D(
  BlockLattice<T, DESCRIPTOR>& blockLattice)
  : BlockLatticeF3D<T, DESCRIPTOR>(blockLattice, 1)
{
  this->getName() = "density";
}

template<typename T, typename DESCRIPTOR>
bool BlockLatticeDensity3D<T, DESCRIPTOR>::operator()(T output[], const int input[])
{
  output[0] = this->_blockLattice.get(input[0], input[1], input[2]).computeRho();
  return true;
}

template<typename T, typename DESCRIPTOR>
SuperLatticePressure3D<T, DESCRIPTOR>::SuperLatticePressure3D(
  SuperLattice<T, DESCRIPTOR>& sLattice) : SuperLatticeF3D<T, DESCRIPTOR>(sLattice, 1)
{
  this->getName() = "lattice_pressure";
  int maxC = this->_sLattice.getLoadBalancer().size();
  this->_blockF.reserve(maxC);
  for (int iC = 0; iC < maxC; iC++) {
    this->_blockF.emplace_back(new BlockLatticePressure3D<T, DESCRIPTOR>(this->_sLattice.getBlock(iC)));
  }
}

template<typename T, typename DESCRIPTOR>
BlockLatticePressure3D<T, DESCRIPTOR>::BlockLatticePressure3D(
  BlockLattice<T, DESCRIPTOR>& blockLattice)
  : BlockLatticeF3D<T, DESCRIPTOR>(blockLattice, 1)
{
  this->getName() = "lattice_pressure";
}

template<typename T, typename DESCRIPTOR>
bool BlockLatticePressure3D<T, DESCRIPTOR>::operator()(T output[], const int input[])
{
  output[0] = (this->_blockLattice.get(input[0], input[1], input[2]).computeRho() - T(1)) / descriptors::invCs2<T,DESCRIPTOR>();
  return true;
}

template<typename T, typename DESCRIPTOR>
SuperLatticeSquarePressure3D<T, DESCRIPTOR>::SuperLatticeSquarePressure3D(
  SuperLattice<T, DESCRIPTOR>& sLattice) : SuperLatticeF3D<T, DESCRIPTOR>(sLattice, 1)
{
  this->getName() = "lattice_square_pressure";
  int maxC = this->_sLattice.getLoadBalancer().size();
  this->_blockF.reserve(maxC);
  for (int iC = 0; iC < maxC; iC++) {
    this->_blockF.emplace_back(new BlockLatticeSquarePressure3D<T, DESCRIPTOR>(this->_sLattice.getBlock(iC)));
  }
}

template<typename T, typename DESCRIPTOR>
BlockLatticeSquarePressure3D<T, DESCRIPTOR>::BlockLatticeSquarePressure3D(
  BlockLattice<T, DESCRIPTOR>& blockLattice)
  : BlockLatticeF3D<T, DESCRIPTOR>(blockLattice, 1)
{
  this->getName() = "lattice_square_pressure";
}

template<typename T, typename DESCRIPTOR>
bool BlockLatticeSquarePressure3D<T, DESCRIPTOR>::operator()(T output[], const int input[])
{
  output[0] = (this->_blockLattice.get(input[0], input[1], input[2]).computeRho() - T(1)) / descriptors::invCs2<T,DESCRIPTOR>();
  output[0] *= (this->_blockLattice.get(input[0], input[1], input[2]).computeRho() - T(1)) / descriptors::invCs2<T,DESCRIPTOR>();
  return true;
}

}
#endif
