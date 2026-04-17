/*  Lattice Boltzmann sample, written in C++, using the OpenLB
 *  library
 *
 *  Copyright (C) 2018 Markus Mohrhard
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

#include <iostream>

using T = double;

enum class FlowType {
  forced,
  nonForced
};

enum class BoundaryType {
  bounceBack,
  local,
  interpolated,
  bouzidi
};

struct TestParam {
  FlowType flowType;
  BoundaryType boundaryType;
  int N;
  int iT;
  T velocityErrorL2;
  T pressureErrorL2;
  T strainErrorL2;
  double errorFactor;
};

std::ostream& operator<<(std::ostream& strm, BoundaryType boundaryType)
{
  switch (boundaryType) {
  case BoundaryType::bounceBack:
    strm << "bounceBack";
    break;
  case BoundaryType::local:
    strm << "local";
    break;
  case BoundaryType::interpolated:
    strm << "interpolated";
    break;
  case BoundaryType::bouzidi:
    strm << "bouzidi";
    break;
  }
  return strm;
}

std::ostream& operator<<(std::ostream& strm, FlowType flowType)
{
  switch (flowType) {
  case FlowType::forced:
    strm << "forced";
    break;
  case FlowType::nonForced:
    strm << "nonForced";
    break;
  }
  return strm;
}

std::ostream& operator<<(std::ostream& strm, const TestParam& param)
{
  strm << "N=" << param.N << ", " << param.flowType << ", " << param.boundaryType;
  return strm;
};
