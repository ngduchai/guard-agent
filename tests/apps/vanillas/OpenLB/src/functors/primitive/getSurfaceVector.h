/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Fedor Bukreev, Michael Grinschewski
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

/*
 * This file contains functions to find the vector to an Indicator from a point
 * There are multiple parameter choices, either supplying the geometry via an indicator or via the BlockIndicator
 * This currently only works for 2D, 3D developement will follow
*/

#ifndef GETSURFACEVECTOR
#define GETSURFACEVECTOR

#include "core/util.h"
namespace olb {

/// Get Wall distance with or without indicator
template<typename T, typename DESCRIPTOR>
Vector<T,DESCRIPTOR::d> getSurfaceVector(BlockIndicatorF<T,DESCRIPTOR::d>& boundaryIndicator,
                                        LatticeR<DESCRIPTOR::d> boundaryLatticeR) any_platform
{
  // check if cell is fluid cell
  if (!boundaryIndicator(boundaryLatticeR)) {
    Vector<T,DESCRIPTOR::d> currentGuess;
    int numInsideVectors = 0;

    for(int dir = 1; dir < DESCRIPTOR::q; dir++){
      Vector<T,DESCRIPTOR::d> boundaryLatticeR2(boundaryLatticeR + descriptors::c<DESCRIPTOR>(dir));
      if (boundaryIndicator(boundaryLatticeR)) {
        numInsideVectors += 1;
        currentGuess += boundaryLatticeR2 - boundaryLatticeR;
      }
    }
    if(numInsideVectors != 0) currentGuess *= 1./numInsideVectors;

    return currentGuess;
  }
return 0;
}

template<typename T, typename DESCRIPTOR>
Vector<T,DESCRIPTOR::d> getSurfaceVector(T physDeltaX,
                     IndicatorF<T,DESCRIPTOR::d>* indicatorAnalyticalBoundary,
                     Vector<T,DESCRIPTOR::d> inputVector,
                     int nSamplingPoints = 128,
                     int nBisection = 20) any_platform
{
  // check if cell is fluid cell
  bool inside[1];
  T coord[2] = {inputVector[0],inputVector[1]};
  indicatorAnalyticalBoundary->operator()(inside,coord);

  if(!inside[0]){
    Vector<T,DESCRIPTOR::d> currentGuess;
    Vector<T,DESCRIPTOR::d> checkVector{ };

    for(int k = 0; k < nSamplingPoints; k++){
      // get vector from circle or sphere, length 1
      Vector<T,DESCRIPTOR::d> dir{};

      if constexpr (DESCRIPTOR::d == 2) {
          // 2D unit circle
          T angle = (2*static_cast<T>(M_PI) * k) / nSamplingPoints;
          dir[0] = util::cos(angle)*util::sqrt(2);
          dir[1] = util::sin(angle)*util::sqrt(2);
      }
      else {
          // 3D: sample unit sphere using "spherical Fibonacci" or simpler
          // Here: stratified sampling with spherical coords
          T z = 2.0 * (k + 0.5) / nSamplingPoints - 1.0;    // uniform in [-1,1]
          T phi = (k * 2.39996322972865332);      // golden angle
          T r = std::sqrt(std::max(T(0), 1.0 - z*z));
          dir[0] = r * std::cos(phi);
          dir[1] = r * std::sin(phi);
          dir[2] = z;
      }

      // add vector to coordinate
      checkVector = inputVector + physDeltaX*dir;
      bool output[1];
      T coord[2] = {checkVector[0],checkVector[1]};
      indicatorAnalyticalBoundary->operator()(output,coord);

      // if cell is boundary, bisect intervall to get correct distance
      if (output[0]){
        // bisection algorithm
        for(int n = 1; n < nBisection; n++){
          coord[0] = checkVector[0];
          coord[1] = checkVector[1];
          indicatorAnalyticalBoundary->operator()(output,coord);
          if (output[0]){
            checkVector = checkVector - (physDeltaX/util::pow(2,n))*dir;
          }
          else{
            checkVector = checkVector + (physDeltaX/util::pow(2,n))*dir;
          }
        }
        if(util::norm<DESCRIPTOR::d>(currentGuess) == 0 ||
           util::norm<DESCRIPTOR::d>(checkVector - inputVector) < util::norm<DESCRIPTOR::d>(currentGuess)){
          currentGuess = checkVector - inputVector;
        }
      }
    }
    return currentGuess;
  }
return 0;
}
} // namespace
#endif
