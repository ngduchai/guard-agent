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
struct CSE<CombinedRLBdynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>, momenta::Tuple<momenta::InnerEdgeDensity3D<0, -1, -1>, momenta::FixedVelocityMomentumGeneric, momenta::InnerEdgeStress3D<0, -1, -1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x22 = parameters.template get<descriptors::OMEGA>();
auto x21 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(2);
auto x20 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x19 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x23 = x22 + V{-1};
auto x24 = V{0.5}*cell[2];
auto x25 = V{0.5}*cell[3];
auto x26 = V{2}*cell[8];
auto x27 = V{1} / (x20 + V{-1});
auto x28 = V{0.25}*cell[0] + V{0.25}*cell[10] + V{0.25}*cell[1] + V{0.5}*cell[8] + V{0.25};
auto x29 = V{1} / (x21 + V{-1});
auto x30 = cell[0] + cell[10] + cell[1] + x26 + V{1};
auto x31 = cell[12] + V{2}*cell[14] + cell[15] + cell[16] + V{2}*cell[2] + cell[3] + V{2}*cell[4] + cell[6] + cell[7] + V{2}*cell[9] + x30;
auto x32 = cell[11] + cell[13] + cell[14] + V{2}*cell[16] + V{2}*cell[18] + cell[2] + V{2}*cell[3] + cell[4] + cell[5] + V{2}*cell[6] + x30;
auto x33 = V{0.25}*x27*x31 + V{0.25}*x29*x32;
auto x34 = ((x19)*(x19));
auto x35 = ((x20)*(x20));
auto x36 = ((x21)*(x21));
auto x37 = V{0.0138888888888889}*x27*x31 + V{0.0138888888888889}*x29*x32;
auto x38 = V{3}*x20;
auto x39 = V{4.5}*((x20 + x21)*(x20 + x21));
auto x40 = V{1.5}*x36;
auto x41 = -x40;
auto x42 = V{1.5}*x35;
auto x43 = V{1} - x42;
auto x44 = x41 + x43;
auto x45 = V{3}*x21;
auto x46 = V{1.5}*x34;
auto x47 = -x46;
auto x48 = x45 + x47;
auto x49 = x38 + x39 + x44 + x48;
auto x50 = x42 + x46 + V{-1};
auto x51 = x40 + x50;
auto x52 = x45 + x51;
auto x53 = x38 - x39 + x52;
auto x54 = x51*(V{0.166666666666667}*x27*x31 + V{0.166666666666667}*x29*x32);
auto x55 = V{1.11022302462516e-16}*cell[4];
auto x56 = V{3}*x19;
auto x57 = V{4.5}*((x19 + x21)*(x19 + x21));
auto x58 = x52 + x56 - x57;
auto x59 = x37*x58;
auto x60 = x44 + x56;
auto x61 = x48 + x57 + x60;
auto x62 = -x37*x61;
auto x63 = -x56;
auto x64 = -x21;
auto x65 = x19 + x64;
auto x66 = -V{4.5}*((x65)*(x65));
auto x67 = x52 + x63 + x66;
auto x68 = x37*x67;
auto x69 = V{1.11022302462516e-16}*x27*x31 + V{1.11022302462516e-16}*x29*x32;
auto x70 = -x45;
auto x71 = x51 + x56;
auto x72 = x70 + x71;
auto x73 = x72 - V{4.5}*((x65)*(x65));
auto x74 = V{0.0277777777777778}*x27*x31 + V{0.0277777777777778}*x29*x32;
auto x75 = V{3}*x36;
auto x76 = x45 + x50 - x75;
auto x77 = x74*x76;
auto x78 = V{4.5}*((x19 + x20)*(x19 + x20));
auto x79 = x38 + x71 - x78;
auto x80 = x19 - x20;
auto x81 = -V{4.5}*((x80)*(x80));
auto x82 = x38 + x51;
auto x83 = x63 + x81 + x82;
auto x84 = x20 + x64;
auto x85 = x70 + x82;
auto x86 = x85 - V{4.5}*((x84)*(x84));
auto x87 = V{0.0555555555555556}*x27*x31 + V{0.0555555555555556}*x29*x32;
auto x88 = V{3}*x35;
auto x89 = x40 + V{-1};
auto x90 = x38 + x46 - x88 + x89;
auto x91 = x43 + x48 + x75;
auto x92 = x74*x91;
auto x93 = V{3}*x34;
auto x94 = x42 + x56 + x89 - x93;
auto x95 = x74*x94;
auto x96 = x60 + x93;
auto x97 = -x74*x96;
auto x98 = V{1.11022302462516e-16}*cell[2];
auto x99 = V{5.55111512312578e-17}*cell[0] + V{5.55111512312578e-17}*cell[10] + V{5.55111512312578e-17}*cell[1] + V{1.11022302462516e-16}*cell[8] + V{5.55111512312578e-17};
auto x100 = V{1.66533453693773e-16}*cell[10] + V{2.22044604925031e-16}*cell[18] + V{1.66533453693773e-16}*cell[1] + V{2.22044604925031e-16}*cell[9] + x27*(V{5.55111512312578e-17}*cell[12] + V{1.11022302462516e-16}*cell[14] + V{5.55111512312578e-17}*cell[15] + V{5.55111512312578e-17}*cell[16] + V{5.55111512312578e-17}*cell[3] + V{5.55111512312578e-17}*cell[6] + V{5.55111512312578e-17}*cell[7] + V{1.11022302462516e-16}*cell[9] + x55 + x98 + x99) + x29*(V{5.55111512312578e-17}*cell[11] + V{5.55111512312578e-17}*cell[13] + V{5.55111512312578e-17}*cell[14] + V{1.11022302462516e-16}*cell[16] + V{1.11022302462516e-16}*cell[18] + V{5.55111512312578e-17}*cell[2] + V{1.11022302462516e-16}*cell[3] + V{5.55111512312578e-17}*cell[4] + V{5.55111512312578e-17}*cell[5] + V{1.11022302462516e-16}*cell[6] + x99) + x34*(V{8.32667268468867e-17}*x27*x31 + V{8.32667268468867e-17}*x29*x32) + x54 + x95 + x97 + V{-2.22044604925031e-16};
auto x101 = x37*x79;
auto x102 = x38 + x47;
auto x103 = x102 + x60 + x78;
auto x104 = -x103*x37;
auto x105 = x37*x83;
auto x106 = -x38;
auto x107 = x106 + x71;
auto x108 = x107 - V{4.5}*((x80)*(x80));
auto x109 = x74*x90;
auto x110 = -V{4.5}*((x84)*(x84));
auto x111 = x106 + x110 + x52;
auto x112 = x102 + x41 + x88 + V{1};
auto x113 = x112*x74;
auto x114 = x27*(V{2.22044604925031e-16}*cell[11] + V{9.71445146547012e-17}*cell[12] + V{1.11022302462516e-16}*cell[13] + V{3.33066907387547e-16}*cell[14] + V{4.71844785465692e-16}*cell[15] + V{5.27355936696949e-16}*cell[16] + V{2.22044604925031e-16}*cell[2] + V{9.71445146547012e-17}*cell[3] + V{3.33066907387547e-16}*cell[5] + V{4.71844785465692e-16}*cell[6] + V{5.27355936696949e-16}*cell[7] + V{4.44089209850063e-16}*cell[8] + x100 + x35*x69 + x36*(V{4.85722573273506e-17}*x27*x31 + V{4.85722573273506e-17}*x29*x32) + x37*x73 - x49*(V{3.08395284618099e-18}*x27*x31 + V{3.08395284618099e-18}*x29*x32) + x53*(V{0.0277777777777778}*x27*x31 + V{0.0277777777777778}*x29*x32) + x55 + x59 + x62 + x68 + x74*x79 + x74*x83 + x74*x86 + x77 + x87*x90 - x92) + x29*(V{1.11022302462516e-16}*cell[11] + V{2.22044604925031e-16}*cell[12] + V{4.71844785465692e-16}*cell[13] + V{5.27355936696949e-16}*cell[14] + V{3.33066907387547e-16}*cell[15] + V{3.33066907387547e-16}*cell[16] + V{2.22044604925031e-16}*cell[3] + V{4.71844785465692e-16}*cell[4] + V{5.27355936696949e-16}*cell[5] + V{3.33066907387547e-16}*cell[6] + V{3.33066907387547e-16}*cell[7] + x100 + x101 + x104 + x105 + x108*x37 + x109 + x111*x74 - x113 + x35*(V{5.55111512312578e-17}*x27*x31 + V{5.55111512312578e-17}*x29*x32) + x36*x69 + x53*(V{0.0277777777777778}*x27*x31 + V{0.0277777777777778}*x29*x32) + x58*x74 + x67*x74 + x76*x87 + x98);
auto x115 = V{0.0833333333333334}*cell[13];
auto x116 = V{0.0833333333333334}*cell[14];
auto x117 = V{0.0833333333333334}*cell[15];
auto x118 = V{0.0833333333333334}*cell[16];
auto x119 = V{0.0833333333333334}*cell[4];
auto x120 = V{0.0833333333333334}*cell[5];
auto x121 = V{0.0833333333333334}*cell[6];
auto x122 = V{0.0833333333333334}*cell[7];
auto x123 = V{0.0833333333333333}*cell[11];
auto x124 = V{0.0833333333333333}*cell[12];
auto x125 = V{0.0833333333333333}*cell[2];
auto x126 = V{0.0833333333333333}*cell[3];
auto x127 = V{3.46944695195361e-18}*cell[0] + V{3.46944695195361e-18}*cell[10] + V{3.46944695195361e-18}*cell[1] + V{6.93889390390723e-18}*cell[8] + V{3.46944695195361e-18};
auto x128 = x27*(V{3.46944695195361e-18}*cell[12] + V{6.93889390390723e-18}*cell[14] + V{3.46944695195361e-18}*cell[15] + V{3.46944695195361e-18}*cell[16] + V{6.93889390390723e-18}*cell[2] + V{3.46944695195361e-18}*cell[3] + V{6.93889390390723e-18}*cell[4] + V{3.46944695195361e-18}*cell[6] + V{3.46944695195361e-18}*cell[7] + V{6.93889390390723e-18}*cell[9] + x127);
auto x129 = x29*(V{3.46944695195361e-18}*cell[11] + V{3.46944695195361e-18}*cell[13] + V{3.46944695195361e-18}*cell[14] + V{6.93889390390723e-18}*cell[16] + V{6.93889390390723e-18}*cell[18] + V{3.46944695195361e-18}*cell[2] + V{6.93889390390723e-18}*cell[3] + V{3.46944695195361e-18}*cell[4] + V{3.46944695195361e-18}*cell[5] + V{6.93889390390723e-18}*cell[6] + x127);
auto x130 = V{0.00231481481481481}*x27*x31 + V{0.00231481481481481}*x29*x32;
auto x131 = V{0.0833333333333333}*x27*x31 + V{0.0833333333333333}*x29*x32;
auto x132 = V{0.0416666666666667}*x27*x31 + V{0.0416666666666667}*x29*x32;
auto x133 = x132*x35;
auto x134 = x132*x36;
auto x135 = V{0.166666666666667}*cell[10] - V{0.166666666666667}*cell[18] + V{0.166666666666667}*cell[1] - V{0.333333333333333}*cell[8] - V{0.166666666666667}*cell[9] + x115 + x116 + x117 + x118 + x119 + x120 + x121 + x122 - x123 - x124 - x125 - x126 + x128 + x129 + x130*x49 + x130*x53 + x131*x34 - x133 - x134 + V{-0.0555555555555555};
auto x136 = V{0.00115740740740741}*x27*x31 + V{0.00115740740740741}*x29*x32;
auto x137 = V{0.0833333333333333}*cell[10] - V{0.0833333333333334}*cell[18] + V{0.0833333333333333}*cell[1] - V{0.166666666666667}*cell[8] - V{0.0833333333333334}*cell[9] - x128 - x129 + x132*x34 + x136*x49 + x136*x53 + V{0.0555555555555555};
auto x138 = -V{0.166666666666667}*cell[11] + V{0.166666666666667}*cell[15] + V{0.166666666666667}*cell[16] - V{0.166666666666667}*cell[2] + V{0.166666666666667}*cell[6] + V{0.166666666666667}*cell[7] - x115 - x116 - x119 - x120 + x124 + x126 - x131*x35 + x134 + x137;
auto x139 = -V{0.166666666666667}*cell[12] + V{0.166666666666667}*cell[13] + V{0.166666666666667}*cell[14] - V{0.166666666666667}*cell[3] + V{0.166666666666667}*cell[4] + V{0.166666666666667}*cell[5] - x117 - x118 - x121 - x122 + x123 + x125 - x131*x36 + x133 + x137;
auto x140 = x27*x31 + x29*x32;
auto x141 = V{0.125}*x140*x19;
auto x142 = x141*x20;
auto x143 = V{0.0208333333333333}*x27*x31 + V{0.0208333333333333}*x29*x32;
auto x144 = V{0.0208333333333333}*cell[0] + V{0.0208333333333333}*cell[10] + V{0.0208333333333333}*cell[1] + V{0.0416666666666667}*cell[8] + V{0.0208333333333333};
auto x145 = x27*(V{0.0208333333333333}*cell[12] + V{0.0416666666666667}*cell[14] + V{0.0208333333333333}*cell[15] + V{0.0208333333333333}*cell[16] + V{0.0416666666666667}*cell[2] + V{0.0208333333333333}*cell[3] + V{0.0416666666666667}*cell[4] + V{0.0208333333333333}*cell[6] + V{0.0208333333333333}*cell[7] + V{0.0416666666666667}*cell[9] + x144);
auto x146 = x29*(V{0.0208333333333333}*cell[11] + V{0.0208333333333333}*cell[13] + V{0.0208333333333333}*cell[14] + V{0.0416666666666667}*cell[16] + V{0.0416666666666667}*cell[18] + V{0.0208333333333333}*cell[2] + V{0.0416666666666667}*cell[3] + V{0.0208333333333333}*cell[4] + V{0.0208333333333333}*cell[5] + V{0.0416666666666667}*cell[6] + x144);
auto x147 = V{0.0416666666666667}*x27*x31 + V{0.0416666666666667}*x29*x32;
auto x148 = V{0.0833333333333333}*cell[11] + V{0.0416666666666667}*cell[15] + V{0.0416666666666667}*cell[16] + V{0.0833333333333333}*cell[2] + V{0.0416666666666667}*cell[6] + V{0.0416666666666667}*cell[7] + x145 + x146 + x147*x35 + V{0.0138888888888889};
auto x149 = V{0.000578703703703704}*x27*x31 + V{0.000578703703703704}*x29*x32;
auto x150 = V{0.0833333333333333}*cell[10] + V{0.0416666666666667}*cell[18] + V{0.0833333333333333}*cell[1] + V{0.0833333333333334}*cell[8] + V{0.0416666666666667}*cell[9] + x147*x34 - x149*x49 - x149*x53;
auto x151 = -V{0.0416666666666667}*cell[12] - V{0.0416666666666667}*cell[3] - x143*x36 + x148 + x150;
auto x152 = V{0.416666666666667}*cell[13] - V{0.0833333333333333}*cell[14] + V{0.416666666666667}*cell[4] - V{0.0833333333333333}*cell[5] + x142 + x151;
auto x153 = -V{0.0833333333333333}*cell[13] + V{0.416666666666667}*cell[14] - V{0.0833333333333333}*cell[4] + V{0.416666666666667}*cell[5] - x142 + x151;
auto x154 = x141*x21;
auto x155 = V{0.0833333333333333}*cell[12] + V{0.0416666666666667}*cell[13] + V{0.0416666666666667}*cell[14] + V{0.0833333333333333}*cell[3] + V{0.0416666666666667}*cell[4] + V{0.0416666666666667}*cell[5] + x147*x36;
auto x156 = -V{0.0416666666666667}*cell[11] - V{0.0416666666666667}*cell[2] - x143*x35 + x145 + x146 + x150 + x155 + V{0.0138888888888889};
auto x157 = V{0.416666666666667}*cell[15] - V{0.0833333333333333}*cell[16] + V{0.416666666666667}*cell[6] - V{0.0833333333333333}*cell[7] + x154 + x156;
auto x158 = -V{0.0833333333333333}*cell[15] + V{0.416666666666667}*cell[16] - V{0.0833333333333333}*cell[6] + V{0.416666666666667}*cell[7] - x154 + x156;
auto x159 = V{0.00578703703703704}*x27*x31 + V{0.00578703703703704}*x29*x32;
auto x160 = V{0.125}*x140*x20*x21;
auto x161 = -V{0.0416666666666667}*cell[10] - V{0.0416666666666667}*cell[1] - x143*x34 + x148 + x155;
auto x162 = -V{0.0833333333333333}*cell[18] + V{0.833333333333333}*cell[8] - V{0.0833333333333333}*cell[9] + x160 + x161;
auto x163 = V{0.00115740740740741}*x27*x31 + V{0.00115740740740741}*x29*x32;
auto x164 = V{0.416666666666667}*cell[18] - V{0.166666666666667}*cell[8] + V{0.416666666666667}*cell[9] - x160 + x161 + x163*x49 + x163*x53;
auto x0 = -x22*(-V{0.166666666666667}*x114*x51 + V{0.333333333333333}) + x23*(V{0.5}*cell[10] + V{0.5}*cell[11] + V{0.5}*cell[12] + V{1}*cell[13] + V{1}*cell[14] + V{1}*cell[15] + V{1}*cell[16] + V{1}*cell[18] + V{0.5}*cell[1] + V{1}*cell[4] + V{1}*cell[5] + V{1}*cell[6] + V{1}*cell[7] + V{1}*cell[9] + x24 + x25 + x26 + x27*(V{0.25}*cell[12] + V{0.5}*cell[14] + V{0.25}*cell[15] + V{0.25}*cell[16] + V{0.25}*cell[3] + V{0.5}*cell[4] + V{0.25}*cell[6] + V{0.25}*cell[7] + V{0.5}*cell[9] + x24 + x28) + x29*(V{0.25}*cell[11] + V{0.25}*cell[13] + V{0.25}*cell[14] + V{0.5}*cell[16] + V{0.5}*cell[18] + V{0.25}*cell[2] + V{0.25}*cell[4] + V{0.25}*cell[5] + V{0.5}*cell[6] + x25 + x28) + x33*x34 + x33*x35 + x33*x36 - x37*x49 - x37*x53 - x54 + V{0.833333333333333});
auto x1 = -x22*(-V{0.0277777777777778}*x114*x94 + V{0.0555555555555556}) - x23*(x135 + x95);
auto x2 = -x22*(-V{0.0277777777777778}*x114*x90 + V{0.0555555555555556}) + x23*(-x109 + x138);
auto x3 = -x22*(-V{0.0277777777777778}*x114*x76 + V{0.0555555555555556}) + x23*(x139 - x77);
auto x4 = -x22*(-V{0.0138888888888889}*x114*x79 + V{0.0277777777777778}) - x23*(x101 + x152);
auto x5 = -x22*(-V{0.0138888888888889}*x108*x114 + V{0.0277777777777778}) - x23*(x153 + x37*(x107 + x81));
auto x6 = -x22*(-V{0.0138888888888889}*x114*x58 + V{0.0277777777777778}) - x23*(x157 + x59);
auto x7 = -x22*(-V{0.0138888888888889}*x114*x73 + V{0.0277777777777778}) - x23*(x158 + x37*(x66 + x72));
auto x8 = -x22*(-V{0.0138888888888889}*x114*x53 + V{0.0277777777777778}) - x23*(-x159*x49 + x162 + x53*(V{0.00810185185185185}*x27*x31 + V{0.00810185185185185}*x29*x32));
auto x9 = -x22*(-V{0.0138888888888889}*x114*x86 + V{0.0277777777777778}) - x23*(x164 + x37*(x110 + x85));
auto x10 = -x22*(V{0.0277777777777778}*x114*x96 + V{0.0555555555555556}) - x23*(x135 + x97);
auto x11 = -x22*(V{0.0277777777777778}*x112*x114 + V{0.0555555555555556}) + x23*(x113 + x138);
auto x12 = -x22*(V{0.0277777777777778}*x114*x91 + V{0.0555555555555556}) + x23*(x139 + x92);
auto x13 = -x22*(V{0.0138888888888889}*x103*x114 + V{0.0277777777777778}) - x23*(x104 + x152);
auto x14 = -x22*(-V{0.0138888888888889}*x114*x83 + V{0.0277777777777778}) - x23*(x105 + x153);
auto x15 = -x22*(V{0.0138888888888889}*x114*x61 + V{0.0277777777777778}) - x23*(x157 + x62);
auto x16 = -x22*(-V{0.0138888888888889}*x114*x67 + V{0.0277777777777778}) - x23*(x158 + x68);
auto x17 = -x22*(V{0.0138888888888889}*x114*x49 + V{0.0277777777777778}) - x23*(-x159*x53 + x162 - x49*(V{0.0196759259259259}*x27*x31 + V{0.0196759259259259}*x29*x32));
auto x18 = -x22*(-V{0.0138888888888889}*x111*x114 + V{0.0277777777777778}) - x23*(x111*x37 + x164);
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
return { -V{0.5}*x114, x34 + x35 + x36 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
