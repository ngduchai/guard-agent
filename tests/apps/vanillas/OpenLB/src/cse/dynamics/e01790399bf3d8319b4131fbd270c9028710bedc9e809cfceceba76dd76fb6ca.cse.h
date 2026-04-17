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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::ThirdOrder, collision::ParameterFromCell<collision::LES::SMAGORINSKY, collision::SmagorinskyEffectiveOmega<collision::ThirdOrderRLB> > >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = cell.template getFieldComponent<olb::collision::LES::SMAGORINSKY>(0);
auto x20 = parameters.template get<descriptors::OMEGA>();
auto x21 = cell[15] + cell[17];
auto x22 = cell[12] + x21;
auto x23 = cell[11] + cell[18];
auto x24 = cell[10] + cell[14] + cell[16];
auto x25 = cell[2] + cell[8] + cell[9];
auto x26 = cell[13] + cell[3];
auto x27 = cell[0] + cell[1] + cell[4] + cell[5] + cell[6] + cell[7] + x22 + x23 + x24 + x25 + x26;
auto x28 = x27 + V{1};
auto x29 = V{1} / (x28);
auto x30 = V{0.333333333333333}*cell[13];
auto x31 = V{0.333333333333333}*cell[14];
auto x32 = V{0.333333333333333}*cell[4];
auto x33 = V{0.333333333333333}*cell[5];
auto x34 = V{0.666666666666667}*cell[12];
auto x35 = V{0.666666666666667}*cell[3];
auto x36 = V{1}*x29;
auto x37 = -cell[18];
auto x38 = -cell[3];
auto x39 = -cell[8];
auto x40 = cell[9] + x39;
auto x41 = x37 + x38 + x40;
auto x42 = -cell[6];
auto x43 = cell[7] + x42;
auto x44 = -cell[16] + x43;
auto x45 = x22 + x41 + x44;
auto x46 = ((x45)*(x45));
auto x47 = x36*x46;
auto x48 = V{0.333333333333333}*cell[0];
auto x49 = V{0.333333333333333}*cell[10];
auto x50 = V{0.333333333333333}*cell[1];
auto x51 = V{0.666666666666667}*cell[17];
auto x52 = V{0.666666666666667}*cell[18];
auto x53 = V{0.666666666666667}*cell[8];
auto x54 = V{0.666666666666667}*cell[9];
auto x55 = x48 + x49 + x50 - x51 - x52 - x53 - x54;
auto x56 = V{0.333333333333333}*cell[11];
auto x57 = V{0.333333333333333}*cell[2];
auto x58 = V{0.666666666666667}*cell[15];
auto x59 = V{0.666666666666667}*cell[16];
auto x60 = V{0.666666666666667}*cell[6];
auto x61 = V{0.666666666666667}*cell[7];
auto x62 = x56 + x57 - x58 - x59 - x60 - x61;
auto x63 = x30 + x31 + x32 + x33 - x34 - x35 + x47 + x55 + x62;
auto x64 = V{0.333333333333333}*cell[15];
auto x65 = V{0.333333333333333}*cell[16];
auto x66 = V{0.333333333333333}*cell[6];
auto x67 = V{0.333333333333333}*cell[7];
auto x68 = V{0.666666666666667}*cell[11];
auto x69 = V{0.666666666666667}*cell[2];
auto x70 = cell[13] + cell[17];
auto x71 = -cell[2];
auto x72 = -cell[9];
auto x73 = x23 + x39 + x71 + x72;
auto x74 = -cell[4];
auto x75 = cell[5] + x74;
auto x76 = -cell[14] + x75;
auto x77 = x70 + x73 + x76;
auto x78 = ((x77)*(x77));
auto x79 = x36*x78;
auto x80 = V{0.333333333333333}*cell[12];
auto x81 = V{0.333333333333333}*cell[3];
auto x82 = V{0.666666666666667}*cell[13];
auto x83 = V{0.666666666666667}*cell[14];
auto x84 = V{0.666666666666667}*cell[4];
auto x85 = V{0.666666666666667}*cell[5];
auto x86 = x80 + x81 - x82 - x83 - x84 - x85;
auto x87 = x55 + x64 + x65 + x66 + x67 - x68 - x69 + x79 + x86;
auto x88 = V{0.333333333333333}*cell[17];
auto x89 = V{0.333333333333333}*cell[18];
auto x90 = V{0.333333333333333}*cell[8];
auto x91 = V{0.333333333333333}*cell[9];
auto x92 = V{0.666666666666667}*cell[10];
auto x93 = V{0.666666666666667}*cell[1];
auto x94 = cell[13] + cell[15];
auto x95 = -cell[1];
auto x96 = -cell[7];
auto x97 = x42 + x95 + x96;
auto x98 = -cell[5] + x74;
auto x99 = x24 + x94 + x97 + x98;
auto x100 = ((x99)*(x99));
auto x101 = x100*x36;
auto x102 = x101 + x48 + x62 + x86 + x88 + x89 + x90 + x91 - x92 - x93;
auto x103 = x29*x99;
auto x104 = x103*x77;
auto x105 = -cell[13] + cell[14] + x104 + x75;
auto x106 = x103*x45;
auto x107 = -cell[15] + cell[16];
auto x108 = x106 + x107 + x43;
auto x109 = x29*x77;
auto x110 = x109*x45;
auto x111 = -cell[17];
auto x112 = cell[18] + x111;
auto x113 = x110 + x112 + x40;
auto x114 = V{1} - V{1} / (V{3.00000046417339}*util::sqrt(x29*((x19)*(x19))*util::sqrt(V{0.5}*((x102)*(x102)) + ((x105)*(x105)) + ((x108)*(x108)) + ((x113)*(x113)) + V{0.5}*((x63)*(x63)) + V{0.5}*((x87)*(x87))) + V{0.0277777691819762}/((x20)*(x20))) + V{0.5}/x20);
auto x115 = V{0.5}*x29;
auto x116 = V{1} / ((x28)*(x28));
auto x117 = V{1.5}*x116;
auto x118 = x117*x46;
auto x119 = x100*x117;
auto x120 = x117*x78;
auto x121 = x119 + x120 + V{-1};
auto x122 = x118 + x121;
auto x123 = x115*x99;
auto x124 = x105*x36;
auto x125 = x36*x45;
auto x126 = V{0.166666666666667}*x29;
auto x127 = V{6.93889390390723e-18}*cell[0];
auto x128 = V{0.0833333333333333}*cell[12];
auto x129 = V{0.0833333333333333}*cell[3];
auto x130 = V{0.0833333333333333}*x29;
auto x131 = -V{0.0833333333333333}*cell[13] - V{0.0833333333333333}*cell[14] - V{0.0833333333333333}*cell[4] - V{0.0833333333333333}*cell[5] + x127 + x128 + x129 - x130*x46;
auto x132 = V{0.0833333333333333}*cell[11];
auto x133 = V{0.0833333333333333}*cell[2];
auto x134 = -V{0.0833333333333333}*cell[15] - V{0.0833333333333333}*cell[16] - V{0.0833333333333333}*cell[6] - V{0.0833333333333333}*cell[7] - x130*x78 + x132 + x133;
auto x135 = -V{0.166666666666667}*cell[10] + V{0.166666666666667}*cell[17] + V{0.166666666666667}*cell[18] - V{0.166666666666667}*cell[1] + V{0.166666666666667}*cell[8] + V{0.166666666666667}*cell[9] + x100*x126 + x131 + x134;
auto x136 = x27 + V{1};
auto x137 = V{3}*x116;
auto x138 = x100*x137;
auto x139 = -x118;
auto x140 = V{1} - x120;
auto x141 = util::pow(x28, -3);
auto x142 = V{6.000003}*x141;
auto x143 = x142*x99;
auto x144 = V{2.999997}*x141;
auto x145 = x144*x77;
auto x146 = V{3}*cell[14];
auto x147 = V{3}*cell[16];
auto x148 = V{3}*cell[5];
auto x149 = V{3}*cell[7];
auto x150 = V{3}*cell[13] - V{3}*cell[4];
auto x151 = V{3}*cell[15] - V{3}*cell[6];
auto x152 = x29*(V{3}*cell[10] - V{3}*cell[1] + x146 + x147 - x148 - x149 + x150 + x151);
auto x153 = -x152;
auto x154 = x143*x78;
auto x155 = x100*x145;
auto x156 = x153 + x154 + x155;
auto x157 = x143*x46 + x145*x46 + x156;
auto x158 = x115*x77;
auto x159 = V{0.0833333333333333}*cell[10];
auto x160 = V{0.0833333333333333}*cell[1];
auto x161 = -V{0.0833333333333333}*cell[17] - V{0.0833333333333333}*cell[18] - V{0.0833333333333333}*cell[8] - V{0.0833333333333333}*cell[9] - x100*x130 + x159 + x160;
auto x162 = -V{0.166666666666667}*cell[11] + V{0.166666666666667}*cell[15] + V{0.166666666666667}*cell[16] - V{0.166666666666667}*cell[2] + V{0.166666666666667}*cell[6] + V{0.166666666666667}*cell[7] + x126*x78 + x131 + x161;
auto x163 = -x119;
auto x164 = x137*x78;
auto x165 = x142*x77;
auto x166 = x144*x99;
auto x167 = V{3}*cell[18];
auto x168 = V{3}*cell[9];
auto x169 = V{3}*cell[17] - V{3}*cell[8];
auto x170 = x29*(V{3}*cell[11] - V{3}*cell[2] - x146 + x148 + x150 + x167 - x168 + x169);
auto x171 = -x170;
auto x172 = x100*x165;
auto x173 = x166*x78;
auto x174 = x171 + x172 + x173;
auto x175 = x165*x46 + x166*x46 + x174;
auto x176 = x115*x45;
auto x177 = x36*x99;
auto x178 = x36*x77;
auto x179 = -V{0.166666666666667}*cell[12] + V{0.166666666666667}*cell[13] + V{0.166666666666667}*cell[14] - V{0.166666666666667}*cell[3] + V{0.166666666666667}*cell[4] + V{0.166666666666667}*cell[5] + x126*x46 + x127 + x134 + x161;
auto x180 = x137*x46;
auto x181 = x29*(V{3}*cell[12] - V{3}*cell[3] - x147 + x149 + x151 - x167 + x168 + x169);
auto x182 = -x181;
auto x183 = V{9}*x141;
auto x184 = x183*x45;
auto x185 = x100*x184 + x182 + x184*x78;
auto x186 = x140 + x163;
auto x187 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[10] + V{0.0277777777777778}*cell[11] + V{0.0277777777777778}*cell[12] + V{0.0277777777777778}*cell[13] + V{0.0277777777777778}*cell[14] + V{0.0277777777777778}*cell[15] + V{0.0277777777777778}*cell[16] + V{0.0277777777777778}*cell[17] + V{0.0277777777777778}*cell[18] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778}*cell[9] + V{0.0277777777777778};
auto x188 = V{4.5}*x116;
auto x189 = cell[10] + cell[16] + x97;
auto x190 = x188*((2*cell[13] - 2*cell[4] + x189 + x21 + x73)*(2*cell[13] - 2*cell[4] + x189 + x21 + x73));
auto x191 = x122 + x152;
auto x192 = V{18}*x141;
auto x193 = x100*x192*x77 + x170 - x183*x46*x77 - x183*x46*x99 + x192*x78*x99;
auto x194 = -x128;
auto x195 = -x129;
auto x196 = V{0.0416666666666667}*x29;
auto x197 = x196*x46;
auto x198 = V{0.25000025}*x103;
auto x199 = x198*x87;
auto x200 = V{0.5000005}*x105;
auto x201 = x109*x200;
auto x202 = V{2.49999999985601e-07}*x103;
auto x203 = x202*x63;
auto x204 = x29*x45;
auto x205 = V{4.99999999971202e-07}*x204;
auto x206 = x108*x205;
auto x207 = -V{0.0416666666666667}*cell[0];
auto x208 = V{0.0833333333333333}*x29;
auto x209 = V{0.0416666666666667}*cell[10] + V{6.93889390390723e-18}*cell[17] + V{6.93889390390723e-18}*cell[18] + V{0.0416666666666667}*cell[1] + V{6.93889390390723e-18}*cell[8] + V{6.93889390390723e-18}*cell[9] - x100*x208 + x207;
auto x210 = V{0.0416666666666667}*cell[11] + V{6.93889390390723e-18}*cell[15] + V{6.93889390390723e-18}*cell[16] + V{0.0416666666666667}*cell[2] + V{6.93889390390723e-18}*cell[6] + V{6.93889390390723e-18}*cell[7] - x208*x78;
auto x211 = x194 + x195 + x197 + x199 + x201 - x203 - x206 + x209 + x210;
auto x212 = V{0.25000025}*x109;
auto x213 = x102*x212;
auto x214 = x103*x200;
auto x215 = V{2.49999999985601e-07}*x109;
auto x216 = x215*x63;
auto x217 = x113*x205;
auto x218 = x213 + x214 - x216 - x217;
auto x219 = V{0.25}*x104;
auto x220 = V{0.375}*cell[13] - V{0.125}*cell[14] + V{0.375}*cell[4] - V{0.125}*cell[5] - x219;
auto x221 = -cell[11] + V{2}*cell[14] + cell[15] - V{2}*cell[5] + x111 + x189 + x25 + x37;
auto x222 = V{3.000006}*x141;
auto x223 = x222*x46*x77;
auto x224 = V{6.000012}*x141;
auto x225 = x224*x78*x99;
auto x226 = x222*x46*x99;
auto x227 = x100*x224*x77;
auto x228 = -x213 - x214 + x216 + x217;
auto x229 = -V{0.125}*cell[13] + V{0.375}*cell[14] - V{0.125}*cell[4] + V{0.375}*cell[5] + x219;
auto x230 = cell[10] + cell[14] + x95 + x98;
auto x231 = x188*((cell[12] + 2*cell[15] - 2*cell[6] + x230 + x41 + x70)*(cell[12] + 2*cell[15] - 2*cell[6] + x230 + x41 + x70));
auto x232 = x141*x45;
auto x233 = V{9.000009}*x232;
auto x234 = x100*x233;
auto x235 = V{8.99999999948164e-06}*x232;
auto x236 = x235*x78;
auto x237 = x181 + x234 - x236;
auto x238 = V{5.999994}*x141;
auto x239 = x238*x46*x77;
auto x240 = V{12.000006}*x141;
auto x241 = x240*x46*x99;
auto x242 = -x154;
auto x243 = -x155;
auto x244 = x191 + x239 + x241 + x242 + x243;
auto x245 = -x132;
auto x246 = -x133;
auto x247 = x196*x78;
auto x248 = x198*x63;
auto x249 = V{0.5000005}*x108;
auto x250 = x204*x249;
auto x251 = x202*x87;
auto x252 = V{4.99999999971202e-07}*x109;
auto x253 = x105*x252;
auto x254 = V{0.0416666666666667}*cell[12] + V{6.93889390390723e-18}*cell[13] + V{6.93889390390723e-18}*cell[14] + V{0.0416666666666667}*cell[3] + V{6.93889390390723e-18}*cell[4] + V{6.93889390390723e-18}*cell[5] - x208*x46;
auto x255 = x209 + x245 + x246 + x247 + x248 + x250 - x251 - x253 + x254;
auto x256 = V{0.25000025}*x204;
auto x257 = x102*x256;
auto x258 = x103*x249;
auto x259 = V{2.49999999985601e-07}*x204;
auto x260 = x259*x87;
auto x261 = x113*x252;
auto x262 = x257 + x258 - x260 - x261;
auto x263 = V{0.25}*x106;
auto x264 = V{0.375}*cell[15] - V{0.125}*cell[16] + V{0.375}*cell[6] - V{0.125}*cell[7] - x263;
auto x265 = -cell[12] + x26;
auto x266 = V{2}*cell[16] - V{2}*cell[7] + cell[8] + x112 + x230 + x265 + x72;
auto x267 = -x257 - x258 + x260 + x261;
auto x268 = -V{0.125}*cell[15] + V{0.375}*cell[16] - V{0.125}*cell[6] + V{0.375}*cell[7] + x263;
auto x269 = cell[11] + x71 + x76;
auto x270 = x188*((cell[12] + 2*cell[17] - 2*cell[8] + x269 + x38 + x44 + x94)*(cell[12] + 2*cell[17] - 2*cell[8] + x269 + x38 + x44 + x94));
auto x271 = x233*x78;
auto x272 = x100*x235;
auto x273 = x181 + x271 - x272;
auto x274 = x238*x46*x99;
auto x275 = x240*x46*x77;
auto x276 = -x172;
auto x277 = -x173;
auto x278 = x122 + x170;
auto x279 = x274 + x275 + x276 + x277 + x278;
auto x280 = -x159;
auto x281 = -x160;
auto x282 = x100*x196;
auto x283 = x212*x63;
auto x284 = V{0.5000005}*x113;
auto x285 = x204*x284;
auto x286 = x102*x215;
auto x287 = V{4.99999999971202e-07}*x103;
auto x288 = x105*x287;
auto x289 = x207 + x210 + x254 + x280 + x281 + x282 + x283 + x285 - x286 - x288;
auto x290 = x256*x87;
auto x291 = x109*x284;
auto x292 = x102*x259;
auto x293 = x108*x287;
auto x294 = x290 + x291 - x292 - x293;
auto x295 = V{0.25}*x110;
auto x296 = V{0.375}*cell[17] - V{0.125}*cell[18] + V{0.375}*cell[8] - V{0.125}*cell[9] - x295;
auto x297 = V{2}*cell[18] + cell[6] - V{2}*cell[9] + x107 + x265 + x269 + x96;
auto x298 = -x290 - x291 + x292 + x293;
auto x299 = -V{0.125}*cell[17] + V{0.375}*cell[18] - V{0.125}*cell[8] + V{0.375}*cell[9] + x295;
auto x300 = -x48;
auto x301 = x300 - x49 - x50 + x51 + x52 + x53 + x54;
auto x302 = -x80 - x81 + x82 + x83 + x84 + x85;
auto x303 = x301 + x302 - x64 - x65 - x66 - x67 + x68 + x69 - x79;
auto x304 = -x56 - x57 + x58 + x59 + x60 + x61;
auto x305 = -x30 + x301 + x304 - x31 - x32 - x33 + x34 + x35 - x47;
auto x306 = -x105;
auto x307 = -x108;
auto x308 = V{0.0555555555555556}*cell[0] + V{0.0555555555555556}*cell[10] + V{0.0555555555555556}*cell[11] + V{0.0555555555555556}*cell[12] + V{0.0555555555555556}*cell[13] + V{0.0555555555555556}*cell[14] + V{0.0555555555555556}*cell[15] + V{0.0555555555555556}*cell[16] + V{0.0555555555555556}*cell[17] + V{0.0555555555555556}*cell[18] + V{0.0555555555555556}*cell[1] + V{0.0555555555555556}*cell[2] + V{0.0555555555555556}*cell[3] + V{0.0555555555555556}*cell[4] + V{0.0555555555555556}*cell[5] + V{0.0555555555555556}*cell[6] + V{0.0555555555555556}*cell[7] + V{0.0555555555555556}*cell[8] + V{0.0555555555555556}*cell[9] + V{0.0555555555555556};
auto x309 = x118 + V{-1};
auto x310 = -x101 + x300 + x302 + x304 - x88 - x89 - x90 - x91 + x92 + x93;
auto x311 = -x113;
auto x312 = x194 + x195 + x197 - x199 - x201 + x203 + x206 + x209 + x210;
auto x313 = x139 + x186;
auto x314 = x152 + x313;
auto x315 = x209 + x245 + x246 + x247 - x248 - x250 + x251 + x253 + x254;
auto x316 = x207 + x210 + x254 + x280 + x281 + x282 - x283 - x285 + x286 + x288;
auto x0 = -V{1}*x114*(-V{0.5}*cell[0] + V{4.16333634234434e-17}*cell[10] + V{4.16333634234434e-17}*cell[11] + V{4.16333634234434e-17}*cell[12] + V{0.5}*cell[13] + V{0.5}*cell[14] + V{0.5}*cell[15] + V{0.5}*cell[16] + V{0.5}*cell[17] + V{0.5}*cell[18] + V{4.16333634234434e-17}*cell[1] + V{4.16333634234434e-17}*cell[2] + V{4.16333634234434e-17}*cell[3] + V{0.5}*cell[4] + V{0.5}*cell[5] + V{0.5}*cell[6] + V{0.5}*cell[7] + V{0.5}*cell[8] + V{0.5}*cell[9] - x100*x115 - x115*x46 - x115*x78) - x122*(x30 + x31 + x32 + x33 + x48 + x49 + x50 + x56 + x57 + x64 + x65 + x66 + x67 + x80 + x81 + x88 + x89 + x90 + x91 + V{0.333333333333333}) + V{-0.333333333333333};
auto x1 = -V{1}*x114*(x108*x125 + x123*x63 + x123*x87 + x124*x77 + x135) + V{0.0555555555555556}*x136*(x138 + x139 + x140 + x157) + V{-0.0555555555555556};
auto x2 = -V{1}*x114*(x102*x158 + x113*x125 + x124*x99 + x158*x63 + x162) + V{0.0555555555555556}*x136*(x139 + x163 + x164 + x175 + V{1}) + V{-0.0555555555555556};
auto x3 = -V{1}*x114*(x102*x176 + x108*x177 + x113*x178 + x176*x87 + x179) + V{0.0555555555555556}*x136*(x180 + x185 + x186) + V{-0.0555555555555556};
auto x4 = V{1}*x114*(x211 + x218 + x220) - x187*(-x190 + x191 + x193) + V{-0.0277777777777778};
auto x5 = -(-V{1}*x114*(x211 + x228 + x229) + x187*(x171 - x188*((x221)*(x221)) + x191 + x223 + x225 - x226 - x227) + V{0.0277777777777778});
auto x6 = V{1}*x114*(x255 + x262 + x264) - x187*(-x231 + x237 + x244) + V{-0.0277777777777778};
auto x7 = -(-V{1}*x114*(x255 + x267 + x268) + x187*(x182 - x188*((x266)*(x266)) - x234 + x236 + x244) + V{0.0277777777777778});
auto x8 = V{1}*x114*(x289 + x294 + x296) - x187*(-x270 + x273 + x279) + V{-0.0277777777777778};
auto x9 = -(-V{1}*x114*(x289 + x298 + x299) + x187*(x182 - x188*((x297)*(x297)) - x271 + x272 + x279) + V{0.0277777777777778});
auto x10 = -V{1}*x114*(x123*x303 + x123*x305 + x125*x307 + x135 + x178*x306) - x308*(x120 - x138 + x157 + x309) + V{-0.0555555555555556};
auto x11 = -V{1}*x114*(x125*x311 + x158*x305 + x158*x310 + x162 + x177*x306) - x308*(x119 - x164 + x175 + x309) + V{-0.0555555555555556};
auto x12 = -V{1}*x114*(x176*x303 + x176*x310 + x177*x307 + x178*x311 + x179) - x308*(x121 - x180 + x185) + V{-0.0555555555555556};
auto x13 = V{1}*x114*(x220 + x228 + x312) + x187*(x190 + x193 + x314) + V{-0.0277777777777778};
auto x14 = -(-V{1}*x114*(x218 + x229 + x312) + x187*(x153 - x188*((x221)*(x221)) - x223 - x225 + x226 + x227 + x278) + V{0.0277777777777778});
auto x15 = V{1}*x114*(x264 + x267 + x315) + x187*(x231 + x237 + x239 + x241 + x242 + x243 + x314) + V{-0.0277777777777778};
auto x16 = -(-V{1}*x114*(x262 + x268 + x315) + x187*(x122 + x156 - x188*((x266)*(x266)) + x237 - x239 - x241) + V{0.0277777777777778});
auto x17 = V{1}*x114*(x296 + x298 + x316) + x187*(x170 + x270 + x273 + x274 + x275 + x276 + x277 + x313) + V{-0.0277777777777778};
auto x18 = -(-V{1}*x114*(x294 + x299 + x316) + x187*(x122 + x174 - x188*((x297)*(x297)) + x273 - x274 - x275) + V{0.0277777777777778});
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
return { x28, V{1}*x116*(x100 + x46 + x78) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
