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
struct CSE<dynamics::Tuple<T, descriptors::D3Q27<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::SmagorinskyEffectiveOmega<collision::BGK>, forcing::Guo<momenta::ForcedWithStress> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x30 = parameters.template get<descriptors::OMEGA>();
auto x31 = parameters.template get<collision::LES::SMAGORINSKY>();
auto x28 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x27 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x29 = cell.template getFieldComponent<olb::descriptors::FORCE>(2);
auto x32 = cell[13] + cell[1] + cell[5] + cell[7];
auto x33 = cell[18] + cell[25] + cell[2] + cell[9];
auto x34 = cell[10] + cell[20] + cell[22] + cell[24] + cell[3];
auto x35 = cell[0] + cell[11] + cell[12] + cell[14] + cell[15] + cell[16] + cell[17] + cell[19] + cell[21] + cell[23] + cell[26] + cell[4] + cell[6] + cell[8] + x32 + x33 + x34;
auto x36 = x35 + V{1};
auto x37 = V{1} / (x36);
auto x38 = -cell[23];
auto x39 = cell[10] + cell[11] - cell[17] - cell[24] + cell[4] + x38;
auto x40 = cell[12] - cell[19] - cell[25] + cell[6];
auto x41 = -cell[14] - cell[18] - cell[20] - cell[26] + x32 + x39 + x40;
auto x42 = x37*(x35 + V{1});
auto x43 = V{0.666666666666667}*cell[10];
auto x44 = V{0.666666666666667}*cell[11];
auto x45 = V{0.666666666666667}*cell[12];
auto x46 = V{0.666666666666667}*cell[13];
auto x47 = V{0.666666666666667}*cell[23];
auto x48 = V{0.666666666666667}*cell[24];
auto x49 = V{0.666666666666667}*cell[25];
auto x50 = V{0.666666666666667}*cell[26];
auto x51 = -V{0.333333333333333}*cell[0];
auto x52 = -V{0.333333333333333}*cell[16] + V{0.666666666666667}*cell[17] + V{0.666666666666667}*cell[18] - V{0.333333333333333}*cell[3] + V{0.666666666666667}*cell[4] + V{0.666666666666667}*cell[5] + x43 + x44 + x45 + x46 + x47 + x48 + x49 + x50 + x51;
auto x53 = -V{0.333333333333333}*cell[15] + V{0.666666666666667}*cell[19] + V{0.666666666666667}*cell[20] - V{0.333333333333333}*cell[2] + V{0.666666666666667}*cell[6] + V{0.666666666666667}*cell[7];
auto x54 = -cell[13] - cell[21] + cell[26] + cell[8];
auto x55 = -cell[12] - cell[15] - cell[22] - cell[5] + x33 + x39 + x54;
auto x56 = -V{0.333333333333333}*cell[14] - V{0.333333333333333}*cell[1] + V{0.666666666666667}*cell[21] + V{0.666666666666667}*cell[22] + V{0.666666666666667}*cell[8] + V{0.666666666666667}*cell[9];
auto x57 = -cell[11] - cell[16] - cell[7] - cell[9] + x34 + x38 + x40 + x54;
auto x58 = V{1}*cell[18];
auto x59 = V{1}*cell[11];
auto x60 = -x59;
auto x61 = V{1}*cell[4];
auto x62 = x42*(x27*x55 + x28*x41);
auto x63 = x37*x55;
auto x64 = x41*x63;
auto x65 = V{1}*cell[12];
auto x66 = V{1}*cell[25];
auto x67 = V{1}*cell[10];
auto x68 = -x67;
auto x69 = -V{1}*cell[23];
auto x70 = x65 + x66 + x68 + x69;
auto x71 = V{1}*cell[13];
auto x72 = V{1}*cell[26];
auto x73 = x71 + x72;
auto x74 = V{1}*cell[5];
auto x75 = -V{1}*cell[17];
auto x76 = V{1}*cell[24];
auto x77 = -x76;
auto x78 = x74 + x75 + x77;
auto x79 = V{2}*cell[13];
auto x80 = V{2}*cell[26];
auto x81 = V{2}*cell[11];
auto x82 = V{2}*cell[24];
auto x83 = -V{2}*cell[10] + V{2}*cell[12] - V{2}*cell[23] + V{2}*cell[25];
auto x84 = V{1}*cell[22];
auto x85 = -x72;
auto x86 = V{1}*cell[8];
auto x87 = x42*(x28*x57 + x29*x55);
auto x88 = x57*x63;
auto x89 = x59 + x76;
auto x90 = V{1}*cell[9];
auto x91 = -x71;
auto x92 = -V{1}*cell[21];
auto x93 = x90 + x91 + x92;
auto x94 = V{1}*cell[20];
auto x95 = V{1}*cell[6];
auto x96 = -x65 + x69;
auto x97 = V{1}*cell[7];
auto x98 = -V{1}*cell[19];
auto x99 = -x66;
auto x100 = x97 + x98 + x99;
auto x101 = V{1} / (V{3.00000046417339}*util::sqrt(x37*((x31)*(x31))*util::sqrt(V{0.5}*(-x58 - x60 + x61 - V{0.5}*x62 - V{1}*x64 - x70 - x73 - x78)*(V{2}*cell[17] - V{2}*cell[18] + V{2}*cell[4] - V{2}*cell[5] - V{1}*x62 - V{2}*x64 - x79 - x80 + x81 + x82 - x83) + V{0.5}*(-x70 - x84 - x85 + x86 - V{0.5}*x87 - V{1}*x88 - x89 - x93)*(V{2}*cell[21] - V{2}*cell[22] + V{2}*cell[8] - V{2}*cell[9] + x79 + x80 - x81 - x82 - x83 - V{1}*x87 - V{2}*x88) + ((-x100 - V{1}*x37*x41*x57 - V{0.5}*x42*(x27*x57 + x29*x41) - x68 - x73 - x89 - x94 + x95 - x96)*(-x100 - V{1}*x37*x41*x57 - V{0.5}*x42*(x27*x57 + x29*x41) - x68 - x73 - x89 - x94 + x95 - x96)) + V{0.5}*((V{0.666666666666667}*cell[14] + V{0.666666666666667}*cell[1] - V{0.333333333333333}*cell[21] - V{0.333333333333333}*cell[22] - V{0.333333333333333}*cell[8] - V{0.333333333333333}*cell[9] - x27*x41*x42 - x37*((x41)*(x41)) + x52 + x53)*(V{0.666666666666667}*cell[14] + V{0.666666666666667}*cell[1] - V{0.333333333333333}*cell[21] - V{0.333333333333333}*cell[22] - V{0.333333333333333}*cell[8] - V{0.333333333333333}*cell[9] - x27*x41*x42 - x37*((x41)*(x41)) + x52 + x53)) + V{0.5}*((V{0.666666666666667}*cell[15] - V{0.333333333333333}*cell[19] - V{0.333333333333333}*cell[20] + V{0.666666666666667}*cell[2] - V{0.333333333333333}*cell[6] - V{0.333333333333333}*cell[7] - x28*x42*x55 - x37*((x55)*(x55)) + x52 + x56)*(V{0.666666666666667}*cell[15] - V{0.333333333333333}*cell[19] - V{0.333333333333333}*cell[20] + V{0.666666666666667}*cell[2] - V{0.333333333333333}*cell[6] - V{0.333333333333333}*cell[7] - x28*x42*x55 - x37*((x55)*(x55)) + x52 + x56)) + V{0.5}*((V{0.666666666666667}*cell[16] - V{0.333333333333333}*cell[17] - V{0.333333333333333}*cell[18] + V{0.666666666666667}*cell[3] - V{0.333333333333333}*cell[4] - V{0.333333333333333}*cell[5] - x29*x42*x57 - x37*((x57)*(x57)) + x43 + x44 + x45 + x46 + x47 + x48 + x49 + x50 + x51 + x53 + x56)*(V{0.666666666666667}*cell[16] - V{0.333333333333333}*cell[17] - V{0.333333333333333}*cell[18] + V{0.666666666666667}*cell[3] - V{0.333333333333333}*cell[4] - V{0.333333333333333}*cell[5] - x29*x42*x57 - x37*((x57)*(x57)) + x43 + x44 + x45 + x46 + x47 + x48 + x49 + x50 + x51 + x53 + x56))) + V{0.0277777691819762}/((x30)*(x30))) + V{0.5}/x30);
auto x102 = V{0.5}*x27;
auto x103 = x59 + x61 + x67;
auto x104 = x65 + x69 + x95;
auto x105 = -V{1}*cell[14] + V{1}*cell[1] + x100 + x103 + x104 - x58 + x71 + x78 + x85 - x94;
auto x106 = -x105*x37;
auto x107 = x102 + x106;
auto x108 = V{0.5}*x28;
auto x109 = x72 + x86;
auto x110 = -V{1}*cell[15] + V{1}*cell[2] + x103 + x109 + x58 + x66 - x74 + x75 + x77 - x84 + x93 + x96;
auto x111 = -x110*x37;
auto x112 = x108 + x111;
auto x113 = V{0.5}*x29;
auto x114 = -V{1}*cell[16] + V{1}*cell[3] + x104 + x109 + x60 + x67 + x76 + x84 - x90 + x91 + x92 + x94 - x97 + x98 + x99;
auto x115 = -x114*x37;
auto x116 = x113 + x115;
auto x117 = V{-1} + V{1.5}*((x107)*(x107)) + V{1.5}*((x112)*(x112)) + V{1.5}*((x116)*(x116));
auto x118 = V{1} - x101;
auto x119 = V{1.5}*x27;
auto x120 = V{3}*cell[13];
auto x121 = V{3}*cell[5];
auto x122 = V{3}*cell[7];
auto x123 = V{3}*cell[18];
auto x124 = V{3}*cell[20];
auto x125 = V{3}*cell[26];
auto x126 = V{3}*cell[10];
auto x127 = V{3}*cell[11];
auto x128 = -V{3}*cell[23];
auto x129 = V{3}*cell[24];
auto x130 = -V{3}*cell[17] + V{3}*cell[4] + x126 + x127 + x128 - x129;
auto x131 = V{3}*cell[12];
auto x132 = V{3}*cell[25];
auto x133 = -V{3}*cell[19] + V{3}*cell[6] + x131 - x132;
auto x134 = -V{3}*cell[14] + V{3}*cell[1] + x120 + x121 + x122 - x123 - x124 - x125 + x130 + x133;
auto x135 = -x134*x37;
auto x136 = x119 + x135;
auto x137 = x136*x27;
auto x138 = V{1.5}*x28;
auto x139 = V{3}*cell[9];
auto x140 = V{3}*cell[22];
auto x141 = -V{3}*cell[21] + V{3}*cell[8] - x120 + x125;
auto x142 = -V{3}*cell[15] + V{3}*cell[2] - x121 + x123 + x130 - x131 + x132 + x139 - x140 + x141;
auto x143 = -x142*x37;
auto x144 = x138 + x143;
auto x145 = x144*x28;
auto x146 = V{1.5}*x29;
auto x147 = -V{3}*cell[16] + V{3}*cell[3] - x122 + x124 + x126 - x127 + x128 + x129 + x133 - x139 + x140 + x141;
auto x148 = -x147*x37;
auto x149 = x146 + x148;
auto x150 = x149*x29;
auto x151 = x145 + x150;
auto x152 = V{1} - V{0.5}*x101;
auto x153 = V{0.0740740740740741}*cell[0] + V{0.0740740740740741}*cell[10] + V{0.0740740740740741}*cell[11] + V{0.0740740740740741}*cell[12] + V{0.0740740740740741}*cell[13] + V{0.0740740740740741}*cell[14] + V{0.0740740740740741}*cell[15] + V{0.0740740740740741}*cell[16] + V{0.0740740740740741}*cell[17] + V{0.0740740740740741}*cell[18] + V{0.0740740740740741}*cell[19] + V{0.0740740740740741}*cell[1] + V{0.0740740740740741}*cell[20] + V{0.0740740740740741}*cell[21] + V{0.0740740740740741}*cell[22] + V{0.0740740740740741}*cell[23] + V{0.0740740740740741}*cell[24] + V{0.0740740740740741}*cell[25] + V{0.0740740740740741}*cell[26] + V{0.0740740740740741}*cell[2] + V{0.0740740740740741}*cell[3] + V{0.0740740740740741}*cell[4] + V{0.0740740740740741}*cell[5] + V{0.0740740740740741}*cell[6] + V{0.0740740740740741}*cell[7] + V{0.0740740740740741}*cell[8] + V{0.0740740740740741}*cell[9] + V{0.0740740740740741};
auto x154 = V{2.25}*x27;
auto x155 = V{4.5}*cell[13];
auto x156 = V{4.5}*cell[5];
auto x157 = V{4.5}*cell[7];
auto x158 = V{4.5}*cell[18];
auto x159 = V{4.5}*cell[20];
auto x160 = V{4.5}*cell[26];
auto x161 = V{4.5}*cell[10];
auto x162 = V{4.5}*cell[11];
auto x163 = -V{4.5}*cell[23];
auto x164 = V{4.5}*cell[24];
auto x165 = -V{4.5}*cell[17] + V{4.5}*cell[4] + x161 + x162 + x163 - x164;
auto x166 = V{4.5}*cell[12];
auto x167 = V{4.5}*cell[25];
auto x168 = -V{4.5}*cell[19] + V{4.5}*cell[6] + x166 - x167;
auto x169 = -V{4.5}*cell[14] + V{4.5}*cell[1] + x155 + x156 + x157 - x158 - x159 - x160 + x165 + x168;
auto x170 = -x169*x37;
auto x171 = x154 + x170;
auto x172 = x117 + x136;
auto x173 = V{6}*cell[13];
auto x174 = V{6}*cell[5];
auto x175 = V{6}*cell[7];
auto x176 = V{6}*cell[18];
auto x177 = V{6}*cell[20];
auto x178 = V{6}*cell[26];
auto x179 = V{6}*cell[10];
auto x180 = V{6}*cell[11];
auto x181 = -V{6}*cell[23];
auto x182 = V{6}*cell[24];
auto x183 = -V{6}*cell[17] + V{6}*cell[4] + x179 + x180 + x181 - x182;
auto x184 = V{6}*cell[12];
auto x185 = V{6}*cell[25];
auto x186 = -V{6}*cell[19] + V{6}*cell[6] + x184 - x185;
auto x187 = -V{6}*cell[14] + V{6}*cell[1] + x173 + x174 + x175 - x176 - x177 - x178 + x183 + x186;
auto x188 = x187*x37;
auto x189 = V{3}*x27;
auto x190 = V{3} - x189;
auto x191 = x188 + x190;
auto x192 = V{0.0740740740740741}*x36;
auto x193 = V{2.25}*x28;
auto x194 = V{4.5}*cell[9];
auto x195 = V{4.5}*cell[22];
auto x196 = -V{4.5}*cell[21] + V{4.5}*cell[8] - x155 + x160;
auto x197 = -V{4.5}*cell[15] + V{4.5}*cell[2] - x156 + x158 + x165 - x166 + x167 + x194 - x195 + x196;
auto x198 = -x197*x37;
auto x199 = x193 + x198;
auto x200 = x117 + x144;
auto x201 = V{6}*cell[9];
auto x202 = V{6}*cell[22];
auto x203 = -V{6}*cell[21] + V{6}*cell[8] - x173 + x178;
auto x204 = -V{6}*cell[15] + V{6}*cell[2] - x174 + x176 + x183 - x184 + x185 + x201 - x202 + x203;
auto x205 = x204*x37;
auto x206 = V{3}*x28;
auto x207 = V{3} - x206;
auto x208 = x205 + x207;
auto x209 = x137 + x150;
auto x210 = V{2.25}*x29;
auto x211 = -V{4.5}*cell[16] + V{4.5}*cell[3] - x157 + x159 + x161 - x162 + x163 + x164 + x168 - x194 + x195 + x196;
auto x212 = -x211*x37;
auto x213 = x210 + x212;
auto x214 = x117 + x149;
auto x215 = -V{6}*cell[16] + V{6}*cell[3] - x175 + x177 + x179 - x180 + x181 + x182 + x186 - x201 + x202 + x203;
auto x216 = x215*x37;
auto x217 = V{3}*x29;
auto x218 = V{3} - x217;
auto x219 = x216 + x218;
auto x220 = x137 + x145;
auto x221 = V{0.0185185185185185}*cell[0] + V{0.0185185185185185}*cell[10] + V{0.0185185185185185}*cell[11] + V{0.0185185185185185}*cell[12] + V{0.0185185185185185}*cell[13] + V{0.0185185185185185}*cell[14] + V{0.0185185185185185}*cell[15] + V{0.0185185185185185}*cell[16] + V{0.0185185185185185}*cell[17] + V{0.0185185185185185}*cell[18] + V{0.0185185185185185}*cell[19] + V{0.0185185185185185}*cell[1] + V{0.0185185185185185}*cell[20] + V{0.0185185185185185}*cell[21] + V{0.0185185185185185}*cell[22] + V{0.0185185185185185}*cell[23] + V{0.0185185185185185}*cell[24] + V{0.0185185185185185}*cell[25] + V{0.0185185185185185}*cell[26] + V{0.0185185185185185}*cell[2] + V{0.0185185185185185}*cell[3] + V{0.0185185185185185}*cell[4] + V{0.0185185185185185}*cell[5] + V{0.0185185185185185}*cell[6] + V{0.0185185185185185}*cell[7] + V{0.0185185185185185}*cell[8] + V{0.0185185185185185}*cell[9] + V{0.0185185185185185};
auto x222 = x107 + x112;
auto x223 = x171 + x199;
auto x224 = x144 + x172;
auto x225 = V{4.5}*x28;
auto x226 = V{9}*cell[18];
auto x227 = V{9}*cell[25];
auto x228 = V{9}*cell[9];
auto x229 = V{9}*cell[12];
auto x230 = V{9}*cell[22];
auto x231 = V{9}*cell[5];
auto x232 = V{9}*cell[10];
auto x233 = V{9}*cell[11];
auto x234 = -V{9}*cell[23];
auto x235 = V{9}*cell[24];
auto x236 = -V{9}*cell[17] + V{9}*cell[4] + x232 + x233 + x234 - x235;
auto x237 = V{9}*cell[26];
auto x238 = V{9}*cell[13];
auto x239 = -V{9}*cell[21] + V{9}*cell[8] + x237 - x238;
auto x240 = -V{9}*cell[15] + V{9}*cell[2] + x226 + x227 + x228 - x229 - x230 - x231 + x236 + x239;
auto x241 = x240*x37;
auto x242 = -x225 + x241;
auto x243 = x191 + x242;
auto x244 = V{4.5}*x27;
auto x245 = V{9}*cell[7];
auto x246 = V{9}*cell[20];
auto x247 = -V{9}*cell[19] + V{9}*cell[6] - x227 + x229;
auto x248 = -V{9}*cell[14] + V{9}*cell[1] - x226 + x231 + x236 - x237 + x238 + x245 - x246 + x247;
auto x249 = x248*x37;
auto x250 = -x244 + x249;
auto x251 = x208 + x250;
auto x252 = x147*x37;
auto x253 = x146 - x252;
auto x254 = x253*x29;
auto x255 = V{0.0185185185185185}*x36;
auto x256 = -x108;
auto x257 = x107 - x111 + x256;
auto x258 = -x193;
auto x259 = x171 - x198 + x258;
auto x260 = -x138;
auto x261 = -x143 + x260;
auto x262 = x172 + x261;
auto x263 = x187*x37 + x190;
auto x264 = x225 - x240*x37;
auto x265 = -x205 + x206 + V{3};
auto x266 = x250 + x265;
auto x267 = V{4.5}*x29;
auto x268 = -V{9}*cell[16] + V{9}*cell[3] - x228 + x230 + x232 - x233 + x234 + x235 + x239 - x245 + x246 + x247;
auto x269 = x268*x37;
auto x270 = -x267 + x269;
auto x271 = x191 + x270;
auto x272 = x142*x37;
auto x273 = x138 - x272;
auto x274 = x273*x28;
auto x275 = x219 + x250;
auto x276 = -x113;
auto x277 = -x115 + x276;
auto x278 = x107 + x277;
auto x279 = -x210;
auto x280 = -x212 + x279;
auto x281 = x171 + x280;
auto x282 = -x146;
auto x283 = -x148 + x282;
auto x284 = x267 - x268*x37;
auto x285 = -x216 + x217 + V{3};
auto x286 = x250 + x285;
auto x287 = x112 + x116;
auto x288 = x199 + x213;
auto x289 = x149 + x200;
auto x290 = x134*x37;
auto x291 = x119 - x290;
auto x292 = x27*x291;
auto x293 = x208 + x270;
auto x294 = x219 + x242;
auto x295 = x112 + x277;
auto x296 = x199 + x280;
auto x297 = x204*x37 + x207;
auto x298 = x242 + x285;
auto x299 = V{0.00462962962962963}*cell[0] + V{0.00462962962962963}*cell[10] + V{0.00462962962962963}*cell[11] + V{0.00462962962962963}*cell[12] + V{0.00462962962962963}*cell[13] + V{0.00462962962962963}*cell[14] + V{0.00462962962962963}*cell[15] + V{0.00462962962962963}*cell[16] + V{0.00462962962962963}*cell[17] + V{0.00462962962962963}*cell[18] + V{0.00462962962962963}*cell[19] + V{0.00462962962962963}*cell[1] + V{0.00462962962962963}*cell[20] + V{0.00462962962962963}*cell[21] + V{0.00462962962962963}*cell[22] + V{0.00462962962962963}*cell[23] + V{0.00462962962962963}*cell[24] + V{0.00462962962962963}*cell[25] + V{0.00462962962962963}*cell[26] + V{0.00462962962962963}*cell[2] + V{0.00462962962962963}*cell[3] + V{0.00462962962962963}*cell[4] + V{0.00462962962962963}*cell[5] + V{0.00462962962962963}*cell[6] + V{0.00462962962962963}*cell[7] + V{0.00462962962962963}*cell[8] + V{0.00462962962962963}*cell[9] + V{0.00462962962962963};
auto x300 = V{0.00462962962962963}*x36;
auto x301 = x267 - x269;
auto x302 = x225 - x241;
auto x303 = x102 - x105*x37;
auto x304 = x114*x37;
auto x305 = x276 + x304;
auto x306 = x110*x37;
auto x307 = x256 + x306;
auto x308 = x154 - x169*x37;
auto x309 = x211*x37;
auto x310 = x279 + x309;
auto x311 = x197*x37;
auto x312 = x258 + x311;
auto x313 = ((x303)*(x303));
auto x314 = x108 - x306;
auto x315 = ((x314)*(x314));
auto x316 = x113 - x304;
auto x317 = ((x316)*(x316));
auto x318 = V{1.5}*x313 + V{1.5}*x315 + V{1.5}*x317 + V{-1};
auto x319 = x260 + x272;
auto x320 = x318 + x319;
auto x321 = x252 + x282;
auto x322 = x320 + x321;
auto x323 = -x119;
auto x324 = x290 + x318 + x323;
auto x325 = -x188 + x189 + V{3};
auto x326 = x193 - x311;
auto x327 = x210 - x309;
auto x328 = x303 + x314;
auto x329 = x308 + x326;
auto x330 = x319 + x324;
auto x331 = x302 + x325;
auto x332 = x244 - x249;
auto x333 = x265 + x332;
auto x334 = -x135 + x323;
auto x335 = x244 - x248*x37;
auto x336 = x242 + x325;
auto x337 = x303 + x316;
auto x338 = x308 + x327;
auto x339 = x321 + x324;
auto x340 = x285 + x332;
auto x341 = x215*x37 + x218;
auto x0 = V{1}*cell[0]*x118 - x101*(x117*(V{0.296296296296296}*cell[0] + V{0.296296296296296}*cell[10] + V{0.296296296296296}*cell[11] + V{0.296296296296296}*cell[12] + V{0.296296296296296}*cell[13] + V{0.296296296296296}*cell[14] + V{0.296296296296296}*cell[15] + V{0.296296296296296}*cell[16] + V{0.296296296296296}*cell[17] + V{0.296296296296296}*cell[18] + V{0.296296296296296}*cell[19] + V{0.296296296296296}*cell[1] + V{0.296296296296296}*cell[20] + V{0.296296296296296}*cell[21] + V{0.296296296296296}*cell[22] + V{0.296296296296296}*cell[23] + V{0.296296296296296}*cell[24] + V{0.296296296296296}*cell[25] + V{0.296296296296296}*cell[26] + V{0.296296296296296}*cell[2] + V{0.296296296296296}*cell[3] + V{0.296296296296296}*cell[4] + V{0.296296296296296}*cell[5] + V{0.296296296296296}*cell[6] + V{0.296296296296296}*cell[7] + V{0.296296296296296}*cell[8] + V{0.296296296296296}*cell[9] + V{0.296296296296296}) + V{0.296296296296296}) - V{0.296296296296296}*x152*x36*(x137 + x151);
auto x1 = V{1}*cell[1]*x118 - x101*(x153*(-x107*x171 + x172) + V{0.0740740740740741}) - x152*x192*(x151 + x191*x27);
auto x2 = V{1}*cell[2]*x118 - x101*(x153*(-x112*x199 + x200) + V{0.0740740740740741}) - x152*x192*(x208*x28 + x209);
auto x3 = V{1}*cell[3]*x118 - x101*(x153*(-x116*x213 + x214) + V{0.0740740740740741}) - x152*x192*(x219*x29 + x220);
auto x4 = V{1}*cell[4]*x118 - x101*(x221*(-x222*x223 + x224) + V{0.0185185185185185}) - x152*x255*(x243*x27 + x251*x28 + x254);
auto x5 = V{1}*cell[5]*x118 - x101*(x221*(-x257*x259 + x262) + V{0.0185185185185185}) - x152*x255*(x150 - x266*x28 + x27*(x263 + x264));
auto x6 = V{1}*cell[6]*x118 - x101*(x221*(x149 + x172 - (x107 + x116)*(x171 + x213)) + V{0.0185185185185185}) - x152*x255*(x27*x271 + x274 + x275*x29);
auto x7 = V{1}*cell[7]*x118 - x101*(x221*(x172 - x278*x281 + x283) + V{0.0185185185185185}) - x152*x255*(x145 + x27*(x263 + x284) - x286*x29);
auto x8 = V{1}*cell[8]*x118 - x101*(x221*(-x287*x288 + x289) + V{0.0185185185185185}) - x152*x255*(x28*x293 + x29*x294 + x292);
auto x9 = V{1}*cell[9]*x118 - x101*(x221*(x200 + x283 - x295*x296) + V{0.0185185185185185}) - x152*x255*(x137 + x28*(x284 + x297) - x29*x298);
auto x10 = V{1}*cell[10]*x118 - x101*(x299*(x149 + x224 - (x116 + x222)*(x213 + x223)) + V{0.00462962962962963}) - x152*x300*(x27*(x243 + x270) + x28*(x251 + x270) + x29*(x242 + x275));
auto x11 = V{1}*cell[11]*x118 - x101*(x299*(x224 + x283 - (-x222 - x277)*(-x223 - x280)) + V{0.00462962962962963}) - x152*x300*(x27*(x243 + x301) + x28*(x251 + x301) + x29*(-x242 - x286));
auto x12 = V{1}*cell[12]*x118 - x101*(x299*(x149 + x262 - (-x116 - x257)*(-x213 - x259)) + V{0.00462962962962963}) - x152*x300*(x27*(x271 + x302) + x28*(-x266 - x270) + x29*(x275 + x302));
auto x13 = -x101*(x299*(x291 + x322 - (-x303 - x305 - x307)*(-x308 - x310 - x312)) + V{0.00462962962962963}) + x118*x71 + x152*x300*(-x27*(x191 + x301 + x302) + x28*(x266 + x301) + x29*(x286 + x302));
auto x14 = V{1}*cell[14]*x118 - x101*(x153*(-x303*x308 + x324) + V{0.0740740740740741}) - x152*x192*(x151 - x27*x325);
auto x15 = V{1}*cell[15]*x118 - x101*(x153*(-x314*x326 + x320) + V{0.0740740740740741}) - x152*x192*(x209 - x265*x28);
auto x16 = V{1}*cell[16]*x118 - x101*(x153*(-x316*x327 + x318 + x321) + V{0.0740740740740741}) - x152*x192*(x220 - x285*x29);
auto x17 = V{1}*cell[17]*x118 - x101*(x221*(-x328*x329 + x330) + V{0.0185185185185185}) + x152*x255*(-x254 + x27*x331 + x28*x333);
auto x18 = V{1}*cell[18]*x118 - x101*(x221*(x200 - x257*x259 + x334) + V{0.0185185185185185}) - x152*x255*(x150 - x27*x336 + x28*(x297 + x335));
auto x19 = V{1}*cell[19]*x118 - x101*(x221*(-x337*x338 + x339) + V{0.0185185185185185}) + x152*x255*(x27*(x301 + x325) - x274 + x29*x340);
auto x20 = V{1}*cell[20]*x118 - x101*(x221*(x214 - x278*x281 + x334) + V{0.0185185185185185}) - x152*x255*(x145 - x27*(x270 + x325) + x29*(x335 + x341));
auto x21 = V{1}*cell[21]*x118 - x101*(x221*(x322 - (x314 + x316)*(x326 + x327)) + V{0.0185185185185185}) + x152*x255*(x28*(x265 + x301) + x29*(x285 + x302) - x292);
auto x22 = V{1}*cell[22]*x118 - x101*(x221*(x214 + x261 - x295*x296) + V{0.0185185185185185}) - x152*x255*(x137 - x28*(x265 + x270) + x29*(x264 + x341));
auto x23 = V{1}*cell[23]*x118 - x101*(x299*(x321 + x330 - (x316 + x328)*(x327 + x329)) + V{0.00462962962962963}) + x152*x300*(x27*(x301 + x331) + x28*(x301 + x333) + x29*(x302 + x340));
auto x24 = -x101*(x299*(x253 + x330 - (x305 + x328)*(x310 + x329)) + V{0.00462962962962963}) + x118*x76 + x152*x300*(x27*(x270 + x331) + x28*(x270 + x333) - x29*(x219 + x302 + x332));
auto x25 = -x101*(x299*(x273 + x339 - (x307 + x337)*(x312 + x338)) + V{0.00462962962962963}) + x118*x66 + x152*x300*(x27*(x301 + x336) - x28*(x208 + x301 + x332) + x29*(x298 + x332));
auto x26 = V{1}*cell[26]*x118 - x101*(x299*(x289 + x334 - (x102 + x106 - x287)*(x154 + x170 - x288)) + V{0.00462962962962963}) - x152*x300*(x27*(-x270 - x336) + x28*(x293 + x332) + x29*(x294 + x332));
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
cell[19] = x19;
cell[20] = x20;
cell[21] = x21;
cell[22] = x22;
cell[23] = x23;
cell[24] = x24;
cell[25] = x25;
cell[26] = x26;
return { x36, x313 + x315 + x317 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
