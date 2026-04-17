/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2021-24 Adrian Kummerlaender, Shota Ito
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
struct CSE<CombinedRLBdynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::SaveVelocity<collision::BGK>, dynamics::DefaultCombination>, momenta::Tuple<momenta::FixedDensity, momenta::FixedPressureMomentum<0, 1>, momenta::RegularizedBoundaryStress<0, 1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x24 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<0, 1>::VELOCITY>(1);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x25 = cell.template getFieldComponent<olb::momenta::FixedPressureMomentum<0, 1>::VELOCITY>(2);
auto x19 = x26 + V{-1};
auto x20 = V{0.0277777777777778}*x22;
auto x21 = V{1} / (x22);
auto x23 = V{2}*cell[13] + V{2}*cell[14] + V{2}*cell[15] + V{2}*cell[16];
auto x27 = cell[0] + V{2}*cell[10] + cell[11] + cell[12] + cell[17] + cell[18] + cell[2] + cell[3] + cell[8] + cell[9] + x23 + V{1};
auto x28 = -x21*x27 + V{1};
auto x29 = ((x28)*(x28));
auto x30 = V{1.5}*x29;
auto x31 = x30 + V{-1};
auto x32 = ((x24)*(x24));
auto x33 = V{1.5}*x32;
auto x34 = V{3}*x25;
auto x35 = ((x25)*(x25));
auto x36 = V{3}*x35;
auto x37 = x33 + x34 - x36;
auto x38 = x31 + x37;
auto x39 = V{1.5}*x35;
auto x40 = V{3}*x24;
auto x41 = V{3}*x32;
auto x42 = x39 + x40 - x41;
auto x43 = x31 + x42;
auto x44 = x33 + x39;
auto x45 = x44 + V{-1};
auto x46 = x30 + x45;
auto x47 = x40 + x46;
auto x48 = V{4.5}*((x24 + x25)*(x24 + x25));
auto x49 = x34 - x48;
auto x50 = x47 + x49;
auto x51 = -x34;
auto x52 = x24 - x25;
auto x53 = x51 - V{4.5}*((x52)*(x52));
auto x54 = x47 + x53;
auto x55 = -x40;
auto x56 = -V{4.5}*((x52)*(x52));
auto x57 = x34 + x55 + x56;
auto x58 = x46 + x57;
auto x59 = V{0.0555555555555556}*x22;
auto x60 = x21*(V{3}*cell[0] + V{6}*cell[10] + V{3}*cell[11] + V{3}*cell[12] + V{6}*cell[13] + V{6}*cell[14] + V{6}*cell[15] + V{6}*cell[16] + V{3}*cell[17] + V{3}*cell[18] + V{3}*cell[2] + V{3}*cell[3] + V{3}*cell[8] + V{3}*cell[9] + V{3});
auto x61 = x44 + V{2};
auto x62 = -x60 + x61;
auto x63 = -V{3}*x29 + x62;
auto x64 = x24 + x28;
auto x65 = x30 + x62;
auto x66 = x40 + x65 - V{4.5}*((x64)*(x64));
auto x67 = x25 + x28;
auto x68 = x34 + x65 - V{4.5}*((x67)*(x67));
auto x69 = x21*x27 + V{-1};
auto x70 = -V{4.5}*((x24 + x69)*(x24 + x69));
auto x71 = x55 + x70;
auto x72 = x65 + x71;
auto x73 = -V{4.5}*((x25 + x69)*(x25 + x69));
auto x74 = x51 + x73;
auto x75 = x65 + x74;
auto x76 = V{0.333333333333333}*x22;
auto x77 = x46*x76;
auto x78 = ((x28)*(x28));
auto x79 = V{1.5}*x78;
auto x80 = V{1} - x79;
auto x81 = -x39 + x40;
auto x82 = x41 + x81;
auto x83 = x80 + x82;
auto x84 = -x33 + x34;
auto x85 = x36 + x84;
auto x86 = x80 + x85;
auto x87 = x48 + x81 + x84;
auto x88 = x80 + x87;
auto x89 = V{1}*cell[10] + V{0.5}*cell[11] + V{0.5}*cell[12] + V{1}*cell[17] + V{1}*cell[18] + V{0.5}*cell[2] + V{0.5}*cell[3] + V{1}*cell[8] + V{1}*cell[9] + x23 + V{0.833333333333333};
auto x90 = V{0.0277777777777778}*x22;
auto x91 = -x54;
auto x92 = V{0.0555555555555555}*x22;
auto x93 = -x38;
auto x94 = -x75;
auto x95 = -x68;
auto x96 = V{1} - x30;
auto x97 = x82 + x96;
auto x98 = x85 + x96;
auto x99 = V{0.0555555555555555}*x22;
auto x100 = -x43;
auto x101 = V{0.111111111111111}*x22;
auto x102 = -x63;
auto x103 = -x46;
auto x104 = x103*x76;
auto x105 = V{0.0277777777777778}*x22;
auto x106 = -x50;
auto x107 = V{0.0555555555555555}*x22;
auto x108 = -x72;
auto x109 = -x66;
auto x110 = V{0.0277777777777778}*x22;
auto x111 = x87 + x96;
auto x112 = -x58;
auto x113 = V{4.44089209850063e-16}*cell[10] + V{1.66533453693773e-16}*cell[11] + V{1.11022302462516e-16}*cell[12] + V{6.66133814775094e-16}*cell[13] + V{6.66133814775094e-16}*cell[14] + V{8.88178419700125e-16}*cell[15] + V{4.44089209850063e-16}*cell[16] + V{4.71844785465692e-16}*cell[17] + V{5.27355936696949e-16}*cell[18] + V{1.66533453693773e-16}*cell[2] + V{1.11022302462516e-16}*cell[3] + V{4.71844785465692e-16}*cell[8] + V{5.27355936696949e-16}*cell[9] + V{2.22044604925031e-16};
auto x114 = x21*(x100*x99 + x101*x102 + x104 + x105*x106 + x107*x108 + x107*x109 + x110*x111 + x110*x112 + x113 + x59*x97 + x59*x98 + x90*x91 + x92*x93 + x92*x94 + x92*x95);
auto x115 = x114 + V{-1};
auto x116 = ((x115)*(x115));
auto x117 = V{1.5}*x116;
auto x118 = x117 + x45;
auto x119 = V{0.333333333333333}*x26*(x118*x22 + V{1});
auto x120 = x44 + V{-4};
auto x121 = x120 + x60;
auto x122 = V{0.0833333333333333}*cell[11];
auto x123 = V{0.0833333333333333}*cell[12];
auto x124 = V{0.0833333333333333}*cell[2];
auto x125 = V{0.0833333333333333}*cell[3];
auto x126 = V{0.166666666666667}*cell[13];
auto x127 = V{0.166666666666667}*cell[14];
auto x128 = V{0.166666666666667}*cell[15];
auto x129 = V{0.166666666666667}*cell[16];
auto x130 = V{0.00462962962962963}*x22;
auto x131 = x130*x38;
auto x132 = x130*x43;
auto x133 = x130*x83;
auto x134 = x130*x86;
auto x135 = V{0.00462962962962963}*x22;
auto x136 = x135*x66;
auto x137 = x135*x68;
auto x138 = x135*x72;
auto x139 = x135*x75;
auto x140 = -V{0.333333333333333}*cell[10] + V{0.166666666666667}*cell[17] + V{0.166666666666667}*cell[18] + V{0.166666666666667}*cell[8] + V{0.166666666666667}*cell[9] + x122 + x123 + x124 + x125 - x126 - x127 - x128 - x129 + x130*x50 + x130*x54 + x130*x58 - x130*x88 + x131 + x132 - x133 - x134 - x136 - x137 - x138 - x139 + V{0.0555555555555555};
auto x141 = V{0.0555555555555556}*x26;
auto x142 = V{1} - x114;
auto x143 = ((x142)*(x142));
auto x144 = V{0.0833333333333333}*x22;
auto x145 = V{0.166666666666667}*x22;
auto x146 = V{0.166666666666667}*x22;
auto x147 = V{0.166666666666667}*x22;
auto x148 = x21*(V{1.33226762955019e-15}*cell[10] + V{4.9960036108132e-16}*cell[11] + V{3.33066907387547e-16}*cell[12] + V{1.99840144432528e-15}*cell[13] + V{1.99840144432528e-15}*cell[14] + V{2.66453525910038e-15}*cell[15] + V{1.33226762955019e-15}*cell[16] + V{1.41553435639707e-15}*cell[17] + V{1.58206781009085e-15}*cell[18] + V{4.9960036108132e-16}*cell[2] + V{3.33066907387547e-16}*cell[3] + V{1.41553435639707e-15}*cell[8] + V{1.58206781009085e-15}*cell[9] + V{0.166666666666667}*x100*x22 + V{0.333333333333333}*x102*x22 + V{1}*x103*x22 + V{0.0833333333333333}*x106*x22 + x108*x146 + x109*x146 + x111*x144 + x112*x144 + x145*x93 + x145*x94 + x145*x95 + x147*x97 + x147*x98 + V{0.0833333333333333}*x22*x91 + V{6.66133814775094e-16});
auto x149 = x117 + x120 + x148;
auto x150 = V{0.0462962962962963}*x22;
auto x151 = x79 + V{-1};
auto x152 = x151 + x42;
auto x153 = V{0.00925925925925926}*x22;
auto x154 = V{0.166666666666667}*cell[11] - V{0.333333333333333}*cell[15] - V{0.333333333333333}*cell[16] + V{0.166666666666667}*cell[2] - x123 - x125 + x126 + x127 + x134;
auto x155 = -x153*x83 + x154;
auto x156 = -V{4.5}*((x64)*(x64));
auto x157 = x62 + x79;
auto x158 = x156 + x157 + x40;
auto x159 = x157 + x71;
auto x160 = x151 + x37;
auto x161 = V{0.00925925925925926}*x22;
auto x162 = -V{4.5}*((x67)*(x67));
auto x163 = x157 + x162 + x34;
auto x164 = x157 + x74;
auto x165 = V{0.00231481481481482}*x22;
auto x166 = x45 + x79;
auto x167 = x40 + x49;
auto x168 = x166 + x167;
auto x169 = x166 + x40 + x51 + x56;
auto x170 = x166 + x57;
auto x171 = x62 - V{3}*x78;
auto x172 = -V{0.166666666666667}*cell[10] + V{0.0833333333333334}*cell[17] + V{0.0833333333333334}*cell[18] + V{0.0833333333333334}*cell[8] + V{0.0833333333333334}*cell[9] - x165*x88 + V{-0.0555555555555555};
auto x173 = -x161*x171 + x165*x168 + x165*x169 + x165*x170 + x172;
auto x174 = -x130*x160 + x135*x158 + x135*x159 - x161*x163 - x161*x164 + x173;
auto x175 = x117 + V{-1};
auto x176 = x141*(x22*(x175 + x42) + V{1});
auto x177 = V{0.166666666666667}*cell[12] - V{0.333333333333333}*cell[13] - V{0.333333333333333}*cell[14] + V{0.166666666666667}*cell[3] - x122 - x124 + x128 + x129 + x133;
auto x178 = -x153*x86 + x177;
auto x179 = -x130*x152 + x135*x163 + x135*x164 - x158*x161 - x159*x161 + x173;
auto x180 = x141*(x22*(x175 + x37) + V{1});
auto x181 = V{0.0231481481481481}*x22;
auto x182 = x121 + x79;
auto x183 = V{0.00462962962962963}*x22;
auto x184 = V{0.00231481481481481}*x22;
auto x185 = V{0.00115740740740741}*x22;
auto x186 = V{0.166666666666667}*cell[10] + V{0.0416666666666667}*cell[17] + V{0.0416666666666667}*cell[18] + V{0.0416666666666667}*cell[8] + V{0.0416666666666667}*cell[9] - x185*x88;
auto x187 = -V{0.0416666666666667}*cell[12] - V{0.0416666666666667}*cell[3] + x184*x86 + x186;
auto x188 = V{0.833333333333333}*cell[13] - V{0.166666666666667}*cell[14] + x187;
auto x189 = V{0.00462962962962963}*x22;
auto x190 = V{0.0833333333333333}*cell[11] + V{0.0833333333333334}*cell[15] + V{0.0833333333333334}*cell[16] + V{0.0833333333333333}*cell[2] - x189*x83 + V{0.0138888888888889};
auto x191 = x152*x189 + x163*x165 + x164*x165 + x190;
auto x192 = x153*x171 + x168*x185 + x169*x185 + x170*x185;
auto x193 = -x160*x184 + x191 + x192;
auto x194 = -x158*x183 + x188 + x193;
auto x195 = V{0.0277777777777778}*x26;
auto x196 = x115 + x24;
auto x197 = -V{0.166666666666667}*cell[13] + V{0.833333333333333}*cell[14] + x187;
auto x198 = -x159*x183 + x193 + x197;
auto x199 = x142 + x24;
auto x200 = -V{0.0416666666666667}*cell[11] - V{0.0416666666666667}*cell[2] + x184*x83 + x186 + V{0.0138888888888889};
auto x201 = V{0.833333333333333}*cell[15] - V{0.166666666666667}*cell[16] + x200;
auto x202 = V{0.0833333333333333}*cell[12] + V{0.0833333333333334}*cell[13] + V{0.0833333333333334}*cell[14] + V{0.0833333333333333}*cell[3] - x189*x86;
auto x203 = x158*x165 + x159*x165 + x160*x189 + x202;
auto x204 = -x152*x184 + x192 + x203;
auto x205 = -x163*x183 + x201 + x204;
auto x206 = x115 + x25;
auto x207 = -V{0.166666666666667}*cell[15] + V{0.833333333333333}*cell[16] + x200;
auto x208 = -x164*x183 + x204 + x207;
auto x209 = x142 + x25;
auto x210 = V{0.0162037037037037}*x22;
auto x211 = V{0.0115740740740741}*x22;
auto x212 = -V{0.0833333333333333}*cell[10];
auto x213 = V{0.416666666666667}*cell[17] - V{0.0833333333333333}*cell[18] + V{0.416666666666667}*cell[8] - V{0.0833333333333333}*cell[9] + x212;
auto x214 = -x211*x88 + x213;
auto x215 = V{0.00231481481481481}*x22;
auto x216 = -x130*x171 + x191 + x203;
auto x217 = -x169*x215 - x170*x215 + x216;
auto x218 = x195*(x22*(x118 + x167) + V{1});
auto x219 = -V{0.0833333333333333}*cell[17] + V{0.416666666666667}*cell[18] - V{0.0833333333333333}*cell[8] + V{0.416666666666667}*cell[9] + x212 + x215*x88;
auto x220 = -x168*x215 + x216 + x219;
auto x221 = x195*(x22*(x118 + x40 + x53) + V{1});
auto x222 = x140 + V{0.037037037037037}*x22*x63;
auto x223 = -x148 + x61;
auto x224 = x22*(-V{3}*x116 + x223) + V{1};
auto x225 = x150*x83 + x154;
auto x226 = ((-x21*(-x101*x63 - x105*x50 - x107*x66 - x107*x72 - x110*x58 + x110*x88 + x113 - x38*x92 - x43*x99 - x54*x90 + x59*x83 + x59*x86 - x68*x92 - x75*x92 - x77) + 1)*(-x21*(-x101*x63 - x105*x50 - x107*x66 - x107*x72 - x110*x58 + x110*x88 + x113 - x38*x92 - x43*x99 - x54*x90 + x59*x83 + x59*x86 - x68*x92 - x75*x92 - x77) + 1));
auto x227 = V{1} - V{1.5}*x226;
auto x228 = x150*x86 + x177;
auto x229 = x117 + x223;
auto x230 = x22*(x229 + x55 - V{4.5}*((x196)*(x196))) + V{1};
auto x231 = x22*(x229 + x40 - V{4.5}*((x199)*(x199))) + V{1};
auto x232 = x22*(x229 + x51 - V{4.5}*((x206)*(x206))) + V{1};
auto x233 = x22*(x229 + x34 - V{4.5}*((x209)*(x209))) + V{1};
auto x234 = x210*x88 + x213;
auto x235 = x195*(x22*(x118 + x57) + V{1});
auto x236 = x165*x68 + x165*x75 + x189*x43 + x190;
auto x237 = x165*x66 + x165*x72 + x189*x38 + x202;
auto x238 = -x130*x63 + x236 + x237;
auto x239 = -x215*x54 - x215*x58 + x238;
auto x240 = -x215*x50 + x219 + x238;
auto x241 = -x161*x63 + x165*x50 + x165*x54 + x165*x58 + x172;
auto x242 = -x131 + x136 + x138 - x161*x68 - x161*x75 + x241;
auto x243 = -x132 + x137 + x139 - x161*x66 - x161*x72 + x241;
auto x244 = V{2}*x26 + V{-2};
auto x245 = x153*x63 + x185*x50 + x185*x54 + x185*x58;
auto x246 = -x184*x38 + x236 + x245;
auto x247 = -x184*x43 + x237 + x245;
auto x248 = V{1} - V{1.5}*x143;
cell[0] = -x119 + x19*(x20*x38 + x20*x43 + x20*x50 + x20*x54 + x20*x58 - x20*x83 - x20*x86 - x20*x88 + x59*x63 + x59*x66 + x59*x68 + x59*x72 + x59*x75 + x77 + x89);
cell[1] = -x141*(x22*(-V{4.5}*x143 + x149) + V{1}) + x19*(x140 - V{0.0185185185185185}*x22*x63 + x59*(x121 + x30 - V{4.5}*x78));
cell[2] = -x176 - x19*(-x150*x152 + x155 + x174);
cell[3] = -x180 - x19*(-x150*x160 + x178 + x179);
cell[4] = -(x19*(x159*x181 + x194 - x20*(x182 + x40 + x70)) + x195*(x22*(x149 + x40 - V{4.5}*((x196)*(x196))) + V{1}));
cell[5] = -(x19*(x158*x181 + x198 - x20*(x156 + x182 + x55)) + x195*(x22*(x149 + x55 - V{4.5}*((x199)*(x199))) + V{1}));
cell[6] = -(x19*(x164*x181 - x20*(x182 + x34 + x73) + x205) + x195*(x22*(x149 + x34 - V{4.5}*((x206)*(x206))) + V{1}));
cell[7] = -(x19*(x163*x181 - x20*(x162 + x182 + x51) + x208) + x195*(x22*(x149 + x51 - V{4.5}*((x209)*(x209))) + V{1}));
cell[8] = -x19*(-x168*x210 + x214 + x217) - x218;
cell[9] = -x19*(-x169*x210 + x170*x211 + x220) - x221;
cell[10] = -x141*x224 + x19*x222;
cell[11] = x141*(x22*(x227 + x82) + V{-1}) - x19*(x152*x153 + x174 + x225);
cell[12] = x141*(x22*(x227 + x85) + V{-1}) - x19*(x153*x160 + x179 + x228);
cell[13] = -x19*(-x130*x159 + x194) - x195*x230;
cell[14] = -x19*(-x130*x158 + x198) - x195*x231;
cell[15] = -x19*(-x130*x164 + x205) - x195*x232;
cell[16] = -x19*(-x130*x163 + x208) - x195*x233;
cell[17] = -x19*(x168*x211 + x217 + x234) + x195*(x22*(x227 + x87) + V{-1});
cell[18] = -x19*(x169*x211 - x170*x210 + x220) - x235;
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[0] = V{1}*x21*(-x119 - x141*x230 - x141*x231 - x141*x232 - x141*x233 - x176 - x180 - x19*(-x150*x38 + x178 + x243) - x19*(-x150*x43 + x155 + x242) - x19*(x153*x38 + x228 + x243) - x19*(x153*x43 + x225 + x242) - x19*(-x210*x50 + x214 + x239) - x19*(-x210*x54 + x211*x58 + x240) - x19*(-x210*x58 + x211*x54 + x240) - x19*(x211*x50 + x234 + x239) + x19*(-x100*x20 - x102*x59 - x104 - x106*x20 - x108*x59 - x109*x59 - x111*x20 - x112*x20 - x20*x91 - x20*x93 - x20*x97 - x20*x98 - x59*x94 - x59*x95 + x89) - x218 - x221 + x222*x244 - V{0.111111111111111}*x224*x26 - x235 - x244*(-x130*x66 - x183*x72 + x197 + x246) - x244*(-x130*x68 - x183*x75 + x207 + x247) - x244*(-x130*x72 - x183*x66 + x188 + x246) - x244*(-x130*x75 - x183*x68 + x201 + x247) + V{0.0555555555555556}*x26*(x22*(x248 + x82) + V{-1}) + V{0.0555555555555556}*x26*(x22*(x248 + x85) + V{-1}) + V{0.0277777777777778}*x26*(x22*(x248 + x87) + V{-1}) + V{1}) + V{-1};
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[1] = x24;
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[2] = x25;
return { x22, V{1}*x226 + x32 + x35 };
}
};

}

}

// Generation Info: commit=42ba761d236a636786976ad8bcab281330b3bed7
