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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::SaveVelocity<collision::BGK>, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x22 = parameters.template get<descriptors::OMEGA>();
auto x19 = x22 + V{-1};
auto x20 = cell[10] + cell[14];
auto x21 = cell[12] + cell[7];
auto x23 = cell[0] + cell[11] + cell[13] + cell[15] + cell[16] + cell[17] + cell[18] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[8] + cell[9] + x20 + x21;
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
auto x34 = -cell[5] + x20;
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
auto x48 = -cell[16] + x21;
auto x49 = ((x44 + x47 + x48)*(x44 + x47 + x48));
auto x50 = x27*x49;
auto x51 = x43 + x50 + V{-1};
auto x52 = x36 + x51;
auto x53 = cell[0]*x19 + V{0.333333333333333}*x22*(x24*x52 + V{1});
auto x54 = cell[1]*x19;
auto x55 = V{0.0555555555555556}*x22;
auto x56 = V{1} / (x25);
auto x57 = V{3}*cell[14];
auto x58 = V{3}*cell[16];
auto x59 = V{3}*cell[5];
auto x60 = V{3}*cell[7];
auto x61 = V{3}*cell[13] - V{3}*cell[4];
auto x62 = V{3}*cell[15] - V{3}*cell[6];
auto x63 = x56*(V{3}*cell[10] - V{3}*cell[1] + x57 + x58 - x59 - x60 + x61 + x62);
auto x64 = V{3}*x26;
auto x65 = x35*x64;
auto x66 = x55*(x24*(x51 + x63 - x65) + V{1});
auto x67 = x54 + x66;
auto x68 = cell[2]*x19;
auto x69 = V{3}*cell[18];
auto x70 = V{3}*cell[9];
auto x71 = V{3}*cell[17] - V{3}*cell[8];
auto x72 = x56*(V{3}*cell[11] - V{3}*cell[2] - x57 + x59 + x61 + x69 - x70 + x71);
auto x73 = x42*x64;
auto x74 = x36 + V{-1};
auto x75 = x55*(x24*(x50 + x72 - x73 + x74) + V{1});
auto x76 = x68 + x75;
auto x77 = cell[3]*x19;
auto x78 = x56*(V{3}*cell[12] - V{3}*cell[3] - x58 + x60 + x62 - x69 + x70 + x71);
auto x79 = x49*x64;
auto x80 = x55*(x24*(x43 + x74 + x78 - x79) + V{1});
auto x81 = x77 + x80;
auto x82 = cell[4]*x19;
auto x83 = V{0.0277777777777778}*x22;
auto x84 = V{4.5}*x26;
auto x85 = cell[10] + x33;
auto x86 = x84*((cell[11] + 2*cell[13] - 2*cell[4] + x39 + x40 + x44 + x85)*(cell[11] + 2*cell[13] - 2*cell[4] + x39 + x40 + x44 + x85));
auto x87 = x52 + x63;
auto x88 = x83*(x24*(x72 - x86 + x87) + V{1});
auto x89 = x82 + x88;
auto x90 = cell[5]*x19;
auto x91 = -x72;
auto x92 = -cell[17] + cell[8];
auto x93 = -cell[11] + V{2}*cell[14] + cell[2] - V{2}*cell[5] + x29 + x46 + x85 + x92;
auto x94 = x83*(x24*(-x84*((x93)*(x93)) + x87 + x91) + V{1});
auto x95 = x90 + x94;
auto x96 = cell[6]*x19;
auto x97 = x31 + x34;
auto x98 = x84*((cell[12] + 2*cell[15] - 2*cell[6] + x38 + x47 + x97)*(cell[12] + 2*cell[15] - 2*cell[6] + x38 + x47 + x97));
auto x99 = x83*(x24*(x78 + x87 - x98) + V{1});
auto x100 = x96 + x99;
auto x101 = cell[7]*x19;
auto x102 = -x78;
auto x103 = -cell[12] + cell[3] + x28;
auto x104 = V{2}*cell[16] - V{2}*cell[7] + x103 + x39 + x92 + x97;
auto x105 = x83*(x24*(x102 - x84*((x104)*(x104)) + x87) + V{1});
auto x106 = x101 + x105;
auto x107 = cell[8]*x19;
auto x108 = x84*((2*cell[17] - 2*cell[8] + x30 + x41 + x45 + x48)*(2*cell[17] - 2*cell[8] + x30 + x41 + x45 + x48));
auto x109 = x52 + x72;
auto x110 = x83*(x24*(-x108 + x109 + x78) + V{1});
auto x111 = x107 + x110;
auto x112 = cell[9]*x19;
auto x113 = -cell[15] + V{2}*cell[18] + cell[6] - V{2}*cell[9] + x103 + x32 + x41;
auto x114 = x83*(x24*(x102 + x109 - x84*((x113)*(x113))) + V{1});
auto x115 = x112 + x114;
auto x116 = cell[10]*x19;
auto x117 = -x43;
auto x118 = V{1} - x50;
auto x119 = x117 + x118;
auto x120 = x119 + x63;
auto x121 = x55*(x24*(x120 + x65) + V{-1});
auto x122 = cell[11]*x19;
auto x123 = -x36;
auto x124 = x123 + x72;
auto x125 = x55*(x24*(x118 + x124 + x73) + V{-1});
auto x126 = cell[12]*x19;
auto x127 = x123 + x78;
auto x128 = x55*(x24*(x117 + x127 + x79 + V{1}) + V{-1});
auto x129 = cell[13]*x19;
auto x130 = x83*(x24*(x120 + x124 + x86) + V{-1});
auto x131 = cell[14]*x19;
auto x132 = -x63;
auto x133 = x83*(x24*(x109 + x132 - x84*((x93)*(x93))) + V{1});
auto x134 = x131 + x133;
auto x135 = cell[15]*x19;
auto x136 = x83*(x24*(x120 + x127 + x98) + V{-1});
auto x137 = cell[16]*x19;
auto x138 = x52 + x78;
auto x139 = x83*(x24*(x132 + x138 - x84*((x104)*(x104))) + V{1});
auto x140 = x137 + x139;
auto x141 = cell[17]*x19;
auto x142 = x83*(x24*(x108 + x119 + x124 + x78) + V{-1});
auto x143 = cell[18]*x19;
auto x144 = x83*(x24*(x138 - x84*((x113)*(x113)) + x91) + V{1});
auto x145 = x143 + x144;
auto x146 = V{1} / (-x100 - x106 - x111 - x115 - x116 + x121 - x122 + x125 - x126 + x128 - x129 + x130 - x134 - x135 + x136 - x140 - x141 + x142 - x145 - x53 - x67 - x76 - x81 - x89 - x95 + V{1});
auto x147 = V{1}*x90;
auto x148 = V{1}*x101;
auto x149 = V{1}*x131;
auto x150 = V{1}*x137;
auto x151 = -V{1}*cell[13]*x19 + x130 + V{1}*x82 + x88;
auto x152 = -V{1}*cell[15]*x19 + x136 + V{1}*x96 + x99;
auto x153 = V{1}*x112;
auto x154 = V{1}*x143;
auto x155 = -V{1}*cell[17]*x19 + V{1}*x107 + x110 + x142;
cell[0] = -x53;
cell[1] = -x67;
cell[2] = -x76;
cell[3] = -x81;
cell[4] = -x89;
cell[5] = -x95;
cell[6] = -x100;
cell[7] = -x106;
cell[8] = -x111;
cell[9] = -x115;
cell[10] = -x116 + x121;
cell[11] = -x122 + x125;
cell[12] = -x126 + x128;
cell[13] = -x129 + x130;
cell[14] = -x134;
cell[15] = -x135 + x136;
cell[16] = -x140;
cell[17] = -x141 + x142;
cell[18] = -x145;
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[0] = -x146*(V{1}*cell[10]*x19 - x105 - x121 + x133 + x139 - x147 - x148 + x149 + x150 - x151 - x152 - V{1}*x54 - x66 - x94);
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[1] = -x146*(V{1}*cell[11]*x19 - x114 - x125 - x133 + x144 + x147 - x149 - x151 - x153 + x154 - x155 - V{1}*x68 - x75 + x94);
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[2] = -x146*(V{1}*cell[12]*x19 + x105 + x114 - x128 - x139 - x144 + x148 - x150 - x152 + x153 - x154 - x155 - V{1}*x77 - x80);
return { x25, V{1}*x26*(x35 + x42 + x49) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
