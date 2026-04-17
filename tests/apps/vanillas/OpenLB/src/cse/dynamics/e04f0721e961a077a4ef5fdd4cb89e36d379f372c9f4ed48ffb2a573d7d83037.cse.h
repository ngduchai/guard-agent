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
struct CSE<Dual<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Porous<momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq> >, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>, T, descriptors::D3Q19<FIELDS...> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x34 = cell.template getFieldComponent<olb::opti::DJDF>(8);
auto x42 = cell.template getFieldComponent<olb::opti::DJDF>(16);
auto x28 = cell.template getFieldComponent<olb::opti::DJDF>(2);
auto x58 = cell.template getFieldComponent<olb::opti::F>(13);
auto x51 = cell.template getFieldComponent<olb::opti::F>(6);
auto x49 = cell.template getFieldComponent<olb::opti::F>(4);
auto x55 = cell.template getFieldComponent<olb::opti::F>(10);
auto x37 = cell.template getFieldComponent<olb::opti::DJDF>(11);
auto x40 = cell.template getFieldComponent<olb::opti::DJDF>(14);
auto x44 = cell.template getFieldComponent<olb::opti::DJDF>(18);
auto x54 = cell.template getFieldComponent<olb::opti::F>(9);
auto x63 = cell.template getFieldComponent<olb::opti::F>(18);
auto x64 = parameters.template get<descriptors::OMEGA>();
auto x35 = cell.template getFieldComponent<olb::opti::DJDF>(9);
auto x46 = cell.template getFieldComponent<olb::opti::F>(1);
auto x33 = cell.template getFieldComponent<olb::opti::DJDF>(7);
auto x38 = cell.template getFieldComponent<olb::opti::DJDF>(12);
auto x27 = cell.template getFieldComponent<olb::opti::DJDF>(1);
auto x39 = cell.template getFieldComponent<olb::opti::DJDF>(13);
auto x61 = cell.template getFieldComponent<olb::opti::F>(16);
auto x52 = cell.template getFieldComponent<olb::opti::F>(7);
auto x56 = cell.template getFieldComponent<olb::opti::F>(11);
auto x41 = cell.template getFieldComponent<olb::opti::DJDF>(15);
auto x31 = cell.template getFieldComponent<olb::opti::DJDF>(5);
auto x26 = cell.template getFieldComponent<olb::opti::DJDF>(0);
auto x59 = cell.template getFieldComponent<olb::opti::F>(14);
auto x50 = cell.template getFieldComponent<olb::opti::F>(5);
auto x32 = cell.template getFieldComponent<olb::opti::DJDF>(6);
auto x57 = cell.template getFieldComponent<olb::opti::F>(12);
auto x36 = cell.template getFieldComponent<olb::opti::DJDF>(10);
auto x62 = cell.template getFieldComponent<olb::opti::F>(17);
auto x47 = cell.template getFieldComponent<olb::opti::F>(2);
auto x30 = cell.template getFieldComponent<olb::opti::DJDF>(4);
auto x53 = cell.template getFieldComponent<olb::opti::F>(8);
auto x22 = cell.template getFieldComponent<olb::descriptors::POROSITY>(0);
auto x60 = cell.template getFieldComponent<olb::opti::F>(15);
auto x48 = cell.template getFieldComponent<olb::opti::F>(3);
auto x45 = cell.template getFieldComponent<olb::opti::F>(0);
auto x29 = cell.template getFieldComponent<olb::opti::DJDF>(3);
auto x43 = cell.template getFieldComponent<olb::opti::DJDF>(17);
auto x19 = V{1}*x64 + V{-1};
auto x20 = V{0.0277777777777778}*x64;
auto x21 = x49 - x58;
auto x23 = x53 - x62;
auto x24 = x21 + x23;
auto x25 = x54 - x63;
auto x65 = -x56;
auto x66 = x47 - x50 + x59 + x65;
auto x67 = x24 + x25 + x66;
auto x68 = -x67;
auto x69 = x46 + x50;
auto x70 = x48 + x61;
auto x71 = x45 + x47 + x49 + x51 + x52 + x53 + x54 + x55 + x56 + x57 + x58 + x59 + x60 + x62 + x63 + x69 + x70;
auto x72 = x71 + V{1};
auto x73 = V{1} / (x72);
auto x74 = x22*x73;
auto x75 = V{3}*x74;
auto x76 = x68*x75;
auto x77 = V{1} / ((x72)*(x72));
auto x78 = V{4.5}*x77;
auto x79 = ((x22)*(x22));
auto x80 = x51 - x60;
auto x81 = -x54 + x63;
auto x82 = -x55;
auto x83 = x52 - x61;
auto x84 = x82 + x83;
auto x85 = x46 + x84;
auto x86 = -x53 + x62;
auto x87 = -x47 + V{2}*x50 + x56 - V{2}*x59 + x80 + x81 + x85 + x86;
auto x88 = -x87;
auto x89 = x21 + x80;
auto x90 = -x59 + x69;
auto x91 = x84 + x89 + x90;
auto x92 = -x91;
auto x93 = x75*x92;
auto x94 = V{1.5}*x77;
auto x95 = x79*((x92)*(x92));
auto x96 = x94*x95;
auto x97 = x79*((x68)*(x68));
auto x98 = x94*x97;
auto x99 = x23 + x80;
auto x100 = -x57;
auto x101 = x100 + x81;
auto x102 = -x52 + x70;
auto x103 = x101 + x102 + x99;
auto x104 = -x103;
auto x105 = x79*((x104)*(x104));
auto x106 = x105*x94;
auto x107 = x106 + x98 + V{-1};
auto x108 = x107 + x96;
auto x109 = x108 - x93;
auto x110 = x104*x75;
auto x111 = x82 + x90;
auto x112 = x21 - x48 + x57;
auto x113 = x111 + x112 + x25 + V{2}*x52 - V{2}*x61 + x86;
auto x114 = -x113;
auto x115 = x112 - x51 + V{2}*x54 + x60 - V{2}*x63 + x66 + x83;
auto x116 = -x115;
auto x117 = x108 - x76;
auto x118 = x25 + x47 + V{2}*x49 - V{2}*x58 + x65 + x85 + x99;
auto x119 = -x118;
auto x120 = x108 + x93;
auto x121 = x101 + x111 + x24 + x48 + V{2}*x51 - V{2}*x60;
auto x122 = -x121;
auto x123 = -x110;
auto x124 = x100 + x102 + V{2}*x53 - V{2}*x62 + x66 + x89;
auto x125 = -x124;
auto x126 = x108 + x76;
auto x127 = V{0.0555555555555556}*x64;
auto x128 = V{3}*x77;
auto x129 = x96 + V{-1};
auto x130 = ((x67)*(x67));
auto x131 = x130*x79*x94;
auto x132 = ((x103)*(x103));
auto x133 = x132*x79*x94 + V{-1};
auto x134 = x131 + x133;
auto x135 = x134 + x75*x91;
auto x136 = ((x91)*(x91));
auto x137 = x136*x79*x94;
auto x138 = x137 + x67*x75;
auto x139 = x103*x75;
auto x140 = x137 + x139;
auto x141 = x71 + V{1};
auto x142 = V{0.0833333333333333}*cell[4];
auto x143 = V{0.0833333333333333}*cell[6];
auto x144 = V{0.25}*x74;
auto x145 = x74*x91;
auto x146 = V{0.5}*cell[0] + V{0.0833333333333333}*cell[10] + V{0.0833333333333333}*cell[11] + V{0.0833333333333333}*cell[12] + V{0.0416666666666667}*cell[13] + V{0.0416666666666667}*cell[14] + V{0.0416666666666667}*cell[15] + V{0.0416666666666667}*cell[16] + V{0.0416666666666667}*cell[17] + V{0.0416666666666667}*cell[18] + V{0.0833333333333333}*cell[1] + V{0.0833333333333333}*cell[2] + V{0.0833333333333333}*cell[3] + V{0.0416666666666667}*cell[4] + V{0.0416666666666667}*cell[5] + V{0.0416666666666667}*cell[6] + V{0.0416666666666667}*cell[7] + V{0.0416666666666667}*cell[8] + V{0.0416666666666667}*cell[9];
auto x147 = cell[13]*x118*x144;
auto x148 = cell[15]*x121*x144;
auto x149 = V{0.5}*x145;
auto x150 = x144*x88;
auto x151 = cell[14]*x150 + V{0.0833333333333333}*cell[14] + cell[5]*x150 - V{0.0833333333333333}*cell[5];
auto x152 = x114*x144;
auto x153 = cell[16]*x152 + V{0.0833333333333333}*cell[16] + cell[7]*x152 - V{0.0833333333333333}*cell[7];
auto x154 = -cell[10]*x149 + V{0.166666666666667}*cell[10] + V{0.0833333333333333}*cell[13] + V{0.0833333333333333}*cell[15] - cell[1]*x149 - V{0.166666666666667}*cell[1] + cell[4]*x119*x144 + cell[6]*x122*x144 - x142 - x143 + V{2}*x145*x146 - x147 - x148 + x151 + x153;
auto x155 = V{0.0833333333333333}*cell[9];
auto x156 = V{0.0833333333333333}*cell[18];
auto x157 = V{0.5}*x67*x74;
auto x158 = x116*x144;
auto x159 = cell[18]*x158;
auto x160 = cell[9]*x158;
auto x161 = cell[17]*x124*x144 - V{0.0833333333333333}*cell[17] - V{0.25}*cell[8]*x125*x22*x73 + V{0.0833333333333333}*cell[8];
auto x162 = -cell[11]*x157 + V{0.166666666666667}*cell[11] + V{0.0833333333333333}*cell[13] - cell[2]*x157 - V{0.166666666666667}*cell[2] + V{0.25}*cell[4]*x119*x22*x73 - x142 + V{2}*x146*x22*x67*x73 - x147 - x151 - x155 + x156 + x159 + x160 - x161;
auto x163 = V{0.5}*x103*x74;
auto x164 = -cell[12]*x163 + V{0.166666666666667}*cell[12] + V{0.0833333333333333}*cell[15] - cell[3]*x163 - V{0.166666666666667}*cell[3] + V{0.25}*cell[6]*x122*x22*x73 + V{2}*x103*x146*x22*x73 - x143 - x148 - x153 + x155 - x156 - x159 - x160 - x161;
auto x165 = V{0.333333333333333}*cell[0]*x108*x64 - V{0.0555555555555556}*cell[10]*x64*(-x135 + V{3}*x136*x77*x79) - V{0.0555555555555556}*cell[11]*x64*(V{3}*x130*x77*x79 - x133 - x138) - V{0.0555555555555556}*cell[12]*x64*(-x131 + V{3}*x132*x77*x79 - x140 + V{1}) + V{0.0277777777777778}*cell[13]*x64*(x135 + x138 - V{4.5}*x77*x79*((x118)*(x118))) + cell[14]*x20*(x109 + x76 - x78*x79*((x88)*(x88))) + V{0.0277777777777778}*cell[15]*x64*(x135 + x140 - V{4.5}*x77*x79*((x121)*(x121))) + cell[16]*x20*(x109 + x110 - x78*x79*((x114)*(x114))) + V{0.0277777777777778}*cell[17]*x64*(x134 + x138 + x139 - V{4.5}*x77*x79*((x124)*(x124))) + cell[18]*x20*(x110 + x117 - x78*x79*((x116)*(x116))) + cell[1]*x127*(x107 - x128*x95 + x93) + cell[2]*x127*(x106 - x128*x97 + x129 + x76) + cell[3]*x127*(-x105*x128 + x110 + x129 + x98) + cell[4]*x20*(x120 + x76 - x78*x79*((x119)*(x119))) + cell[5]*x20*(x117 - x78*x79*((x87)*(x87)) + x93) + cell[6]*x20*(x110 + x120 - x78*x79*((x122)*(x122))) + cell[7]*x20*(x120 + x123 - x78*x79*((x113)*(x113))) + cell[8]*x20*(x110 + x126 - x78*x79*((x125)*(x125))) + cell[9]*x20*(x123 + x126 - x78*x79*((x115)*(x115))) - V{1}*x103*x141*x164*x22*x64*x77 - V{1}*x141*x154*x22*x64*x77*x91 - V{1}*x141*x162*x22*x64*x67*x77;
auto x166 = cell[0]*x19 + x165 + x26;
auto x167 = V{1}*x141*x64*x74;
auto x168 = x154*x167;
auto x169 = x165 + x168;
auto x170 = cell[1]*x19 + x169 + x27;
auto x171 = x162*x167;
auto x172 = x165 + x171;
auto x173 = cell[2]*x19 + x172 + x28;
auto x174 = x164*x167;
auto x175 = x165 + x174;
auto x176 = cell[3]*x19 + x175 + x29;
auto x177 = cell[4]*x19 + x169 + x171 + x30;
auto x178 = -x171;
auto x179 = cell[5]*x19 + x169 + x178 + x31;
auto x180 = cell[6]*x19 + x169 + x174 + x32;
auto x181 = -x174;
auto x182 = cell[7]*x19 + x169 + x181 + x33;
auto x183 = cell[8]*x19 + x172 + x174 + x34;
auto x184 = cell[9]*x19 + x172 + x181 + x35;
auto x185 = -x168;
auto x186 = x165 + x185;
auto x187 = cell[10]*x19 + x186 + x36;
auto x188 = x165 + x178;
auto x189 = cell[11]*x19 + x188 + x37;
auto x190 = cell[12]*x19 + x165 + x181 + x38;
auto x191 = cell[13]*x19 + x178 + x186 + x39;
auto x192 = cell[14]*x19 + x172 + x185 + x40;
auto x193 = cell[15]*x19 + x181 + x186 + x41;
auto x194 = cell[16]*x19 + x175 + x185 + x42;
auto x195 = cell[17]*x19 + x181 + x188 + x43;
auto x196 = cell[18]*x19 + x175 + x178 + x44;
cell[0] = -x166;
cell[1] = -x170;
cell[2] = -x173;
cell[3] = -x176;
cell[4] = -x177;
cell[5] = -x179;
cell[6] = -x180;
cell[7] = -x182;
cell[8] = -x183;
cell[9] = -x184;
cell[10] = -x187;
cell[11] = -x189;
cell[12] = -x190;
cell[13] = -x191;
cell[14] = -x192;
cell[15] = -x193;
cell[16] = -x194;
cell[17] = -x195;
cell[18] = -x196;
return { V{1} - x166, ((x166)*(x166)) + ((x170)*(x170)) + ((x173)*(x173)) + ((x176)*(x176)) + ((x177)*(x177)) + ((x179)*(x179)) + ((x180)*(x180)) + ((x182)*(x182)) + ((x183)*(x183)) + ((x184)*(x184)) + ((x187)*(x187)) + ((x189)*(x189)) + ((x190)*(x190)) + ((x191)*(x191)) + ((x192)*(x192)) + ((x193)*(x193)) + ((x194)*(x194)) + ((x195)*(x195)) + ((x196)*(x196)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
