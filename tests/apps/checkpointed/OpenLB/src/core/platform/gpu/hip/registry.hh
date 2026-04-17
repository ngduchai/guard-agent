/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2022, 2025 Adrian Kummerlaender, Leonardo Dorneles
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

#ifndef GPU_HIP_REGISTRY_HH
#define GPU_HIP_REGISTRY_HH

#include "registry.h"

namespace olb {

namespace gpu {

namespace hip {

/// Mapping of TYPE in CONTEXT to runtime-fixed index
/**
 * Used for dynamic access to field arrays
 **/
template <typename CONTEXT, typename TYPE>
__constant__ std::size_t field_type_index;

/// Host-side version of gpu::cuda::AnyDeviceFieldArrayD
struct FieldArrayPointer {
  gpu::hip::device::unique_ptr<void*> data;
  const unsigned column_count;
  const unsigned element_size;
};

}

}

template <typename T, typename DESCRIPTOR>
struct FieldTypeRegistry<T,DESCRIPTOR,Platform::GPU_HIP>::Data {
  Data():
    indexOnHost(2, nullptr)
  { }

  std::map<std::type_index,gpu::hip::FieldArrayPointer> fieldArrayPointers;

  std::vector<void**>                   indexOnHost;
  gpu::hip::device::unique_ptr<void**> indexOnDevice;

};

template <typename T, typename DESCRIPTOR>
FieldTypeRegistry<T,DESCRIPTOR,Platform::GPU_HIP>::FieldTypeRegistry():
  _data(new Data()),
  _modified{true} { }

template <typename T, typename DESCRIPTOR>
FieldTypeRegistry<T,DESCRIPTOR,Platform::GPU_HIP>::~FieldTypeRegistry()
{ }

template <typename T, typename DESCRIPTOR>
template <typename FIELD_TYPE>
void FieldTypeRegistry<T,DESCRIPTOR,Platform::GPU_HIP>::track(
  AnyFieldTypeD<T,DESCRIPTOR,Platform::GPU_HIP>* fieldType)
{
  _index.template set<FIELD_TYPE>(fieldType);

  // Copy host-side field index to device-side field index
  std::size_t index = _index.template index<FIELD_TYPE>();

  HIP_ASSERT(
    hipMemcpyToSymbol(
#if defined(__HIP_PLATFORM_NVIDIA__)
        &gpu::hip::field_type_index<FieldTypeRegistry,FIELD_TYPE>,
#else
        gpu::hip::field_type_index<FieldTypeRegistry, FIELD_TYPE>,
#endif
        &index,
        sizeof(std::size_t))
  );

  if (index >= _data->indexOnHost.size()) {
    _data->indexOnHost.resize(2*index);
  }

  // Update device-side pointers to Array<FIELD> field types
  using ConcreteFieldType = typename FIELD_TYPE::template type<T,DESCRIPTOR,Platform::GPU_HIP>;
  if constexpr (std::is_base_of_v<ColumnVectorBase, ConcreteFieldType>) {
    using field_t = typename ConcreteFieldType::field_t;
    auto& fieldArray = *fieldType->template as<FIELD_TYPE>();

    std::array<void*,DESCRIPTOR::template size<field_t>()> componentPointers;
    for (unsigned iD=0; iD < componentPointers.size(); ++iD) {
      componentPointers[iD] = fieldArray[iD].deviceData();
    }

    auto componentPointersOnDevice = gpu::hip::device::malloc<void*>(DESCRIPTOR::template size<field_t>());
    gpu::hip::device::copyToDevice(componentPointers.data(),
                                    componentPointersOnDevice,
                                    componentPointers.size()*sizeof(void*));

    _data->indexOnHost[index] = componentPointersOnDevice;
    _data->fieldArrayPointers.emplace(typeid(field_t), gpu::hip::FieldArrayPointer{
      gpu::hip::device::unique_ptr<void*>(componentPointersOnDevice),
      componentPointers.size(),
      sizeof(typename field_t::template value_type<T>)
    });
  }

  _modified = true;
}

template<typename T, typename DESCRIPTOR>
void*** FieldTypeRegistry<T,DESCRIPTOR,Platform::GPU_HIP>::deviceData()
{
  if (_modified) {
    _data->indexOnDevice = gpu::hip::device::malloc<void**>(_data->indexOnHost.size());
    gpu::hip::device::copyToDevice(_data->indexOnHost.data(),
                                    _data->indexOnDevice.get(),
                                    _data->indexOnHost.size()*sizeof(void**));
    _modified = false;
  }
  return _data->indexOnDevice.get();
}

template <typename T, typename DESCRIPTOR>
template <typename FIELD>
void FieldTypeRegistry<T,DESCRIPTOR,Platform::GPU_HIP>::refreshDeviceFieldArray(
  FieldArrayD<T,DESCRIPTOR,Platform::GPU_HIP,FIELD>& fieldArray)
{
  std::array<void*,DESCRIPTOR::template size<FIELD>()> componentPointers;
  for (unsigned iD=0; iD < componentPointers.size(); ++iD) {
    componentPointers[iD] = fieldArray[iD].deviceData();
  }
  auto& ptr = _data->fieldArrayPointers.at(typeid(FIELD));
  gpu::hip::device::copyToDevice(componentPointers.data(),
                                  ptr.data.get(),
                                  componentPointers.size()*sizeof(void*));
}

template <typename T, typename DESCRIPTOR>
gpu::hip::AnyDeviceFieldArrayD
FieldTypeRegistry<T,DESCRIPTOR,Platform::GPU_HIP>::deviceFieldArray(
  std::type_index field)
{
  auto& ptr = _data->fieldArrayPointers.at(field);
  return gpu::hip::AnyDeviceFieldArrayD{
    ptr.data.get(),
    ptr.column_count,
    ptr.element_size
  };
}

template <typename T, typename DESCRIPTOR>
std::vector<gpu::hip::AnyDeviceFieldArrayD>
FieldTypeRegistry<T,DESCRIPTOR,Platform::GPU_HIP>::deviceFieldArrays(
  const std::vector<std::type_index>& fields)
{
  std::vector<gpu::hip::AnyDeviceFieldArrayD> deviceFields;
  deviceFields.reserve(fields.size());
  for (std::type_index field : fields) {
    deviceFields.emplace_back(deviceFieldArray(field));
  }
  return deviceFields;
}

}

#endif
