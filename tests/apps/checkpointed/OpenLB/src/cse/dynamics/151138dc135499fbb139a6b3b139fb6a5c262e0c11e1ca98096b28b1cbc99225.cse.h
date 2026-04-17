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
struct CSE<dynamics::Tuple<T, descriptors::D3Q27<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::ParameterFromCell<collision::LES::SMAGORINSKY, collision::SmagorinskyEffectiveOmega<collision::BGK> >, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x27 = cell.template getFieldComponent<olb::collision::LES::SMAGORINSKY>(0);
auto x28 = parameters.template get<descriptors::OMEGA>();
auto x29 = cell[18] + cell[25] + cell[26];
auto x30 = cell[10] + cell[4];
auto x31 = cell[12] + x30;
auto x32 = cell[22] + cell[6];
auto x33 = cell[15] + cell[21];
auto x34 = cell[16] + cell[9];
auto x35 = cell[19] + cell[7];
auto x36 = cell[0] + cell[11] + cell[13] + cell[14] + cell[17] + cell[1] + cell[20] + cell[23] + cell[24] + cell[2] + cell[3] + cell[5] + cell[8] + x29 + x31 + x32 + x33 + x34 + x35 + V{1};
auto x37 = V{1} / (x36);
auto x38 = V{1}*x37;
auto x39 = -cell[26];
auto x40 = -cell[25];
auto x41 = -cell[18];
auto x42 = -cell[19];
auto x43 = cell[7] + x42;
auto x44 = -cell[23];
auto x45 = cell[11] + x44;
auto x46 = x43 + x45;
auto x47 = -cell[24];
auto x48 = -cell[17];
auto x49 = cell[5] + x48;
auto x50 = cell[13] + x47 + x49;
auto x51 = -cell[20];
auto x52 = -cell[14] + cell[1];
auto x53 = cell[6] + x51 + x52;
auto x54 = x31 + x39 + x40 + x41 + x46 + x50 + x53;
auto x55 = ((x54)*(x54));
auto x56 = V{0.666666666666667}*cell[10];
auto x57 = V{0.666666666666667}*cell[11];
auto x58 = V{0.666666666666667}*cell[12];
auto x59 = V{0.666666666666667}*cell[13];
auto x60 = V{0.666666666666667}*cell[23];
auto x61 = V{0.666666666666667}*cell[24];
auto x62 = V{0.666666666666667}*cell[25];
auto x63 = V{0.666666666666667}*cell[26];
auto x64 = -V{0.333333333333333}*cell[0];
auto x65 = -V{0.333333333333333}*cell[16] + V{0.666666666666667}*cell[17] + V{0.666666666666667}*cell[18] - V{0.333333333333333}*cell[3] + V{0.666666666666667}*cell[4] + V{0.666666666666667}*cell[5] + x56 + x57 + x58 + x59 + x60 + x61 + x62 + x63 + x64;
auto x66 = -V{0.333333333333333}*cell[15] + V{0.666666666666667}*cell[19] + V{0.666666666666667}*cell[20] - V{0.333333333333333}*cell[2] + V{0.666666666666667}*cell[6] + V{0.666666666666667}*cell[7];
auto x67 = -cell[12];
auto x68 = -cell[13];
auto x69 = cell[8] + x68;
auto x70 = -cell[15] + cell[2];
auto x71 = x47 + x70;
auto x72 = -cell[5] + x48;
auto x73 = -cell[22];
auto x74 = -cell[21];
auto x75 = cell[9] + x74;
auto x76 = x73 + x75;
auto x77 = x29 + x30 + x45 + x67 + x69 + x71 + x72 + x76;
auto x78 = ((x77)*(x77));
auto x79 = -V{0.333333333333333}*cell[14] - V{0.333333333333333}*cell[1] + V{0.666666666666667}*cell[21] + V{0.666666666666667}*cell[22] + V{0.666666666666667}*cell[8] + V{0.666666666666667}*cell[9];
auto x80 = cell[26] + x40;
auto x81 = cell[20] + x80;
auto x82 = -cell[11];
auto x83 = cell[12] + x44 + x82;
auto x84 = -cell[16] + cell[3];
auto x85 = cell[10] + cell[24] + x84;
auto x86 = -cell[9];
auto x87 = x74 + x86;
auto x88 = -cell[7] + x42;
auto x89 = x32 + x69 + x81 + x83 + x85 + x87 + x88;
auto x90 = ((x89)*(x89));
auto x91 = x37*x89;
auto x92 = -cell[8];
auto x93 = cell[22] + x92;
auto x94 = cell[11] + cell[12] + x68;
auto x95 = cell[25] + x39 + x44;
auto x96 = -cell[10];
auto x97 = cell[24] + x96;
auto x98 = -cell[6];
auto x99 = cell[13] + x67;
auto x100 = V{1} / (V{3.00000046417339}*util::sqrt(x37*((x27)*(x27))*util::sqrt(((-cell[4] + x29 + x37*x54*x77 + x50 + x83 + x96)*(-cell[4] + x29 + x37*x54*x77 + x50 + x83 + x96)) + ((x46 + x54*x91 + x81 + x97 + x98 + x99)*(x46 + x54*x91 + x81 + x97 + x98 + x99)) + ((x75 + x77*x91 + x93 + x94 + x95 + x97)*(x75 + x77*x91 + x93 + x94 + x95 + x97)) + V{0.5}*((V{0.666666666666667}*cell[14] + V{0.666666666666667}*cell[1] - V{0.333333333333333}*cell[21] - V{0.333333333333333}*cell[22] - V{0.333333333333333}*cell[8] - V{0.333333333333333}*cell[9] - x38*x55 + x65 + x66)*(V{0.666666666666667}*cell[14] + V{0.666666666666667}*cell[1] - V{0.333333333333333}*cell[21] - V{0.333333333333333}*cell[22] - V{0.333333333333333}*cell[8] - V{0.333333333333333}*cell[9] - x38*x55 + x65 + x66)) + V{0.5}*((V{0.666666666666667}*cell[15] - V{0.333333333333333}*cell[19] - V{0.333333333333333}*cell[20] + V{0.666666666666667}*cell[2] - V{0.333333333333333}*cell[6] - V{0.333333333333333}*cell[7] - x38*x78 + x65 + x79)*(V{0.666666666666667}*cell[15] - V{0.333333333333333}*cell[19] - V{0.333333333333333}*cell[20] + V{0.666666666666667}*cell[2] - V{0.333333333333333}*cell[6] - V{0.333333333333333}*cell[7] - x38*x78 + x65 + x79)) + V{0.5}*((V{0.666666666666667}*cell[16] - V{0.333333333333333}*cell[17] - V{0.333333333333333}*cell[18] + V{0.666666666666667}*cell[3] - V{0.333333333333333}*cell[4] - V{0.333333333333333}*cell[5] - x38*x90 + x56 + x57 + x58 + x59 + x60 + x61 + x62 + x63 + x64 + x66 + x79)*(V{0.666666666666667}*cell[16] - V{0.333333333333333}*cell[17] - V{0.333333333333333}*cell[18] + V{0.666666666666667}*cell[3] - V{0.333333333333333}*cell[4] - V{0.333333333333333}*cell[5] - x38*x90 + x56 + x57 + x58 + x59 + x60 + x61 + x62 + x63 + x64 + x66 + x79))) + V{0.0277777691819762}/((x28)*(x28))) + V{0.5}/x28);
auto x101 = V{1} / ((x36)*(x36));
auto x102 = V{1.5}*x101;
auto x103 = ((x54)*(x54));
auto x104 = x102*x103;
auto x105 = ((x89)*(x89));
auto x106 = x102*x105;
auto x107 = ((x77)*(x77));
auto x108 = x102*x107;
auto x109 = x106 + x108 + V{-1};
auto x110 = x104 + x109;
auto x111 = V{1} - x100;
auto x112 = V{0.0740740740740741}*cell[0] + V{0.0740740740740741}*cell[10] + V{0.0740740740740741}*cell[11] + V{0.0740740740740741}*cell[12] + V{0.0740740740740741}*cell[13] + V{0.0740740740740741}*cell[14] + V{0.0740740740740741}*cell[15] + V{0.0740740740740741}*cell[16] + V{0.0740740740740741}*cell[17] + V{0.0740740740740741}*cell[18] + V{0.0740740740740741}*cell[19] + V{0.0740740740740741}*cell[1] + V{0.0740740740740741}*cell[20] + V{0.0740740740740741}*cell[21] + V{0.0740740740740741}*cell[22] + V{0.0740740740740741}*cell[23] + V{0.0740740740740741}*cell[24] + V{0.0740740740740741}*cell[25] + V{0.0740740740740741}*cell[26] + V{0.0740740740740741}*cell[2] + V{0.0740740740740741}*cell[3] + V{0.0740740740740741}*cell[4] + V{0.0740740740740741}*cell[5] + V{0.0740740740740741}*cell[6] + V{0.0740740740740741}*cell[7] + V{0.0740740740740741}*cell[8] + V{0.0740740740740741}*cell[9] + V{0.0740740740740741};
auto x113 = V{3}*cell[13];
auto x114 = V{3}*cell[5];
auto x115 = V{3}*cell[7];
auto x116 = V{3}*cell[18];
auto x117 = V{3}*cell[20];
auto x118 = V{3}*cell[26];
auto x119 = V{3}*cell[10];
auto x120 = V{3}*cell[11];
auto x121 = -V{3}*cell[23];
auto x122 = V{3}*cell[24];
auto x123 = -V{3}*cell[17] + V{3}*cell[4] + x119 + x120 + x121 - x122;
auto x124 = V{3}*cell[12];
auto x125 = V{3}*cell[25];
auto x126 = -V{3}*cell[19] + V{3}*cell[6] + x124 - x125;
auto x127 = -V{3}*cell[14] + V{3}*cell[1] + x113 + x114 + x115 - x116 - x117 - x118 + x123 + x126;
auto x128 = -x127*x37;
auto x129 = V{3}*x101;
auto x130 = V{3}*cell[9];
auto x131 = V{3}*cell[22];
auto x132 = -V{3}*cell[21] + V{3}*cell[8] - x113 + x118;
auto x133 = -V{3}*cell[15] + V{3}*cell[2] - x114 + x116 + x123 - x124 + x125 + x130 - x131 + x132;
auto x134 = -x133*x37;
auto x135 = x104 + V{-1};
auto x136 = -V{3}*cell[16] + V{3}*cell[3] - x115 + x117 + x119 - x120 + x121 + x122 + x126 - x130 + x131 + x132;
auto x137 = -x136*x37;
auto x138 = V{0.0185185185185185}*cell[0] + V{0.0185185185185185}*cell[10] + V{0.0185185185185185}*cell[11] + V{0.0185185185185185}*cell[12] + V{0.0185185185185185}*cell[13] + V{0.0185185185185185}*cell[14] + V{0.0185185185185185}*cell[15] + V{0.0185185185185185}*cell[16] + V{0.0185185185185185}*cell[17] + V{0.0185185185185185}*cell[18] + V{0.0185185185185185}*cell[19] + V{0.0185185185185185}*cell[1] + V{0.0185185185185185}*cell[20] + V{0.0185185185185185}*cell[21] + V{0.0185185185185185}*cell[22] + V{0.0185185185185185}*cell[23] + V{0.0185185185185185}*cell[24] + V{0.0185185185185185}*cell[25] + V{0.0185185185185185}*cell[26] + V{0.0185185185185185}*cell[2] + V{0.0185185185185185}*cell[3] + V{0.0185185185185185}*cell[4] + V{0.0185185185185185}*cell[5] + V{0.0185185185185185}*cell[6] + V{0.0185185185185185}*cell[7] + V{0.0185185185185185}*cell[8] + V{0.0185185185185185}*cell[9] + V{0.0185185185185185};
auto x139 = V{4.5}*x101;
auto x140 = x43 + x53;
auto x141 = -V{2}*cell[17] + V{2}*cell[4];
auto x142 = -V{2}*cell[23];
auto x143 = V{2}*cell[10];
auto x144 = cell[8] + x142 + x143;
auto x145 = V{2}*cell[11] - V{2}*cell[24];
auto x146 = x145 + x70;
auto x147 = x140 + x141 + x144 + x146 + x76;
auto x148 = x110 + x128;
auto x149 = x134 + x148;
auto x150 = V{2}*cell[25];
auto x151 = V{2}*cell[12];
auto x152 = -x150 + x151;
auto x153 = V{2}*cell[26];
auto x154 = V{2}*cell[13];
auto x155 = -x153 + x154;
auto x156 = V{2}*cell[18];
auto x157 = V{2}*cell[5];
auto x158 = -cell[2] - x156 + x157;
auto x159 = x140 + x152 + x155 + x158 + x33 + x86 + x93;
auto x160 = -x134;
auto x161 = x148 + x160;
auto x162 = cell[4] + x84;
auto x163 = -V{2}*cell[19] + V{2}*cell[6] + x52;
auto x164 = x41 + x49;
auto x165 = cell[22] + x144 + x152 + x162 + x163 + x164 + x87;
auto x166 = -x137;
auto x167 = -cell[3];
auto x168 = cell[4] + x167;
auto x169 = V{2}*cell[20];
auto x170 = V{2}*cell[7];
auto x171 = -x169 + x170 + x52;
auto x172 = cell[21] + x145 + x155 + x164 + x168 + x171 + x34 + x73 + x92;
auto x173 = cell[18] + x72;
auto x174 = -V{2}*cell[21] + V{2}*cell[8];
auto x175 = x174 + x70;
auto x176 = cell[20] + cell[6] + x142 + x143 + x153 - x154 + x162 + x173 + x175 + x88;
auto x177 = x110 + x134;
auto x178 = x137 + x177;
auto x179 = V{2}*cell[22];
auto x180 = V{2}*cell[9];
auto x181 = cell[16] - x179 + x180;
auto x182 = x146 + x150 - x151 + x168 + x173 + x181 + x35 + x51 + x98;
auto x183 = V{0.00462962962962963}*cell[0] + V{0.00462962962962963}*cell[10] + V{0.00462962962962963}*cell[11] + V{0.00462962962962963}*cell[12] + V{0.00462962962962963}*cell[13] + V{0.00462962962962963}*cell[14] + V{0.00462962962962963}*cell[15] + V{0.00462962962962963}*cell[16] + V{0.00462962962962963}*cell[17] + V{0.00462962962962963}*cell[18] + V{0.00462962962962963}*cell[19] + V{0.00462962962962963}*cell[1] + V{0.00462962962962963}*cell[20] + V{0.00462962962962963}*cell[21] + V{0.00462962962962963}*cell[22] + V{0.00462962962962963}*cell[23] + V{0.00462962962962963}*cell[24] + V{0.00462962962962963}*cell[25] + V{0.00462962962962963}*cell[26] + V{0.00462962962962963}*cell[2] + V{0.00462962962962963}*cell[3] + V{0.00462962962962963}*cell[4] + V{0.00462962962962963}*cell[5] + V{0.00462962962962963}*cell[6] + V{0.00462962962962963}*cell[7] + V{0.00462962962962963}*cell[8] + V{0.00462962962962963}*cell[9] + V{0.00462962962962963};
auto x184 = V{3}*cell[10] - V{3}*cell[23] + x141 + x163 + x174 + x71 + x80 + x84 + x94;
auto x185 = cell[10] + V{3}*cell[11] - V{3}*cell[24] + x141 + x167 + x171 + x181 + x70 + x95 + x99;
auto x186 = x44 + x82 + x85;
auto x187 = V{3}*cell[12] + cell[13] + cell[15] - V{3}*cell[25] + x158 + x163 + x179 - x180 + x186 + x39;
auto x188 = x127*x37;
auto x189 = -V{3}*cell[13] + cell[14] - cell[1] + cell[25] + V{3}*cell[26] + x156 - x157 + x169 - x170 + x175 + x186 + x67;
auto x190 = x136*x37;
auto x191 = x102*x78;
auto x192 = x102*x90 + V{-1};
auto x193 = x191 + x192;
auto x194 = x133*x37;
auto x195 = x102*x55;
auto x196 = x194 + x195;
auto x197 = x190 + x193 + x196;
auto x198 = x188 + x193;
auto x199 = x190 + x195;
auto x200 = x196 + x198;
auto x201 = -x128;
auto x202 = x198 + x199;
auto x203 = x110 + x137;
auto x0 = V{1}*cell[0]*x111 - x100*(x110*(V{0.296296296296296}*cell[0] + V{0.296296296296296}*cell[10] + V{0.296296296296296}*cell[11] + V{0.296296296296296}*cell[12] + V{0.296296296296296}*cell[13] + V{0.296296296296296}*cell[14] + V{0.296296296296296}*cell[15] + V{0.296296296296296}*cell[16] + V{0.296296296296296}*cell[17] + V{0.296296296296296}*cell[18] + V{0.296296296296296}*cell[19] + V{0.296296296296296}*cell[1] + V{0.296296296296296}*cell[20] + V{0.296296296296296}*cell[21] + V{0.296296296296296}*cell[22] + V{0.296296296296296}*cell[23] + V{0.296296296296296}*cell[24] + V{0.296296296296296}*cell[25] + V{0.296296296296296}*cell[26] + V{0.296296296296296}*cell[2] + V{0.296296296296296}*cell[3] + V{0.296296296296296}*cell[4] + V{0.296296296296296}*cell[5] + V{0.296296296296296}*cell[6] + V{0.296296296296296}*cell[7] + V{0.296296296296296}*cell[8] + V{0.296296296296296}*cell[9] + V{0.296296296296296}) + V{0.296296296296296});
auto x1 = V{1}*cell[1]*x111 - x100*(x112*(-x103*x129 + x109 + x128) + V{0.0740740740740741});
auto x2 = V{1}*cell[2]*x111 - x100*(x112*(x106 - x107*x129 + x134 + x135) + V{0.0740740740740741});
auto x3 = V{1}*cell[3]*x111 - x100*(x112*(-x105*x129 + x108 + x135 + x137) + V{0.0740740740740741});
auto x4 = V{1}*cell[4]*x111 - x100*(x138*(-x139*((x147)*(x147)) + x149) + V{0.0185185185185185});
auto x5 = V{1}*cell[5]*x111 - x100*(x138*(-x139*((x159)*(x159)) + x161) + V{0.0185185185185185});
auto x6 = V{1}*cell[6]*x111 - x100*(x138*(x137 - x139*((x165)*(x165)) + x148) + V{0.0185185185185185});
auto x7 = V{1}*cell[7]*x111 - x100*(x138*(-x139*((x172)*(x172)) + x148 + x166) + V{0.0185185185185185});
auto x8 = V{1}*cell[8]*x111 - x100*(x138*(-x139*((x176)*(x176)) + x178) + V{0.0185185185185185});
auto x9 = V{1}*cell[9]*x111 - x100*(x138*(-x139*((x182)*(x182)) + x166 + x177) + V{0.0185185185185185});
auto x10 = V{1}*cell[10]*x111 - x100*(x183*(x137 - x139*((x184)*(x184)) + x149) + V{0.00462962962962963});
auto x11 = V{1}*cell[11]*x111 - x100*(x183*(-x139*((x185)*(x185)) + x149 + x166) + V{0.00462962962962963});
auto x12 = V{1}*cell[12]*x111 - x100*(x183*(x137 - x139*((x187)*(x187)) + x161) + V{0.00462962962962963});
auto x13 = V{1}*cell[13]*x111 - x100*(x183*(-x139*((x189)*(x189)) - x188 + x197) + V{0.00462962962962963});
auto x14 = V{1}*cell[14]*x111 - x100*(x112*(-x129*x55 + x198) + V{0.0740740740740741});
auto x15 = V{1}*cell[15]*x111 - x100*(x112*(-x129*x78 + x192 + x196) + V{0.0740740740740741});
auto x16 = V{1}*cell[16]*x111 - x100*(x112*(-x129*x90 + x191 + x199 + V{-1}) + V{0.0740740740740741});
auto x17 = V{1}*cell[17]*x111 - x100*(x138*(-x139*((x147)*(x147)) + x200) + V{0.0185185185185185});
auto x18 = V{1}*cell[18]*x111 - x100*(x138*(-x139*((x159)*(x159)) + x177 + x201) + V{0.0185185185185185});
auto x19 = V{1}*cell[19]*x111 - x100*(x138*(-x139*((x165)*(x165)) + x202) + V{0.0185185185185185});
auto x20 = V{1}*cell[20]*x111 - x100*(x138*(-x139*((x172)*(x172)) + x201 + x203) + V{0.0185185185185185});
auto x21 = V{1}*cell[21]*x111 - x100*(x138*(-x139*((x176)*(x176)) + x197) + V{0.0185185185185185});
auto x22 = V{1}*cell[22]*x111 - x100*(x138*(-x139*((x182)*(x182)) + x160 + x203) + V{0.0185185185185185});
auto x23 = V{1}*cell[23]*x111 - x100*(x183*(-x139*((x184)*(x184)) + x190 + x200) + V{0.00462962962962963});
auto x24 = V{1}*cell[24]*x111 - x100*(x183*(-x139*((x185)*(x185)) - x190 + x200) + V{0.00462962962962963});
auto x25 = V{1}*cell[25]*x111 - x100*(x183*(-x139*((x187)*(x187)) - x194 + x202) + V{0.00462962962962963});
auto x26 = V{1}*cell[26]*x111 - x100*(x183*(-x139*((x189)*(x189)) + x178 + x201) + V{0.00462962962962963});
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
return { x36, V{1}*x101*(x55 + x78 + x90) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
