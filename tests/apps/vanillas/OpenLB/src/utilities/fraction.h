/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2019 Adrian Kummerlaender
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

#ifndef UTILITIES_FRACTION_H
#define UTILITIES_FRACTION_H

#include <stdexcept>
// #include <cassert>

#if defined(__HIP_DEVICE_COMPILE__)
#include <hip/hip_runtime.h>
#endif

#if defined(__CUDA_ARCH__) || defined(__HIP_DEVICE_COMPILE__)
#include <cassert>
#endif

namespace olb {

namespace utilities {

/// Floating-point independent fraction type
class Fraction {
private:
  const int _numerator;
  const int _denominator;

public:
  constexpr Fraction(int num, int denum):
    _numerator(num), _denominator(denum)
  {
    #if defined(__HIP_DEVICE_COMPILE__) || defined(__CUDA_ARCH__)
    // On the DEVICE
    assert(_denominator != 0);
    #else
    if (_denominator == 0) {
        throw std::invalid_argument("denominator must not be zero");
    }
    #endif
  }

  constexpr Fraction(int parts[2]):
    Fraction(parts[0], parts[1]) { }

  constexpr Fraction(int num):
    Fraction(num, 1) { }

  constexpr Fraction():
    Fraction(0) { }

  template <typename T>
  constexpr T as() const
  {
    return T(_numerator) / T(_denominator);
  }

  template <typename T>
  constexpr T inverseAs() const
  {
    #if defined(__HIP_DEVICE_COMPILE__) || defined(__CUDA_ARCH__)
    // On the DEVICE
      assert(_numerator != 0);
      return T(_denominator) / T(_numerator);
    #else
      return _numerator != 0 ? T(_denominator) / T(_numerator) : throw std::invalid_argument("inverse of zero is undefined");
    #endif
  }
};

}

}

#endif
