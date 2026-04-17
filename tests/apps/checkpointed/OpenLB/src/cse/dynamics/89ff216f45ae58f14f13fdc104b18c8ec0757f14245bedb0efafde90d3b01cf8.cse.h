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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, forcing::ScaledPlainGuo>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x21 = cell.template getFieldComponent<olb::descriptors::FORCE>(2);
auto x23 = parameters.template get<descriptors::OMEGA>();
auto x20 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x22 = cell.template getFieldComponent<olb::descriptors::SCALAR>(0);
auto x24 = x23 + V{-1};
auto x25 = cell[0] + cell[10] + cell[11] + cell[12] + cell[13] + cell[14] + cell[15] + cell[16] + cell[17] + cell[18] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8] + cell[9];
auto x26 = x25 + V{1};
auto x27 = x25 + V{1};
auto x28 = V{1} / (x27);
auto x29 = V{1}*cell[14];
auto x30 = V{1}*cell[16];
auto x31 = V{1}*cell[5];
auto x32 = V{1}*cell[7];
auto x33 = V{1}*cell[13] - V{1}*cell[4];
auto x34 = V{1}*cell[15] - V{1}*cell[6];
auto x35 = V{0.5}*x19 + x28*(V{1}*cell[10] - V{1}*cell[1] + x29 + x30 - x31 - x32 + x33 + x34);
auto x36 = ((x35)*(x35));
auto x37 = V{1.5}*x36;
auto x38 = V{0.5}*x20;
auto x39 = V{1}*cell[18];
auto x40 = V{1}*cell[9];
auto x41 = V{1}*cell[17] - V{1}*cell[8];
auto x42 = x28*(V{1}*cell[11] - V{1}*cell[2] - x29 + x31 + x33 + x39 - x40 + x41);
auto x43 = x38 + x42;
auto x44 = ((x43)*(x43));
auto x45 = V{1.5}*x44;
auto x46 = V{1}*cell[12] - V{1}*cell[3] - x30 + x32 + x34 - x39 + x40 + x41;
auto x47 = V{0.5}*x21 + x28*x46;
auto x48 = ((x47)*(x47));
auto x49 = V{1.5}*x48;
auto x50 = x37 + x45 + x49 + V{-1};
auto x51 = V{0.5}*x23 + V{-1};
auto x52 = V{1.5}*x19;
auto x53 = V{3}*cell[14];
auto x54 = V{3}*cell[16];
auto x55 = V{3}*cell[5];
auto x56 = V{3}*cell[7];
auto x57 = V{3}*cell[13] - V{3}*cell[4];
auto x58 = V{3}*cell[15] - V{3}*cell[6];
auto x59 = x28*(V{3}*cell[10] - V{3}*cell[1] + x53 + x54 - x55 - x56 + x57 + x58);
auto x60 = x52 + x59;
auto x61 = x19*x60;
auto x62 = V{1.5}*x20;
auto x63 = V{3}*cell[18];
auto x64 = V{3}*cell[9];
auto x65 = V{3}*cell[17] - V{3}*cell[8];
auto x66 = x28*(V{3}*cell[11] - V{3}*cell[2] - x53 + x55 + x57 + x63 - x64 + x65);
auto x67 = x62 + x66;
auto x68 = x20*x67;
auto x69 = V{1.5}*x21;
auto x70 = x28*(V{3}*cell[12] - V{3}*cell[3] - x54 + x56 + x58 - x63 + x64 + x65);
auto x71 = x69 + x70;
auto x72 = x21*x71;
auto x73 = x68 + x72;
auto x74 = V{0.0555555555555556}*x23;
auto x75 = V{4.5}*cell[14];
auto x76 = V{4.5}*cell[16];
auto x77 = V{4.5}*cell[5];
auto x78 = V{4.5}*cell[7];
auto x79 = V{4.5}*cell[13] - V{4.5}*cell[4];
auto x80 = V{4.5}*cell[15] - V{4.5}*cell[6];
auto x81 = V{2.25}*x19 + x28*(V{4.5}*cell[10] - V{4.5}*cell[1] + x75 + x76 - x77 - x78 + x79 + x80);
auto x82 = x35*x81;
auto x83 = x50 + x60;
auto x84 = V{3}*x19;
auto x85 = V{6}*cell[14];
auto x86 = V{6}*cell[16];
auto x87 = V{6}*cell[5];
auto x88 = V{6}*cell[7];
auto x89 = V{6}*cell[13] - V{6}*cell[4];
auto x90 = V{6}*cell[15] - V{6}*cell[6];
auto x91 = x28*(V{6}*cell[10] - V{6}*cell[1] + x85 + x86 - x87 - x88 + x89 + x90);
auto x92 = x84 + x91;
auto x93 = x92 + V{-3};
auto x94 = x22*x27*x51;
auto x95 = V{0.0555555555555556}*x94;
auto x96 = V{2.25}*x20;
auto x97 = V{4.5}*cell[18];
auto x98 = V{4.5}*cell[9];
auto x99 = V{4.5}*cell[17] - V{4.5}*cell[8];
auto x100 = x28*(V{4.5}*cell[11] - V{4.5}*cell[2] - x75 + x77 + x79 + x97 - x98 + x99);
auto x101 = x100 + x96;
auto x102 = x101*x43;
auto x103 = x50 + x67;
auto x104 = V{3}*x20;
auto x105 = V{6}*cell[18];
auto x106 = V{6}*cell[9];
auto x107 = V{6}*cell[17] - V{6}*cell[8];
auto x108 = x28*(V{6}*cell[11] - V{6}*cell[2] + x105 - x106 + x107 - x85 + x87 + x89);
auto x109 = x104 + x108;
auto x110 = x109 + V{-3};
auto x111 = x61 + x72;
auto x112 = V{4.5}*cell[12] - V{4.5}*cell[3] - x76 + x78 + x80 - x97 + x98 + x99;
auto x113 = x112*x28 + V{2.25}*x21;
auto x114 = x113*x47;
auto x115 = x50 + x71;
auto x116 = V{3}*x21;
auto x117 = x28*(V{6}*cell[12] - V{6}*cell[3] - x105 + x106 + x107 - x86 + x88 + x90);
auto x118 = x116 + x117;
auto x119 = x118 + V{-3};
auto x120 = x61 + x68;
auto x121 = V{0.0277777777777778}*x23;
auto x122 = (x101 + x81)*(x35 + x43);
auto x123 = V{4.5}*x20;
auto x124 = V{9}*cell[18];
auto x125 = V{9}*cell[5];
auto x126 = V{9}*cell[14];
auto x127 = V{9}*cell[9];
auto x128 = V{9}*cell[13] - V{9}*cell[4];
auto x129 = V{9}*cell[17] - V{9}*cell[8];
auto x130 = x28*(V{9}*cell[11] - V{9}*cell[2] + x124 + x125 - x126 - x127 + x128 + x129);
auto x131 = x123 + x130;
auto x132 = V{4.5}*x19;
auto x133 = V{9}*cell[16];
auto x134 = V{9}*cell[7];
auto x135 = V{9}*cell[15] - V{9}*cell[6];
auto x136 = x28*(V{9}*cell[10] - V{9}*cell[1] - x125 + x126 + x128 + x133 - x134 + x135);
auto x137 = x132 + x136;
auto x138 = -x72;
auto x139 = V{0.0277777777777778}*x94;
auto x140 = x35 - x38 - x42;
auto x141 = -x100 + x81 - x96;
auto x142 = -x62 - x66;
auto x143 = x131 + V{3};
auto x144 = -x84 - x91;
auto x145 = x109 + V{3};
auto x146 = -x132 - x136;
auto x147 = (x113 + x81)*(x35 + x47);
auto x148 = V{4.5}*x21;
auto x149 = x28*(V{9}*cell[12] - V{9}*cell[3] - x124 + x127 + x129 - x133 + x134 + x135);
auto x150 = x148 + x149;
auto x151 = -x68;
auto x152 = -V{0.5}*x21 - x28*x46;
auto x153 = x152 + x35;
auto x154 = -x112*x28 - V{2.25}*x21;
auto x155 = x154 + x81;
auto x156 = -x69 - x70;
auto x157 = x150 + V{3};
auto x158 = x118 + V{3};
auto x159 = (x101 + x113)*(x43 + x47);
auto x160 = -x61;
auto x161 = x152 + x43;
auto x162 = x101 + x154;
auto x163 = -x104 - x108;
auto x164 = -x123 - x130;
auto x165 = -x37 - x45 - x49 + V{1};
auto x166 = x165 + x60;
auto x167 = x92 + V{3};
auto x168 = x165 + x67;
auto x169 = -x52 - x59;
auto x170 = x137 + V{3};
auto x171 = -x116 - x117;
auto x172 = -x148 - x149;
auto x0 = -cell[0]*x24 + V{0.333333333333333}*x22*x27*x51*(x61 + x73) - V{0.333333333333333}*x23*(x26*x50 + V{1});
auto x1 = -cell[1]*x24 - x74*(x26*(-x82 + x83) + V{1}) - x95*(x19*x93 - x73);
auto x2 = -cell[2]*x24 - x74*(x26*(-x102 + x103) + V{1}) - x95*(x110*x20 - x111);
auto x3 = -cell[3]*x24 - x74*(x26*(-x114 + x115) + V{1}) - x95*(x119*x21 - x120);
auto x4 = -cell[4]*x24 - x121*(x26*(-x122 + x67 + x83) + V{1}) - x139*(x138 + x19*(x131 + x93) + x20*(x110 + x137));
auto x5 = -cell[5]*x24 - x121*(x26*(-x140*x141 + x142 + x83) + V{1}) - x139*(-x19*(x143 + x144) + x20*(x145 + x146) - x72);
auto x6 = -cell[6]*x24 - x121*(x26*(-x147 + x71 + x83) + V{1}) - x139*(x151 + x19*(x150 + x93) + x21*(x119 + x137));
auto x7 = -cell[7]*x24 - x121*(x26*(-x153*x155 + x156 + x83) + V{1}) - x139*(-x19*(x144 + x157) + x21*(x146 + x158) - x68);
auto x8 = -cell[8]*x24 - x121*(x26*(x103 - x159 + x71) + V{1}) - x139*(x160 + x20*(x110 + x150) + x21*(x119 + x131));
auto x9 = -cell[9]*x24 - x121*(x26*(x103 + x156 - x161*x162) + V{1}) - x139*(-x20*(x157 + x163) + x21*(x158 + x164) - x61);
auto x10 = -cell[10]*x24 + V{0.0555555555555556}*x23*(x26*(x166 + x82) + V{-1}) - x95*(x167*x19 - x73);
auto x11 = -cell[11]*x24 + V{0.0555555555555556}*x23*(x26*(x102 + x168) + V{-1}) - x95*(-x111 + x145*x20);
auto x12 = -cell[12]*x24 + V{0.0555555555555556}*x23*(x26*(x114 + x165 + x71) + V{-1}) - x95*(-x120 + x158*x21);
auto x13 = -cell[13]*x24 - x139*(x138 + x19*(x131 + x167) + x20*(x137 + x145)) + V{0.0277777777777778}*x23*(x26*(x122 + x166 + x67) + V{-1});
auto x14 = -cell[14]*x24 - x121*(x26*(x103 - x140*x141 + x169) + V{1}) - x139*(x19*(x164 + x167) - x20*(x163 + x170) - x72);
auto x15 = -cell[15]*x24 - x139*(x151 + x19*(x150 + x167) + x21*(x137 + x158)) + V{0.0277777777777778}*x23*(x26*(x147 + x166 + x71) + V{-1});
auto x16 = -cell[16]*x24 - x121*(x26*(x115 - x153*x155 + x169) + V{1}) - x139*(x19*(x167 + x172) - x21*(x170 + x171) - x68);
auto x17 = -cell[17]*x24 - x139*(x160 + x20*(x145 + x150) + x21*(x131 + x158)) + V{0.0277777777777778}*x23*(x26*(x159 + x168 + x71) + V{-1});
auto x18 = -cell[18]*x24 - x121*(x26*(x115 + x142 - x161*x162) + V{1}) - x139*(x20*(x145 + x172) - x21*(x143 + x171) - x61);
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
return { x27, x36 + x44 + x48 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
