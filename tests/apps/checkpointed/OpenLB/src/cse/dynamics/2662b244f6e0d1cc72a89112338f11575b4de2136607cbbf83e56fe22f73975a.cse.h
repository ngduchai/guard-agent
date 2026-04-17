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
struct CSE<Dual<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Porous<momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq> >, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x22 = cell.template getFieldComponent<olb::descriptors::POROSITY>(0);
auto x26 = cell.template getFieldComponent<olb::opti::DJDF>(0);
auto x27 = cell.template getFieldComponent<olb::opti::DJDF>(1);
auto x28 = cell.template getFieldComponent<olb::opti::DJDF>(10);
auto x29 = cell.template getFieldComponent<olb::opti::DJDF>(11);
auto x30 = cell.template getFieldComponent<olb::opti::DJDF>(12);
auto x31 = cell.template getFieldComponent<olb::opti::DJDF>(13);
auto x32 = cell.template getFieldComponent<olb::opti::DJDF>(14);
auto x33 = cell.template getFieldComponent<olb::opti::DJDF>(15);
auto x34 = cell.template getFieldComponent<olb::opti::DJDF>(16);
auto x35 = cell.template getFieldComponent<olb::opti::DJDF>(17);
auto x36 = cell.template getFieldComponent<olb::opti::DJDF>(18);
auto x37 = cell.template getFieldComponent<olb::opti::DJDF>(2);
auto x38 = cell.template getFieldComponent<olb::opti::DJDF>(3);
auto x39 = cell.template getFieldComponent<olb::opti::DJDF>(4);
auto x40 = cell.template getFieldComponent<olb::opti::DJDF>(5);
auto x41 = cell.template getFieldComponent<olb::opti::DJDF>(6);
auto x42 = cell.template getFieldComponent<olb::opti::DJDF>(7);
auto x43 = cell.template getFieldComponent<olb::opti::DJDF>(8);
auto x44 = cell.template getFieldComponent<olb::opti::DJDF>(9);
auto x45 = cell.template getFieldComponent<olb::opti::F>(0);
auto x46 = cell.template getFieldComponent<olb::opti::F>(1);
auto x47 = cell.template getFieldComponent<olb::opti::F>(10);
auto x48 = cell.template getFieldComponent<olb::opti::F>(11);
auto x49 = cell.template getFieldComponent<olb::opti::F>(12);
auto x50 = cell.template getFieldComponent<olb::opti::F>(13);
auto x51 = cell.template getFieldComponent<olb::opti::F>(14);
auto x52 = cell.template getFieldComponent<olb::opti::F>(15);
auto x53 = cell.template getFieldComponent<olb::opti::F>(16);
auto x54 = cell.template getFieldComponent<olb::opti::F>(17);
auto x55 = cell.template getFieldComponent<olb::opti::F>(18);
auto x56 = cell.template getFieldComponent<olb::opti::F>(2);
auto x57 = cell.template getFieldComponent<olb::opti::F>(3);
auto x58 = cell.template getFieldComponent<olb::opti::F>(4);
auto x59 = cell.template getFieldComponent<olb::opti::F>(5);
auto x60 = cell.template getFieldComponent<olb::opti::F>(6);
auto x61 = cell.template getFieldComponent<olb::opti::F>(7);
auto x62 = cell.template getFieldComponent<olb::opti::F>(8);
auto x63 = cell.template getFieldComponent<olb::opti::F>(9);
auto x64 = parameters.template get<descriptors::OMEGA>();
auto x19 = V{1}*x64 + V{-1};
auto x20 = V{0.0277777777777778}*x64;
auto x21 = x54 - x62;
auto x23 = -x63;
auto x24 = -x51 + x59;
auto x25 = x23 + x24 + x55;
auto x65 = -x56;
auto x66 = x48 + x50;
auto x67 = -x58 + x65 + x66;
auto x68 = x21 + x25 + x67;
auto x69 = x49 + x52;
auto x70 = x45 + x46 + x47 + x51 + x53 + x54 + x55 + x56 + x57 + x58 + x59 + x60 + x61 + x62 + x63 + x66 + x69;
auto x71 = x70 + V{1};
auto x72 = x22/x71;
auto x73 = V{3}*x72;
auto x74 = x68*x73;
auto x75 = V{1} / ((x71)*(x71));
auto x76 = V{4.5}*x75;
auto x77 = ((x22)*(x22));
auto x78 = -x53 + x61;
auto x79 = x21 + x78;
auto x80 = -x47;
auto x81 = -x52 + x60;
auto x82 = x46 + x80 + x81;
auto x83 = x23 + x48 - V{2}*x51 + x55 + V{2}*x59 + x65 + x79 + x82;
auto x84 = -x83;
auto x85 = x24 + x78;
auto x86 = x46 - x50 + x58 + x80;
auto x87 = x81 + x85 + x86;
auto x88 = -x87;
auto x89 = x73*x88;
auto x90 = V{1.5}*x75;
auto x91 = x77*((x88)*(x88));
auto x92 = x90*x91;
auto x93 = x77*((x68)*(x68));
auto x94 = x90*x93;
auto x95 = -x55 + x63;
auto x96 = -x57;
auto x97 = -x60 + x69 + x96;
auto x98 = x79 + x95 + x97;
auto x99 = x77*((x98)*(x98));
auto x100 = x90*x99;
auto x101 = x100 + x94 + V{-1};
auto x102 = x101 + x92;
auto x103 = x102 - x89;
auto x104 = x73*x98;
auto x105 = x21 + x24 + x49 - V{2}*x53 + V{2}*x61 + x86 + x95 + x96;
auto x106 = -x105;
auto x107 = -x49 + x57;
auto x108 = x107 + x24 + x53 + V{2}*x55 - x61 - V{2}*x63 + x67 + x81;
auto x109 = -x74;
auto x110 = x102 + x109;
auto x111 = -x54 + x62;
auto x112 = -x111 + x48 + V{2}*x50 - x56 - V{2}*x58 - x78 - x82 - x95;
auto x113 = -x76*x77*((x112)*(x112));
auto x114 = x102 + x89;
auto x115 = -x107 - x111 - x25 + V{2}*x52 - V{2}*x60 - x86;
auto x116 = -x76*x77*((x115)*(x115));
auto x117 = -x104;
auto x118 = V{2}*x54 - V{2}*x62 + x67 + x85 + x97;
auto x119 = x76*x77*((x118)*(x118));
auto x120 = x102 + x74;
auto x121 = V{0.0555555555555556}*x64;
auto x122 = V{3}*x75;
auto x123 = x122*x93;
auto x124 = x92 + V{-1};
auto x125 = x122*x99;
auto x126 = ((x87)*(x87));
auto x127 = x126*x77*x90;
auto x128 = x101 + x73*x87;
auto x129 = x127 + x128;
auto x130 = V{1} - x127;
auto x131 = -x100 + x130 + x74;
auto x132 = x104 - x94;
auto x133 = V{0.0833333333333333}*cell[18];
auto x134 = V{0.0833333333333333}*cell[5];
auto x135 = V{0.0833333333333333}*cell[14];
auto x136 = V{0.0833333333333333}*cell[9];
auto x137 = V{0.25}*x72;
auto x138 = cell[14]*x137*x83;
auto x139 = x108*x137;
auto x140 = cell[18]*x139;
auto x141 = cell[9]*x139;
auto x142 = x68*x72;
auto x143 = V{0.5}*x142;
auto x144 = cell[5]*x137*x84;
auto x145 = V{1}*cell[0] + V{0.166666666666667}*cell[10] + V{0.166666666666667}*cell[11] + V{0.166666666666667}*cell[12] + V{0.0833333333333333}*cell[13] + V{0.0833333333333333}*cell[14] + V{0.0833333333333333}*cell[15] + V{0.0833333333333333}*cell[16] + V{0.0833333333333333}*cell[17] + V{0.0833333333333333}*cell[18] + V{0.166666666666667}*cell[1] + V{0.166666666666667}*cell[2] + V{0.166666666666667}*cell[3] + V{0.0833333333333333}*cell[4] + V{0.0833333333333333}*cell[5] + V{0.0833333333333333}*cell[6] + V{0.0833333333333333}*cell[7] + V{0.0833333333333333}*cell[8] + V{0.0833333333333333}*cell[9];
auto x146 = x112*x137;
auto x147 = cell[13]*x146 + V{0.0833333333333333}*cell[13] + cell[4]*x146 - V{0.0833333333333333}*cell[4];
auto x148 = x118*x137;
auto x149 = cell[17]*x148 + V{0.0833333333333333}*cell[17] + cell[8]*x148 - V{0.0833333333333333}*cell[8];
auto x150 = cell[11]*x143 + V{0.166666666666667}*cell[11] + cell[2]*x143 - V{0.166666666666667}*cell[2] + x133 + x134 - x135 - x136 + x138 + x140 + x141 - x142*x145 - x144 + x147 + x149;
auto x151 = x70 + V{1};
auto x152 = V{1}*x151*x64;
auto x153 = x152*x22*x75;
auto x154 = V{0.0833333333333333}*cell[7];
auto x155 = V{0.0833333333333333}*cell[16];
auto x156 = cell[16]*x105*x137;
auto x157 = x72*x98;
auto x158 = V{0.5}*x157;
auto x159 = cell[7]*x106*x137;
auto x160 = x115*x137;
auto x161 = cell[15]*x160 + V{0.0833333333333333}*cell[15] + cell[6]*x160 - V{0.0833333333333333}*cell[6];
auto x162 = cell[12]*x158 + V{0.166666666666667}*cell[12] + cell[3]*x158 - V{0.166666666666667}*cell[3] - x133 + x136 - x140 - x141 - x145*x157 + x149 + x154 - x155 + x156 - x159 + x161;
auto x163 = x72*x87;
auto x164 = V{0.5}*x163;
auto x165 = -cell[10]*x164 + V{0.166666666666667}*cell[10] - cell[1]*x164 - V{0.166666666666667}*cell[1] - x134 + x135 - x138 + x144 + x145*x163 + x147 - x154 + x155 - x156 + x159 + x161;
auto x166 = V{0.333333333333333}*cell[0]*x102*x64 - V{0.0555555555555556}*cell[10]*x64*(V{3}*x126*x75*x77 - x128) - V{0.0555555555555556}*cell[11]*x64*(x123 + x131) - V{0.0555555555555556}*cell[12]*x64*(x125 + x130 + x132) - V{0.0277777777777778}*cell[13]*x64*(-x109 - x113 - x129) + cell[14]*x20*(x103 + x74 - x76*x77*((x84)*(x84))) - V{0.0277777777777778}*cell[15]*x64*(-x116 - x117 - x129) + cell[16]*x20*(x103 + x104 - x76*x77*((x106)*(x106))) - V{0.0277777777777778}*cell[17]*x64*(x119 + x131 + x132) + cell[18]*x20*(x104 + x110 - x76*x77*((x108)*(x108))) + cell[1]*x121*(x101 - x122*x91 + x89) + cell[2]*x121*(x100 - x123 + x124 + x74) + cell[3]*x121*(x104 + x124 - x125 + x94) + cell[4]*x20*(x113 + x114 + x74) + cell[5]*x20*(x110 - x76*x77*((x83)*(x83)) + x89) + cell[6]*x20*(x104 + x114 + x116) + cell[7]*x20*(x114 + x117 - x76*x77*((x105)*(x105))) + cell[8]*x20*(x104 - x119 + x120) + cell[9]*x20*(x117 + x120 - x76*x77*((x108)*(x108))) + x150*x153*x68 - V{1}*x151*x165*x22*x64*x75*x87 + x153*x162*x98;
auto x167 = cell[0]*x19 + x166 + x26;
auto x168 = x152*x72;
auto x169 = x165*x168;
auto x170 = x166 - x169;
auto x171 = cell[10]*x19 + x170 + x28;
auto x172 = x150*x168;
auto x173 = -x172;
auto x174 = x166 + x173;
auto x175 = cell[11]*x19 + x174 + x29;
auto x176 = x162*x168;
auto x177 = -x176;
auto x178 = x166 + x177;
auto x179 = cell[12]*x19 + x178 + x30;
auto x180 = cell[13]*x19 + x170 + x173 + x31;
auto x181 = cell[14]*x19 + x170 + x172 + x32;
auto x182 = cell[15]*x19 + x170 + x177 + x33;
auto x183 = cell[16]*x19 + x170 + x176 + x34;
auto x184 = cell[17]*x19 + x174 + x177 + x35;
auto x185 = cell[18]*x19 + x174 + x176 + x36;
auto x186 = x166 + x169;
auto x187 = cell[1]*x19 + x186 + x27;
auto x188 = x166 + x172;
auto x189 = cell[2]*x19 + x188 + x37;
auto x190 = cell[3]*x19 + x166 + x176 + x38;
auto x191 = cell[4]*x19 + x172 + x186 + x39;
auto x192 = cell[5]*x19 + x169 + x174 + x40;
auto x193 = cell[6]*x19 + x176 + x186 + x41;
auto x194 = cell[7]*x19 + x169 + x178 + x42;
auto x195 = cell[8]*x19 + x176 + x188 + x43;
auto x196 = cell[9]*x19 + x172 + x178 + x44;
cell[0] = -x167;
cell[10] = -x171;
cell[11] = -x175;
cell[12] = -x179;
cell[13] = -x180;
cell[14] = -x181;
cell[15] = -x182;
cell[16] = -x183;
cell[17] = -x184;
cell[18] = -x185;
cell[1] = -x187;
cell[2] = -x189;
cell[3] = -x190;
cell[4] = -x191;
cell[5] = -x192;
cell[6] = -x193;
cell[7] = -x194;
cell[8] = -x195;
cell[9] = -x196;
return { V{1} - x167, ((x167)*(x167)) + ((x171)*(x171)) + ((x175)*(x175)) + ((x179)*(x179)) + ((x180)*(x180)) + ((x181)*(x181)) + ((x182)*(x182)) + ((x183)*(x183)) + ((x184)*(x184)) + ((x185)*(x185)) + ((x187)*(x187)) + ((x189)*(x189)) + ((x190)*(x190)) + ((x191)*(x191)) + ((x192)*(x192)) + ((x193)*(x193)) + ((x194)*(x194)) + ((x195)*(x195)) + ((x196)*(x196)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
