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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, forcing::Guo<momenta::ForcedWithStress> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x20 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x21 = cell.template getFieldComponent<olb::descriptors::FORCE>(2);
auto x22 = parameters.template get<descriptors::OMEGA>();
auto x23 = x22 + V{-1};
auto x24 = V{0.5}*x22 + V{-1};
auto x25 = cell[0] + cell[10] + cell[11] + cell[12] + cell[13] + cell[14] + cell[15] + cell[16] + cell[17] + cell[18] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8] + cell[9];
auto x26 = x25 + V{1};
auto x27 = V{1.5}*x19;
auto x28 = V{1} / (x26);
auto x29 = V{3}*cell[14];
auto x30 = V{3}*cell[16];
auto x31 = V{3}*cell[5];
auto x32 = V{3}*cell[7];
auto x33 = V{3}*cell[13] - V{3}*cell[4];
auto x34 = V{3}*cell[15] - V{3}*cell[6];
auto x35 = x28*(V{3}*cell[10] - V{3}*cell[1] + x29 + x30 - x31 - x32 + x33 + x34);
auto x36 = x27 + x35;
auto x37 = x19*x36;
auto x38 = V{1.5}*x20;
auto x39 = V{3}*cell[18];
auto x40 = V{3}*cell[9];
auto x41 = V{3}*cell[17] - V{3}*cell[8];
auto x42 = x28*(V{3}*cell[11] - V{3}*cell[2] - x29 + x31 + x33 + x39 - x40 + x41);
auto x43 = x38 + x42;
auto x44 = x20*x43;
auto x45 = V{1.5}*x21;
auto x46 = x28*(V{3}*cell[12] - V{3}*cell[3] - x30 + x32 + x34 - x39 + x40 + x41);
auto x47 = x45 + x46;
auto x48 = x21*x47;
auto x49 = x44 + x48;
auto x50 = x25 + V{1};
auto x51 = V{1}*cell[14];
auto x52 = V{1}*cell[16];
auto x53 = V{1}*cell[5];
auto x54 = V{1}*cell[7];
auto x55 = V{1}*cell[13] - V{1}*cell[4];
auto x56 = V{1}*cell[15] - V{1}*cell[6];
auto x57 = V{0.5}*x19 + x28*(V{1}*cell[10] - V{1}*cell[1] + x51 + x52 - x53 - x54 + x55 + x56);
auto x58 = ((x57)*(x57));
auto x59 = V{1.5}*x58;
auto x60 = V{0.5}*x20;
auto x61 = V{1}*cell[18];
auto x62 = V{1}*cell[9];
auto x63 = V{1}*cell[17] - V{1}*cell[8];
auto x64 = x28*(V{1}*cell[11] - V{1}*cell[2] - x51 + x53 + x55 + x61 - x62 + x63);
auto x65 = x60 + x64;
auto x66 = ((x65)*(x65));
auto x67 = V{1.5}*x66;
auto x68 = V{0.5}*x21;
auto x69 = x28*(V{1}*cell[12] - V{1}*cell[3] - x52 + x54 + x56 - x61 + x62 + x63);
auto x70 = x68 + x69;
auto x71 = ((x70)*(x70));
auto x72 = V{1.5}*x71;
auto x73 = x59 + x67 + x72 + V{-1};
auto x74 = V{3}*x19;
auto x75 = V{6}*cell[14];
auto x76 = V{6}*cell[16];
auto x77 = V{6}*cell[5];
auto x78 = V{6}*cell[7];
auto x79 = V{6}*cell[13] - V{6}*cell[4];
auto x80 = V{6}*cell[15] - V{6}*cell[6];
auto x81 = x28*(V{6}*cell[10] - V{6}*cell[1] + x75 + x76 - x77 - x78 + x79 + x80);
auto x82 = x74 + x81;
auto x83 = x82 + V{3};
auto x84 = x24*x26;
auto x85 = V{0.0555555555555556}*x84;
auto x86 = V{4.5}*cell[14];
auto x87 = V{4.5}*cell[16];
auto x88 = V{4.5}*cell[5];
auto x89 = V{4.5}*cell[7];
auto x90 = V{4.5}*cell[13] - V{4.5}*cell[4];
auto x91 = V{4.5}*cell[15] - V{4.5}*cell[6];
auto x92 = V{2.25}*x19 + x28*(V{4.5}*cell[10] - V{4.5}*cell[1] + x86 + x87 - x88 - x89 + x90 + x91);
auto x93 = x57*x92;
auto x94 = -x59 - x67 - x72 + V{1};
auto x95 = x36 + x94;
auto x96 = V{3}*x20;
auto x97 = V{6}*cell[18];
auto x98 = V{6}*cell[9];
auto x99 = V{6}*cell[17] - V{6}*cell[8];
auto x100 = x28*(V{6}*cell[11] - V{6}*cell[2] - x75 + x77 + x79 + x97 - x98 + x99);
auto x101 = x100 + x96;
auto x102 = x101 + V{3};
auto x103 = x37 + x48;
auto x104 = V{2.25}*x20;
auto x105 = V{4.5}*cell[18];
auto x106 = V{4.5}*cell[9];
auto x107 = V{4.5}*cell[17] - V{4.5}*cell[8];
auto x108 = x28*(V{4.5}*cell[11] - V{4.5}*cell[2] + x105 - x106 + x107 - x86 + x88 + x90);
auto x109 = x104 + x108;
auto x110 = x109*x65;
auto x111 = x43 + x94;
auto x112 = V{3}*x21;
auto x113 = x28*(V{6}*cell[12] - V{6}*cell[3] - x76 + x78 + x80 - x97 + x98 + x99);
auto x114 = x112 + x113;
auto x115 = x114 + V{3};
auto x116 = x37 + x44;
auto x117 = V{2.25}*x21;
auto x118 = x28*(V{4.5}*cell[12] - V{4.5}*cell[3] - x105 + x106 + x107 - x87 + x89 + x91);
auto x119 = x117 + x118;
auto x120 = x119*x70;
auto x121 = -x48;
auto x122 = V{4.5}*x20;
auto x123 = V{9}*cell[18];
auto x124 = V{9}*cell[5];
auto x125 = V{9}*cell[14];
auto x126 = V{9}*cell[9];
auto x127 = V{9}*cell[13] - V{9}*cell[4];
auto x128 = V{9}*cell[17] - V{9}*cell[8];
auto x129 = x28*(V{9}*cell[11] - V{9}*cell[2] + x123 + x124 - x125 - x126 + x127 + x128);
auto x130 = x122 + x129;
auto x131 = V{4.5}*x19;
auto x132 = V{9}*cell[16];
auto x133 = V{9}*cell[7];
auto x134 = V{9}*cell[15] - V{9}*cell[6];
auto x135 = x28*(V{9}*cell[10] - V{9}*cell[1] - x124 + x125 + x127 + x132 - x133 + x134);
auto x136 = x131 + x135;
auto x137 = V{0.0277777777777778}*x84;
auto x138 = (x109 + x92)*(x57 + x65);
auto x139 = x136 + V{3};
auto x140 = -x100 - x96;
auto x141 = -x122 - x129;
auto x142 = V{0.0277777777777778}*x22;
auto x143 = x57 - x60 - x64;
auto x144 = -x104 - x108 + x92;
auto x145 = x43 + x73;
auto x146 = -x27 - x35;
auto x147 = -x44;
auto x148 = V{4.5}*x21;
auto x149 = x28*(V{9}*cell[12] - V{9}*cell[3] - x123 + x126 + x128 - x132 + x133 + x134);
auto x150 = x148 + x149;
auto x151 = (x119 + x92)*(x57 + x70);
auto x152 = -x112 - x113;
auto x153 = -x148 - x149;
auto x154 = -x68 - x69;
auto x155 = x154 + x57;
auto x156 = -x117 - x118;
auto x157 = x156 + x92;
auto x158 = x47 + x73;
auto x159 = -x37;
auto x160 = (x109 + x119)*(x65 + x70);
auto x161 = x130 + V{3};
auto x162 = x154 + x65;
auto x163 = x109 + x156;
auto x164 = -x38 - x42;
auto x165 = x82 + V{-3};
auto x166 = V{0.0555555555555556}*x22;
auto x167 = x36 + x73;
auto x168 = x101 + V{-3};
auto x169 = x114 + V{-3};
auto x170 = -x74 - x81;
auto x171 = -x131 - x135;
auto x172 = x150 + V{3};
auto x173 = -x45 - x46;
auto x0 = -cell[0]*x23 - V{0.333333333333333}*x22*(x50*x73 + V{1}) + V{0.333333333333333}*x24*x26*(x37 + x49);
auto x1 = -cell[10]*x23 + V{0.0555555555555556}*x22*(x50*(x93 + x95) + V{-1}) - x85*(x19*x83 - x49);
auto x2 = -cell[11]*x23 + V{0.0555555555555556}*x22*(x50*(x110 + x111) + V{-1}) - x85*(x102*x20 - x103);
auto x3 = -cell[12]*x23 + V{0.0555555555555556}*x22*(x50*(x120 + x47 + x94) + V{-1}) - x85*(x115*x21 - x116);
auto x4 = -cell[13]*x23 - x137*(x121 + x19*(x130 + x83) + x20*(x102 + x136)) + V{0.0277777777777778}*x22*(x50*(x138 + x43 + x95) + V{-1});
auto x5 = -cell[14]*x23 - x137*(x19*(x141 + x83) - x20*(x139 + x140) - x48) - x142*(x50*(-x143*x144 + x145 + x146) + V{1});
auto x6 = -cell[15]*x23 - x137*(x147 + x19*(x150 + x83) + x21*(x115 + x136)) + V{0.0277777777777778}*x22*(x50*(x151 + x47 + x95) + V{-1});
auto x7 = -cell[16]*x23 - x137*(x19*(x153 + x83) - x21*(x139 + x152) - x44) - x142*(x50*(x146 - x155*x157 + x158) + V{1});
auto x8 = -cell[17]*x23 - x137*(x159 + x20*(x102 + x150) + x21*(x115 + x130)) + V{0.0277777777777778}*x22*(x50*(x111 + x160 + x47) + V{-1});
auto x9 = -cell[18]*x23 - x137*(x20*(x102 + x153) - x21*(x152 + x161) - x37) - x142*(x50*(x158 - x162*x163 + x164) + V{1});
auto x10 = -cell[1]*x23 - x166*(x50*(x167 - x93) + V{1}) - x85*(x165*x19 - x49);
auto x11 = -cell[2]*x23 - x166*(x50*(-x110 + x145) + V{1}) - x85*(-x103 + x168*x20);
auto x12 = -cell[3]*x23 - x166*(x50*(-x120 + x158) + V{1}) - x85*(-x116 + x169*x21);
auto x13 = -cell[4]*x23 - x137*(x121 + x19*(x130 + x165) + x20*(x136 + x168)) - x142*(x50*(-x138 + x167 + x43) + V{1});
auto x14 = -cell[5]*x23 - x137*(-x19*(x161 + x170) + x20*(x102 + x171) - x48) - x142*(x50*(-x143*x144 + x164 + x167) + V{1});
auto x15 = -cell[6]*x23 - x137*(x147 + x19*(x150 + x165) + x21*(x136 + x169)) - x142*(x50*(-x151 + x167 + x47) + V{1});
auto x16 = -cell[7]*x23 - x137*(-x19*(x170 + x172) + x21*(x115 + x171) - x44) - x142*(x50*(-x155*x157 + x167 + x173) + V{1});
auto x17 = -cell[8]*x23 - x137*(x159 + x20*(x150 + x168) + x21*(x130 + x169)) - x142*(x50*(x145 - x160 + x47) + V{1});
auto x18 = -cell[9]*x23 - x137*(-x20*(x140 + x172) + x21*(x115 + x141) - x37) - x142*(x50*(x145 - x162*x163 + x173) + V{1});
cell[0] = x0;
cell[10] = x1;
cell[11] = x2;
cell[12] = x3;
cell[13] = x4;
cell[14] = x5;
cell[15] = x6;
cell[16] = x7;
cell[17] = x8;
cell[18] = x9;
cell[1] = x10;
cell[2] = x11;
cell[3] = x12;
cell[4] = x13;
cell[5] = x14;
cell[6] = x15;
cell[7] = x16;
cell[8] = x17;
cell[9] = x18;
return { x26, x58 + x66 + x71 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
