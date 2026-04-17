/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Yuji (Sam) Shimojima, Adrian Kummerlaender, Shota Ito
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

#ifndef SUPER_LATTICE_FIELD_REDUCTION_O_H
#define SUPER_LATTICE_FIELD_REDUCTION_O_H

#include "core/superD.h"
#include "optimization/primitives/singleLatticeO.h"
#include "optimization/primitives/functors/objectiveF.h"
#include "blockLatticeFieldReductionO.h"

namespace olb {

namespace stage::reduction {

struct ReductionField {};

} // namespace stage::reduction

template <typename T, typename DESCRIPTOR, typename FIELD, typename REDUCTION_OP,
          typename CONDITION = reduction::ConditionTrue<>>
class SuperLatticeFieldReductionO final {
public:
  template <unsigned D>
  struct REDUCED_FIELD : public descriptors::SPATIAL_DESCRIPTOR<D, FIELD> {};

private:
  using _CONDITION = CONDITION;
  using _OPERATOR  = BlockLatticeFieldReductionO<FIELD, REDUCTION_OP, _CONDITION>;
  SuperLattice<T, DESCRIPTOR>& _sLattice;
  std::unique_ptr<SuperLatticeCoupling<SingleLatticeO<_OPERATOR>,
                                       meta::map<names::Lattice1, descriptors::VALUED_DESCRIPTOR<T, DESCRIPTOR>>>>
                                                           _operator;
  std::unique_ptr<SuperD<T, REDUCED_FIELD<DESCRIPTOR::d>>> _superReducedFieldD;
  static constexpr unsigned                                _fieldDimension = FieldD<T, DESCRIPTOR, FIELD>::d;
  FieldD<T, DESCRIPTOR, FIELD>                             _reductedField {};

  bool _rankDoesReduction;

  void _gatherField(const FieldD<T, DESCRIPTOR, FIELD>& f)
  {
    for (unsigned iD = 0; iD < f.d; iD++) {
      _reductedField[iD] = REDUCTION_OP {}(_reductedField[iD], f[iD]);
    }
  }

#ifdef PARALLEL_MODE_MPI
  void _mpiGatherField(MPI_Op op)
  {
    std::vector<T> localFields(_fieldDimension, T {});
    for (std::size_t iD = 0; iD < _fieldDimension; ++iD) {
      localFields[iD] = _reductedField[iD];
    }

    std::vector<T> globalFields(_fieldDimension, T {});
    if constexpr (!util::is_adf_v<T>) {
      singleton::mpi().allreduce(localFields.data(), globalFields.data(), globalFields.size(), op, MPI_COMM_WORLD);
    }
    else {
      singleton::mpi().allreduce<typename T::base_t, T::dim>(localFields.data(), globalFields.data(),
                                                             globalFields.size(), op, MPI_COMM_WORLD);
    }

    for (std::size_t iD = 0; iD < _fieldDimension; ++iD) {
      _reductedField[iD] = globalFields[iD];
    }
  }

#endif // PARALLEL_MODE_MPI

public:
  ~SuperLatticeFieldReductionO() {};
  SuperLatticeFieldReductionO(SuperLattice<T, DESCRIPTOR>&                    sLattice,
                              FunctorPtr<SuperIndicatorF<T, DESCRIPTOR::d>>&& SuperIndicator)
      : _sLattice(sLattice)
      , _operator(makeSingleLatticeO<_OPERATOR, T, DESCRIPTOR>(sLattice))
      , _superReducedFieldD(new SuperD<T, REDUCED_FIELD<DESCRIPTOR::d>>(sLattice.getLoadBalancer()))
      , _rankDoesReduction {singleton::mpi().isMainProcessor()}

  {
    OstreamManager clout(std::cout, "SuperLatticeFieldReductionO");
    auto&          load = _sLattice.getLoadBalancer();
    {
      for (int iC = 0; iC < load.size(); ++iC) {
        auto& block     = _sLattice.getBlock(iC);
        auto& indicator = SuperIndicator->getBlockIndicatorF(iC);
        block.forCoreSpatialLocations([&](LatticeR<DESCRIPTOR::d> loc) {
          block.get(loc).template setField<field::reduction::TAG_CORE>(
              true); //this tag exracts core region. The main purpose is for GPU.
          block.get(loc).template setField<typename _CONDITION::tag_field_t>(
              indicator(loc)); //this tag exracted by analytical condition
        });
        block.template getData<Array<field::reduction::TAG_CORE>>().setProcessingContext(ProcessingContext::Simulation);
        block.template getData<Array<typename _CONDITION::tag_field_t>>().setProcessingContext(
            ProcessingContext::Simulation);
      }
    }

    //clout << "Set up operators and communication" << std::endl;

    {
      auto& c = _sLattice.getCommunicator(stage::reduction::ReductionField {});

      c.template requestField<FIELD>();
      c.requestOverlap(1);
      c.exchangeRequests();
    }

    //clout << "Set operator parameters" << std::endl;
    for (int iC = 0; iC < load.size(); ++iC) {
      auto& elementsBlock = _superReducedFieldD->getBlock(iC);
      elementsBlock.resize(1);

      auto&    abstractFieldArray = elementsBlock.template getField<FIELD>();
      Platform platform           = abstractFieldArray.getPlatform();
      callUsingConcretePlatform(platform, [&](auto platform) {
        using abstractFieldArray_t = std::remove_reference_t<decltype(abstractFieldArray)>;
        auto& fieldArray = dynamic_cast<FieldArrayD<T, typename abstractFieldArray_t::descriptor_t, platform.value,
                                                    typename abstractFieldArray_t::field_t>&>(abstractFieldArray);
        FieldD<T, DESCRIPTOR, fields::array_of<FIELD>> fieldArrayPointers;
        for (unsigned iD = 0; iD < fieldArray.d; ++iD) {
          if constexpr (platform.value == Platform::GPU_CUDA) {
            fieldArrayPointers[iD] = fieldArray[iD].deviceData();
          }
          else {
            fieldArrayPointers[iD] = fieldArray[iD].data();
          }
        }
        _operator->getBlock(iC).getParameters().template set<fields::array_of<FIELD>>(std::move(fieldArrayPointers));
      });
    }

    _sLattice.getCommunicator(stage::reduction::ReductionField {}).communicate();
    _superReducedFieldD->setProcessingContext(ProcessingContext::Simulation);
  } //end constructor

  SuperLatticeFieldReductionO(SuperLattice<T, DESCRIPTOR>& sLattice, SuperGeometry<T, DESCRIPTOR::d>& sGeometry,
                              IndicatorF<T, DESCRIPTOR::d>& indicator)
      : _sLattice(sLattice)
      , _operator(makeSingleLatticeO<_OPERATOR, T, DESCRIPTOR>(sLattice))
      , _superReducedFieldD(new SuperD<T, REDUCED_FIELD<DESCRIPTOR::d>>(sLattice.getLoadBalancer()))
      , _rankDoesReduction {singleton::mpi().isMainProcessor()}

  {
    OstreamManager clout(std::cout, "SuperLatticeFieldReductionO");
    auto&          load = _sLattice.getLoadBalancer();

    {
      for (int iC = 0; iC < load.size(); ++iC) {
        auto& block = _sLattice.getBlock(iC);
        block.forCoreSpatialLocations([&](LatticeR<DESCRIPTOR::d> loc) {
          block.get(loc).template setField<field::reduction::TAG_CORE>(
              true); //this tag exracts core region. The main purpose is for GPU.
          auto&                    blockGeometry        = sGeometry.getBlockGeometry(iC);
          bool                     indicator_boolean[1] = {false};
          Vector<T, DESCRIPTOR::d> PhysR {};
          blockGeometry.getPhysR(PhysR, loc);
          indicator(indicator_boolean, PhysR.data()); //this tag exracted by analytical condition
          block.get(loc).template setField<typename _CONDITION::tag_field_t>(indicator_boolean[0]);
        });
        block.template getData<Array<field::reduction::TAG_CORE>>().setProcessingContext(ProcessingContext::Simulation);
        block.template getData<Array<typename _CONDITION::tag_field_t>>().setProcessingContext(
            ProcessingContext::Simulation);
      }
    }

    //clout << "Set up operators and communication" << std::endl;

    {
      auto& c = _sLattice.getCommunicator(stage::reduction::ReductionField {});

      c.template requestField<FIELD>();
      c.requestOverlap(1);
      c.exchangeRequests();
    }

    //clout << "Set operator parameters" << std::endl;
    for (int iC = 0; iC < load.size(); ++iC) {
      auto& elementsBlock = _superReducedFieldD->getBlock(iC);
      elementsBlock.resize(1);

      auto&    abstractFieldArray = elementsBlock.template getField<FIELD>();
      Platform platform           = abstractFieldArray.getPlatform();
      callUsingConcretePlatform(platform, [&](auto platform) {
        using abstractFieldArray_t = std::remove_reference_t<decltype(abstractFieldArray)>;
        auto& fieldArray = dynamic_cast<FieldArrayD<T, typename abstractFieldArray_t::descriptor_t, platform.value,
                                                    typename abstractFieldArray_t::field_t>&>(abstractFieldArray);
        FieldD<T, DESCRIPTOR, fields::array_of<FIELD>> fieldArrayPointers;
        for (unsigned iD = 0; iD < fieldArray.d; ++iD) {
          if constexpr (platform.value == Platform::GPU_CUDA) {
            fieldArrayPointers[iD] = fieldArray[iD].deviceData();
          }
          else {
            fieldArrayPointers[iD] = fieldArray[iD].data();
          }
        }
        _operator->getBlock(iC).getParameters().template set<fields::array_of<FIELD>>(std::move(fieldArrayPointers));
      });
    }

    _sLattice.getCommunicator(stage::reduction::ReductionField {}).communicate();
    _superReducedFieldD->setProcessingContext(ProcessingContext::Simulation);
  } //end constructor

  SuperLatticeFieldReductionO(SuperLattice<T, DESCRIPTOR>& sLattice)
      : _sLattice(sLattice)
      , _operator(makeSingleLatticeO<_OPERATOR, T, DESCRIPTOR>(sLattice))
      , _superReducedFieldD(new SuperD<T, REDUCED_FIELD<DESCRIPTOR::d>>(sLattice.getLoadBalancer()))
      , _rankDoesReduction {singleton::mpi().isMainProcessor()}

  {
    OstreamManager clout(std::cout, "SuperLatticeFieldReductionO");
    auto&          load = _sLattice.getLoadBalancer();

    {
      for (int iC = 0; iC < load.size(); ++iC) {
        auto& block = _sLattice.getBlock(iC);
        block.forCoreSpatialLocations([&](LatticeR<DESCRIPTOR::d> loc) {
          block.get(loc).template setField<field::reduction::TAG_CORE>(
              true); //this tag exracts core region. The main purpose is for GPU.
        });
        block.template getData<Array<field::reduction::TAG_CORE>>().setProcessingContext(ProcessingContext::Simulation);
      }
    }

    //clout << "Set up operators and communication" << std::endl;

    {
      auto& c = _sLattice.getCommunicator(stage::reduction::ReductionField {});

      c.template requestField<FIELD>();
      c.requestOverlap(1);
      c.exchangeRequests();
    }

    //clout << "Set operator parameters" << std::endl;
    for (int iC = 0; iC < load.size(); ++iC) {
      auto& elementsBlock = _superReducedFieldD->getBlock(iC);
      elementsBlock.resize(1);

      auto&    abstractFieldArray = elementsBlock.template getField<FIELD>();
      Platform platform           = abstractFieldArray.getPlatform();
      callUsingConcretePlatform(platform, [&](auto platform) {
        using abstractFieldArray_t = std::remove_reference_t<decltype(abstractFieldArray)>;
        auto& fieldArray = dynamic_cast<FieldArrayD<T, typename abstractFieldArray_t::descriptor_t, platform.value,
                                                    typename abstractFieldArray_t::field_t>&>(abstractFieldArray);
        FieldD<T, DESCRIPTOR, fields::array_of<FIELD>> fieldArrayPointers;
        for (unsigned iD = 0; iD < fieldArray.d; ++iD) {
          if constexpr (platform.value == Platform::GPU_CUDA) {
            fieldArrayPointers[iD] = fieldArray[iD].deviceData();
          }
          else {
            fieldArrayPointers[iD] = fieldArray[iD].data();
          }
        }
        _operator->getBlock(iC).getParameters().template set<fields::array_of<FIELD>>(std::move(fieldArrayPointers));
      });
    }

    _sLattice.getCommunicator(stage::reduction::ReductionField {}).communicate();
    _superReducedFieldD->setProcessingContext(ProcessingContext::Simulation);
  } //end constructor

  bool rankDoesReduction() const { return _rankDoesReduction; }

  FieldD<T, DESCRIPTOR, FIELD> compute()
  {
    OstreamManager clout(std::cout, "SuperLatticeFieldReductionO");
    _operator->apply();
    for (unsigned iD = 0; iD < _fieldDimension; iD++) {
      _reductedField[iD] = REDUCTION_OP {}.reset(_reductedField[iD]);
    }

    for (int iC = 0; iC < _sLattice.getLoadBalancer().size(); ++iC) {
      auto& block      = _superReducedFieldD->getBlock(iC);
      auto& blockField = block.template getField<FIELD>();
      block.setProcessingContext(ProcessingContext::Evaluation);

      FieldD<T, DESCRIPTOR, FIELD> f([&](std::size_t iD) {
        return blockField[iD][0];
      });
      _gatherField(f);
    }

#ifdef PARALLEL_MODE_MPI
    _mpiGatherField(REDUCTION_OP {}.forMPI());
#endif
    return _reductedField;
  }
};

// Utility function for integrating fields
template <typename FIELD, typename T, typename DESCRIPTOR, int TAGS_INDICATOR_ID = 0>
auto integrateField(SuperLattice<T, DESCRIPTOR>& lattice, auto&& domain, T weight = 1.0)
{

  using Condition = reduction::checkTagIndicator<TAGS_INDICATOR_ID>;

  SuperLatticeFieldReductionO<T, DESCRIPTOR, FIELD, reduction::SumO, Condition> reductionO(lattice,
                                                                                           std::forward<decltype(domain)>(domain));

  return reductionO.compute() * util::pow(weight, DESCRIPTOR::d);
}

// Utility function for computing the L2 norm using a functor
template <typename FIELD, typename T, typename DESCRIPTOR, int TAGS_INDICATOR_ID = 0>
auto computeL2Norm(SuperLattice<T, DESCRIPTOR>& lattice, auto& domain, T dx)
{
  auto L2F = makeWriteFunctorO<functors::L2F<FIELD>, descriptors::L2_NORM>(lattice);
  L2F->restrictTo(domain);
  L2F->template setParameter<parameters::DX>(dx);
  L2F->apply();
  using Condition = reduction::checkTagIndicator<TAGS_INDICATOR_ID>;
  SuperLatticeFieldReductionO<T, DESCRIPTOR, descriptors::L2_NORM, reduction::SumO, Condition> reductionO(lattice,
                                                                                                          domain);
  return reductionO.compute();
}

} // namespace olb

#endif
