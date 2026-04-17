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
struct CSE<CombinedRLBdynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>, momenta::Tuple<momenta::InnerEdgeDensity3D<0, 1, 1>, momenta::FixedVelocityMomentumGeneric, momenta::InnerEdgeStress3D<0, 1, 1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x22 = parameters.template get<descriptors::OMEGA>();
auto x21 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(2);
auto x19 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x20 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x23 = x22 + V{-1};
auto x24 = V{0.5}*cell[11];
auto x25 = V{0.5}*cell[12];
auto x26 = V{2}*cell[17];
auto x27 = V{1} / (x20 + V{1});
auto x28 = V{0.25}*cell[0] + V{0.25}*cell[10] + V{0.5}*cell[17] + V{0.25}*cell[1] + V{0.25};
auto x29 = V{1} / (x21 + V{1});
auto x30 = cell[0] + cell[10] + cell[1] + x26 + V{1};
auto x31 = V{2}*cell[11] + cell[12] + V{2}*cell[13] + cell[15] + cell[16] + V{2}*cell[18] + cell[3] + V{2}*cell[5] + cell[6] + cell[7] + x30;
auto x32 = cell[11] + V{2}*cell[12] + cell[13] + cell[14] + V{2}*cell[15] + cell[2] + cell[4] + cell[5] + V{2}*cell[7] + V{2}*cell[9] + x30;
auto x33 = ((x21)*(x21));
auto x34 = V{1.5}*x33;
auto x35 = ((x19)*(x19));
auto x36 = V{1.5}*x35;
auto x37 = ((x20)*(x20));
auto x38 = V{1.5}*x37;
auto x39 = x36 + x38 + V{-1};
auto x40 = x34 + x39;
auto x41 = x40*(V{0.166666666666667}*x27*x31 + V{0.166666666666667}*x29*x32);
auto x42 = V{0.25}*x27*x31 + V{0.25}*x29*x32;
auto x43 = V{0.0138888888888889}*x27*x31 + V{0.0138888888888889}*x29*x32;
auto x44 = V{3}*x20;
auto x45 = V{4.5}*((x20 + x21)*(x20 + x21));
auto x46 = -x34;
auto x47 = V{1} - x38;
auto x48 = x46 + x47;
auto x49 = V{3}*x21;
auto x50 = -x36;
auto x51 = x49 + x50;
auto x52 = x44 + x45 + x48 + x51;
auto x53 = x40 + x49;
auto x54 = x44 - x45 + x53;
auto x55 = -x21;
auto x56 = x19 + x55;
auto x57 = -x49;
auto x58 = V{3}*x19;
auto x59 = x40 + x58;
auto x60 = x57 + x59;
auto x61 = x60 - V{4.5}*((x56)*(x56));
auto x62 = V{0.0277777777777778}*x27*x31 + V{0.0277777777777778}*x29*x32;
auto x63 = x19 - x20;
auto x64 = -x44;
auto x65 = x59 + x64;
auto x66 = x65 - V{4.5}*((x63)*(x63));
auto x67 = V{1.11022302462516e-16}*cell[12];
auto x68 = V{4.5}*((x19 + x21)*(x19 + x21));
auto x69 = x53 + x58 - x68;
auto x70 = -x43*x69;
auto x71 = x48 + x58;
auto x72 = x51 + x68 + x71;
auto x73 = x43*x72;
auto x74 = -x58;
auto x75 = -V{4.5}*((x56)*(x56));
auto x76 = x53 + x74 + x75;
auto x77 = -x43*x76;
auto x78 = V{3}*x33;
auto x79 = x47 + x51 + x78;
auto x80 = x62*x79;
auto x81 = V{4.5}*((x19 + x20)*(x19 + x20));
auto x82 = x44 + x50;
auto x83 = x71 + x81 + x82;
auto x84 = V{0.0555555555555556}*x27*x31 + V{0.0555555555555556}*x29*x32;
auto x85 = V{3}*x37;
auto x86 = x46 + x82 + x85 + V{1};
auto x87 = V{5.55111512312578e-17}*x27*x31 + V{5.55111512312578e-17}*x29*x32;
auto x88 = V{1.11022302462516e-16}*x27*x31 + V{1.11022302462516e-16}*x29*x32;
auto x89 = x39 + x49 - x78;
auto x90 = x62*x89;
auto x91 = x20 + x55;
auto x92 = -V{4.5}*((x91)*(x91));
auto x93 = x53 + x64 + x92;
auto x94 = V{3}*x35;
auto x95 = x34 + V{-1};
auto x96 = x38 + x58 - x94 + x95;
auto x97 = -x62*x96;
auto x98 = x71 + x94;
auto x99 = x62*x98;
auto x100 = V{1.11022302462516e-16}*cell[11];
auto x101 = V{5.55111512312578e-17}*cell[0] + V{5.55111512312578e-17}*cell[10] + V{1.11022302462516e-16}*cell[17] + V{5.55111512312578e-17}*cell[1] + V{5.55111512312578e-17};
auto x102 = V{1.66533453693773e-16}*cell[10] + V{1.66533453693773e-16}*cell[1] - x27*(V{5.55111512312578e-17}*cell[12] + V{1.11022302462516e-16}*cell[13] + V{5.55111512312578e-17}*cell[15] + V{5.55111512312578e-17}*cell[16] + V{1.11022302462516e-16}*cell[18] + V{5.55111512312578e-17}*cell[3] + V{1.11022302462516e-16}*cell[5] + V{5.55111512312578e-17}*cell[6] + V{5.55111512312578e-17}*cell[7] + x100 + x101) - x29*(V{5.55111512312578e-17}*cell[11] + V{5.55111512312578e-17}*cell[13] + V{5.55111512312578e-17}*cell[14] + V{1.11022302462516e-16}*cell[15] + V{5.55111512312578e-17}*cell[2] + V{5.55111512312578e-17}*cell[4] + V{5.55111512312578e-17}*cell[5] + V{1.11022302462516e-16}*cell[7] + V{1.11022302462516e-16}*cell[9] + x101 + x67) - x35*(V{8.32667268468867e-17}*x27*x31 + V{8.32667268468867e-17}*x29*x32) - x41 + x97 + x99 + V{-2.22044604925031e-16};
auto x103 = V{2.22044604925031e-16}*cell[11] + V{3.33066907387547e-16}*cell[13] + V{3.33066907387547e-16}*cell[14] + V{4.71844785465692e-16}*cell[15] + V{5.27355936696949e-16}*cell[16] + V{8.88178419700125e-16}*cell[17] + V{2.22044604925031e-16}*cell[18] + V{2.22044604925031e-16}*cell[2] + V{1.11022302462516e-16}*cell[3] + V{3.33066907387547e-16}*cell[4] + V{3.33066907387547e-16}*cell[5] + V{4.71844785465692e-16}*cell[6] + V{5.27355936696949e-16}*cell[7] + V{2.22044604925031e-16}*cell[9] + x102 - x33*x87 - x37*x88 + x52*(V{0.0277777777777778}*x27*x31 + V{0.0277777777777778}*x29*x32) - x54*(V{6.16790569236198e-18}*x27*x31 + V{6.16790569236198e-18}*x29*x32) + x62*x83 - x62*x93 + x67 + x70 + x73 + x77 + x80 + x84*x86 - x90;
auto x104 = x40 + x44;
auto x105 = x104 + x57;
auto x106 = x105 - V{4.5}*((x91)*(x91));
auto x107 = x44 + x59 - x81;
auto x108 = -x107*x43;
auto x109 = x43*x83;
auto x110 = -V{4.5}*((x63)*(x63));
auto x111 = x104 + x110 + x74;
auto x112 = -x111*x43;
auto x113 = x62*x86;
auto x114 = x36 + x44 - x85 + x95;
auto x115 = x114*x62;
auto x116 = V{2.22044604925031e-16}*cell[12] + V{4.44089209850063e-16}*cell[13] + V{4.9960036108132e-16}*cell[14] + V{3.33066907387547e-16}*cell[15] + V{3.33066907387547e-16}*cell[16] + V{4.44089209850063e-16}*cell[17] + V{1.11022302462516e-16}*cell[2] + V{2.22044604925031e-16}*cell[3] + V{4.44089209850063e-16}*cell[4] + V{4.9960036108132e-16}*cell[5] + V{3.33066907387547e-16}*cell[6] + V{3.33066907387547e-16}*cell[7] + x100 + x102 + x108 + x109 + x112 + x113 - x115 - x33*x88 - x37*x87 + x52*(V{0.0277777777777778}*x27*x31 + V{0.0277777777777778}*x29*x32) - x54*(V{3.08395284618099e-18}*x27*x31 + V{3.08395284618099e-18}*x29*x32) + x62*x72 + x79*x84;
auto x117 = x27*(x103 - x43*x61 - x62*x66) + x29*(-x106*x62 + x116 - x43*x66 - x61*x62);
auto x118 = V{0.0833333333333334}*cell[13];
auto x119 = V{0.0833333333333334}*cell[14];
auto x120 = V{0.0833333333333334}*cell[15];
auto x121 = V{0.0833333333333334}*cell[16];
auto x122 = V{0.0833333333333334}*cell[4];
auto x123 = V{0.0833333333333334}*cell[5];
auto x124 = V{0.0833333333333334}*cell[6];
auto x125 = V{0.0833333333333334}*cell[7];
auto x126 = V{0.0833333333333333}*cell[11];
auto x127 = V{0.0833333333333333}*cell[12];
auto x128 = V{0.0833333333333333}*cell[2];
auto x129 = V{0.0833333333333333}*cell[3];
auto x130 = V{3.46944695195361e-18}*cell[0] + V{3.46944695195361e-18}*cell[10] + V{6.93889390390723e-18}*cell[17] + V{3.46944695195361e-18}*cell[1] + V{3.46944695195361e-18};
auto x131 = x27*(V{6.93889390390723e-18}*cell[11] + V{3.46944695195361e-18}*cell[12] + V{6.93889390390723e-18}*cell[13] + V{3.46944695195361e-18}*cell[15] + V{3.46944695195361e-18}*cell[16] + V{6.93889390390723e-18}*cell[18] + V{3.46944695195361e-18}*cell[3] + V{6.93889390390723e-18}*cell[5] + V{3.46944695195361e-18}*cell[6] + V{3.46944695195361e-18}*cell[7] + x130);
auto x132 = x29*(V{3.46944695195361e-18}*cell[11] + V{6.93889390390723e-18}*cell[12] + V{3.46944695195361e-18}*cell[13] + V{3.46944695195361e-18}*cell[14] + V{6.93889390390723e-18}*cell[15] + V{3.46944695195361e-18}*cell[2] + V{3.46944695195361e-18}*cell[4] + V{3.46944695195361e-18}*cell[5] + V{6.93889390390723e-18}*cell[7] + V{6.93889390390723e-18}*cell[9] + x130);
auto x133 = V{0.00231481481481481}*x27*x31 + V{0.00231481481481481}*x29*x32;
auto x134 = V{0.0416666666666667}*x27*x31 + V{0.0416666666666667}*x29*x32;
auto x135 = x134*x37;
auto x136 = x134*x33;
auto x137 = V{0.0833333333333333}*x27*x31 + V{0.0833333333333333}*x29*x32;
auto x138 = V{0.166666666666667}*cell[10] - V{0.333333333333333}*cell[17] - V{0.166666666666667}*cell[18] + V{0.166666666666667}*cell[1] - V{0.166666666666667}*cell[9] + x118 + x119 + x120 + x121 + x122 + x123 + x124 + x125 - x126 - x127 - x128 - x129 - x131 - x132 + x133*x52 + x133*x54 + x135 + x136 - x137*x35 + V{-0.0555555555555555};
auto x139 = V{0.00115740740740741}*x27*x31 + V{0.00115740740740741}*x29*x32;
auto x140 = V{0.0833333333333333}*cell[10] - V{0.166666666666667}*cell[17] - V{0.0833333333333334}*cell[18] + V{0.0833333333333333}*cell[1] - V{0.0833333333333334}*cell[9] + x131 + x132 - x134*x35 + x139*x52 + x139*x54 + V{0.0555555555555555};
auto x141 = -V{0.166666666666667}*cell[11] + V{0.166666666666667}*cell[15] + V{0.166666666666667}*cell[16] - V{0.166666666666667}*cell[2] + V{0.166666666666667}*cell[6] + V{0.166666666666667}*cell[7] - x118 - x119 - x122 - x123 + x127 + x129 - x136 + x137*x37 + x140;
auto x142 = -V{0.166666666666667}*cell[12] + V{0.166666666666667}*cell[13] + V{0.166666666666667}*cell[14] - V{0.166666666666667}*cell[3] + V{0.166666666666667}*cell[4] + V{0.166666666666667}*cell[5] - x120 - x121 - x124 - x125 + x126 + x128 - x135 + x137*x33 + x140;
auto x143 = x27*x31 + x29*x32;
auto x144 = V{0.125}*x143*x19;
auto x145 = x144*x20;
auto x146 = V{0.0208333333333333}*x27*x31 + V{0.0208333333333333}*x29*x32;
auto x147 = V{0.0208333333333333}*cell[0] + V{0.0208333333333333}*cell[10] + V{0.0416666666666667}*cell[17] + V{0.0208333333333333}*cell[1] + V{0.0208333333333333};
auto x148 = -x27*(V{0.0416666666666667}*cell[11] + V{0.0208333333333333}*cell[12] + V{0.0416666666666667}*cell[13] + V{0.0208333333333333}*cell[15] + V{0.0208333333333333}*cell[16] + V{0.0416666666666667}*cell[18] + V{0.0208333333333333}*cell[3] + V{0.0416666666666667}*cell[5] + V{0.0208333333333333}*cell[6] + V{0.0208333333333333}*cell[7] + x147);
auto x149 = -x29*(V{0.0208333333333333}*cell[11] + V{0.0416666666666667}*cell[12] + V{0.0208333333333333}*cell[13] + V{0.0208333333333333}*cell[14] + V{0.0416666666666667}*cell[15] + V{0.0208333333333333}*cell[2] + V{0.0208333333333333}*cell[4] + V{0.0208333333333333}*cell[5] + V{0.0416666666666667}*cell[7] + V{0.0416666666666667}*cell[9] + x147);
auto x150 = V{0.0416666666666667}*x27*x31 + V{0.0416666666666667}*x29*x32;
auto x151 = V{0.0833333333333333}*cell[11] + V{0.0416666666666667}*cell[15] + V{0.0416666666666667}*cell[16] + V{0.0833333333333333}*cell[2] + V{0.0416666666666667}*cell[6] + V{0.0416666666666667}*cell[7] + x148 + x149 - x150*x37 + V{0.0138888888888889};
auto x152 = V{0.000578703703703704}*x27*x31 + V{0.000578703703703704}*x29*x32;
auto x153 = V{0.0833333333333333}*cell[10] + V{0.0833333333333334}*cell[17] + V{0.0416666666666667}*cell[18] + V{0.0833333333333333}*cell[1] + V{0.0416666666666667}*cell[9] - x150*x35 - x152*x52 - x152*x54;
auto x154 = -V{0.0416666666666667}*cell[12] - V{0.0416666666666667}*cell[3] + x146*x33 + x151 + x153;
auto x155 = V{0.416666666666667}*cell[13] - V{0.0833333333333333}*cell[14] + V{0.416666666666667}*cell[4] - V{0.0833333333333333}*cell[5] - x145 + x154;
auto x156 = x110 + x65;
auto x157 = -x156*x43;
auto x158 = -V{0.0833333333333333}*cell[13] + V{0.416666666666667}*cell[14] - V{0.0833333333333333}*cell[4] + V{0.416666666666667}*cell[5] + x145 + x154;
auto x159 = x144*x21;
auto x160 = V{0.0833333333333333}*cell[12] + V{0.0416666666666667}*cell[13] + V{0.0416666666666667}*cell[14] + V{0.0833333333333333}*cell[3] + V{0.0416666666666667}*cell[4] + V{0.0416666666666667}*cell[5] - x150*x33;
auto x161 = -V{0.0416666666666667}*cell[11] - V{0.0416666666666667}*cell[2] + x146*x37 + x148 + x149 + x153 + x160 + V{0.0138888888888889};
auto x162 = V{0.416666666666667}*cell[15] - V{0.0833333333333333}*cell[16] + V{0.416666666666667}*cell[6] - V{0.0833333333333333}*cell[7] - x159 + x161;
auto x163 = x60 + x75;
auto x164 = -x163*x43;
auto x165 = -V{0.0833333333333333}*cell[15] + V{0.416666666666667}*cell[16] - V{0.0833333333333333}*cell[6] + V{0.416666666666667}*cell[7] + x159 + x161;
auto x166 = V{0.00578703703703704}*x27*x31 + V{0.00578703703703704}*x29*x32;
auto x167 = V{0.125}*x143*x20*x21;
auto x168 = -V{0.0416666666666667}*cell[10] - V{0.0416666666666667}*cell[1] + x146*x35 + x151 + x160;
auto x169 = V{0.833333333333333}*cell[17] - V{0.0833333333333333}*cell[18] - V{0.0833333333333333}*cell[9] - x167 + x168;
auto x170 = x105 + x92;
auto x171 = V{0.00115740740740741}*x27*x31 + V{0.00115740740740741}*x29*x32;
auto x172 = -V{0.166666666666667}*cell[17] + V{0.416666666666667}*cell[18] + V{0.416666666666667}*cell[9] + x167 + x168 + x171*x52 + x171*x54;
auto x173 = x27*(x103 - x156*x62 + x164) + x29*(x116 + x157 - x163*x62 - x170*x62);
auto x0 = -x22*(V{0.166666666666667}*x117*x40 + V{0.333333333333333}) + x23*(V{0.5}*cell[10] + V{1}*cell[13] + V{1}*cell[14] + V{1}*cell[15] + V{1}*cell[16] + V{1}*cell[18] + V{0.5}*cell[1] + V{0.5}*cell[2] + V{0.5}*cell[3] + V{1}*cell[4] + V{1}*cell[5] + V{1}*cell[6] + V{1}*cell[7] + V{1}*cell[9] + x24 + x25 + x26 - x27*(V{0.25}*cell[12] + V{0.5}*cell[13] + V{0.25}*cell[15] + V{0.25}*cell[16] + V{0.5}*cell[18] + V{0.25}*cell[3] + V{0.5}*cell[5] + V{0.25}*cell[6] + V{0.25}*cell[7] + x24 + x28) - x29*(V{0.25}*cell[11] + V{0.25}*cell[13] + V{0.25}*cell[14] + V{0.5}*cell[15] + V{0.25}*cell[2] + V{0.25}*cell[4] + V{0.25}*cell[5] + V{0.5}*cell[7] + V{0.5}*cell[9] + x25 + x28) - x33*x42 - x35*x42 - x37*x42 + x41 - x43*x52 - x43*x54 + V{0.833333333333333});
auto x1 = -x22*(V{0.0277777777777778}*x117*x96 + V{0.0555555555555556}) - x23*(x138 + x97);
auto x2 = -x22*(V{0.0277777777777778}*x114*x117 + V{0.0555555555555556}) + x23*(x115 + x141);
auto x3 = -x22*(V{0.0277777777777778}*x117*x89 + V{0.0555555555555556}) + x23*(x142 + x90);
auto x4 = -x22*(V{0.0138888888888889}*x107*x117 + V{0.0277777777777778}) - x23*(x108 + x155);
auto x5 = -x22*(V{0.0138888888888889}*x117*x66 + V{0.0277777777777778}) - x23*(x157 + x158);
auto x6 = -x22*(V{0.0138888888888889}*x117*x69 + V{0.0277777777777778}) - x23*(x162 + x70);
auto x7 = -x22*(V{0.0138888888888889}*x117*x61 + V{0.0277777777777778}) - x23*(x164 + x165);
auto x8 = -x22*(V{0.0138888888888889}*x117*x54 + V{0.0277777777777778}) - x23*(-x166*x52 + x169 - x54*(V{0.0196759259259259}*x27*x31 + V{0.0196759259259259}*x29*x32));
auto x9 = -x22*(V{0.0138888888888889}*x106*x117 + V{0.0277777777777778}) - x23*(-x170*x43 + x172);
auto x10 = x22*(V{0.0277777777777778}*x173*x98 + V{-0.0555555555555556}) - x23*(x138 + x99);
auto x11 = x22*(V{0.0277777777777778}*x173*x86 + V{-0.0555555555555556}) + x23*(-x113 + x141);
auto x12 = x22*(V{0.0277777777777778}*x173*x79 + V{-0.0555555555555556}) + x23*(x142 - x80);
auto x13 = x22*(V{0.0138888888888889}*x173*x83 + V{-0.0277777777777778}) - x23*(x109 + x155);
auto x14 = -x22*(V{0.0138888888888889}*x111*x117 + V{0.0277777777777778}) - x23*(x112 + x158);
auto x15 = x22*(V{0.0138888888888889}*x173*x72 + V{-0.0277777777777778}) - x23*(x162 + x73);
auto x16 = -x22*(V{0.0138888888888889}*x117*x76 + V{0.0277777777777778}) - x23*(x165 + x77);
auto x17 = x22*(V{0.0138888888888889}*x173*x52 + V{-0.0277777777777778}) - x23*(-x166*x54 + x169 + x52*(V{0.00810185185185185}*x27*x31 + V{0.00810185185185185}*x29*x32));
auto x18 = -x22*(V{0.0138888888888889}*x117*x93 + V{0.0277777777777778}) - x23*(x172 - x43*x93);
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
return { V{0.5}*x173, x33 + x35 + x37 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
