/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Yuji (Sam) Shimojima
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

#ifndef BLOCK_LATTICE_FIELD_REDUCTION_O_H
#define BLOCK_LATTICE_FIELD_REDUCTION_O_H

namespace olb {

namespace field::reduction {

//this filed is tag for extracting the 'core' grid area(no padding area)  for the reduction, especially in GPU.
struct TAG_CORE : public descriptors::TYPED_FIELD_BASE<bool, 1> {};
struct TAG_TRUE : public descriptors::TYPED_FIELD_BASE<bool, 1> {};

template <int ID>
struct TAGS_INDICATORS : public descriptors::TYPED_FIELD_BASE<bool, 1> {
  static const char* getName()
  {
    static std::string name = "TAGS_INDICATORS_" + std::to_string(ID);
    return name.c_str();
  }
};

} // namespace field::reduction

namespace reduction {

template <typename TAG_FIELD>
struct checkTag {
  template <typename CELL, typename T = typename CELL::value_t, typename DESCRIPTOR = typename CELL::descriptor_t>
  bool operator()(CELL& cell) any_platform
  {
    return cell.template getField<TAG_FIELD>();
  }
  static const char* getName() { return TAG_FIELD::getName(); }
  using tag_field_t = TAG_FIELD;
};

template <int ID =0>
using checkTagIndicator = checkTag<field::reduction::TAGS_INDICATORS<ID>>;

template <typename TAG_FIELD = field::reduction::TAG_TRUE>
struct ConditionTrue {
  template <typename CELL>
  bool operator()(CELL& cell) any_platform
  {
    return true;
  }
  static const char* getName() { return "ConditionTrue"; }
  using tag_field_t = TAG_FIELD;
};

struct SumO {
  template <typename FIELDD>
  FIELDD operator()(FIELDD lhs, FIELDD rhs) any_platform
  {
    return lhs + rhs;
  }

  template <typename T>
  T reset(T lhs) any_platform
  {
    T reset {};
    return reset;
  }

#ifdef PARALLEL_MODE_MPI
  MPI_Op forMPI() { return MPI_SUM; }
#endif // PARALLEL_MODE_MPI
};

struct MaxO {
  template <typename FIELDD>
  FIELDD operator()(FIELDD lhs, FIELDD rhs) any_platform
  {
    //    return maxv(lhs, rhs);
    return lhs > rhs ? lhs : rhs;
  }

  template <typename T>
  T reset(T lhs) any_platform
  {
    return std::numeric_limits<T>::lowest();
  }

#ifdef PARALLEL_MODE_MPI
  MPI_Op forMPI() { return MPI_MAX; }
#endif // PARALLEL_MODE_MPI
};

struct MinO {
  template <typename FIELDD>
  FIELDD operator()(FIELDD lhs, FIELDD rhs) any_platform
  {
    //    return minv(lhs, rhs);
    return lhs < rhs ? lhs : rhs;
  }

  template <typename T>
  T reset(T lhs) any_platform
  {
    return std::numeric_limits<T>::max();
  }

#ifdef PARALLEL_MODE_MPI
  MPI_Op forMPI() { return MPI_MIN; }
#endif // PARALLEL_MODE_MPI
};

struct ResetO {
  template <typename FIELDD>
  FIELDD operator()(FIELDD lhs) any_platform
  {
    FIELDD reset {};
    return reset;
  }
};

} // namespace reduction

template <typename FIELD, typename REDUCTION_OP, typename CONDITION>
struct BlockLatticeFieldReductionO {
  static constexpr OperatorScope scope = OperatorScope::PerBlockWithParameters;

  using parameters = meta::list<fields::array_of<FIELD>>;

  int getPriority() const { return 2; }

  template <typename BLOCK, typename PARAMETERS>
  struct type {
    void setup(BLOCK& blockLattice, PARAMETERS& parameters) {}
    void apply(BLOCK& blockLattice, PARAMETERS& parameters)
    {
      throw std::runtime_error("BlockLatticeFieldReductionO not implemented");
    }
  };

  template <typename BLOCK, typename PARAMETERS>
  void setup(BLOCK& blockLattice, PARAMETERS& parameters)
  {
    type<BLOCK, PARAMETERS> {}.setup(blockLattice, parameters);
  }

  template <typename BLOCK, typename PARAMETERS>
  void apply(BLOCK& blockLattice, PARAMETERS& parameters)
  {
    type<BLOCK, PARAMETERS> {}.apply(blockLattice, parameters);
  }
};

template <typename FIELD, typename REDUCTION_OP, typename CONDITION>
template <typename T, typename DESCRIPTOR, Platform PLATFORM>
requires(isPlatformCPU(PLATFORM)) struct BlockLatticeFieldReductionO<FIELD, REDUCTION_OP, CONDITION>::type<
    ConcreteBlockLattice<T, DESCRIPTOR, PLATFORM>, StaticParametersD<T, DESCRIPTOR, fields::array_of<FIELD>>> {

  using PARAMETERS = StaticParametersD<T, DESCRIPTOR, fields::array_of<FIELD>>;

  void setup(ConcreteBlockLattice<T, DESCRIPTOR, PLATFORM>& blockLattice, PARAMETERS& parameters)
  {
    blockLattice.template getData<OperatorParameters<BlockLatticeFieldReductionO>>();
  }

  void apply(ConcreteBlockLattice<T, DESCRIPTOR, PLATFORM>& blockLattice, PARAMETERS& parameters)
  {
    OstreamManager clout(std::cout, "Apply function in BlockLatticeFieldReductionO on CPU");

    const auto&                                    blockField = blockLattice.template getField<FIELD>();
    FieldD<T, DESCRIPTOR, fields::array_of<FIELD>> elementField =
        parameters.template get<fields::array_of<FIELD>>(); //not auto. because of considering 1 dimensional field

    for (unsigned iD = 0; iD < blockField.d; iD++) {
      if (elementField[iD] == nullptr) {
        //clout << "Error: elementField[" << iD << "] is nullptr in BlockLatticeFieldReductionO." << std::endl;
        return;
      }
      else {
        elementField[iD][0] = REDUCTION_OP {}.reset(elementField[iD][0]);
      }
    }

    blockLattice.forSpatialLocations([&](LatticeR<DESCRIPTOR::d> latticeR) {
      const std::size_t              iCell = blockLattice.getCellId(latticeR);
      const ConstCell<T, DESCRIPTOR> cell  = blockLattice.get(iCell);
      if (cell.template getField<field::reduction::TAG_CORE>()) {
        if (CONDITION {}(cell)) {
          FieldD<T, DESCRIPTOR, FIELD> blockCellField = blockField.getRow(iCell);
          for (unsigned iD = 0; iD < blockField.d; iD++) {
            elementField[iD][0] = REDUCTION_OP {}(elementField[iD][0], blockCellField[iD]);
          }
        }
      }
    });
  }
};

} // namespace olb

#endif //BLOCK_LATTICE_FIELD_REDUCTION_O_H
