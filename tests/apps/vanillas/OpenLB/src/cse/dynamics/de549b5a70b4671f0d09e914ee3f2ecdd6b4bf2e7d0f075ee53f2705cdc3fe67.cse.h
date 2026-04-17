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

namespace dynamics {

template <typename T, typename... FIELDS>
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::FixedDensity, momenta::FixedPressureMomentum<1, 1>, momenta::BulkStress, momenta::DefineSeparately>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x23 = parameters.template get<descriptors::OMEGA>();
auto x20 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<1, 1>::VELOCITY>(0);
auto x19 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<1, 1>::VELOCITY>(2);
auto x21 = x23 + V{-1};
auto x24 = ((x20)*(x20));
auto x25 = V{1.5}*x24;
auto x26 = ((x22)*(x22));
auto x27 = V{1.5}*x26;
auto x28 = x25 + x27;
auto x29 = V{1} / (x19);
auto x30 = x29*(cell[0] + cell[10] + V{2}*cell[11] + cell[12] + V{2}*cell[13] + cell[15] + cell[16] + V{2}*cell[17] + V{2}*cell[18] + cell[1] + cell[3] + V{2}*cell[5] + cell[6] + cell[7] + V{1});
auto x31 = V{1} - x30;
auto x32 = ((x31)*(x31));
auto x33 = V{1.5}*x32;
auto x34 = x33 + V{-1};
auto x35 = x28 + x34;
auto x36 = V{0.0555555555555556}*x23;
auto x37 = V{3}*x20;
auto x38 = V{3}*x24;
auto x39 = ((x31)*(x31));
auto x40 = x29*(V{3}*cell[0] + V{3}*cell[10] + V{6}*cell[11] + V{3}*cell[12] + V{6}*cell[13] + V{3}*cell[15] + V{3}*cell[16] + V{6}*cell[17] + V{6}*cell[18] + V{3}*cell[1] + V{3}*cell[3] + V{6}*cell[5] + V{3}*cell[6] + V{3}*cell[7] + V{3});
auto x41 = x28 + x33 + x40 + V{-4};
auto x42 = V{3}*x22;
auto x43 = V{3}*x26;
auto x44 = V{0.0277777777777778}*x23;
auto x45 = x30 + V{-1};
auto x46 = x20 + x45;
auto x47 = x20 + x31;
auto x48 = x28 - x40 + V{2};
auto x49 = x33 + x48;
auto x50 = V{4.5}*((x20 + x22)*(x20 + x22));
auto x51 = x35 + x37;
auto x52 = -x42;
auto x53 = x20 - x22;
auto x54 = x22 + x45;
auto x55 = x22 + x31;
auto x56 = V{1} - V{1.5}*x39;
auto x57 = -x27 + x37 + x56;
auto x58 = -x25 + x42;
auto x59 = -x37;
auto x0 = -cell[0]*x21 - V{0.333333333333333}*x23*(x19*x35 + V{1});
auto x1 = -cell[1]*x21 - x36*(x19*(x27 + x34 + x37 - x38) + V{1});
auto x2 = -cell[2]*x21 - x36*(x19*(-V{4.5}*x39 + x41) + V{1});
auto x3 = -cell[3]*x21 - x36*(x19*(x25 + x34 + x42 - x43) + V{1});
auto x4 = -(cell[4]*x21 + x44*(x19*(x37 + x41 - V{4.5}*((x46)*(x46))) + V{1}));
auto x5 = -(cell[5]*x21 + x44*(x19*(x37 + x49 - V{4.5}*((x47)*(x47))) + V{1}));
auto x6 = -cell[6]*x21 - x44*(x19*(x42 - x50 + x51) + V{1});
auto x7 = -(cell[7]*x21 + x44*(x19*(x51 + x52 - V{4.5}*((x53)*(x53))) + V{1}));
auto x8 = -(cell[8]*x21 + x44*(x19*(x41 + x42 - V{4.5}*((x54)*(x54))) + V{1}));
auto x9 = -(cell[9]*x21 + x44*(x19*(x41 + x52 - V{4.5}*((x55)*(x55))) + V{1}));
auto x10 = -cell[10]*x21 + x36*(x19*(x38 + x57) + V{-1});
auto x11 = -cell[11]*x21 - x36*(x19*(-V{3}*x32 + x48) + V{1});
auto x12 = -cell[12]*x21 + x36*(x19*(x43 + x56 + x58) + V{-1});
auto x13 = -(cell[13]*x21 + x44*(x19*(x49 + x59 - V{4.5}*((x46)*(x46))) + V{1}));
auto x14 = -(cell[14]*x21 + x44*(x19*(x41 + x59 - V{4.5}*((x47)*(x47))) + V{1}));
auto x15 = -cell[15]*x21 + x44*(x19*(x50 + x57 + x58) + V{-1});
auto x16 = -(cell[16]*x21 + x44*(x19*(x35 + x42 + x59 - V{4.5}*((x53)*(x53))) + V{1}));
auto x17 = -(cell[17]*x21 + x44*(x19*(x49 + x52 - V{4.5}*((x54)*(x54))) + V{1}));
auto x18 = -(cell[18]*x21 + x44*(x19*(x42 + x49 - V{4.5}*((x55)*(x55))) + V{1}));
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
return { x19, x24 + x26 + V{1}*x39 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
