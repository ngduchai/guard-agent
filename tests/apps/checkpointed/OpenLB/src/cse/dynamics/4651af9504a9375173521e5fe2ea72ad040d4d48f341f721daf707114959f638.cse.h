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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::MovingPorousMomentumCombinationNoWM<momenta::BulkMomentum>, momenta::BulkStress, momenta::DefineToNEq>, equilibria::ThirdOrder, collision::SmagorinskyEffectiveOmega<collision::ThirdOrderRLB> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x23 = parameters.template get<descriptors::OMEGA>();
auto x19 = cell.template getFieldComponent<olb::descriptors::POROSITY>(0);
auto x24 = parameters.template get<collision::LES::SMAGORINSKY>();
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x22 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x25 = V{0.5}/x23;
auto x26 = V{0.0277777691819762}/((x23)*(x23));
auto x27 = cell[12] + cell[17] + cell[7];
auto x28 = cell[11] + cell[13] + cell[18];
auto x29 = cell[10] + cell[14] + cell[16];
auto x30 = cell[0] + cell[15] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[8] + cell[9] + x27 + x28 + x29;
auto x31 = x30 + V{1};
auto x32 = V{1} / (x31);
auto x33 = ((x24)*(x24));
auto x34 = x19 + V{-1};
auto x35 = -x34;
auto x36 = x22*x35;
auto x37 = -cell[8];
auto x38 = cell[9] + x37;
auto x39 = cell[15] - cell[6];
auto x40 = -cell[16] - cell[18] - cell[3] + x27 + x38 + x39;
auto x41 = x19*x32;
auto x42 = x40*x41;
auto x43 = V{1}*x42;
auto x44 = x36 + x43;
auto x45 = ((x44)*(x44));
auto x46 = x31*x45;
auto x47 = V{0.333333333333333}*cell[13];
auto x48 = V{0.333333333333333}*cell[14];
auto x49 = V{0.333333333333333}*cell[4];
auto x50 = V{0.333333333333333}*cell[5];
auto x51 = V{0.666666666666667}*cell[12];
auto x52 = V{0.666666666666667}*cell[3];
auto x53 = V{0.333333333333333}*cell[0];
auto x54 = V{0.333333333333333}*cell[10];
auto x55 = V{0.333333333333333}*cell[1];
auto x56 = V{0.666666666666667}*cell[17];
auto x57 = V{0.666666666666667}*cell[18];
auto x58 = V{0.666666666666667}*cell[8];
auto x59 = V{0.666666666666667}*cell[9];
auto x60 = x53 + x54 + x55 - x56 - x57 - x58 - x59;
auto x61 = V{0.333333333333333}*cell[11];
auto x62 = V{0.333333333333333}*cell[2];
auto x63 = V{0.666666666666667}*cell[15];
auto x64 = V{0.666666666666667}*cell[16];
auto x65 = V{0.666666666666667}*cell[6];
auto x66 = V{0.666666666666667}*cell[7];
auto x67 = x61 + x62 - x63 - x64 - x65 - x66;
auto x68 = x47 + x48 + x49 + x50 - x51 - x52 + x60 + x67;
auto x69 = x46 + x68;
auto x70 = x21*x35;
auto x71 = -cell[4];
auto x72 = cell[5] + x71;
auto x73 = -cell[14] + cell[17] - cell[2] - cell[9] + x28 + x37 + x72;
auto x74 = x41*x73;
auto x75 = V{1}*x74;
auto x76 = x70 + x75;
auto x77 = ((x76)*(x76));
auto x78 = x31*x77;
auto x79 = V{0.333333333333333}*cell[15];
auto x80 = V{0.333333333333333}*cell[16];
auto x81 = V{0.333333333333333}*cell[6];
auto x82 = V{0.333333333333333}*cell[7];
auto x83 = V{0.666666666666667}*cell[11];
auto x84 = V{0.666666666666667}*cell[2];
auto x85 = V{0.333333333333333}*cell[12];
auto x86 = V{0.333333333333333}*cell[3];
auto x87 = V{0.666666666666667}*cell[13];
auto x88 = V{0.666666666666667}*cell[14];
auto x89 = V{0.666666666666667}*cell[4];
auto x90 = V{0.666666666666667}*cell[5];
auto x91 = x85 + x86 - x87 - x88 - x89 - x90;
auto x92 = x60 + x79 + x80 + x81 + x82 - x83 - x84 + x91;
auto x93 = x78 + x92;
auto x94 = x20*x35;
auto x95 = cell[13] - cell[1] - cell[5] - cell[7] + x29 + x39 + x71;
auto x96 = x41*x95;
auto x97 = V{1}*x96;
auto x98 = x94 + x97;
auto x99 = ((x98)*(x98));
auto x100 = x31*x99;
auto x101 = V{0.333333333333333}*cell[17];
auto x102 = V{0.333333333333333}*cell[18];
auto x103 = V{0.333333333333333}*cell[8];
auto x104 = V{0.333333333333333}*cell[9];
auto x105 = V{0.666666666666667}*cell[10];
auto x106 = V{0.666666666666667}*cell[1];
auto x107 = x101 + x102 + x103 + x104 - x105 - x106 + x53 + x67 + x91;
auto x108 = x100 + x107;
auto x109 = x31*x98;
auto x110 = -V{1}*cell[15] + V{1}*cell[16] - V{1}*cell[6] + V{1}*cell[7];
auto x111 = x109*x44 + x110;
auto x112 = x109*x76;
auto x113 = -cell[13] + cell[14] + x72;
auto x114 = -V{1}*cell[13] + V{1}*cell[14] - V{1}*cell[4] + V{1}*cell[5];
auto x115 = x112 + x114;
auto x116 = x31*x44*x76;
auto x117 = -cell[17] + cell[18] + x38;
auto x118 = -V{1}*cell[17] + V{1}*cell[18] - V{1}*cell[8] + V{1}*cell[9];
auto x119 = x116 + x118;
auto x120 = V{1} - V{1} / (x25 + V{3.00000046417339}*util::sqrt(x26 + x32*x33*util::sqrt(x115*(x112 + x113) + x119*(x116 + x117) + V{0.5}*((x108)*(x108)) + V{1}*((x111)*(x111)) + V{0.5}*((x69)*(x69)) + V{0.5}*((x93)*(x93)))));
auto x121 = V{0.5}*cell[13];
auto x122 = V{0.5}*cell[14];
auto x123 = V{0.5}*cell[15];
auto x124 = V{0.5}*cell[16];
auto x125 = V{0.5}*cell[17];
auto x126 = V{0.5}*cell[18];
auto x127 = V{0.5}*cell[4];
auto x128 = V{0.5}*cell[5];
auto x129 = V{0.5}*cell[6];
auto x130 = V{0.5}*cell[7];
auto x131 = V{0.5}*cell[8];
auto x132 = V{0.5}*cell[9];
auto x133 = V{0.5}*cell[0];
auto x134 = V{0.5}*cell[10] + V{0.5}*cell[11] + V{0.5}*cell[12] + V{0.5}*cell[1] + V{0.5}*cell[2] + V{0.5}*cell[3] + x121 + x122 + x123 + x124 + x125 + x126 + x127 + x128 + x129 + x130 + x131 + x132 + x133 + V{0.5};
auto x135 = V{1.5}*x45 + V{1.5}*x77 + V{1.5}*x99 + V{-1};
auto x136 = x22*x34;
auto x137 = -x136;
auto x138 = x137 + x43;
auto x139 = ((x138)*(x138));
auto x140 = x139*x31 + x68;
auto x141 = x21*x34;
auto x142 = -x141;
auto x143 = x142 + x75;
auto x144 = ((x143)*(x143));
auto x145 = x144*x31 + x92;
auto x146 = x20*x34;
auto x147 = -x146;
auto x148 = x147 + x97;
auto x149 = ((x148)*(x148));
auto x150 = x107 + x149*x31;
auto x151 = x148*x31;
auto x152 = x138*x151;
auto x153 = x110 + x152;
auto x154 = x143*x151;
auto x155 = x114 + x154;
auto x156 = x138*x143*x31;
auto x157 = x118 + x156;
auto x158 = V{1} - V{1} / (x25 + V{3.00000046417339}*util::sqrt(x26 + x32*x33*util::sqrt(x155*(x113 + x154) + x157*(x117 + x156) + V{0.5}*((x140)*(x140)) + V{0.5}*((x145)*(x145)) + V{0.5}*((x150)*(x150)) + V{1}*((x153)*(x153)))));
auto x159 = V{0.5}*x19*x32*x95;
auto x160 = x159 - V{0.5}*x20*x34;
auto x161 = x142 + x74;
auto x162 = V{1}*x115;
auto x163 = x137 + x42;
auto x164 = V{1}*x163;
auto x165 = V{0.166666666666667}*cell[10];
auto x166 = V{0.166666666666667}*cell[11];
auto x167 = V{0.166666666666667}*cell[12];
auto x168 = V{0.166666666666667}*cell[13];
auto x169 = V{0.166666666666667}*cell[14];
auto x170 = V{0.166666666666667}*cell[15];
auto x171 = V{0.166666666666667}*cell[16];
auto x172 = V{0.166666666666667}*cell[17];
auto x173 = V{0.166666666666667}*cell[18];
auto x174 = V{0.166666666666667}*cell[1];
auto x175 = V{0.166666666666667}*cell[2];
auto x176 = V{0.166666666666667}*cell[3];
auto x177 = V{0.166666666666667}*cell[4];
auto x178 = V{0.166666666666667}*cell[5];
auto x179 = V{0.166666666666667}*cell[6];
auto x180 = V{0.166666666666667}*cell[7];
auto x181 = V{0.166666666666667}*cell[8];
auto x182 = V{0.166666666666667}*cell[9];
auto x183 = V{0.166666666666667}*cell[0] + x165 + x166 + x167 + x168 + x169 + x170 + x171 + x172 + x173 + x174 + x175 + x176 + x177 + x178 + x179 + x180 + x181 + x182 + V{0.166666666666667};
auto x184 = V{0.0833333333333333}*cell[0] + V{0.0833333333333333}*cell[10] + V{0.0833333333333333}*cell[11] + V{0.0833333333333333}*cell[12] + V{0.0833333333333333}*cell[13] + V{0.0833333333333333}*cell[14] + V{0.0833333333333333}*cell[15] + V{0.0833333333333333}*cell[16] + V{0.0833333333333333}*cell[17] + V{0.0833333333333333}*cell[18] + V{0.0833333333333333}*cell[1] + V{0.0833333333333333}*cell[2] + V{0.0833333333333333}*cell[3] + V{0.0833333333333333}*cell[4] + V{0.0833333333333333}*cell[5] + V{0.0833333333333333}*cell[6] + V{0.0833333333333333}*cell[7] + V{0.0833333333333333}*cell[8] + V{0.0833333333333333}*cell[9] + V{0.0833333333333333};
auto x185 = V{6.93889390390723e-18}*cell[0];
auto x186 = V{0.0833333333333333}*cell[12];
auto x187 = V{0.0833333333333333}*cell[3];
auto x188 = V{0.0833333333333333}*cell[13];
auto x189 = V{0.0833333333333333}*cell[14];
auto x190 = V{0.0833333333333333}*cell[4];
auto x191 = V{0.0833333333333333}*cell[5];
auto x192 = x185 + x186 + x187 - x188 - x189 - x190 - x191;
auto x193 = -x139*x184 + x192;
auto x194 = V{0.0833333333333333}*cell[11];
auto x195 = V{0.0833333333333333}*cell[2];
auto x196 = V{0.0833333333333333}*cell[15];
auto x197 = V{0.0833333333333333}*cell[16];
auto x198 = V{0.0833333333333333}*cell[6];
auto x199 = V{0.0833333333333333}*cell[7];
auto x200 = x194 + x195 - x196 - x197 - x198 - x199;
auto x201 = -x144*x184 + x200;
auto x202 = -x165 + x172 + x173 - x174 + x181 + x182;
auto x203 = x30 + V{1};
auto x204 = x147 + x96;
auto x205 = V{6.000003}*x19*x32*x95;
auto x206 = -V{6.000003}*x20*x34 + x205;
auto x207 = V{2.999997}*x19*x32*x73;
auto x208 = x207 - V{2.999997}*x21*x34;
auto x209 = V{1.5}*x149;
auto x210 = V{1.5}*x144;
auto x211 = V{1.5}*x139;
auto x212 = -x209 - x210 - x211 + V{1};
auto x213 = V{3}*x96;
auto x214 = -x213;
auto x215 = V{3}*x146 + x214;
auto x216 = x144*x206 + x149*x208 + x215;
auto x217 = V{0.5}*x19*x32*x73;
auto x218 = -V{0.5}*x21*x34 + x217;
auto x219 = V{0.0833333333333333}*cell[10];
auto x220 = V{0.0833333333333333}*cell[1];
auto x221 = V{0.0833333333333333}*cell[17];
auto x222 = V{0.0833333333333333}*cell[18];
auto x223 = V{0.0833333333333333}*cell[8];
auto x224 = V{0.0833333333333333}*cell[9];
auto x225 = x219 + x220 - x221 - x222 - x223 - x224;
auto x226 = -x149*x184 + x225;
auto x227 = -x166 + x170 + x171 - x175 + x179 + x180;
auto x228 = V{6.000003}*x19*x32*x73;
auto x229 = -V{6.000003}*x21*x34 + x228;
auto x230 = V{2.999997}*x19*x32*x95;
auto x231 = -V{2.999997}*x20*x34 + x230;
auto x232 = V{3}*x74;
auto x233 = -x232;
auto x234 = V{3}*x141 + x233;
auto x235 = x144*x231 + x149*x229 + x234;
auto x236 = V{0.0555555555555556}*cell[0] + V{0.0555555555555556}*cell[10] + V{0.0555555555555556}*cell[11] + V{0.0555555555555556}*cell[12] + V{0.0555555555555556}*cell[13] + V{0.0555555555555556}*cell[14] + V{0.0555555555555556}*cell[15] + V{0.0555555555555556}*cell[16] + V{0.0555555555555556}*cell[17] + V{0.0555555555555556}*cell[18] + V{0.0555555555555556}*cell[1] + V{0.0555555555555556}*cell[2] + V{0.0555555555555556}*cell[3] + V{0.0555555555555556}*cell[4] + V{0.0555555555555556}*cell[5] + V{0.0555555555555556}*cell[6] + V{0.0555555555555556}*cell[7] + V{0.0555555555555556}*cell[8] + V{0.0555555555555556}*cell[9] + V{0.0555555555555556};
auto x237 = V{9}*x19*x32*x40 + V{9}*x22*x35;
auto x238 = x237*x99;
auto x239 = x237*x77;
auto x240 = x36 + x42;
auto x241 = x135 - V{4.5}*((x240)*(x240));
auto x242 = V{3}*x36;
auto x243 = V{3}*x42;
auto x244 = x242 + x243;
auto x245 = V{0.5}*x19*x32*x40;
auto x246 = -V{0.5}*x22*x34 + x245;
auto x247 = x111*x204;
auto x248 = x119*x161;
auto x249 = -x167 + x168 + x169 - x176 + x177 + x178 + x185;
auto x250 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[10] + V{0.0277777777777778}*cell[11] + V{0.0277777777777778}*cell[12] + V{0.0277777777777778}*cell[13] + V{0.0277777777777778}*cell[14] + V{0.0277777777777778}*cell[15] + V{0.0277777777777778}*cell[16] + V{0.0277777777777778}*cell[17] + V{0.0277777777777778}*cell[18] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778}*cell[9] + V{0.0277777777777778};
auto x251 = x70 + x74;
auto x252 = x94 + x96;
auto x253 = V{18}*x19*x32*x95;
auto x254 = V{18}*x19*x32*x73;
auto x255 = V{9}*x19*x32*x95;
auto x256 = V{9}*x19*x32*x73;
auto x257 = V{3}*x70;
auto x258 = x232 + x257;
auto x259 = V{3}*x94;
auto x260 = x213 + x259;
auto x261 = x135 + x260;
auto x262 = -x186;
auto x263 = -x187;
auto x264 = V{0.25000025}*x19*x32*x95 - V{0.25000025}*x20*x34;
auto x265 = x264*x93;
auto x266 = V{0.5000005}*x115;
auto x267 = x161*x266;
auto x268 = V{0.0416666666666667}*cell[0] + V{0.0416666666666667}*cell[10] + V{0.0416666666666667}*cell[11] + V{0.0416666666666667}*cell[12] + V{0.0416666666666667}*cell[13] + V{0.0416666666666667}*cell[14] + V{0.0416666666666667}*cell[15] + V{0.0416666666666667}*cell[16] + V{0.0416666666666667}*cell[17] + V{0.0416666666666667}*cell[18] + V{0.0416666666666667}*cell[1] + V{0.0416666666666667}*cell[2] + V{0.0416666666666667}*cell[3] + V{0.0416666666666667}*cell[4] + V{0.0416666666666667}*cell[5] + V{0.0416666666666667}*cell[6] + V{0.0416666666666667}*cell[7] + V{0.0416666666666667}*cell[8] + V{0.0416666666666667}*cell[9] + V{0.0416666666666667};
auto x269 = x139*x268;
auto x270 = V{2.49999999985601e-07}*x19*x32*x95 - V{2.49999999985601e-07}*x20*x34;
auto x271 = x270*x69;
auto x272 = V{4.99999999971202e-07}*x163;
auto x273 = x111*x272;
auto x274 = -V{0.0416666666666667}*cell[0];
auto x275 = V{0.0833333333333333}*cell[0] + x186 + x187 + x188 + x189 + x190 + x191 + x194 + x195 + x196 + x197 + x198 + x199 + x219 + x220 + x221 + x222 + x223 + x224 + V{0.0833333333333333};
auto x276 = V{0.0416666666666667}*cell[10] + V{6.93889390390723e-18}*cell[17] + V{6.93889390390723e-18}*cell[18] + V{0.0416666666666667}*cell[1] + V{6.93889390390723e-18}*cell[8] + V{6.93889390390723e-18}*cell[9] - x149*x275 + x274;
auto x277 = V{0.0416666666666667}*cell[11] + V{6.93889390390723e-18}*cell[15] + V{6.93889390390723e-18}*cell[16] + V{0.0416666666666667}*cell[2] + V{6.93889390390723e-18}*cell[6] + V{6.93889390390723e-18}*cell[7] - x144*x275;
auto x278 = x262 + x263 + x265 + x267 + x269 - x271 - x273 + x276 + x277;
auto x279 = V{0.25000025}*x19*x32*x73 - V{0.25000025}*x21*x34;
auto x280 = x108*x279;
auto x281 = x204*x266;
auto x282 = V{2.49999999985601e-07}*x19*x32*x73 - V{2.49999999985601e-07}*x21*x34;
auto x283 = x282*x69;
auto x284 = x119*x272;
auto x285 = x280 + x281 - x283 - x284;
auto x286 = V{0.25}*x154;
auto x287 = V{0.375}*cell[13] - V{0.125}*cell[14] + V{0.375}*cell[4] - V{0.125}*cell[5] - x286;
auto x288 = x252 - x70 - x74;
auto x289 = x45*(V{3.000006}*x19*x32*x73 + V{3.000006}*x21*x35);
auto x290 = x77*(V{6.000012}*x19*x32*x95 + V{6.000012}*x20*x35);
auto x291 = x45*(V{3.000006}*x19*x32*x95 + V{3.000006}*x20*x35);
auto x292 = x99*(V{6.000012}*x19*x32*x73 + V{6.000012}*x21*x35);
auto x293 = x135 + x233 - x257;
auto x294 = -V{0.125}*cell[13] + V{0.375}*cell[14] - V{0.125}*cell[4] + V{0.375}*cell[5] + x286;
auto x295 = V{9.000009}*x19*x32*x40;
auto x296 = V{9.000009}*x22*x35 + x295;
auto x297 = x296*x99;
auto x298 = V{8.99999999948164e-06}*x19*x32*x40;
auto x299 = V{8.99999999948164e-06}*x22*x35 + x298;
auto x300 = x299*x77;
auto x301 = x244 + x297 - x300;
auto x302 = V{5.999994}*x19*x32*x73;
auto x303 = x45*(V{5.999994}*x21*x35 + x302);
auto x304 = V{12.000006}*x19*x32*x95;
auto x305 = x45*(V{12.000006}*x20*x35 + x304);
auto x306 = V{6.000003}*x20*x35 + x205;
auto x307 = x306*x77;
auto x308 = x207 + V{2.999997}*x21*x35;
auto x309 = x308*x99;
auto x310 = x261 + x303 + x305 - x307 - x309;
auto x311 = -x194;
auto x312 = -x195;
auto x313 = x264*x69;
auto x314 = V{0.5000005}*x163;
auto x315 = x111*x314;
auto x316 = x144*x268;
auto x317 = x270*x93;
auto x318 = V{4.99999999971202e-07}*x115;
auto x319 = x161*x318;
auto x320 = V{0.0416666666666667}*cell[12] + V{6.93889390390723e-18}*cell[13] + V{6.93889390390723e-18}*cell[14] + V{0.0416666666666667}*cell[3] + V{6.93889390390723e-18}*cell[4] + V{6.93889390390723e-18}*cell[5] - x139*x275;
auto x321 = x276 + x311 + x312 + x313 + x315 + x316 - x317 - x319 + x320;
auto x322 = V{0.25000025}*x19*x32*x40 - V{0.25000025}*x22*x34;
auto x323 = x108*x322;
auto x324 = V{0.5000005}*x247;
auto x325 = V{2.49999999985601e-07}*x19*x32*x40 - V{2.49999999985601e-07}*x22*x34;
auto x326 = x325*x93;
auto x327 = V{4.99999999971202e-07}*x248;
auto x328 = x323 + x324 - x326 - x327;
auto x329 = V{0.25}*x152;
auto x330 = V{0.375}*cell[15] - V{0.125}*cell[16] + V{0.375}*cell[6] - V{0.125}*cell[7] - x329;
auto x331 = -x19*x32*x40 - x22*x35;
auto x332 = x252 + x331;
auto x333 = -x243;
auto x334 = -x242 + x333;
auto x335 = -V{0.125}*cell[15] + V{0.375}*cell[16] - V{0.125}*cell[6] + V{0.375}*cell[7] + x329;
auto x336 = x296*x77;
auto x337 = x299*x99;
auto x338 = x244 + x336 - x337;
auto x339 = V{5.999994}*x19*x32*x95;
auto x340 = x45*(V{5.999994}*x20*x35 + x339);
auto x341 = V{12.000006}*x19*x32*x73;
auto x342 = x45*(V{12.000006}*x21*x35 + x341);
auto x343 = V{6.000003}*x21*x35 + x228;
auto x344 = x343*x99;
auto x345 = V{2.999997}*x20*x35 + x230;
auto x346 = x345*x77;
auto x347 = x135 + x258 + x340 + x342 - x344 - x346;
auto x348 = -x219;
auto x349 = -x220;
auto x350 = x279*x69;
auto x351 = x119*x314;
auto x352 = x149*x268;
auto x353 = x108*x282;
auto x354 = x204*x318;
auto x355 = x274 + x277 + x320 + x348 + x349 + x350 + x351 + x352 - x353 - x354;
auto x356 = x322*x93;
auto x357 = V{0.5000005}*x248;
auto x358 = x108*x325;
auto x359 = V{4.99999999971202e-07}*x247;
auto x360 = x356 + x357 - x358 - x359;
auto x361 = V{0.25}*x156;
auto x362 = V{0.375}*cell[17] - V{0.125}*cell[18] + V{0.375}*cell[8] - V{0.125}*cell[9] - x361;
auto x363 = x251 + x331;
auto x364 = -V{0.125}*cell[17] + V{0.375}*cell[18] - V{0.125}*cell[8] + V{0.375}*cell[9] + x361;
auto x365 = x159 + V{0.5}*x20*x35;
auto x366 = -x53;
auto x367 = x366 - x54 - x55 + x56 + x57 + x58 + x59;
auto x368 = -x85 - x86 + x87 + x88 + x89 + x90;
auto x369 = x367 + x368 - x78 - x79 - x80 - x81 - x82 + x83 + x84;
auto x370 = -x61 - x62 + x63 + x64 + x65 + x66;
auto x371 = x367 + x370 - x46 - x47 - x48 - x49 - x50 + x51 + x52;
auto x372 = -V{1}*x115;
auto x373 = -x111;
auto x374 = V{1}*x240;
auto x375 = -x184*x45 + x192;
auto x376 = -x184*x77 + x200;
auto x377 = x135 + x214 - x259;
auto x378 = x307 + x309 + x377;
auto x379 = V{0.5}*x21*x35 + x217;
auto x380 = -x100 - x101 - x102 - x103 - x104 + x105 + x106 + x366 + x368 + x370;
auto x381 = -x119;
auto x382 = -x184*x99 + x225;
auto x383 = x293 + x344 + x346;
auto x384 = V{0.5}*x22*x35 + x245;
auto x385 = x209 + x210 + x211 + V{-1};
auto x386 = V{0.5000005}*x155;
auto x387 = x262 + x263 + x269 + x276 + x277;
auto x388 = -V{8.99999999948164e-06}*x22*x34 + x298;
auto x389 = -V{9.000009}*x22*x34 + x295;
auto x390 = V{3}*x136 + x333 + x385;
auto x391 = V{4.99999999971202e-07}*x161;
auto x392 = x153*x204;
auto x393 = x276 + x311 + x312 + x316 + x320;
auto x394 = x274 + x277 + x320 + x348 + x349 + x352;
auto x0 = -V{1}*x120*(V{4.16333634234434e-17}*cell[10] + V{4.16333634234434e-17}*cell[11] + V{4.16333634234434e-17}*cell[12] + V{4.16333634234434e-17}*cell[1] + V{4.16333634234434e-17}*cell[2] + V{4.16333634234434e-17}*cell[3] + x121 + x122 + x123 + x124 + x125 + x126 + x127 + x128 + x129 + x130 + x131 + x132 - x133 - x134*x45 - x134*x77 - x134*x99) - x135*(x101 + x102 + x103 + x104 + x47 + x48 + x49 + x50 + x53 + x54 + x55 + x61 + x62 + x79 + x80 + x81 + x82 + x85 + x86 + V{0.333333333333333}) + V{-0.333333333333333};
auto x1 = -(V{1}*x158*(x111*x164 + x149*x183 + x160*x69 + x160*x93 + x161*x162 + x193 + x201 + x202) - V{0.0555555555555556}*x203*(x139*x206 + x139*x208 + x212 + x216 + V{4.5}*((x204)*(x204))) + V{0.0555555555555556});
auto x2 = -(V{1}*x158*(x108*x218 + x119*x164 + x144*x183 + x162*x204 + x193 + x218*x69 + x226 + x227) - V{0.0555555555555556}*x203*(x139*x229 + x139*x231 + x212 + x235 + V{4.5}*((x161)*(x161))) + V{0.0555555555555556});
auto x3 = V{1}*x120*(-x108*x246 - x139*x183 - x201 - x226 - x246*x93 - V{1}*x247 - V{1}*x248 - x249) - x236*(-x238 - x239 + x241 + x244) + V{-0.0555555555555556};
auto x4 = -(-V{1}*x120*(x278 + x285 + x287) + x250*(x258 + x261 - x45*(V{9}*x20*x35 + x255) - x45*(V{9}*x21*x35 + x256) + x77*(V{18}*x20*x35 + x253) + x99*(V{18}*x21*x35 + x254) - V{4.5}*((x251 + x252)*(x251 + x252))) + V{0.0277777777777778});
auto x5 = -(-V{1}*x120*(x278 - x280 - x281 + x283 + x284 + x294) + x250*(x260 + x289 + x290 - x291 - x292 + x293 - V{4.5}*((x288)*(x288))) + V{0.0277777777777778});
auto x6 = -(-V{1}*x120*(x321 + x328 + x330) + x250*(x301 + x310 - V{4.5}*((x240 + x252)*(x240 + x252))) + V{0.0277777777777778});
auto x7 = -(-V{1}*x120*(x321 - x323 - x324 + x326 + x327 + x335) + x250*(-x297 + x300 + x310 + x334 - V{4.5}*((x332)*(x332))) + V{0.0277777777777778});
auto x8 = -(-V{1}*x120*(x355 + x360 + x362) + x250*(x338 + x347 - V{4.5}*((x240 + x251)*(x240 + x251))) + V{0.0277777777777778});
auto x9 = -(-V{1}*x120*(x355 - x356 - x357 + x358 + x359 + x364) + x250*(x334 - x336 + x337 + x347 - V{4.5}*((x363)*(x363))) + V{0.0277777777777778});
auto x10 = -(V{1}*x120*(x183*x99 + x202 + x251*x372 + x365*x369 + x365*x371 + x373*x374 + x375 + x376) + x236*(x306*x45 + x308*x45 + x378 - V{4.5}*((x252)*(x252))) + V{0.0555555555555556});
auto x11 = -(V{1}*x120*(x183*x77 + x227 + x252*x372 + x371*x379 + x374*x381 + x375 + x379*x380 + x382) + x236*(x343*x45 + x345*x45 + x383 - V{4.5}*((x251)*(x251))) + V{0.0555555555555556});
auto x12 = -V{1}*x120*(x183*x45 + x249 + V{1}*x251*x381 + V{1}*x252*x373 + x369*x384 + x376 + x380*x384 + x382) - x236*(x238 + x239 + x241 + x334) + V{-0.0555555555555556};
auto x13 = -(-V{1}*x158*(x140*x270 + x140*x282 - x145*x264 - x150*x279 + x153*x272 + x157*x272 - x161*x386 - x204*x386 + x287 + x387) + x250*(x139*(-V{9}*x20*x34 + x255) + x139*(-V{9}*x21*x34 + x256) - x144*(-V{18}*x20*x34 + x253) - x149*(-V{18}*x21*x34 + x254) + x215 + x234 + x385 - V{4.5}*((x161 + x204)*(x161 + x204))) + V{0.0277777777777778});
auto x14 = -(-V{1}*x120*(-x265 - x267 + x271 + x273 + x285 + x294 + x387) + x250*(x258 - x289 - x290 + x291 + x292 + x377 - V{4.5}*((x288)*(x288))) + V{0.0277777777777778});
auto x15 = -(-V{1}*x158*(-x140*x264 + x145*x270 + x145*x325 - x150*x322 - x153*x314 + x155*x391 + x157*x391 + x330 - V{0.5000005}*x392 + x393) + x250*(-x139*(-V{12.000006}*x20*x34 + x304) - x139*(-V{5.999994}*x21*x34 + x302) + x144*x388 - x149*x389 + x216 + x390 - V{4.5}*((x163 + x204)*(x163 + x204))) + V{0.0277777777777778});
auto x16 = -(-V{1}*x120*(-x313 - x315 + x317 + x319 + x328 + x335 + x393) + x250*(x301 - x303 - x305 + x378 - V{4.5}*((x332)*(x332))) + V{0.0277777777777778});
auto x17 = -(-V{1}*x158*(-x140*x279 - x145*x322 + x150*x282 + x150*x325 + V{4.99999999971202e-07}*x155*x204 - V{0.5000005}*x157*x161 - x157*x314 + x362 + V{4.99999999971202e-07}*x392 + x394) + x250*(-x139*(-V{5.999994}*x20*x34 + x339) - x139*(-V{12.000006}*x21*x34 + x341) - x144*x389 + x149*x388 + x235 + x390 - V{4.5}*((x161 + x163)*(x161 + x163))) + V{0.0277777777777778});
auto x18 = -(-V{1}*x120*(-x350 - x351 + x353 + x354 + x360 + x364 + x394) + x250*(x338 - x340 - x342 + x383 - V{4.5}*((x363)*(x363))) + V{0.0277777777777778});
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
return { x31, x139 + x144 + x149 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
