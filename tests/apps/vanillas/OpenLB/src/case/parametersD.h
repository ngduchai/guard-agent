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
#ifndef CASE_PARAMETERSD_H
#define CASE_PARAMETERSD_H

#include "io/cliReader.h"
#include "parameters.h"

#include <functional>
#include <stdexcept>

namespace olb {

/// On-demand allocating parameter field storage
/**
 * To be used in non-critical sections for convenient storage of parameter values
 **/
template <concepts::BaseType T, concepts::Descriptor DESCRIPTOR>
class ParametersD final {
private:
  struct TypeErasedFieldD {
    void* field = nullptr;

    std::string name;

    std::function<void()> deleter;
    std::function<std::string()> value;
    std::function<void(std::string)> set;
    std::function<void()> calculate;

    bool isBeingComputedRightNow = false;

    ~TypeErasedFieldD() {
      if (field && deleter) {
        deleter();
      }
    }
  };

  std::unordered_map<std::type_index, TypeErasedFieldD> _map;
  std::optional<CLIreader> _args;

  template <concepts::Field FIELD>
  void setupTypeErasedField(TypeErasedFieldD& typeErasedField) {
    typeErasedField.name = parameters::name<FIELD>();
    typeErasedField.deleter = [&typeErasedField]() {
      delete static_cast<FieldD<T,DESCRIPTOR,FIELD>*>(typeErasedField.field);
    };
    typeErasedField.value = [this]() -> std::string {
      std::stringstream out;
      out << *static_cast<FieldD<T,DESCRIPTOR,FIELD>*>(this->getFieldPtr<FIELD>());
      return out.str();
    };
    typeErasedField.set = [this](std::string str) {
      if (auto v = FieldD<T,DESCRIPTOR,FIELD>::fromString(str)) {
        this->set<FIELD>(*v);
      }
    };
  }

  void tryUpdateFromCLI(TypeErasedFieldD& typeErasedField) {
    if (_args) {
      const std::string key = "--" + typeErasedField.name;
      if (_args->contains(key)) {
        typeErasedField.set(_args->getValueOrFallback<std::string>(key, "[]"));
      }
    }
  }

  // Helper to get the typed field pointer, executing calculate if needed
  template <concepts::Field FIELD>
  void* getFieldPtr() {
    TypeErasedFieldD& typeErasedField = _map[typeid(FIELD)];
    // If not initialized at all, use default value
    if (!typeErasedField.field && !typeErasedField.calculate) {
      set<FIELD>(FIELD::template getInitialValue<T,DESCRIPTOR>());
      tryUpdateFromCLI(typeErasedField); // Allow CLI override of default
    }
    else if (typeErasedField.calculate) {
      if (typeErasedField.isBeingComputedRightNow) {
        throw std::runtime_error("Cyclic dependency detected in parameter: " + typeErasedField.name);
      }
      typeErasedField.isBeingComputedRightNow = true;
      typeErasedField.calculate();
      typeErasedField.isBeingComputedRightNow = false;

      // Check for CLI override after calculation to ensure CLI can always override
      tryUpdateFromCLI(typeErasedField);
    }
    return typeErasedField.field;
  }

public:
  using value_t = T;
  using descriptor_t = DESCRIPTOR;

  ParametersD() = default;

  // Set parameter with a concrete value
  template <concepts::Field FIELD>
  void set(FieldD<T,DESCRIPTOR,FIELD> value) {
    if (!FIELD::template isValid<T,DESCRIPTOR,FIELD>(value)) {
      std::stringstream msg;
      msg << "Value " << value << " for " << fields::name<FIELD>() << " is invalid" << std::endl;
      throw std::invalid_argument(msg.str());
    }

    TypeErasedFieldD& typeErasedField = _map[typeid(FIELD)];

    // If this set call is not triggered by recomputation it is a manual override
    if (!typeErasedField.isBeingComputedRightNow) {
      typeErasedField.calculate = nullptr;
    }

    if (typeErasedField.field && typeErasedField.deleter) {
      typeErasedField.deleter();
    }

    typeErasedField.field = new FieldD<T,DESCRIPTOR,FIELD>{value};
    setupTypeErasedField<FIELD>(typeErasedField);
  }

  template <concepts::Field FIELD>
  requires (   DESCRIPTOR::template size<FIELD>() == 1
            && std::is_same_v<typename FIELD::template value_type<T>,std::string>)
  void set(const char* text) {
    set<FIELD>(std::string(text));
  }

  // Set dependent parameter with a lambda for lazy evaluation
  template <concepts::Field FIELD>
  void set(concepts::CallableReturning<FieldD<T,DESCRIPTOR,FIELD>> auto&& f) {
    TypeErasedFieldD& typeErasedField = _map[typeid(FIELD)];
    if (typeErasedField.field && typeErasedField.deleter) {
      typeErasedField.deleter();
      typeErasedField.field = nullptr;
    }
    typeErasedField.calculate = [this,f]() {
      this->set<FIELD>(f());
    };
    setupTypeErasedField<FIELD>(typeErasedField);
  }

  template <concepts::Field FIELD>
  auto get() {
    void* ptr = getFieldPtr<FIELD>();
    if constexpr (DESCRIPTOR::template size<FIELD>() == 1) {
      return (*static_cast<FieldD<T,DESCRIPTOR,FIELD>*>(ptr))[0];
    } else {
      return *static_cast<FieldD<T,DESCRIPTOR,FIELD>*>(ptr);
    }
  }

  void print(OstreamManager clout = {std::cout, "ParametersD"}) {
    std::size_t nCharName = 0;
    for (auto& [_, typeErasedField] : _map) {
      nCharName = std::max(nCharName, typeErasedField.name.length());
    }
    for (auto& [_, typeErasedField] : _map) {
      clout << typeErasedField.name << std::string(nCharName - typeErasedField.name.length() + 1, ' ')
            << "= " << typeErasedField.value()
            << std::endl;
    }
  }

  void fromCLI(int& argc, char** argv) {
    if (!_args) {
      _args = CLIreader(argc, argv);
    }
    // Can only update fields already present in the map, fields relying on
    // lazily-instantiated defaults are handled in getFieldPtr.
    for (auto& [_, typeErasedField] : _map) {
      tryUpdateFromCLI(typeErasedField);
    }
    if (_args->contains("--help")) {
      OstreamManager clout(std::cout, "help");
      clout << std::endl;
      clout << "-- Parameters --" << std::endl;
      print(clout);
      clout << std::endl;
      clout << "You can change any of these parameters via `./app --NAME VALUE`." << std::endl;
      clout << "The defined values are printed at the start of the simulation." << std::endl;
      clout << std::endl;
      std::exit(0); // Terminate on help printout
    }
  }
};

}

#endif
