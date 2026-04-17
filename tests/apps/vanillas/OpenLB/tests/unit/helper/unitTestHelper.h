/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2017 Markus Mohrhard
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

#include <gtest/gtest.h>

#include <initializer_list>

#include <olb.h>

#include <iostream>

namespace olb {

namespace util {

template<>
inline bool approxEqual(const int& a, const int& b, const int& )
{
  return a == b;
}

}

namespace test {

template<typename CELL, typename T=typename CELL::value_t, typename DESCRIPTOR=typename CELL::descriptor_t>
bool compareCell(CELL& cell, const std::initializer_list<T>& compare)
{
  auto itr = compare.begin();
  for (size_t iPop = 0; iPop < DESCRIPTOR::q; ++itr, ++iPop) {
    if (!util::approxEqual(*itr, cell[iPop], T(1e-6))) {
      return false;
    }
  }

  return true;
}

template<typename CELL, typename T=typename CELL::value_t, typename DESCRIPTOR=typename CELL::descriptor_t>
testing::AssertionResult checkCell(CELL& cell, const std::initializer_list<T>& compare)
{
  size_t q = DESCRIPTOR::q;
  assert(q == compare.size());

  if (compareCell(cell, compare)) {
    return testing::AssertionSuccess();
  }
  else {
    auto result = testing::AssertionFailure();
    result << "Expected: ";

    for (auto& val: compare) {
      result << val << ", ";
    }

    result << "\nActual: ";

    for (size_t i = 0; i < q; ++i) {
      result << cell[i] << ", ";
    }

    return result;
  }
}

template<typename T, typename DESCRIPTOR>
testing::AssertionResult checkCell(BlockLattice<T,DESCRIPTOR>& lattice, int x, int y, const std::initializer_list<T>& compare)
{
  auto cell = lattice.get(x,y);
  return checkCell(cell, compare);
}

template<typename T, typename DESCRIPTOR>
testing::AssertionResult checkCell(BlockLattice<T,DESCRIPTOR>& lattice, int x, int y, int z, const std::initializer_list<T>& compare)
{
  auto cell = lattice.get(x,y,z);
  return checkCell(cell, compare);
}

template<typename CELL, typename T=typename CELL::value_t, typename DESCRIPTOR=typename CELL::descriptor_t>
void initCell(CELL& cell, const std::initializer_list<T>& initData)
{
  size_t q = DESCRIPTOR::q;
  assert(q == initData.size());

  std::vector<T> data(initData);

  for (size_t i = 0; i < q; ++i) {
    cell[i] = data[i];
  }
}

template<typename T, typename DESCRIPTOR>
void initCell(BlockLattice<T,DESCRIPTOR>& lattice, int x, int y, const std::initializer_list<T>& initData)
{
  auto cell = lattice.get(x,y);
  return initCell(cell, initData);
}

template<typename T, typename DESCRIPTOR>
void initCell(BlockLattice<T,DESCRIPTOR>& lattice, int x, int y, int z, const std::initializer_list<T>& initData)
{
  auto cell = lattice.get(x,y,z);
  return initCell(cell, initData);
}

template<typename T, typename BaseType = T>
BlockData<2,T, BaseType> createBlockData2D(int n_x, int n_y, const std::initializer_list<std::initializer_list<T>>& data)
{
  BlockData<2,T, BaseType> res({{n_x, n_y}, 0}, 1);
  int x = 0;
  for (auto& row_data : data) {
    int y = 0;
    for (auto& cell : row_data) {
      res.get({x, y}) = cell;
      ++y;
    }
    ++x;
  }

  return res;
}

template<typename T, typename BaseType = T>
void initBlockData2D(BlockData<2,T, BaseType>& blockData, std::function<BaseType(int, int)> initFunc)
{
  for (int iX = 0; iX < blockData.getNx(); ++iX) {
    for (int iY = 0; iY < blockData.getNy(); ++iY) {
      blockData.get({iX, iY}) = initFunc(iX, iY);
    }
  }
}

template<typename T, typename BaseType = T>
void initBlockData2D(BlockData<2,T, BaseType>& blockData, std::function<BaseType(int, int, int)> initFunc)
{
  for (int iX = 0; iX < blockData.getNx(); ++iX) {
    for (int iY = 0; iY < blockData.getNy(); ++iY) {
      for (int iD = 0; iD < blockData.getSize(); ++iD) {
        blockData.get({iX, iY}, iD) = initFunc(iX, iY, iD);
      }
    }
  }
}

template<typename T, typename BaseType = T>
void initBlockData3D(BlockData<3,T, BaseType>& blockData, std::function<BaseType(int, int, int)> initFunc)
{
  for (int iX = 0; iX < blockData.getNx(); ++iX) {
    for (int iY = 0; iY < blockData.getNy(); ++iY) {
      for (int iZ = 0; iZ < blockData.getNz(); ++iZ) {
        blockData.get({iX, iY, iZ}) = initFunc(iX, iY, iZ);
      }
    }
  }
}

template<typename T, typename BaseType = T>
void initBlockData3D(BlockData<3,T, BaseType>& blockData, std::function<BaseType(int, int, int, int)> initFunc)
{
  for (int iX = 0; iX < blockData.getNx(); ++iX) {
    for (int iY = 0; iY < blockData.getNy(); ++iY) {
      for (int iZ = 0; iZ < blockData.getNz(); ++iZ) {
        for (int iD = 0; iD < blockData.getSize(); ++iD) {
          blockData.get({iX, iY, iZ}, iD) = initFunc(iX, iY, iZ, iD);
        }
      }
    }
  }
}

template<typename T, typename BaseType = T>
BlockData<3,T, BaseType> createBlockData3D(int n_x, int n_y, int n_z, const std::initializer_list<std::initializer_list<std::initializer_list<T>>>& data)
{
  BlockData<3,T,BaseType> res({{n_x, n_y, n_z}, 0},1);
  int x = 0;
  for (auto& x_data : data) {
    int y = 0;
    for (auto& y_data : x_data) {
      int z = 0;
      for (auto& cell : y_data) {
        res.get({x, y, z}) = cell;
        ++z;
      }
      ++y;
    }
    ++x;
  }

  return res;
}

template<typename T, typename DESCRIPTOR>
void initBlockLattice2D(BlockLattice<T, DESCRIPTOR>& lattice, std::initializer_list<std::initializer_list<T>> values)
{
  assert (lattice.getNcells() == values.size());

  auto itr = values.begin();
  for (std::size_t iCell=0; iCell < lattice.getNcells(); ++iCell) {
    auto cell = lattice.get(iCell);
    initCell(cell, *itr);
    ++itr;
  }
}

template<typename T, typename DESCRIPTOR>
void initBlockLattice3D(BlockLattice<T,DESCRIPTOR>& lattice, std::initializer_list<std::initializer_list<T>> values)
{
  assert (lattice.getNcells() == values.size());

  auto itr = values.begin();
  for (std::size_t iCell=0; iCell < lattice.getNcells(); ++iCell) {
    auto cell = lattice.get(iCell);
    initCell(cell, *itr);
    ++itr;
  }
}

template<typename T, typename DESCRIPTOR>
testing::AssertionResult checkLattice2D(BlockLattice<T,DESCRIPTOR>& lattice, std::initializer_list<std::initializer_list<T>> values)
{
  assert (lattice.getNcells() == values.size());

  auto itr = values.begin();
  for (std::size_t iCell=0; iCell < lattice.getNcells(); ++iCell) {
    auto cell = lattice.get(iCell);
    testing::AssertionResult res = checkCell(cell, *itr);
    if (!res) {
      res << "Position: " << iCell;
      return res;
    }

    ++itr;
  }

  return testing::AssertionSuccess();
}

template<typename T, typename DESCRIPTOR>
testing::AssertionResult checkLattice3D(BlockLattice<T,DESCRIPTOR>& lattice, std::initializer_list<std::initializer_list<T>> values)
{
  assert (lattice.getNcells() == values.size());

  auto itr = values.begin();
  for (std::size_t iCell=0; iCell < lattice.getNcells(); ++iCell) {
    auto cell = lattice.get(iCell);
    testing::AssertionResult res = checkCell(cell, *itr);
    if (!res) {
      res << "Position: " << iCell;
      return res;
    }

    ++itr;
  }

  return testing::AssertionSuccess();
}

template<typename T, typename DESCRIPTOR>
void dumpLattice(BlockLattice<T, DESCRIPTOR>& lattice)
{
  for (std::size_t iCell=0; iCell < lattice.getNcells(); ++iCell) {
    std::cout << ", {";
    Cell<T,DESCRIPTOR> cell = lattice.get(iCell);
    for (int iPop = 0; iPop < DESCRIPTOR::q; ++iPop) {
      if (iPop != 0) {
        std::cout << ",";
      }
      std::cout << cell[iPop];
    }
    std::cout << "}" << std::endl;
  }
}

}

}
