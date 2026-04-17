/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Christoph Gaul, Mathias J. Krause
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
 * Set of functions for floating point relational operators, inspired by
 * https://www.learncpp.com/cpp-tutorial/relational-operators-and-floating-point-comparisons/
 * https://floating-point-gui.de/errors/comparison/
 *
 */

// relEps, absEbs as template specialization
#ifndef FLOATING_POINT_RELATIONAL_OPERATORS_H
#define FLOATING_POINT_RELATIONAL_OPERATORS_H

#include <numeric>
#include <type_traits>

#include "core/baseType.h"
#include "utilities/omath.h"
#include "utilities/oalgorithm.h"
#include "descriptor/functions.h"
#include "core/vector.h"

namespace olb {
namespace util {

template <typename T> struct is_adf;

namespace numericLimits {
/** Wrapper functions for std::numeric_limits to provide a custom epsilon and min value.
* Only intended to be used in this file!
*/

/// Wrapper function for std::numeric_limits<T>::epsilon() to provide a custom epsilon value.
/// Only intended to be used in this file!
template <typename T>
constexpr T epsilon() any_platform
{
  if constexpr (is_adf<T>::value) {
    return T{3. * std::numeric_limits<BaseType<T>>::epsilon()};
  } else {
    return 3. * std::numeric_limits<T>::epsilon();
  }
}

/// Wrapper function for std::numeric_limits<T>::min() to provide a custom epsilon value.
/// Only intended to be used in this file!
template <typename T>
constexpr T minLimit() any_platform
{
  if constexpr (is_adf<T>::value) {
    return T{std::numeric_limits<BaseType<T>>::min() / std::numeric_limits<BaseType<T>>::epsilon()};
  } else {
    return std::numeric_limits<T>::min() / std::numeric_limits<T>::epsilon();
  }
}

/// Wrapper function for std::numeric_limits<T>::max() to provide a custom epsilon value.
/// Only intended to be used in this file!
template <typename T>
constexpr T maxLimit() any_platform
{
  if constexpr (is_adf<T>::value) {
    return T{std::numeric_limits<BaseType<T>>::max() * std::numeric_limits<BaseType<T>>::epsilon()};
  } else {
    return std::numeric_limits<T>::max() * std::numeric_limits<T>::epsilon();
  }
}

} // namespace numericLimits


/// This function compares floating point numbers for equlity using a relativ epsilon value.
/// It also handles special cases for numbers close to zero, infinities and numbers close to the limits.
/// This function was inspired by https://floating-point-gui.de/errors/comparison/
/// This function compares floating point numbers for equlity using a relativ epsilon value.
/// It also handles special cases for numbers close to zero, infinities and numbers close to the limits.
/// This function was inspired by https://floating-point-gui.de/errors/comparison/
template <typename T>
constexpr bool equal(T a, T b, T relEpsilon = util::numericLimits::epsilon<T>(),
                     T minLimit=  util::numericLimits::minLimit<T>(),
                     T maxLimit = util::numericLimits::maxLimit<T>())
{
  if (a == b) { // shortcut for exact equality and infinities
    return true;
  }
  T absA = util::fabs(a);
  T absB = util::fabs(b);

  if (a == 0 || b == 0 || (absA + absB < minLimit)) {
    // a or b is zero or both are extremely close to it
    // relative error is less meaningful here
    T diff = util::fabs(a - b);
    return diff < minLimit * relEpsilon;
  }
  else { // default case, in which relative error is used
    // if both numbers are very large, the maxLimit is used to avoid overflow
    T diff = util::fabs(a - b);
    return diff < util::min((absA + absB), maxLimit) * relEpsilon;
  }
}

// Function will be renamed when the old implementation is removed
template <typename T>
constexpr inline bool nearZeroNew(T a, T relEpsilon = util::numericLimits::epsilon<T>(),
                               T minLimit = util::numericLimits::minLimit<T>(),
                               T maxLimit = util::numericLimits::maxLimit<T>())
{
  return equal(a, T(0), relEpsilon, minLimit, maxLimit);
}

/// Checks if a is less or equal than b
template <typename T>
constexpr inline bool lessOrEqual(T a, T b, T relEpsilon = util::numericLimits::epsilon<T>(),
                                   T minLimit = util::numericLimits::minLimit<T>(),
                                   T maxLimit = util::numericLimits::maxLimit<T>())
{
  return a <= b || equal(a, b, relEpsilon, minLimit, maxLimit);
}

/// Checks if a is strictly greater than b
template <typename T>
constexpr inline bool greater(T a, T b, T relEpsilon = util::numericLimits::epsilon<T>(),
                              T minLimit = util::numericLimits::minLimit<T>(),
                              T maxLimit = util::numericLimits::maxLimit<T>())
{
  return !lessOrEqual(a, b, relEpsilon, minLimit, maxLimit);
}

/// Checks if a is greater or equal than b
template <typename T>
constexpr inline bool greaterOrEqual(T a, T b, T relEpsilon = util::numericLimits::epsilon<T>(),
                                     T minLimit = util::numericLimits::minLimit<T>(),
                                     T maxLimit = util::numericLimits::maxLimit<T>())
{
  return a >= b || equal(a, b, relEpsilon, minLimit, maxLimit);
}

/// Checks if a is strictly less than b
template <typename T>
constexpr inline bool less(T a, T b, T relEpsilon = util::numericLimits::epsilon<T>(),
                           T minLimit = util::numericLimits::minLimit<T>(),
                           T maxLimit = util::numericLimits::maxLimit<T>())
{
  return !greaterOrEqual(a, b, relEpsilon, minLimit, maxLimit);
}

/// This function checks if a value is in the open interval (a, b).
/// Values almost equal to a or b are considered outside the interval.
template <typename T>
constexpr inline bool isInside(T x, T a, T b, T relEpsilon = util::numericLimits::epsilon<T>(),
                           T minLimit = util::numericLimits::minLimit<T>(),
                           T maxLimit = util::numericLimits::maxLimit<T>())
{
  return greater(x,a) && less(x,b);
}

/// This function checks if a value is outside the open interval (a, b).
/// Values almost equal to a or b are considered inside the interval.
template <typename T>
constexpr inline bool isOutside(T x, T a, T b, T relEpsilon = util::numericLimits::epsilon<T>(),
                           T minLimit = util::numericLimits::minLimit<T>(),
                           T maxLimit = util::numericLimits::maxLimit<T>())
{
  return less(x,a) || greater(x,b);
}

/// equal function taking Vectors as arguments
template <typename T, size_t DIM>
constexpr inline bool equal(const Vector<T, DIM>& a, const Vector<T, DIM>& b,
                            T relEpsilon = util::numericLimits::epsilon<T>(),
                            T minLimit = util::numericLimits::minLimit<T>(),
                            T maxLimit = util::numericLimits::maxLimit<T>())
{
  for (int i = 0; i < DIM; ++i) {
    if (!equal(a[i], b[i], relEpsilon, minLimit, maxLimit)) {
      return false;
    }
  }
  return true;
}

template <typename T, size_t DIM>
constexpr inline bool lessOrEqual(const Vector<T, DIM>& a, const Vector<T, DIM>& b,
                                   T relEpsilon = util::numericLimits::epsilon<T>(),
                                   T minLimit = util::numericLimits::minLimit<T>(),
                                   T maxLimit = util::numericLimits::maxLimit<T>())
{
  for (int i = 0; i < DIM; ++i) {
    if (!lessOrEqual(a[i], b[i], relEpsilon, minLimit, maxLimit)) {
      return false;
    }
  }
  return true;
}

template <typename T, size_t DIM>
constexpr bool greater(const Vector<T, DIM>& a, const Vector<T, DIM>& b,
                              T relEpsilon = util::numericLimits::epsilon<T>(),
                              T minLimit = util::numericLimits::minLimit<T>(),
                              T maxLimit = util::numericLimits::maxLimit<T>())
{
  return !lessOrEqual(a, b, relEpsilon, minLimit, maxLimit);
}

template <typename T, size_t DIM>
constexpr bool greaterOrEqual(const Vector<T, DIM>& a, const Vector<T, DIM>& b,
                                     T relEpsilon = util::numericLimits::epsilon<T>(),
                                     T minLimit = util::numericLimits::minLimit<T>(),
                                     T maxLimit = util::numericLimits::maxLimit<T>())
{
  for (int i = 0; i < DIM; ++i) {
    if (!greaterOrEqual(a[i], b[i], relEpsilon, minLimit, maxLimit)) {
      return false;
    }
  }
  return true;
}

template <typename T, size_t DIM>
constexpr bool less(const Vector<T, DIM>& a, const Vector<T, DIM>& b,
                           T relEpsilon = util::numericLimits::epsilon<T>(),
                           T minLimit = util::numericLimits::minLimit<T>(),
                           T maxLimit = util::numericLimits::maxLimit<T>())
{
  return !greaterOrEqual(a, b, relEpsilon, minLimit, maxLimit);
}

template <typename T, size_t DIM>
constexpr bool isInside(const Vector<T, DIM>& x, const Vector<T, DIM>& a, const Vector<T, DIM>& b,
                               T relEpsilon = util::numericLimits::epsilon<T>(),
                               T minLimit = util::numericLimits::minLimit<T>(),
                               T maxLimit = util::numericLimits::maxLimit<T>())
{
  for (int i = 0; i < DIM; ++i) {
    if (!isInside(x[i], a[i], b[i], relEpsilon, minLimit, maxLimit)) {
      return false;
    }
  }
  return true;
}

template <typename T, size_t DIM>
constexpr bool isOutside(const Vector<T, DIM>& x, const Vector<T, DIM>& a, const Vector<T, DIM>& b,
                                T relEpsilon = util::numericLimits::epsilon<T>(),
                                T minLimit = util::numericLimits::minLimit<T>(),
                                T maxLimit = util::numericLimits::maxLimit<T>())
{
  for (int i = 0; i < DIM; ++i) {
    if (!isOutside(x[i], a[i], b[i], relEpsilon, minLimit, maxLimit)) {
      return false;
    }
  }
  return true;
}





template <typename T>
constexpr inline bool nearZero(T a) any_platform
{
  if (a == T()) {
    return true;
  }
  T epsilon = std::numeric_limits<T>::epsilon();
  return a > -epsilon && a < epsilon;
}

// returns relative epsilon for a given value, used in indicator functions
template <typename T>
constexpr inline T epsRelative(T a) any_platform
{
  if (nearZero(a)) { //Needed if a is exactly zero.
    return util::numericLimits::minLimit<T>();
  }
  return util::numericLimits::epsilon<T>() * util::fabs(a);
}

template <typename T>
constexpr inline bool nearZero(T a, T epsilon) any_platform
{
  return a > -epsilon && a < epsilon;
}

template <typename T, typename U = T, typename W = T>
constexpr inline bool approxEqual(T a, U b, W epsilon) any_platform
{

  if (a == b) {
    return true;
  }
  return nearZero<T>(a - b, epsilon);
}

template <typename T, typename U = T>
constexpr inline bool approxEqual(T a, U b) any_platform
{
  if (a == b) {
    return true;
  }
  if (nearZero(a) && nearZero(b)) {
    return true;
  }
  T epsilon = std::numeric_limits<T>::epsilon();
  return approxEqual(a, b, epsilon);
}

constexpr inline bool contained(int x, int y, int x0, int x1, int y0, int y1) { return x >= x0 && x <= x1 && y >= y0 && y <= y1; }

constexpr inline bool contained(int x, int y, int z, int x0, int x1, int y0, int y1, int z0, int z1)
{
  return x >= x0 && x <= x1 && y >= y0 && y <= y1 && z >= z0 && z <= z1;
}

} //namespace util

} //namespace olb

#endif
