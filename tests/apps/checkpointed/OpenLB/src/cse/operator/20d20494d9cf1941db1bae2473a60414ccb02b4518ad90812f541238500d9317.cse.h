/*  This file is part of the OpenLB library
 *
 *  Copyright (C) Adrian Kummerlaender, Shota Ito
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

/*  ========================================================
 *  ==  WARNING: This is an automatically generated file, ==
 *  ==                  do not modify.                    ==
 *  ========================================================
 */

#pragma once


namespace olb {

namespace operators {

template <typename T, typename... FIELDS>
struct CSE_O<StraightConvectionBoundaryProcessor3D<T, descriptors::D3Q19<FIELDS...>, 0, -1>,descriptors::D3Q19<FIELDS...>> {
template <concepts::Cell CELL>
void apply(CELL& cell) any_platform {
using V = typename CELL::value_t;
using DESCRIPTOR = typename CELL::descriptor_t;
V v_S0 = cell.computeRho();
auto x19 = V{3}*v_S0;
V v_V0 [DESCRIPTOR::d]; cell.computeU(v_V0);
auto x21 = v_S0*v_V0[0];
auto x24 = V{0.0416666666666667}*x21;
V v_S1 = cell.neighbor({1,0,0}).computeRho();
auto x20 = V{4}*v_S1;
V v_V1 [DESCRIPTOR::d]; cell.neighbor({1,0,0}).computeU(v_V1);
V v_S2 = cell.neighbor({2,0,0}).computeRho();
V v_V2 [DESCRIPTOR::d]; cell.neighbor({2,0,0}).computeU(v_V2);
auto x22 = x21*(v_S2*v_V2[0] + v_V0[0]*x19 - v_V1[0]*x20);
auto x23 = V{0.0416666666666667}*x22;
auto x26 = -x23;
auto x25 = x24*(v_S2*v_V2[1] + v_V0[1]*x19 - v_V1[1]*x20);
auto x27 = x24*(v_S2*v_V2[2] + v_V0[2]*x19 - v_V1[2]*x20);
auto x0 = cell[0];
auto x1 = cell[1];
auto x2 = cell[2];
auto x3 = cell[3];
auto x4 = cell[4];
auto x5 = cell[5];
auto x6 = cell[6];
auto x7 = cell[7];
auto x8 = cell[8];
auto x9 = cell[9];
auto x10 = cell.template getFieldComponent<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>(0);
auto x11 = cell[11];
auto x12 = cell[12];
auto x13 = cell.template getFieldComponent<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>(1);
auto x14 = cell.template getFieldComponent<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>(2);
auto x15 = cell.template getFieldComponent<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>(3);
auto x16 = cell.template getFieldComponent<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>(4);
auto x17 = cell[17];
auto x18 = cell[18];
cell.template getFieldPointer<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>()[0] = cell.template getFieldComponent<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>(0) - V{0.0833333333333333}*x22;
cell.template getFieldPointer<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>()[1] = cell.template getFieldComponent<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>(1) - x23 - x25;
cell.template getFieldPointer<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>()[2] = cell.template getFieldComponent<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>(2) + x25 + x26;
cell.template getFieldPointer<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>()[3] = cell.template getFieldComponent<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>(3) - x23 - x27;
cell.template getFieldPointer<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>()[4] = cell.template getFieldComponent<olb::StraightConvectionBoundaryProcessor3D<olb::Expr, olb::descriptors::D3Q19<>, 0, -1>::PREV_CELL>(4) + x26 + x27;
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
cell[9] = x9;
cell[10] = x10;
cell[11] = x11;
cell[12] = x12;
cell[13] = x13;
cell[14] = x14;
cell[15] = x15;
cell[16] = x16;
cell[17] = x17;
cell[18] = x18;
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
