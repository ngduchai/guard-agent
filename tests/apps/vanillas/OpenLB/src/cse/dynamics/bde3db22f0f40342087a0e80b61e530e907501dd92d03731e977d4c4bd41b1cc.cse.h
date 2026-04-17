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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, forcing::fsi::HLBM>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x11 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x12 = parameters.template get<descriptors::OMEGA>();
auto x10 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x9 = cell.template getFieldComponent<olb::descriptors::POROSITY>(0);
auto x13 = x12 + V{-1};
auto x14 = cell[0] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8];
auto x15 = x14 + V{1};
auto x16 = x14 + V{1};
auto x17 = V{1} / ((x16)*(x16));
auto x18 = V{1.5}*x17;
auto x19 = cell[1] - cell[5];
auto x20 = -cell[4] + cell[8];
auto x21 = -cell[3] + cell[7] + x19 + x20;
auto x22 = ((x21)*(x21));
auto x23 = x18*x22;
auto x24 = cell[2] - cell[6];
auto x25 = cell[3] - cell[7] + x19 + x24;
auto x26 = -x25;
auto x27 = x18*((x26)*(x26)) + V{-1};
auto x28 = x23 + x27;
auto x29 = V{1} / (x16);
auto x30 = V{1}*cell[3];
auto x31 = V{1}*cell[1] - V{1}*cell[5];
auto x32 = x29*(-V{1}*cell[4] + V{1}*cell[7] + V{1}*cell[8] - x30 + x31);
auto x33 = x9 + V{-1};
auto x34 = -x33;
auto x35 = -x32;
auto x36 = x11 + x35;
auto x37 = x34*x36;
auto x38 = V{1}*cell[2] - V{1}*cell[6] - V{1}*cell[7] + x30 + x31;
auto x39 = -x29*x38;
auto x40 = x34*(x10 - x39);
auto x41 = V{-1} + V{1.5}*((x32 + x37)*(x32 + x37)) + V{1.5}*((x39 + x40)*(x39 + x40));
auto x42 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778};
auto x43 = V{3}*cell[3];
auto x44 = V{3}*cell[7];
auto x45 = V{3}*cell[1] - V{3}*cell[5];
auto x46 = V{3}*cell[2] - V{3}*cell[6] + x43 - x44 + x45;
auto x47 = x29*x46;
auto x48 = V{4.5}*x17;
auto x49 = V{2}*cell[1] - V{2}*cell[5] + x20 + x24;
auto x50 = V{1} - x23;
auto x51 = x29*(-V{3}*cell[4] + V{3}*cell[8] - x43 + x44 + x45);
auto x52 = ((x25)*(x25));
auto x53 = x18*x52;
auto x54 = x51 - x53;
auto x55 = x50 + x54;
auto x56 = x47 + x48*((x49)*(x49)) + x55;
auto x57 = x21*x29;
auto x58 = -x57;
auto x59 = x26*x29 + x40;
auto x60 = -x51;
auto x61 = V{3}*x37;
auto x62 = -x29*x46;
auto x63 = V{3}*x40 + x41 + x62;
auto x64 = V{0.111111111111111}*cell[0] + V{0.111111111111111}*cell[1] + V{0.111111111111111}*cell[2] + V{0.111111111111111}*cell[3] + V{0.111111111111111}*cell[4] + V{0.111111111111111}*cell[5] + V{0.111111111111111}*cell[6] + V{0.111111111111111}*cell[7] + V{0.111111111111111}*cell[8] + V{0.111111111111111};
auto x65 = V{3}*x17;
auto x66 = x50 + x52*x65;
auto x67 = x47 + x66;
auto x68 = V{0.0277777777777778}*x12;
auto x69 = x48*((-2*cell[3] - cell[4] + 2*cell[7] + cell[8] - x24)*(-2*cell[3] - cell[4] + 2*cell[7] + cell[8] - x24));
auto x70 = x28 + x51 + x62 - x69;
auto x71 = x37 + x57;
auto x72 = x51 + x61;
auto x73 = V{0.111111111111111}*x12;
auto x74 = x22*x65;
auto x75 = x27 + x51 - x74;
auto x76 = x47 + V{-1};
auto x77 = x51 + x76;
auto x78 = -(-V{4.5}*x17*((x49)*(x49)) + x23 + x53 + x77);
auto x79 = x33*x36;
auto x80 = V{3}*x79;
auto x81 = -x80;
auto x82 = x29*x38;
auto x83 = x33*(x10 + x82);
auto x84 = x25*x29 + x83;
auto x85 = V{1.5}*((x82 + x83)*(x82 + x83));
auto x86 = V{1.5}*((-x35 - x79)*(-x35 - x79));
auto x87 = V{3}*x83 + x85 + x86;
auto x88 = -x47;
auto x89 = x66 + x88;
auto x90 = x76 + x87;
auto x91 = x55 + x69 + x88;
auto x92 = x58 + x79;
auto x93 = x54 + x74 + V{1};
auto x0 = -cell[0]*x13 - V{0.444444444444444}*x12*(x15*x28 + V{1}) + V{0.444444444444444}*x15*x28 - x41*(V{0.444444444444444}*cell[0] + V{0.444444444444444}*cell[1] + V{0.444444444444444}*cell[2] + V{0.444444444444444}*cell[3] + V{0.444444444444444}*cell[4] + V{0.444444444444444}*cell[5] + V{0.444444444444444}*cell[6] + V{0.444444444444444}*cell[7] + V{0.444444444444444}*cell[8] + V{0.444444444444444});
auto x1 = -(cell[1]*x13 - V{0.0277777777777778}*x12*(x15*x56 + V{-1}) + x42*x56 + x42*(x60 - x61 + x63 - V{4.5}*((x34*x36 - x58 - x59)*(x34*x36 - x58 - x59))));
auto x2 = -(cell[2]*x13 - V{0.111111111111111}*x12*(x15*x67 + V{-1}) + x64*x67 + x64*(x63 - V{4.5}*((x59)*(x59))));
auto x3 = -(cell[3]*x13 - V{0.0277777777777778}*x15*x70 + x42*(x63 + x72 - V{4.5}*((x59 + x71)*(x59 + x71))) + x68*(x15*x70 + V{1}));
auto x4 = -(cell[4]*x13 - V{0.111111111111111}*x15*x75 + x64*(x41 + x72 - V{4.5}*((x71)*(x71))) + x73*(x15*x75 + V{1}));
auto x5 = -cell[5]*x13 - x42*x78 - x42*(x77 + x81 + x87 - V{4.5}*((-x57 + x79 - x84)*(-x57 + x79 - x84))) + x68*(x15*x78 + V{-1});
auto x6 = -cell[6]*x13 - x64*x89 - x64*(x90 - V{4.5}*((x84)*(x84))) + x73*(x15*x89 + V{-1});
auto x7 = -cell[7]*x13 - x42*x91 - x42*(x60 + x80 + x90 - V{4.5}*((-x84 - x92)*(-x84 - x92))) + x68*(x15*x91 + V{-1});
auto x8 = -cell[8]*x13 - x64*x93 + x64*(x51 + x81 - x85 - x86 + V{1} + V{4.5}*((x92)*(x92))) + x73*(x15*x93 + V{-1});
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x16, V{1}*x17*(x22 + x52) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
