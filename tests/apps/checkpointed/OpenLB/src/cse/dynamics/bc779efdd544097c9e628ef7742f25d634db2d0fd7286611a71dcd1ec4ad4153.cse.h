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
struct CSE<CombinedRLBdynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>, momenta::Tuple<momenta::VelocityBoundaryDensity<2, -1>, momenta::FixedVelocityMomentumGeneric, momenta::RegularizedBoundaryStress<2, -1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x21 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(2);
auto x19 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x20 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x22 = parameters.template get<descriptors::OMEGA>();
auto x23 = x22 + V{-1};
auto x24 = x21 + V{-1};
auto x25 = -1/x24;
auto x26 = V{2}*cell[16] + V{2}*cell[18] + V{2}*cell[6] + V{2}*cell[8];
auto x27 = cell[0] + cell[10] + cell[11] + cell[13] + cell[14] + cell[1] + cell[2] + V{2}*cell[3] + cell[4] + cell[5] + x26 + V{1};
auto x28 = x25*x27;
auto x29 = V{0.0277777777777778}*x28;
auto x30 = ((x19)*(x19));
auto x31 = V{3}*x19;
auto x32 = ((x20)*(x20));
auto x33 = V{1.5}*x32;
auto x34 = -x33;
auto x35 = ((x21)*(x21));
auto x36 = V{1.5}*x35;
auto x37 = V{1} - x36;
auto x38 = x34 + x37;
auto x39 = x31 + x38;
auto x40 = V{3}*x30 + x39;
auto x41 = V{3}*x20;
auto x42 = V{1.5}*x30;
auto x43 = -x42;
auto x44 = x41 + x43;
auto x45 = V{3}*x32 + x37 + x44;
auto x46 = x33 + x36 + V{-1};
auto x47 = -V{3}*x30 + x31 + x46;
auto x48 = -x47;
auto x49 = x42 + V{-1};
auto x50 = -V{3}*x32 + x36 + x41 + x49;
auto x51 = -x50;
auto x52 = ((x19 + x20)*(x19 + x20));
auto x53 = x39 + x44 + V{4.5}*x52;
auto x54 = -x31;
auto x55 = x19 - x20;
auto x56 = -V{4.5}*((x55)*(x55));
auto x57 = x42 + x46;
auto x58 = x41 + x57;
auto x59 = x54 + x56 + x58;
auto x60 = -x59;
auto x61 = -x41 + x57;
auto x62 = x31 + x61;
auto x63 = x62 - V{4.5}*((x55)*(x55));
auto x64 = -x63;
auto x65 = x31 - V{4.5}*x52 + x58;
auto x66 = -x65;
auto x67 = V{0.0555555555555556}*x28;
auto x68 = V{3}*x21;
auto x69 = x33 - V{3}*x35 + x49 + x68;
auto x70 = -x69;
auto x71 = -x21;
auto x72 = x19 + x71;
auto x73 = x57 + x68;
auto x74 = x54 + x73 - V{4.5}*((x72)*(x72));
auto x75 = -x74;
auto x76 = x20 + x71;
auto x77 = x61 + x68 - V{4.5}*((x76)*(x76));
auto x78 = -x77;
auto x79 = ((x19 + x21)*(x19 + x21));
auto x80 = x31 + x73 - V{4.5}*x79;
auto x81 = -x80;
auto x82 = ((x20 + x21)*(x20 + x21));
auto x83 = x58 + x68 - V{4.5}*x82;
auto x84 = -x83;
auto x85 = -x57;
auto x86 = V{0.333333333333333}*x28*x85;
auto x87 = V{0.0555555555555555}*x28;
auto x88 = V{0.0555555555555555}*x28;
auto x89 = V{0.0277777777777778}*x28;
auto x90 = V{1.66533453693773e-16}*cell[10] + V{1.11022302462516e-16}*cell[11] + V{4.71844785465692e-16}*cell[13] + V{5.27355936696949e-16}*cell[14] + V{6.66133814775094e-16}*cell[16] + V{4.44089209850063e-16}*cell[18] + V{1.66533453693773e-16}*cell[1] + V{1.11022302462516e-16}*cell[2] + V{4.44089209850063e-16}*cell[3] + V{4.71844785465692e-16}*cell[4] + V{5.27355936696949e-16}*cell[5] + V{6.66133814775094e-16}*cell[6] + V{2.22044604925031e-16};
auto x91 = V{0.0555555555555555}*x28*x48 + V{0.0277777777777778}*x28*x64 + V{0.0277777777777778}*x28*x66 + V{0.111111111111111}*x28*x70 + x40*x67 + x45*x67 + x51*x87 + x53*x89 + x60*x89 + x75*x88 + x78*x87 + x81*x88 + x84*x87 + x86 + x90;
auto x92 = V{0.166666666666667}*cell[16];
auto x93 = V{0.166666666666667}*cell[6];
auto x94 = V{0.0833333333333333}*cell[11];
auto x95 = V{0.0833333333333333}*cell[2];
auto x96 = V{0.333333333333333}*cell[18];
auto x97 = V{0.333333333333333}*cell[8];
auto x98 = V{1} / (x24);
auto x99 = x27*x98;
auto x100 = V{0.00462962962962963}*x99;
auto x101 = V{0.00925925925925926}*x99;
auto x102 = V{0.0462962962962963}*x99;
auto x103 = V{0.00925925925925926}*x99;
auto x104 = x100*x45;
auto x105 = V{0.00462962962962963}*x99;
auto x106 = x105*x80;
auto x107 = x105*x74;
auto x108 = V{0.166666666666667}*cell[3];
auto x109 = V{0.00231481481481482}*x99;
auto x110 = x109*x65;
auto x111 = x109*x63;
auto x112 = x109*x59;
auto x113 = V{0.0833333333333334}*cell[13] + V{0.0833333333333334}*cell[14] + V{0.0833333333333334}*cell[4] + V{0.0833333333333334}*cell[5] + x101*x69 - x108 + x109*x53 - x110 - x111 - x112 + V{-0.0555555555555555};
auto x114 = V{0.0555555555555556}*x22;
auto x115 = V{0.166666666666667}*cell[18];
auto x116 = V{0.166666666666667}*cell[8];
auto x117 = V{0.0833333333333333}*cell[10];
auto x118 = V{0.0833333333333333}*cell[1];
auto x119 = V{0.333333333333333}*cell[16];
auto x120 = V{0.333333333333333}*cell[6];
auto x121 = x100*x40;
auto x122 = x105*x83;
auto x123 = x105*x77;
auto x124 = -x92;
auto x125 = -x93;
auto x126 = x104 + x106 + x107 + x124 + x125 - V{0.00462962962962963}*x27*x50*x98 + x94 + x95 + V{0.0555555555555555};
auto x127 = -x115;
auto x128 = -x116;
auto x129 = x117 + x118 + x121 + x122 + x123 + x127 + x128 - V{0.00462962962962963}*x27*x47*x98;
auto x130 = V{0.166666666666667}*cell[13] + V{0.166666666666667}*cell[14] - V{0.333333333333333}*cell[3] + V{0.166666666666667}*cell[4] + V{0.166666666666667}*cell[5];
auto x131 = V{0.0115740740740741}*x99;
auto x132 = V{0.0162037037037037}*x99;
auto x133 = V{0.00231481481481481}*x99;
auto x134 = V{0.00462962962962963}*x99;
auto x135 = V{0.0833333333333333}*cell[10] + V{0.0833333333333334}*cell[18] + V{0.0833333333333333}*cell[1] + V{0.0833333333333334}*cell[8] - x109*x77 - x109*x83 + x134*x40 - x134*x47 + V{0.0138888888888889};
auto x136 = V{0.0833333333333333}*cell[11] + V{0.0833333333333334}*cell[16] + V{0.0833333333333333}*cell[2] + V{0.0833333333333334}*cell[6] - x109*x74 - x109*x80 + x134*x45 - x134*x50;
auto x137 = -V{0.0833333333333333}*cell[3] + x100*x69 + x135 + x136;
auto x138 = V{0.416666666666667}*cell[13] - V{0.0833333333333333}*cell[14] + V{0.416666666666667}*cell[4] - V{0.0833333333333333}*cell[5] + x133*x59 + x133*x63 + x137;
auto x139 = V{0.0277777777777778}*x22;
auto x140 = -V{0.0833333333333333}*cell[13] + V{0.416666666666667}*cell[14] - V{0.0833333333333333}*cell[4] + V{0.416666666666667}*cell[5] - x133*x53 + x133*x65 + x137;
auto x141 = V{0.00462962962962963}*x99;
auto x142 = V{0.00231481481481481}*x99;
auto x143 = V{0.00115740740740741}*x99;
auto x144 = V{0.0416666666666667}*cell[13] + V{0.0416666666666667}*cell[14] + V{0.166666666666667}*cell[3] + V{0.0416666666666667}*cell[4] + V{0.0416666666666667}*cell[5] - x103*x69 + x143*x53 - x143*x59 - x143*x63 - x143*x65;
auto x145 = -V{0.0416666666666667}*cell[11] - V{0.0416666666666667}*cell[2] + x135 - x142*x45 + x142*x50 + x144;
auto x146 = -V{0.166666666666667}*cell[16] + V{0.833333333333333}*cell[6] + x141*x74 + x145;
auto x147 = V{0.0277777777777778}*x99;
auto x148 = -x68;
auto x149 = x148 + x31 + x57 - V{4.5}*((x72)*(x72));
auto x150 = V{0.0231481481481481}*x99;
auto x151 = V{0.833333333333333}*cell[16] - V{0.166666666666667}*cell[6] + x141*x80 + x145;
auto x152 = -V{0.0416666666666667}*cell[10] - V{0.0416666666666667}*cell[1] + x136 - x142*x40 + x142*x47 + x144 + V{0.0138888888888889};
auto x153 = -V{0.166666666666667}*cell[18] + V{0.833333333333333}*cell[8] + x141*x77 + x152;
auto x154 = x148 + x58 - V{4.5}*((x76)*(x76));
auto x155 = V{0.833333333333333}*cell[18] - V{0.166666666666667}*cell[8] + x141*x83 + x152;
auto x156 = -V{0.0833333333333334}*cell[13] - V{0.0833333333333334}*cell[14] - V{0.0833333333333334}*cell[4] - V{0.0833333333333334}*cell[5] + x108 + x110 + x111 + x112 - V{0.00231481481481482}*x27*x53*x98 - V{0.00925925925925926}*x27*x69*x98;
auto x157 = V{0.00462962962962963}*x28;
auto x158 = V{0.00462962962962963}*x28;
auto x159 = x43 + x68;
auto x160 = x159 + x34 + V{3}*x35 + V{1};
auto x161 = x159 + x39 + V{4.5}*x79;
auto x162 = x38 + x44 + x68 + V{4.5}*x82;
auto x163 = V{0.0555555555555555}*x99;
auto x164 = V{0.0555555555555555}*x99;
auto x165 = V{0.0277777777777778}*x99;
auto x166 = V{0.0555555555555556}*x99;
auto x0 = -V{0.333333333333333}*x22*(-x25*x85*x91 + V{1}) + x23*(V{0.5}*cell[10] + V{0.5}*cell[11] + V{1}*cell[13] + V{1}*cell[14] + V{0.5}*cell[1] + V{0.5}*cell[2] + V{1}*cell[3] + V{1}*cell[4] + V{1}*cell[5] + x26 - x29*x40 - x29*x45 - x29*x48 - x29*x51 - x29*x53 - x29*x60 - x29*x64 - x29*x66 - x67*x70 - x67*x75 - x67*x78 - x67*x81 - x67*x84 - x86 + V{0.833333333333333});
auto x1 = -x114*(-x25*x48*x91 + V{1}) - x23*(V{0.166666666666667}*cell[10] + V{0.166666666666667}*cell[1] + x100*x50 + x101*x77 + x101*x83 + x102*x47 + x103*x40 - x104 - x106 - x107 + x113 + x92 + x93 - x94 - x95 - x96 - x97);
auto x2 = -x114*(-x25*x51*x91 + V{1}) - x23*(V{0.166666666666667}*cell[11] + V{0.166666666666667}*cell[2] + x100*x47 + x101*x74 + x101*x80 + x102*x50 + x103*x45 + x113 + x115 + x116 - x117 - x118 - x119 - x120 - x121 - x122 - x123);
auto x3 = -x114*(-x25*x70*x91 + V{1}) - x23*(-x100*x53 - x126 - x129 - x130 + V{0.00462962962962963}*x27*x59*x98 + V{0.00462962962962963}*x27*x63*x98 + V{0.00462962962962963}*x27*x65*x98 + V{0.037037037037037}*x27*x69*x98);
auto x4 = -x139*(-x25*x66*x91 + V{1}) - x23*(x131*x53 + x132*x65 + x138);
auto x5 = -x139*(-x25*x64*x91 + V{1}) - x23*(-x131*x59 + x132*x63 + x140);
auto x6 = -x139*(-x25*x81*x91 + V{1}) - x23*(x100*x80 + x146);
auto x7 = -x139*(x149*x25*x91 + V{1}) - x23*(x147*x149 - x150*x74 + x151);
auto x8 = -x139*(-x25*x84*x91 + V{1}) - x23*(x100*x83 + x153);
auto x9 = -x139*(x154*x25*x91 + V{1}) - x23*(x147*x154 - x150*x77 + x155);
auto x10 = -x114*(-x25*x40*x91 + V{1}) - x23*(V{0.166666666666667}*cell[10] + V{0.166666666666667}*cell[1] - x102*x40 - x103*x47 - x126 - x156 + V{0.00925925925925926}*x27*x77*x98 + V{0.00925925925925926}*x27*x83*x98 - x96 - x97);
auto x11 = -x114*(-x25*x45*x91 + V{1}) - x23*(V{0.166666666666667}*cell[11] + V{0.166666666666667}*cell[2] - x102*x45 - x103*x50 - x119 - x120 - x129 - x156 + V{0.00925925925925926}*x27*x74*x98 + V{0.00925925925925926}*x27*x80*x98 + V{-0.0555555555555555});
auto x12 = -x114*(-x160*x25*x91 + V{1}) + x23*(x117 + x118 + x124 + x125 + x127 + x128 + x130 + x157*x75 + x157*x78 + x157*x81 + x157*x84 - x158*x40 - x158*x45 - x158*x48 - x158*x51 - x158*x53 - x158*x60 - x158*x64 - x158*x66 - x160*x67 + V{0.0185185185185185}*x28*x70 + x94 + x95 + V{0.0555555555555555});
auto x13 = -x139*(-x25*x53*x91 + V{1}) - x23*(-x131*x65 - x132*x53 + x138);
auto x14 = -x139*(-x25*x60*x91 + V{1}) - x23*(-x131*x63 + x132*x59 + x140);
auto x15 = -x139*(-x161*x25*x91 + V{1}) - x23*(x146 - x147*x161 - x150*x80);
auto x16 = -x139*(-x25*x75*x91 + V{1}) - x23*(x100*x74 + x151);
auto x17 = -x139*(-x162*x25*x91 + V{1}) - x23*(-x147*x162 - x150*x83 + x153);
auto x18 = -x139*(-x25*x78*x91 + V{1}) - x23*(x100*x77 + x155);
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
return { -V{1}*x98*(x163*x50 + x163*x77 + x163*x83 + x164*x74 + x164*x80 - x165*x53 + x165*x59 - x166*x40 - x166*x45 + V{0.0555555555555555}*x47*x99 + V{0.333333333333333}*x57*x99 + V{0.0277777777777778}*x65*x99 + V{0.111111111111111}*x69*x99 + x90 + V{0.0277777777777778}*x99*(x56 + x62)), x30 + x32 + x35 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
