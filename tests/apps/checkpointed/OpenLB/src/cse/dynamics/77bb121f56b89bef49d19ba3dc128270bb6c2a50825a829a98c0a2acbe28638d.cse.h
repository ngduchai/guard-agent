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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = parameters.template get<descriptors::OMEGA>();
auto x20 = x19 + V{-1};
auto x21 = cell[10] + cell[14];
auto x22 = cell[12] + cell[7];
auto x23 = cell[0] + cell[11] + cell[13] + cell[15] + cell[16] + cell[17] + cell[18] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[8] + cell[9] + x21 + x22;
auto x24 = x23 + V{1};
auto x25 = x23 + V{1};
auto x26 = V{1} / ((x25)*(x25));
auto x27 = V{1.5}*x26;
auto x28 = cell[13] - cell[4];
auto x29 = cell[15] - cell[6];
auto x30 = x28 + x29;
auto x31 = -cell[1];
auto x32 = cell[16] - cell[7];
auto x33 = x31 + x32;
auto x34 = -cell[5] + x21;
auto x35 = ((x30 + x33 + x34)*(x30 + x33 + x34));
auto x36 = x27*x35;
auto x37 = cell[17] - cell[8];
auto x38 = x28 + x37;
auto x39 = cell[18] - cell[9];
auto x40 = -cell[2];
auto x41 = cell[11] - cell[14] + cell[5] + x40;
auto x42 = ((x38 + x39 + x41)*(x38 + x39 + x41));
auto x43 = x27*x42;
auto x44 = x29 + x37;
auto x45 = -cell[3];
auto x46 = -cell[18] + cell[9];
auto x47 = x45 + x46;
auto x48 = -cell[16] + x22;
auto x49 = ((x44 + x47 + x48)*(x44 + x47 + x48));
auto x50 = x27*x49;
auto x51 = x43 + x50 + V{-1};
auto x52 = x36 + x51;
auto x53 = V{0.0555555555555556}*x19;
auto x54 = V{1} / (x25);
auto x55 = V{3}*cell[14];
auto x56 = V{3}*cell[16];
auto x57 = V{3}*cell[5];
auto x58 = V{3}*cell[7];
auto x59 = V{3}*cell[13] - V{3}*cell[4];
auto x60 = V{3}*cell[15] - V{3}*cell[6];
auto x61 = x54*(V{3}*cell[10] - V{3}*cell[1] + x55 + x56 - x57 - x58 + x59 + x60);
auto x62 = V{3}*x26;
auto x63 = x35*x62;
auto x64 = V{3}*cell[18];
auto x65 = V{3}*cell[9];
auto x66 = V{3}*cell[17] - V{3}*cell[8];
auto x67 = x54*(V{3}*cell[11] - V{3}*cell[2] - x55 + x57 + x59 + x64 - x65 + x66);
auto x68 = x42*x62;
auto x69 = x36 + V{-1};
auto x70 = x54*(V{3}*cell[12] - V{3}*cell[3] - x56 + x58 + x60 - x64 + x65 + x66);
auto x71 = x49*x62;
auto x72 = V{0.0277777777777778}*x19;
auto x73 = V{4.5}*x26;
auto x74 = cell[10] + x33;
auto x75 = x73*((cell[11] + 2*cell[13] - 2*cell[4] + x39 + x40 + x44 + x74)*(cell[11] + 2*cell[13] - 2*cell[4] + x39 + x40 + x44 + x74));
auto x76 = x52 + x61;
auto x77 = -x67;
auto x78 = -cell[17] + cell[8];
auto x79 = -cell[11] + V{2}*cell[14] + cell[2] - V{2}*cell[5] + x29 + x46 + x74 + x78;
auto x80 = x31 + x34;
auto x81 = x73*((cell[12] + 2*cell[15] - 2*cell[6] + x38 + x47 + x80)*(cell[12] + 2*cell[15] - 2*cell[6] + x38 + x47 + x80));
auto x82 = -x70;
auto x83 = -cell[12] + cell[3] + x28;
auto x84 = V{2}*cell[16] - V{2}*cell[7] + x39 + x78 + x80 + x83;
auto x85 = x73*((2*cell[17] - 2*cell[8] + x30 + x41 + x45 + x48)*(2*cell[17] - 2*cell[8] + x30 + x41 + x45 + x48));
auto x86 = x52 + x67;
auto x87 = -cell[15] + V{2}*cell[18] + cell[6] - V{2}*cell[9] + x32 + x41 + x83;
auto x88 = -x43;
auto x89 = V{1} - x50;
auto x90 = x88 + x89;
auto x91 = x61 + x90;
auto x92 = -x36;
auto x93 = x67 + x92;
auto x94 = x70 + x92;
auto x95 = -x61;
auto x96 = x52 + x70;
auto x0 = -cell[0]*x20 - V{0.333333333333333}*x19*(x24*x52 + V{1});
auto x1 = -cell[1]*x20 - x53*(x24*(x51 + x61 - x63) + V{1});
auto x2 = -cell[2]*x20 - x53*(x24*(x50 + x67 - x68 + x69) + V{1});
auto x3 = -cell[3]*x20 - x53*(x24*(x43 + x69 + x70 - x71) + V{1});
auto x4 = -cell[4]*x20 - x72*(x24*(x67 - x75 + x76) + V{1});
auto x5 = -(cell[5]*x20 + x72*(x24*(-x73*((x79)*(x79)) + x76 + x77) + V{1}));
auto x6 = -cell[6]*x20 - x72*(x24*(x70 + x76 - x81) + V{1});
auto x7 = -(cell[7]*x20 + x72*(x24*(-x73*((x84)*(x84)) + x76 + x82) + V{1}));
auto x8 = -cell[8]*x20 - x72*(x24*(x70 - x85 + x86) + V{1});
auto x9 = -(cell[9]*x20 + x72*(x24*(-x73*((x87)*(x87)) + x82 + x86) + V{1}));
auto x10 = -cell[10]*x20 + x53*(x24*(x63 + x91) + V{-1});
auto x11 = -cell[11]*x20 + x53*(x24*(x68 + x89 + x93) + V{-1});
auto x12 = -cell[12]*x20 + x53*(x24*(x71 + x88 + x94 + V{1}) + V{-1});
auto x13 = -cell[13]*x20 + x72*(x24*(x75 + x91 + x93) + V{-1});
auto x14 = -(cell[14]*x20 + x72*(x24*(-x73*((x79)*(x79)) + x86 + x95) + V{1}));
auto x15 = -cell[15]*x20 + x72*(x24*(x81 + x91 + x94) + V{-1});
auto x16 = -(cell[16]*x20 + x72*(x24*(-x73*((x84)*(x84)) + x95 + x96) + V{1}));
auto x17 = -cell[17]*x20 + x72*(x24*(x70 + x85 + x90 + x93) + V{-1});
auto x18 = -(cell[18]*x20 + x72*(x24*(-x73*((x87)*(x87)) + x77 + x96) + V{1}));
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
return { x25, V{1}*x26*(x35 + x42 + x49) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
