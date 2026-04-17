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
struct CSE<Dual<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, forcing::PlainGuo> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x20 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x21 = cell.template getFieldComponent<olb::descriptors::FORCE>(2);
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
auto x22 = x64 + V{-1};
auto x23 = V{0.5}*x64 + V{-1};
auto x24 = V{1.5}*x21;
auto x25 = x46 + x58 + x60;
auto x65 = x48 + x50 + x55;
auto x66 = x49 + x52 + x63;
auto x67 = x25 + x45 + x47 + x51 + x53 + x54 + x56 + x57 + x59 + x61 + x62 + x65 + x66;
auto x68 = x67 + V{1};
auto x69 = V{1} / (x68);
auto x70 = V{3}*x52;
auto x71 = V{3}*x63;
auto x72 = V{3}*x55;
auto x73 = V{3}*x60;
auto x74 = V{3}*x54 - V{3}*x62;
auto x75 = -V{3}*x53 + V{3}*x61;
auto x76 = x69*(V{3}*x49 - V{3}*x57 + x70 + x71 - x72 - x73 + x74 + x75);
auto x77 = x24 + x76;
auto x78 = x21*x77;
auto x79 = -x78;
auto x80 = V{3}*x19;
auto x81 = V{6}*x58;
auto x82 = V{6}*x60;
auto x83 = V{6}*x50;
auto x84 = V{6}*x52;
auto x85 = -V{6}*x51 + V{6}*x59;
auto x86 = -V{6}*x53 + V{6}*x61;
auto x87 = V{6}*x46 - V{6}*x47 + x81 + x82 - x83 - x84 + x85 + x86;
auto x88 = x69*x87;
auto x89 = x80 - x88;
auto x90 = x89 + V{3};
auto x91 = V{4.5}*x20;
auto x92 = V{9}*x50;
auto x93 = V{9}*x55;
auto x94 = V{9}*x58;
auto x95 = V{9}*x63;
auto x96 = -V{9}*x51 + V{9}*x59;
auto x97 = V{9}*x54 - V{9}*x62;
auto x98 = x69*(V{9}*x48 - V{9}*x56 + x92 + x93 - x94 - x95 + x96 + x97);
auto x99 = x91 + x98;
auto x100 = V{3}*x20;
auto x101 = V{6}*x55;
auto x102 = V{6}*x63;
auto x103 = V{6}*x54 - V{6}*x62;
auto x104 = x69*(x101 - x102 + x103 + V{6}*x48 - V{6}*x56 - x81 + x83 + x85);
auto x105 = x100 + x104;
auto x106 = x105 + V{3};
auto x107 = V{4.5}*x19;
auto x108 = V{9}*x60;
auto x109 = V{9}*x52;
auto x110 = -V{9}*x53 + V{9}*x61;
auto x111 = x108 - x109 + x110 + V{9}*x46 - V{9}*x47 - x92 + x94 + x96;
auto x112 = x111*x69;
auto x113 = x107 - x112;
auto x114 = V{0.0277777777777778}*cell[13];
auto x115 = V{0.0277777777777778}*x64;
auto x116 = V{0.5}*x20;
auto x117 = V{1}*x50;
auto x118 = V{1}*x55;
auto x119 = V{1}*x58;
auto x120 = V{1}*x63;
auto x121 = -V{1}*x51 + V{1}*x59;
auto x122 = V{1}*x54 - V{1}*x62;
auto x123 = x69*(x117 + x118 - x119 - x120 + x121 + x122 + V{1}*x48 - V{1}*x56);
auto x124 = V{0.5}*x19;
auto x125 = V{1}*x60;
auto x126 = V{1}*x52;
auto x127 = -V{1}*x53 + V{1}*x61;
auto x128 = -x117 + x119 + x121 + x125 - x126 + x127 + V{1}*x46 - V{1}*x47;
auto x129 = x124 - x128*x69;
auto x130 = -x116 - x123 + x129;
auto x131 = V{2.25}*x20;
auto x132 = V{4.5}*x50;
auto x133 = V{4.5}*x55;
auto x134 = V{4.5}*x58;
auto x135 = V{4.5}*x63;
auto x136 = -V{4.5}*x51 + V{4.5}*x59;
auto x137 = V{4.5}*x54 - V{4.5}*x62;
auto x138 = x69*(x132 + x133 - x134 - x135 + x136 + x137 + V{4.5}*x48 - V{4.5}*x56);
auto x139 = V{2.25}*x19;
auto x140 = V{4.5}*x60;
auto x141 = V{4.5}*x52;
auto x142 = -V{4.5}*x53 + V{4.5}*x61;
auto x143 = -x132 + x134 + x136 + x140 - x141 + x142 + V{4.5}*x46 - V{4.5}*x47;
auto x144 = x139 - x143*x69;
auto x145 = -x131 - x138 + x144;
auto x146 = V{1.5}*x20;
auto x147 = V{3}*x50;
auto x148 = V{3}*x58;
auto x149 = -V{3}*x51 + V{3}*x59;
auto x150 = x69*(x147 - x148 + x149 + V{3}*x48 - V{3}*x56 - x71 + x72 + x74);
auto x151 = x146 + x150;
auto x152 = x116 + x123;
auto x153 = V{1.5}*((x152)*(x152));
auto x154 = V{0.5}*x21;
auto x155 = x69*(-x118 + x120 + x122 - x125 + x126 + x127 + V{1}*x49 - V{1}*x57);
auto x156 = x154 + x155;
auto x157 = V{1.5}*((x156)*(x156));
auto x158 = x153 + x157 + V{-1};
auto x159 = x158 + V{1.5}*((x129)*(x129));
auto x160 = x151 + x159;
auto x161 = V{1.5}*x19;
auto x162 = -x161;
auto x163 = -x147 + x148 + x149 + V{3}*x46 - V{3}*x47 - x70 + x73 + x75;
auto x164 = -x163*x69;
auto x165 = x162 - x164;
auto x166 = x107 - x111*x69 + V{3};
auto x167 = -x100 - x104;
auto x168 = -x80;
auto x169 = x168 + x88;
auto x170 = x169 + V{-3};
auto x171 = V{0.0277777777777778}*cell[14];
auto x172 = x151*x20;
auto x173 = -x172;
auto x174 = V{4.5}*x21;
auto x175 = x69*(-x108 + x109 + x110 + V{9}*x49 - V{9}*x57 - x93 + x95 + x97);
auto x176 = x174 + x175;
auto x177 = V{3}*x21;
auto x178 = x69*(-x101 + x102 + x103 + V{6}*x49 - V{6}*x57 - x82 + x84 + x86);
auto x179 = x177 + x178;
auto x180 = x179 + V{3};
auto x181 = V{0.0277777777777778}*cell[15];
auto x182 = -x154 - x155;
auto x183 = x129 + x182;
auto x184 = V{2.25}*x21;
auto x185 = x69*(-x133 + x135 + x137 - x140 + x141 + x142 + V{4.5}*x49 - V{4.5}*x57);
auto x186 = -x184 - x185;
auto x187 = x144 + x186;
auto x188 = x159 + x77;
auto x189 = -x177 - x178;
auto x190 = V{0.0277777777777778}*cell[16];
auto x191 = x161 + x164;
auto x192 = x19*x191;
auto x193 = -x192;
auto x194 = V{0.0277777777777778}*x23;
auto x195 = x152 + x182;
auto x196 = x131 + x138;
auto x197 = x186 + x196;
auto x198 = -x146 - x150;
auto x199 = x99 + V{3};
auto x200 = x129 + x152;
auto x201 = x144 + x196;
auto x202 = x159 + x191;
auto x203 = x89 + V{-3};
auto x204 = x105 + V{-3};
auto x205 = V{0.0277777777777778}*cell[4];
auto x206 = x168 + x69*x87;
auto x207 = -x107 + x112;
auto x208 = V{0.0277777777777778}*cell[5];
auto x209 = x129 + x156;
auto x210 = x184 + x185;
auto x211 = x144 + x210;
auto x212 = x179 + V{-3};
auto x213 = V{0.0277777777777778}*cell[6];
auto x214 = -x24 - x76;
auto x215 = x176 + V{3};
auto x216 = V{0.0277777777777778}*cell[7];
auto x217 = x152 + x156;
auto x218 = x196 + x210;
auto x219 = x217*x218;
auto x220 = x172 + x78;
auto x221 = V{0.0555555555555556}*cell[10];
auto x222 = x192 + x78;
auto x223 = V{0.0555555555555556}*x23;
auto x224 = x172 + x192;
auto x225 = V{0.0555555555555556}*x64;
auto x226 = V{0.0555555555555556}*cell[1];
auto x227 = x152*x196;
auto x228 = x156*x210;
auto x229 = x128*x69;
auto x230 = x124 - x229;
auto x231 = x152 + x230;
auto x232 = x143*x69;
auto x233 = x139 - x232;
auto x234 = x196 + x233;
auto x235 = V{1.5}*((x230)*(x230));
auto x236 = -x153 - x157 - x235 + V{1};
auto x237 = x151 + x236;
auto x238 = x163*x69;
auto x239 = x161 - x238;
auto x240 = x156 + x230;
auto x241 = x210 + x233;
auto x242 = x236 + x77;
auto x243 = -x51 + x59;
auto x244 = x54 - x62;
auto x245 = x243 + x244 - x56 - x58 - x63 + x65;
auto x246 = V{0.333333333333333}*x20;
auto x247 = V{0.25}*x19;
auto x248 = V{0.166666666666667}*x20;
auto x249 = V{0.25}*x21;
auto x250 = V{1}*x23;
auto x251 = x250*(V{1}*cell[0]*x20 + V{0.166666666666667}*cell[10]*x20 - cell[11]*x246 + V{0.166666666666667}*cell[12]*x20 - cell[13]*x247 - cell[13]*x248 + V{0.25}*cell[14]*x19 - cell[14]*x248 + V{0.0833333333333333}*cell[15]*x20 + V{0.0833333333333333}*cell[16]*x20 - cell[17]*x248 - cell[17]*x249 + V{0.25}*cell[18]*x21 - cell[18]*x248 + V{0.166666666666667}*cell[1]*x20 - cell[2]*x246 + V{0.166666666666667}*cell[3]*x20 - cell[4]*x247 - cell[4]*x248 + V{0.25}*cell[5]*x19 - cell[5]*x248 + V{0.0833333333333333}*cell[6]*x20 + V{0.0833333333333333}*cell[7]*x20 - cell[8]*x248 - cell[8]*x249 + V{0.25}*cell[9]*x21 - cell[9]*x248);
auto x252 = -x53 + x61;
auto x253 = x244 + x252 - x55 - x57 - x60 + x66;
auto x254 = V{0.333333333333333}*x21;
auto x255 = V{0.166666666666667}*x21;
auto x256 = V{0.25}*x20;
auto x257 = x250*(V{1}*cell[0]*x21 + V{0.166666666666667}*cell[10]*x21 + V{0.166666666666667}*cell[11]*x21 - cell[12]*x254 + V{0.0833333333333333}*cell[13]*x21 + V{0.0833333333333333}*cell[14]*x21 - cell[15]*x247 - cell[15]*x255 + V{0.25}*cell[16]*x19 - cell[16]*x255 - cell[17]*x255 - cell[17]*x256 + V{0.25}*cell[18]*x20 - cell[18]*x255 + V{0.166666666666667}*cell[1]*x21 + V{0.166666666666667}*cell[2]*x21 - cell[3]*x254 + V{0.0833333333333333}*cell[4]*x21 + V{0.0833333333333333}*cell[5]*x21 - cell[6]*x247 - cell[6]*x255 + V{0.25}*cell[7]*x19 - cell[7]*x255 - cell[8]*x255 - cell[8]*x256 + V{0.25}*cell[9]*x20 - cell[9]*x255);
auto x258 = x243 + x25 + x252 - x47 - x50 - x52;
auto x259 = V{0.333333333333333}*x19;
auto x260 = V{0.166666666666667}*x19;
auto x261 = V{1}*cell[0]*x19 - cell[10]*x259 + V{0.166666666666667}*cell[11]*x19 + V{0.166666666666667}*cell[12]*x19 - cell[13]*x256 - cell[13]*x260 + V{0.25}*cell[14]*x20 - cell[14]*x260 - cell[15]*x249 - cell[15]*x260 + V{0.25}*cell[16]*x21 - cell[16]*x260 + V{0.0833333333333333}*cell[17]*x19 + V{0.0833333333333333}*cell[18]*x19 - cell[1]*x259 + V{0.166666666666667}*cell[2]*x19 + V{0.166666666666667}*cell[3]*x19 - cell[4]*x256 - cell[4]*x260 + V{0.25}*cell[5]*x20 - cell[5]*x260 - cell[6]*x249 - cell[6]*x260 + V{0.25}*cell[7]*x21 - cell[7]*x260 + V{0.0833333333333333}*cell[8]*x19 + V{0.0833333333333333}*cell[9]*x19;
auto x262 = V{0.0833333333333333}*cell[18];
auto x263 = V{0.0833333333333333}*cell[5];
auto x264 = V{0.0833333333333333}*cell[14];
auto x265 = V{0.0833333333333333}*cell[9];
auto x266 = V{0.125}*x195;
auto x267 = cell[18]*x266;
auto x268 = cell[9]*x266;
auto x269 = V{0.25}*x152;
auto x270 = V{0.0277777777777778}*x197;
auto x271 = cell[18]*x270;
auto x272 = cell[9]*x270;
auto x273 = V{0.0555555555555556}*x196;
auto x274 = -x124 + x229;
auto x275 = V{0.125}*cell[14]*(-x152 - x274);
auto x276 = V{0.125}*cell[5]*x130;
auto x277 = V{1}*cell[0] + V{0.166666666666667}*cell[10] + V{0.166666666666667}*cell[11] + V{0.166666666666667}*cell[12] + V{0.0833333333333333}*cell[13] + V{0.0833333333333333}*cell[14] + V{0.0833333333333333}*cell[15] + V{0.0833333333333333}*cell[16] + V{0.0833333333333333}*cell[17] + V{0.0833333333333333}*cell[18] + V{0.166666666666667}*cell[1] + V{0.166666666666667}*cell[2] + V{0.166666666666667}*cell[3] + V{0.0833333333333333}*cell[4] + V{0.0833333333333333}*cell[5] + V{0.0833333333333333}*cell[6] + V{0.0833333333333333}*cell[7] + V{0.0833333333333333}*cell[8] + V{0.0833333333333333}*cell[9];
auto x278 = -x139 + x232;
auto x279 = x171*(-x196 - x278);
auto x280 = x145*x208;
auto x281 = V{0.125}*cell[13]*x231 + V{0.0833333333333333}*cell[13] + V{0.125}*cell[4]*x200 - V{0.0833333333333333}*cell[4] + x114*x234 + x201*x205;
auto x282 = V{0.125}*x217;
auto x283 = V{0.0277777777777778}*x218;
auto x284 = cell[17]*x282 + cell[17]*x283 + V{0.0833333333333333}*cell[17] + cell[8]*x282 + cell[8]*x283 - V{0.0833333333333333}*cell[8];
auto x285 = cell[11]*x269 + cell[11]*x273 + V{0.166666666666667}*cell[11] + cell[2]*x269 + cell[2]*x273 - V{0.166666666666667}*cell[2] - x152*x277 + x262 + x263 - x264 - x265 + x267 + x268 + x271 + x272 - x275 - x276 - x279 - x280 + x281 + x284;
auto x286 = V{1} / ((x68)*(x68));
auto x287 = x67 + V{1};
auto x288 = V{1}*x287*x64;
auto x289 = x286*x288;
auto x290 = V{0.0833333333333333}*cell[7];
auto x291 = V{0.0833333333333333}*cell[16];
auto x292 = V{0.25}*x156;
auto x293 = V{0.0555555555555556}*x210;
auto x294 = V{0.125}*cell[16]*(-x156 - x274);
auto x295 = V{0.125}*cell[7]*x183;
auto x296 = x190*(-x210 - x278);
auto x297 = x187*x216;
auto x298 = V{0.125}*cell[15]*x240 + V{0.0833333333333333}*cell[15] + V{0.125}*cell[6]*x209 - V{0.0833333333333333}*cell[6] + x181*x241 + x211*x213;
auto x299 = cell[12]*x292 + cell[12]*x293 + V{0.166666666666667}*cell[12] + cell[3]*x292 + cell[3]*x293 - V{0.166666666666667}*cell[3] - x156*x277 - x262 + x265 - x267 - x268 - x271 - x272 + x284 + x290 - x291 - x294 - x295 - x296 - x297 + x298;
auto x300 = V{0.25}*cell[10]*x230 + V{0.166666666666667}*cell[10] + V{0.25}*cell[1]*x129 - V{0.166666666666667}*cell[1] + x144*x226 + x221*x233 - x230*x277 - x263 + x264 + x275 + x276 + x279 + x280 + x281 - x290 + x291 + x294 + x295 + x296 + x297 + x298;
auto x301 = V{0.333333333333333}*cell[0]*x159*x64 - V{0.333333333333333}*cell[0]*x23*(x192 + x220) - V{0.0555555555555556}*cell[10]*x64*(-x158 - x162 + x230*x233 - x235 - x238) + cell[11]*x223*(x106*x20 - x222) - V{0.0555555555555556}*cell[11]*x64*(x227 + x237) + cell[12]*x223*(x180*x21 - x224) - V{0.0555555555555556}*cell[12]*x64*(x228 + x242) - V{0.0277777777777778}*cell[13]*x64*(x231*x234 + x237 + x239) + cell[14]*x115*(-x130*x145 + x160 + x165) - V{0.0277777777777778}*cell[15]*x64*(x239 + x240*x241 + x242) + cell[16]*x115*(x165 - x183*x187 + x188) + cell[17]*x194*(x193 + x20*(x106 + x176) + x21*(x180 + x99)) - V{0.0277777777777778}*cell[17]*x64*(x219 + x237 + x77) + cell[18]*x115*(x188 - x195*x197 + x198) + cell[18]*x194*(-x192 + x20*(x106 - x174 - x175) - x21*(x189 + x199)) + cell[1]*x225*(-x129*x144 + x202) + cell[2]*x223*(x20*x204 - x222) + cell[2]*x225*(x160 - x227) + cell[3]*x223*(x21*x212 - x224) + cell[3]*x225*(x188 - x228) + cell[4]*x115*(x151 - x200*x201 + x202) + cell[5]*x115*(-x130*x145 + x198 + x202) + cell[6]*x115*(x202 - x209*x211 + x77) + cell[7]*x115*(-x183*x187 + x202 + x214) + cell[8]*x115*(x160 - x219 + x77) + cell[8]*x194*(x193 + x20*(x176 + x204) + x21*(x212 + x99)) + cell[9]*x115*(x160 - x195*x197 + x214) + cell[9]*x194*(-x192 - x20*(x167 + x215) + x21*(x180 - x91 - x98)) + x114*x23*(x19*(x90 + x99) + x20*(x106 + x113) + x79) + x171*x23*(x19*(-x170 - x99) - x20*(x166 + x167) - x78) + x181*x23*(x173 + x19*(x176 + x90) + x21*(x113 + x180)) + x190*x23*(-x172 + x19*(-x170 - x176) - x21*(x166 + x189)) + x205*x23*(x19*(x203 + x99) + x20*(x113 + x204) + x79) + x208*x23*(-x19*(x199 + x206) + x20*(x106 + x207) - x78) + x213*x23*(x173 + x19*(x176 + x203) + x21*(x113 + x212)) + x216*x23*(-x172 - x19*(x206 + x215) + x21*(x180 + x207)) + x221*x23*(x19*x90 - x220) + x226*x23*(x19*(-x169 + V{-3}) - x220) - V{1}*x23*x258*x261*x69 + x245*x251*x69 + x245*x285*x289 + x253*x257*x69 + x253*x289*x299 - V{1}*x258*x286*x287*x300*x64;
auto x302 = V{1}*cell[0]*x22 + x26 + x301;
auto x303 = V{1}*x22;
auto x304 = x250*x261;
auto x305 = x288*x69;
auto x306 = x300*x305;
auto x307 = x301 - x304 - x306;
auto x308 = cell[10]*x303 + x28 + x307;
auto x309 = x285*x305;
auto x310 = -x251 - x309;
auto x311 = x301 + x310;
auto x312 = cell[11]*x303 + x29 + x311;
auto x313 = x299*x305;
auto x314 = -x257 - x313;
auto x315 = x301 + x314;
auto x316 = cell[12]*x303 + x30 + x315;
auto x317 = cell[13]*x303 + x307 + x31 + x310;
auto x318 = x251 + x309;
auto x319 = cell[14]*x303 + x307 + x318 + x32;
auto x320 = cell[15]*x303 + x307 + x314 + x33;
auto x321 = x257 + x313;
auto x322 = cell[16]*x303 + x307 + x321 + x34;
auto x323 = cell[17]*x303 + x311 + x314 + x35;
auto x324 = cell[18]*x303 + x311 + x321 + x36;
auto x325 = x304 + x306;
auto x326 = x301 + x325;
auto x327 = cell[1]*x303 + x27 + x326;
auto x328 = x301 + x318;
auto x329 = cell[2]*x303 + x328 + x37;
auto x330 = cell[3]*x303 + x301 + x321 + x38;
auto x331 = cell[4]*x303 + x318 + x326 + x39;
auto x332 = cell[5]*x303 + x311 + x325 + x40;
auto x333 = cell[6]*x303 + x321 + x326 + x41;
auto x334 = cell[7]*x303 + x315 + x325 + x42;
auto x335 = cell[8]*x303 + x321 + x328 + x43;
auto x336 = cell[9]*x303 + x315 + x318 + x44;
cell[0] = -x302;
cell[10] = -x308;
cell[11] = -x312;
cell[12] = -x316;
cell[13] = -x317;
cell[14] = -x319;
cell[15] = -x320;
cell[16] = -x322;
cell[17] = -x323;
cell[18] = -x324;
cell[1] = -x327;
cell[2] = -x329;
cell[3] = -x330;
cell[4] = -x331;
cell[5] = -x332;
cell[6] = -x333;
cell[7] = -x334;
cell[8] = -x335;
cell[9] = -x336;
return { V{1} - x302, ((x302)*(x302)) + ((x308)*(x308)) + ((x312)*(x312)) + ((x316)*(x316)) + ((x317)*(x317)) + ((x319)*(x319)) + ((x320)*(x320)) + ((x322)*(x322)) + ((x323)*(x323)) + ((x324)*(x324)) + ((x327)*(x327)) + ((x329)*(x329)) + ((x330)*(x330)) + ((x331)*(x331)) + ((x332)*(x332)) + ((x333)*(x333)) + ((x334)*(x334)) + ((x335)*(x335)) + ((x336)*(x336)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
