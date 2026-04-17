/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Adrian Kummerlaender
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

#ifndef UTILITIES_OPTIONAL_VALUE_H
#define UTILITIES_OPTIONAL_VALUE_H

#include <optional>

namespace olb {

/// Simple wrapper of std::optional with transparent access (throwing if undefined)
template <typename T>
class OptionalValue {
private:
  std::optional<T> _value;

public:
  OptionalValue() = default;
  OptionalValue(T value): _value(value) { }

  OptionalValue(const OptionalValue&) = default;
  OptionalValue(OptionalValue&&) = default;
  OptionalValue& operator=(const OptionalValue&) = default;
  OptionalValue& operator=(OptionalValue&&) = default;

  OptionalValue& operator=(T val) {
    _value = val;
    return *this;
  }

  operator T&() {
    return _value.value();
  }

  operator const T&() const {
    return _value.value();
  }

  T& operator*() {
    return _value.value();
  }

  const T& operator*() const {
    return _value.value();
  }

  T* operator->() {
      return &_value.value();
  }

  const T* operator->() const {
    return &_value.value();
  }

  T& value() {
    return _value.value();
  }

  const T& value() const {
    return _value.value();
  }

  bool hasValue() const {
    return _value.has_value();
  }

  void reset() {
    _value.reset();
  }

};

template <typename U, typename T>
auto operator+(const U& lhs, const OptionalValue<T>& rhs) -> decltype(lhs + rhs.value()) {
  return lhs + rhs.value();
}

template <typename T, typename U>
auto operator+(const OptionalValue<T>& lhs, const U& rhs) -> decltype(lhs.value() + rhs) {
  return lhs.value() + rhs;
}

template <typename T>
auto operator+(const OptionalValue<T>& lhs, const OptionalValue<T>& rhs) -> decltype(lhs.value() + rhs.value()) {
  return lhs.value() + rhs.value();
}

template <typename U, typename T>
auto operator-(const U& lhs, const OptionalValue<T>& rhs) -> decltype(lhs - rhs.value()) {
  return lhs - rhs.value();
}

template <typename T, typename U>
auto operator-(const OptionalValue<T>& lhs, const U& rhs) -> decltype(lhs.value() - rhs) {
  return lhs.value() - rhs;
}

template <typename T>
auto operator-(const OptionalValue<T>& lhs, const OptionalValue<T>& rhs) -> decltype(lhs.value() - rhs.value()) {
  return lhs.value() - rhs.value();
}

template <typename U, typename T>
auto operator*(const U& lhs, const OptionalValue<T>& rhs) -> decltype(lhs * rhs.value()) {
  return lhs * rhs.value();
}

template <typename T, typename U>
auto operator*(const OptionalValue<T>& lhs, const U& rhs) -> decltype(lhs.value() * rhs) {
  return lhs.value() * rhs;
}

template <typename T>
auto operator*(const OptionalValue<T>& lhs, const OptionalValue<T>& rhs) -> decltype(lhs.value() * rhs.value()) {
  return lhs.value() * rhs.value();
}

template <typename U, typename T>
auto operator/(const U& lhs, const OptionalValue<T>& rhs) -> decltype(lhs / rhs.value()) {
  return lhs / rhs.value();
}

template <typename T, typename U>
auto operator/(const OptionalValue<T>& lhs, const U& rhs) -> decltype(lhs.value() / rhs) {
  return lhs.value() / rhs;
}

template <typename T>
auto operator/(const OptionalValue<T>& lhs, const OptionalValue<T>& rhs) -> decltype(lhs.value() / rhs.value()) {
  return lhs.value() / rhs.value();
}

template <typename T>
auto operator-(const OptionalValue<T>& rhs) -> decltype(-rhs.value()) {
  return -rhs.value();
}

}

#endif
