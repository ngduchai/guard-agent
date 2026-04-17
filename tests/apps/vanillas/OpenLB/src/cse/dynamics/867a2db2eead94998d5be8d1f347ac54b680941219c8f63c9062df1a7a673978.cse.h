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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::ThirdOrder, collision::SmagorinskyEffectiveOmega<collision::ThirdOrderRLB>, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = parameters.template get<collision::LES::SMAGORINSKY>();
auto x20 = parameters.template get<descriptors::OMEGA>();
auto x21 = V{0.333333333333333}*cell[0];
auto x22 = V{0.333333333333333}*cell[10];
auto x23 = V{0.333333333333333}*cell[11];
auto x24 = V{0.333333333333333}*cell[12];
auto x25 = V{0.333333333333333}*cell[13];
auto x26 = V{0.333333333333333}*cell[14];
auto x27 = V{0.333333333333333}*cell[15];
auto x28 = V{0.333333333333333}*cell[16];
auto x29 = V{0.333333333333333}*cell[17];
auto x30 = V{0.333333333333333}*cell[18];
auto x31 = V{0.333333333333333}*cell[1];
auto x32 = V{0.333333333333333}*cell[2];
auto x33 = V{0.333333333333333}*cell[3];
auto x34 = V{0.333333333333333}*cell[4];
auto x35 = V{0.333333333333333}*cell[5];
auto x36 = V{0.333333333333333}*cell[6];
auto x37 = V{0.333333333333333}*cell[7];
auto x38 = V{0.333333333333333}*cell[8];
auto x39 = V{0.333333333333333}*cell[9];
auto x40 = cell[15] + cell[17];
auto x41 = cell[12] + x40;
auto x42 = cell[11] + cell[18];
auto x43 = cell[10] + cell[14] + cell[16];
auto x44 = cell[2] + cell[8] + cell[9];
auto x45 = cell[13] + cell[3];
auto x46 = cell[0] + cell[1] + cell[4] + cell[5] + cell[6] + cell[7] + x41 + x42 + x43 + x44 + x45;
auto x47 = x46 + V{1};
auto x48 = V{1} / ((x47)*(x47));
auto x49 = V{1.5}*x48;
auto x50 = -cell[18];
auto x51 = -cell[3];
auto x52 = -cell[8];
auto x53 = cell[9] + x52;
auto x54 = x50 + x51 + x53;
auto x55 = -cell[6];
auto x56 = cell[7] + x55;
auto x57 = -cell[16] + x56;
auto x58 = x41 + x54 + x57;
auto x59 = ((x58)*(x58));
auto x60 = x49*x59;
auto x61 = cell[13] + cell[15];
auto x62 = -cell[1];
auto x63 = -cell[7];
auto x64 = x55 + x62 + x63;
auto x65 = -cell[4];
auto x66 = -cell[5] + x65;
auto x67 = x43 + x61 + x64 + x66;
auto x68 = ((x67)*(x67));
auto x69 = x49*x68;
auto x70 = cell[13] + cell[17];
auto x71 = -cell[2];
auto x72 = -cell[9];
auto x73 = x42 + x52 + x71 + x72;
auto x74 = cell[5] + x65;
auto x75 = -cell[14] + x74;
auto x76 = x70 + x73 + x75;
auto x77 = ((x76)*(x76));
auto x78 = x49*x77;
auto x79 = x69 + x78 + V{-1};
auto x80 = x60 + x79;
auto x81 = V{1} / (x47);
auto x82 = x67*x81;
auto x83 = x76*x82;
auto x84 = -cell[13] + cell[14] + x74 + x83;
auto x85 = x58*x82;
auto x86 = -cell[15] + cell[16];
auto x87 = x56 + x85 + x86;
auto x88 = x76*x81;
auto x89 = x58*x88;
auto x90 = -cell[17];
auto x91 = cell[18] + x90;
auto x92 = x53 + x89 + x91;
auto x93 = V{0.666666666666667}*cell[10];
auto x94 = V{0.666666666666667}*cell[1];
auto x95 = V{1}*x81;
auto x96 = x68*x95;
auto x97 = V{0.666666666666667}*cell[15];
auto x98 = V{0.666666666666667}*cell[16];
auto x99 = V{0.666666666666667}*cell[6];
auto x100 = V{0.666666666666667}*cell[7];
auto x101 = -x100 + x23 + x32 - x97 - x98 - x99;
auto x102 = V{0.666666666666667}*cell[13];
auto x103 = V{0.666666666666667}*cell[14];
auto x104 = V{0.666666666666667}*cell[4];
auto x105 = V{0.666666666666667}*cell[5];
auto x106 = -x102 - x103 - x104 - x105 + x24 + x33;
auto x107 = x101 + x106 + x21 + x29 + x30 + x38 + x39 - x93 - x94 + x96;
auto x108 = V{0.666666666666667}*cell[11];
auto x109 = V{0.666666666666667}*cell[2];
auto x110 = x77*x95;
auto x111 = V{0.666666666666667}*cell[17];
auto x112 = V{0.666666666666667}*cell[18];
auto x113 = V{0.666666666666667}*cell[8];
auto x114 = V{0.666666666666667}*cell[9];
auto x115 = -x111 - x112 - x113 - x114 + x21 + x22 + x31;
auto x116 = x106 - x108 - x109 + x110 + x115 + x27 + x28 + x36 + x37;
auto x117 = V{0.666666666666667}*cell[12];
auto x118 = V{0.666666666666667}*cell[3];
auto x119 = x59*x95;
auto x120 = x101 + x115 - x117 - x118 + x119 + x25 + x26 + x34 + x35;
auto x121 = V{1} - V{1} / (V{3.00000046417339}*util::sqrt(x81*((x19)*(x19))*util::sqrt(V{0.5}*((x107)*(x107)) + V{0.5}*((x116)*(x116)) + V{0.5}*((x120)*(x120)) + ((x84)*(x84)) + ((x87)*(x87)) + ((x92)*(x92))) + V{0.0277777691819762}/((x20)*(x20))) + V{0.5}/x20);
auto x122 = V{0.5}*x81;
auto x123 = V{0.0555555555555556}*cell[0] + V{0.0555555555555556}*cell[10] + V{0.0555555555555556}*cell[11] + V{0.0555555555555556}*cell[12] + V{0.0555555555555556}*cell[13] + V{0.0555555555555556}*cell[14] + V{0.0555555555555556}*cell[15] + V{0.0555555555555556}*cell[16] + V{0.0555555555555556}*cell[17] + V{0.0555555555555556}*cell[18] + V{0.0555555555555556}*cell[1] + V{0.0555555555555556}*cell[2] + V{0.0555555555555556}*cell[3] + V{0.0555555555555556}*cell[4] + V{0.0555555555555556}*cell[5] + V{0.0555555555555556}*cell[6] + V{0.0555555555555556}*cell[7] + V{0.0555555555555556}*cell[8] + V{0.0555555555555556}*cell[9] + V{0.0555555555555556};
auto x124 = V{3}*x48;
auto x125 = x124*x68;
auto x126 = x60 + V{-1};
auto x127 = util::pow(x47, -3);
auto x128 = V{6.000003}*x127;
auto x129 = x128*x67;
auto x130 = V{2.999997}*x127;
auto x131 = x130*x76;
auto x132 = V{3}*cell[14];
auto x133 = V{3}*cell[16];
auto x134 = V{3}*cell[5];
auto x135 = V{3}*cell[7];
auto x136 = V{3}*cell[13] - V{3}*cell[4];
auto x137 = V{3}*cell[15] - V{3}*cell[6];
auto x138 = x81*(V{3}*cell[10] - V{3}*cell[1] + x132 + x133 - x134 - x135 + x136 + x137);
auto x139 = -x138;
auto x140 = x129*x77;
auto x141 = x131*x68;
auto x142 = x139 + x140 + x141;
auto x143 = x129*x59 + x131*x59 + x142;
auto x144 = x122*x67;
auto x145 = -x21;
auto x146 = x111 + x112 + x113 + x114 + x145 - x22 - x31;
auto x147 = x102 + x103 + x104 + x105 - x24 - x33;
auto x148 = x108 + x109 - x110 + x146 + x147 - x27 - x28 - x36 - x37;
auto x149 = x100 - x23 - x32 + x97 + x98 + x99;
auto x150 = x117 + x118 - x119 + x146 + x149 - x25 - x26 - x34 - x35;
auto x151 = -x84*x95;
auto x152 = -x87;
auto x153 = x58*x95;
auto x154 = V{0.166666666666667}*x81;
auto x155 = V{6.93889390390723e-18}*cell[0];
auto x156 = V{0.0833333333333333}*cell[12];
auto x157 = V{0.0833333333333333}*cell[3];
auto x158 = V{0.0833333333333333}*x81;
auto x159 = -V{0.0833333333333333}*cell[13] - V{0.0833333333333333}*cell[14] - V{0.0833333333333333}*cell[4] - V{0.0833333333333333}*cell[5] + x155 + x156 + x157 - x158*x59;
auto x160 = V{0.0833333333333333}*cell[11];
auto x161 = V{0.0833333333333333}*cell[2];
auto x162 = -V{0.0833333333333333}*cell[15] - V{0.0833333333333333}*cell[16] - V{0.0833333333333333}*cell[6] - V{0.0833333333333333}*cell[7] - x158*x77 + x160 + x161;
auto x163 = -V{0.166666666666667}*cell[10] + V{0.166666666666667}*cell[17] + V{0.166666666666667}*cell[18] - V{0.166666666666667}*cell[1] + V{0.166666666666667}*cell[8] + V{0.166666666666667}*cell[9] + x154*x68 + x159 + x162;
auto x164 = x124*x77;
auto x165 = x128*x76;
auto x166 = x130*x67;
auto x167 = V{3}*cell[18];
auto x168 = V{3}*cell[9];
auto x169 = V{3}*cell[17] - V{3}*cell[8];
auto x170 = x81*(V{3}*cell[11] - V{3}*cell[2] - x132 + x134 + x136 + x167 - x168 + x169);
auto x171 = -x170;
auto x172 = x165*x68;
auto x173 = x166*x77;
auto x174 = x171 + x172 + x173;
auto x175 = x165*x59 + x166*x59 + x174;
auto x176 = x122*x76;
auto x177 = x145 + x147 + x149 - x29 - x30 - x38 - x39 + x93 + x94 - x96;
auto x178 = -x92;
auto x179 = V{0.0833333333333333}*cell[10];
auto x180 = V{0.0833333333333333}*cell[1];
auto x181 = -V{0.0833333333333333}*cell[17] - V{0.0833333333333333}*cell[18] - V{0.0833333333333333}*cell[8] - V{0.0833333333333333}*cell[9] - x158*x68 + x179 + x180;
auto x182 = -V{0.166666666666667}*cell[11] + V{0.166666666666667}*cell[15] + V{0.166666666666667}*cell[16] - V{0.166666666666667}*cell[2] + V{0.166666666666667}*cell[6] + V{0.166666666666667}*cell[7] + x154*x77 + x159 + x181;
auto x183 = x124*x59;
auto x184 = x81*(V{3}*cell[12] - V{3}*cell[3] - x133 + x135 + x137 - x167 + x168 + x169);
auto x185 = -x184;
auto x186 = V{9}*x127;
auto x187 = x186*x58;
auto x188 = x185 + x187*x68 + x187*x77;
auto x189 = x122*x58;
auto x190 = x67*x95;
auto x191 = x76*x95;
auto x192 = -V{0.166666666666667}*cell[12] + V{0.166666666666667}*cell[13] + V{0.166666666666667}*cell[14] - V{0.166666666666667}*cell[3] + V{0.166666666666667}*cell[4] + V{0.166666666666667}*cell[5] + x154*x59 + x155 + x162 + x181;
auto x193 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[10] + V{0.0277777777777778}*cell[11] + V{0.0277777777777778}*cell[12] + V{0.0277777777777778}*cell[13] + V{0.0277777777777778}*cell[14] + V{0.0277777777777778}*cell[15] + V{0.0277777777777778}*cell[16] + V{0.0277777777777778}*cell[17] + V{0.0277777777777778}*cell[18] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778}*cell[9] + V{0.0277777777777778};
auto x194 = V{4.5}*x48;
auto x195 = cell[10] + cell[16] + x64;
auto x196 = x194*((2*cell[13] - 2*cell[4] + x195 + x40 + x73)*(2*cell[13] - 2*cell[4] + x195 + x40 + x73));
auto x197 = -x60;
auto x198 = -x69;
auto x199 = V{1} - x78;
auto x200 = x198 + x199;
auto x201 = x138 + x197 + x200;
auto x202 = V{18}*x127;
auto x203 = x170 - x186*x59*x67 - x186*x59*x76 + x202*x67*x77 + x202*x68*x76;
auto x204 = -x156;
auto x205 = -x157;
auto x206 = V{0.0416666666666667}*x81;
auto x207 = x206*x59;
auto x208 = V{2.49999999985601e-07}*x82;
auto x209 = x120*x208;
auto x210 = x58*x81;
auto x211 = V{4.99999999971202e-07}*x210;
auto x212 = x211*x87;
auto x213 = V{0.25000025}*x82;
auto x214 = x116*x213;
auto x215 = V{0.5000005}*x84;
auto x216 = x215*x88;
auto x217 = -V{0.0416666666666667}*cell[0];
auto x218 = V{0.0833333333333333}*x81;
auto x219 = V{0.0416666666666667}*cell[10] + V{6.93889390390723e-18}*cell[17] + V{6.93889390390723e-18}*cell[18] + V{0.0416666666666667}*cell[1] + V{6.93889390390723e-18}*cell[8] + V{6.93889390390723e-18}*cell[9] + x217 - x218*x68;
auto x220 = V{0.0416666666666667}*cell[11] + V{6.93889390390723e-18}*cell[15] + V{6.93889390390723e-18}*cell[16] + V{0.0416666666666667}*cell[2] + V{6.93889390390723e-18}*cell[6] + V{6.93889390390723e-18}*cell[7] - x218*x77;
auto x221 = x204 + x205 + x207 + x209 + x212 - x214 - x216 + x219 + x220;
auto x222 = V{2.49999999985601e-07}*x88;
auto x223 = x120*x222;
auto x224 = x211*x92;
auto x225 = V{0.25000025}*x88;
auto x226 = x107*x225;
auto x227 = x215*x82;
auto x228 = x223 + x224 - x226 - x227;
auto x229 = V{0.25}*x83;
auto x230 = V{0.375}*cell[13] - V{0.125}*cell[14] + V{0.375}*cell[4] - V{0.125}*cell[5] - x229;
auto x231 = -cell[11] + V{2}*cell[14] + cell[15] - V{2}*cell[5] + x195 + x44 + x50 + x90;
auto x232 = V{3.000006}*x127;
auto x233 = x232*x59*x67;
auto x234 = V{6.000012}*x127;
auto x235 = x234*x68*x76;
auto x236 = x232*x59*x76;
auto x237 = x234*x67*x77;
auto x238 = x170 + x80;
auto x239 = -x223 - x224 + x226 + x227;
auto x240 = -V{0.125}*cell[13] + V{0.375}*cell[14] - V{0.125}*cell[4] + V{0.375}*cell[5] + x229;
auto x241 = cell[10] + cell[14] + x62 + x66;
auto x242 = x194*((cell[12] + 2*cell[15] - 2*cell[6] + x241 + x54 + x70)*(cell[12] + 2*cell[15] - 2*cell[6] + x241 + x54 + x70));
auto x243 = x127*x58;
auto x244 = V{9.000009}*x243;
auto x245 = x244*x68;
auto x246 = V{8.99999999948164e-06}*x243;
auto x247 = x246*x77;
auto x248 = x184 + x245 - x247;
auto x249 = V{5.999994}*x127;
auto x250 = x249*x59*x76;
auto x251 = V{12.000006}*x127;
auto x252 = x251*x59*x67;
auto x253 = -x140 - x141 + x250 + x252;
auto x254 = x248 + x253;
auto x255 = -x160;
auto x256 = -x161;
auto x257 = x206*x77;
auto x258 = x116*x208;
auto x259 = V{4.99999999971202e-07}*x88;
auto x260 = x259*x84;
auto x261 = x120*x213;
auto x262 = V{0.5000005}*x87;
auto x263 = x210*x262;
auto x264 = V{0.0416666666666667}*cell[12] + V{6.93889390390723e-18}*cell[13] + V{6.93889390390723e-18}*cell[14] + V{0.0416666666666667}*cell[3] + V{6.93889390390723e-18}*cell[4] + V{6.93889390390723e-18}*cell[5] - x218*x59;
auto x265 = x219 + x255 + x256 + x257 + x258 + x260 - x261 - x263 + x264;
auto x266 = V{2.49999999985601e-07}*x210;
auto x267 = x116*x266;
auto x268 = x259*x92;
auto x269 = V{0.25000025}*x210;
auto x270 = x107*x269;
auto x271 = x262*x82;
auto x272 = x267 + x268 - x270 - x271;
auto x273 = V{0.25}*x85;
auto x274 = V{0.375}*cell[15] - V{0.125}*cell[16] + V{0.375}*cell[6] - V{0.125}*cell[7] - x273;
auto x275 = -cell[12] + x45;
auto x276 = V{2}*cell[16] - V{2}*cell[7] + cell[8] + x241 + x275 + x72 + x91;
auto x277 = -x267 - x268 + x270 + x271;
auto x278 = -V{0.125}*cell[15] + V{0.375}*cell[16] - V{0.125}*cell[6] + V{0.375}*cell[7] + x273;
auto x279 = cell[11] + x71 + x75;
auto x280 = x194*((cell[12] + 2*cell[17] - 2*cell[8] + x279 + x51 + x57 + x61)*(cell[12] + 2*cell[17] - 2*cell[8] + x279 + x51 + x57 + x61));
auto x281 = x244*x77;
auto x282 = x246*x68;
auto x283 = x184 + x281 - x282;
auto x284 = x249*x59*x67;
auto x285 = x251*x59*x76;
auto x286 = -x172 - x173 + x284 + x285;
auto x287 = x283 + x286;
auto x288 = -x179;
auto x289 = -x180;
auto x290 = x206*x68;
auto x291 = x107*x222;
auto x292 = V{4.99999999971202e-07}*x82;
auto x293 = x292*x84;
auto x294 = x120*x225;
auto x295 = V{0.5000005}*x92;
auto x296 = x210*x295;
auto x297 = x217 + x220 + x264 + x288 + x289 + x290 + x291 + x293 - x294 - x296;
auto x298 = x107*x266;
auto x299 = x292*x87;
auto x300 = x116*x269;
auto x301 = x295*x88;
auto x302 = x298 + x299 - x300 - x301;
auto x303 = V{0.25}*x89;
auto x304 = V{0.375}*cell[17] - V{0.125}*cell[18] + V{0.375}*cell[8] - V{0.125}*cell[9] - x303;
auto x305 = V{2}*cell[18] + cell[6] - V{2}*cell[9] + x275 + x279 + x63 + x86;
auto x306 = -x298 - x299 + x300 + x301;
auto x307 = -V{0.125}*cell[17] + V{0.375}*cell[18] - V{0.125}*cell[8] + V{0.375}*cell[9] + x303;
auto x308 = x46 + V{1};
auto x309 = x138 + x80;
auto x310 = x204 + x205 + x207 - x209 - x212 + x214 + x216 + x219 + x220;
auto x311 = x219 + x255 + x256 + x257 - x258 - x260 + x261 + x263 + x264;
auto x312 = x217 + x220 + x264 + x288 + x289 + x290 - x291 - x293 + x294 + x296;
auto x0 = -V{1}*x121*(-V{0.5}*cell[0] + V{4.16333634234434e-17}*cell[10] + V{4.16333634234434e-17}*cell[11] + V{4.16333634234434e-17}*cell[12] + V{0.5}*cell[13] + V{0.5}*cell[14] + V{0.5}*cell[15] + V{0.5}*cell[16] + V{0.5}*cell[17] + V{0.5}*cell[18] + V{4.16333634234434e-17}*cell[1] + V{4.16333634234434e-17}*cell[2] + V{4.16333634234434e-17}*cell[3] + V{0.5}*cell[4] + V{0.5}*cell[5] + V{0.5}*cell[6] + V{0.5}*cell[7] + V{0.5}*cell[8] + V{0.5}*cell[9] - x122*x59 - x122*x68 - x122*x77) - x80*(x21 + x22 + x23 + x24 + x25 + x26 + x27 + x28 + x29 + x30 + x31 + x32 + x33 + x34 + x35 + x36 + x37 + x38 + x39 + V{0.333333333333333}) + V{-0.333333333333333};
auto x1 = -V{1}*x121*(x144*x148 + x144*x150 + x151*x76 + x152*x153 + x163) - x123*(-x125 + x126 + x143 + x78) + V{-0.0555555555555556};
auto x2 = -V{1}*x121*(x150*x176 + x151*x67 + x153*x178 + x176*x177 + x182) - x123*(x126 - x164 + x175 + x69) + V{-0.0555555555555556};
auto x3 = -V{1}*x121*(x148*x189 + x152*x190 + x177*x189 + x178*x191 + x192) - x123*(-x183 + x188 + x79) + V{-0.0555555555555556};
auto x4 = V{1}*x121*(x221 + x228 + x230) + x193*(x196 + x201 + x203) + V{-0.0277777777777778};
auto x5 = -(-V{1}*x121*(x221 + x239 + x240) + x193*(x139 - x194*((x231)*(x231)) + x233 + x235 - x236 - x237 + x238) + V{0.0277777777777778});
auto x6 = V{1}*x121*(x265 + x272 + x274) + x193*(x201 + x242 + x254) + V{-0.0277777777777778};
auto x7 = -(-V{1}*x121*(x265 + x277 + x278) + x193*(x142 - x194*((x276)*(x276)) + x248 - x250 - x252 + x80) + V{0.0277777777777778});
auto x8 = V{1}*x121*(x297 + x302 + x304) + x193*(x170 + x197 + x200 + x280 + x287) + V{-0.0277777777777778};
auto x9 = -(-V{1}*x121*(x297 + x306 + x307) + x193*(x174 - x194*((x305)*(x305)) + x283 - x284 - x285 + x80) + V{0.0277777777777778});
auto x10 = -V{1}*x121*(x116*x144 + x120*x144 + x153*x87 + x163 + x191*x84) + V{0.0555555555555556}*x308*(x125 + x143 + x197 + x199) + V{-0.0555555555555556};
auto x11 = -V{1}*x121*(x107*x176 + x120*x176 + x153*x92 + x182 + x190*x84) + V{0.0555555555555556}*x308*(x164 + x175 + x197 + x198 + V{1}) + V{-0.0555555555555556};
auto x12 = -V{1}*x121*(x107*x189 + x116*x189 + x190*x87 + x191*x92 + x192) + V{0.0555555555555556}*x308*(x183 + x188 + x200) + V{-0.0555555555555556};
auto x13 = V{1}*x121*(x230 + x239 + x310) - x193*(-x196 + x203 + x309) + V{-0.0277777777777778};
auto x14 = -(-V{1}*x121*(x228 + x240 + x310) + x193*(x171 - x194*((x231)*(x231)) - x233 - x235 + x236 + x237 + x309) + V{0.0277777777777778});
auto x15 = V{1}*x121*(x274 + x277 + x311) - x193*(-x242 + x254 + x309) + V{-0.0277777777777778};
auto x16 = -(-V{1}*x121*(x272 + x278 + x311) + x193*(x185 - x194*((x276)*(x276)) - x245 + x247 + x253 + x309) + V{0.0277777777777778});
auto x17 = V{1}*x121*(x304 + x306 + x312) - x193*(x238 - x280 + x287) + V{-0.0277777777777778};
auto x18 = -(-V{1}*x121*(x302 + x307 + x312) + x193*(x185 - x194*((x305)*(x305)) + x238 - x281 + x282 + x286) + V{0.0277777777777778});
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
return { x47, V{1}*x48*(x59 + x68 + x77) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
