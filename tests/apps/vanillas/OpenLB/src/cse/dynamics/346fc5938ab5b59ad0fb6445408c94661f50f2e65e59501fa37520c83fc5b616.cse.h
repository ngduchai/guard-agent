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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::FixedDensity, momenta::FixedPressureMomentum<0, 1>, momenta::BulkStress, momenta::DefineSeparately>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x23 = parameters.template get<descriptors::OMEGA>();
auto x22 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<0, 1>::VELOCITY>(2);
auto x21 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<0, 1>::VELOCITY>(1);
auto x19 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x20 = x23 + V{-1};
auto x24 = ((x21)*(x21));
auto x25 = V{1.5}*x24;
auto x26 = ((x22)*(x22));
auto x27 = V{1.5}*x26;
auto x28 = x25 + x27;
auto x29 = V{1} / (x19);
auto x30 = x29*(cell[0] + V{2}*cell[10] + cell[11] + cell[12] + V{2}*cell[13] + V{2}*cell[14] + V{2}*cell[15] + V{2}*cell[16] + cell[17] + cell[18] + cell[2] + cell[3] + cell[8] + cell[9] + V{1});
auto x31 = V{1} - x30;
auto x32 = ((x31)*(x31));
auto x33 = V{1.5}*x32;
auto x34 = x33 + V{-1};
auto x35 = x28 + x34;
auto x36 = V{0.0555555555555556}*x23;
auto x37 = ((x31)*(x31));
auto x38 = x29*(V{3}*cell[0] + V{6}*cell[10] + V{3}*cell[11] + V{3}*cell[12] + V{6}*cell[13] + V{6}*cell[14] + V{6}*cell[15] + V{6}*cell[16] + V{3}*cell[17] + V{3}*cell[18] + V{3}*cell[2] + V{3}*cell[3] + V{3}*cell[8] + V{3}*cell[9] + V{3});
auto x39 = x28 + x33 + x38 + V{-4};
auto x40 = V{3}*x21;
auto x41 = V{3}*x24;
auto x42 = V{3}*x22;
auto x43 = V{3}*x26;
auto x44 = V{0.0277777777777778}*x23;
auto x45 = x30 + V{-1};
auto x46 = x21 + x45;
auto x47 = -x40;
auto x48 = x21 + x31;
auto x49 = x22 + x45;
auto x50 = -x42;
auto x51 = x22 + x31;
auto x52 = V{4.5}*((x21 + x22)*(x21 + x22));
auto x53 = x35 + x40;
auto x54 = x21 - x22;
auto x55 = x28 - x38 + V{2};
auto x56 = V{1} - V{1.5}*x37;
auto x57 = -x27 + x40 + x56;
auto x58 = -x25 + x42;
auto x59 = x33 + x55;
auto x0 = -cell[0]*x20 - V{0.333333333333333}*x23*(x19*x35 + V{1});
auto x1 = -cell[1]*x20 - x36*(x19*(-V{4.5}*x37 + x39) + V{1});
auto x2 = -cell[2]*x20 - x36*(x19*(x27 + x34 + x40 - x41) + V{1});
auto x3 = -cell[3]*x20 - x36*(x19*(x25 + x34 + x42 - x43) + V{1});
auto x4 = -(cell[4]*x20 + x44*(x19*(x39 + x40 - V{4.5}*((x46)*(x46))) + V{1}));
auto x5 = -(cell[5]*x20 + x44*(x19*(x39 + x47 - V{4.5}*((x48)*(x48))) + V{1}));
auto x6 = -(cell[6]*x20 + x44*(x19*(x39 + x42 - V{4.5}*((x49)*(x49))) + V{1}));
auto x7 = -(cell[7]*x20 + x44*(x19*(x39 + x50 - V{4.5}*((x51)*(x51))) + V{1}));
auto x8 = -cell[8]*x20 - x44*(x19*(x42 - x52 + x53) + V{1});
auto x9 = -(cell[9]*x20 + x44*(x19*(x50 + x53 - V{4.5}*((x54)*(x54))) + V{1}));
auto x10 = -cell[10]*x20 - x36*(x19*(-V{3}*x32 + x55) + V{1});
auto x11 = -cell[11]*x20 + x36*(x19*(x41 + x57) + V{-1});
auto x12 = -cell[12]*x20 + x36*(x19*(x43 + x56 + x58) + V{-1});
auto x13 = -(cell[13]*x20 + x44*(x19*(x47 + x59 - V{4.5}*((x46)*(x46))) + V{1}));
auto x14 = -(cell[14]*x20 + x44*(x19*(x40 + x59 - V{4.5}*((x48)*(x48))) + V{1}));
auto x15 = -(cell[15]*x20 + x44*(x19*(x50 + x59 - V{4.5}*((x49)*(x49))) + V{1}));
auto x16 = -(cell[16]*x20 + x44*(x19*(x42 + x59 - V{4.5}*((x51)*(x51))) + V{1}));
auto x17 = -cell[17]*x20 + x44*(x19*(x52 + x57 + x58) + V{-1});
auto x18 = -(cell[18]*x20 + x44*(x19*(x35 + x42 + x47 - V{4.5}*((x54)*(x54))) + V{1}));
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
return { x19, x24 + x26 + V{1}*x37 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
