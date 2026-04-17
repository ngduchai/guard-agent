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
struct CSE<CombinedRLBdynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>, momenta::Tuple<momenta::VelocityBoundaryDensity<1, -1>, momenta::FixedVelocityMomentumGeneric, momenta::RegularizedBoundaryStress<1, -1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x22 = parameters.template get<descriptors::OMEGA>();
auto x21 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(2);
auto x19 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x20 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x23 = x22 + V{-1};
auto x24 = x20 + V{-1};
auto x25 = -1/x24;
auto x26 = V{2}*cell[14] + V{2}*cell[4] + V{2}*cell[8] + V{2}*cell[9];
auto x27 = cell[0] + cell[10] + cell[12] + cell[15] + cell[16] + cell[1] + V{2}*cell[2] + cell[3] + cell[6] + cell[7] + x26 + V{1};
auto x28 = x25*x27;
auto x29 = V{0.0277777777777778}*x28;
auto x30 = ((x19)*(x19));
auto x31 = V{3}*x19;
auto x32 = ((x21)*(x21));
auto x33 = V{1.5}*x32;
auto x34 = -x33;
auto x35 = ((x20)*(x20));
auto x36 = V{1.5}*x35;
auto x37 = V{1} - x36;
auto x38 = x34 + x37;
auto x39 = x31 + x38;
auto x40 = V{3}*x30 + x39;
auto x41 = V{3}*x21;
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
auto x52 = ((x19 + x21)*(x19 + x21));
auto x53 = x39 + x44 + V{4.5}*x52;
auto x54 = -x31;
auto x55 = -x21;
auto x56 = x19 + x55;
auto x57 = -V{4.5}*((x56)*(x56));
auto x58 = x42 + x46;
auto x59 = x41 + x58;
auto x60 = x54 + x57 + x59;
auto x61 = -x60;
auto x62 = -x41 + x58;
auto x63 = x31 + x62;
auto x64 = x63 - V{4.5}*((x56)*(x56));
auto x65 = -x64;
auto x66 = x31 - V{4.5}*x52 + x59;
auto x67 = -x66;
auto x68 = V{0.0555555555555556}*x28;
auto x69 = V{3}*x20;
auto x70 = x33 - V{3}*x35 + x49 + x69;
auto x71 = -x70;
auto x72 = x19 - x20;
auto x73 = x58 + x69;
auto x74 = x54 + x73 - V{4.5}*((x72)*(x72));
auto x75 = -x74;
auto x76 = x20 + x55;
auto x77 = x62 + x69;
auto x78 = x77 - V{4.5}*((x76)*(x76));
auto x79 = -x78;
auto x80 = ((x19 + x20)*(x19 + x20));
auto x81 = x31 + x73 - V{4.5}*x80;
auto x82 = -x81;
auto x83 = ((x20 + x21)*(x20 + x21));
auto x84 = x59 + x69 - V{4.5}*x83;
auto x85 = -x84;
auto x86 = -x58;
auto x87 = V{0.333333333333333}*x28*x86;
auto x88 = V{0.0555555555555555}*x28;
auto x89 = V{0.0555555555555555}*x28;
auto x90 = V{0.0277777777777778}*x28;
auto x91 = V{1.66533453693773e-16}*cell[10] + V{9.71445146547012e-17}*cell[12] + V{6.66133814775094e-16}*cell[14] + V{4.71844785465692e-16}*cell[15] + V{5.27355936696949e-16}*cell[16] + V{1.66533453693773e-16}*cell[1] + V{4.44089209850063e-16}*cell[2] + V{9.71445146547012e-17}*cell[3] + V{2.22044604925031e-16}*cell[4] + V{4.71844785465692e-16}*cell[6] + V{5.27355936696949e-16}*cell[7] + V{4.44089209850063e-16}*cell[8] + V{4.44089209850063e-16}*cell[9] + V{2.22044604925031e-16};
auto x92 = V{0.0555555555555555}*x28*x48 + V{0.0277777777777778}*x28*x65 + V{0.0277777777777778}*x28*x67 + V{0.111111111111111}*x28*x71 + x40*x68 + x45*x68 + x51*x88 + x53*x90 + x61*x90 + x75*x89 + x79*x88 + x82*x89 + x85*x88 + x87 + x91;
auto x93 = V{0.166666666666667}*cell[14];
auto x94 = V{0.166666666666667}*cell[4];
auto x95 = V{0.0833333333333333}*cell[12];
auto x96 = V{0.0833333333333333}*cell[3];
auto x97 = V{0.333333333333333}*cell[8];
auto x98 = V{0.333333333333333}*cell[9];
auto x99 = V{1} / (x24);
auto x100 = x27*x99;
auto x101 = V{0.00462962962962963}*x100;
auto x102 = V{0.00925925925925926}*x100;
auto x103 = V{0.0462962962962963}*x100;
auto x104 = V{0.00925925925925926}*x100;
auto x105 = x101*x45;
auto x106 = V{0.00462962962962963}*x100;
auto x107 = x106*x81;
auto x108 = x106*x74;
auto x109 = V{0.166666666666667}*cell[2];
auto x110 = V{0.00231481481481482}*x100;
auto x111 = x110*x66;
auto x112 = x110*x64;
auto x113 = x110*x60;
auto x114 = V{0.0833333333333334}*cell[15] + V{0.0833333333333334}*cell[16] + V{0.0833333333333334}*cell[6] + V{0.0833333333333334}*cell[7] + x102*x70 - x109 + x110*x53 - x111 - x112 - x113 + V{-0.0555555555555555};
auto x115 = V{0.0555555555555556}*x22;
auto x116 = -x93;
auto x117 = -x94;
auto x118 = x105 + x107 + x108 + x116 + x117 - V{0.00462962962962963}*x27*x50*x99 + x95 + x96 + V{0.0555555555555555};
auto x119 = V{0.0833333333333333}*cell[10];
auto x120 = V{0.0833333333333333}*cell[1];
auto x121 = V{0.166666666666667}*cell[8];
auto x122 = -x121;
auto x123 = V{0.166666666666667}*cell[9];
auto x124 = -x123;
auto x125 = x101*x40;
auto x126 = x106*x84;
auto x127 = x106*x78;
auto x128 = x119 + x120 + x122 + x124 + x125 + x126 + x127 - V{0.00462962962962963}*x27*x47*x99;
auto x129 = V{0.166666666666667}*cell[15] + V{0.166666666666667}*cell[16] - V{0.333333333333333}*cell[2] + V{0.166666666666667}*cell[6] + V{0.166666666666667}*cell[7];
auto x130 = V{0.333333333333333}*cell[14];
auto x131 = V{0.333333333333333}*cell[4];
auto x132 = V{0.00462962962962963}*x100;
auto x133 = V{0.00231481481481481}*x100;
auto x134 = V{0.00462962962962963}*x100;
auto x135 = V{0.0833333333333333}*cell[10] + V{0.0833333333333333}*cell[1] + V{0.0833333333333334}*cell[8] + V{0.0833333333333334}*cell[9] - x110*x78 - x110*x84 + x134*x40 - x134*x47 + V{0.0138888888888889};
auto x136 = V{0.00115740740740741}*x100;
auto x137 = V{0.0416666666666667}*cell[15] + V{0.0416666666666667}*cell[16] + V{0.166666666666667}*cell[2] + V{0.0416666666666667}*cell[6] + V{0.0416666666666667}*cell[7] - x104*x70 + x136*x53 - x136*x60 - x136*x64 - x136*x66;
auto x138 = -V{0.0416666666666667}*cell[12] - V{0.0416666666666667}*cell[3] - x133*x45 + x133*x50 + x135 + x137;
auto x139 = -V{0.166666666666667}*cell[14] + V{0.833333333333333}*cell[4] + x132*x74 + x138;
auto x140 = V{0.0277777777777778}*x22;
auto x141 = V{0.0277777777777778}*x100;
auto x142 = -x69;
auto x143 = x142 + x31 + x58 - V{4.5}*((x72)*(x72));
auto x144 = V{0.0231481481481481}*x100;
auto x145 = V{0.833333333333333}*cell[14] - V{0.166666666666667}*cell[4] + x132*x81 + x138;
auto x146 = V{0.0115740740740741}*x100;
auto x147 = V{0.0162037037037037}*x100;
auto x148 = V{0.00231481481481481}*x100;
auto x149 = V{0.0833333333333333}*cell[12] + V{0.0833333333333334}*cell[14] + V{0.0833333333333333}*cell[3] + V{0.0833333333333334}*cell[4] - x110*x74 - x110*x81 + x134*x45 - x134*x50;
auto x150 = -V{0.0833333333333333}*cell[2] + x101*x70 + x135 + x149;
auto x151 = V{0.416666666666667}*cell[15] - V{0.0833333333333333}*cell[16] + V{0.416666666666667}*cell[6] - V{0.0833333333333333}*cell[7] + x148*x60 + x148*x64 + x150;
auto x152 = -V{0.0833333333333333}*cell[15] + V{0.416666666666667}*cell[16] - V{0.0833333333333333}*cell[6] + V{0.416666666666667}*cell[7] - x148*x53 + x148*x66 + x150;
auto x153 = -V{0.0416666666666667}*cell[10] - V{0.0416666666666667}*cell[1] - x133*x40 + x133*x47 + x137 + x149 + V{0.0138888888888889};
auto x154 = V{0.833333333333333}*cell[8] - V{0.166666666666667}*cell[9] + x132*x78 + x153;
auto x155 = -V{0.166666666666667}*cell[8] + V{0.833333333333333}*cell[9] + x132*x84 + x153;
auto x156 = -V{0.0833333333333334}*cell[15] - V{0.0833333333333334}*cell[16] - V{0.0833333333333334}*cell[6] - V{0.0833333333333334}*cell[7] + x109 + x111 + x112 + x113 - V{0.00231481481481482}*x27*x53*x99 - V{0.00925925925925926}*x27*x70*x99;
auto x157 = V{0.00462962962962963}*x28;
auto x158 = V{0.00462962962962963}*x28;
auto x159 = x43 + x69;
auto x160 = x159 + x34 + V{3}*x35 + V{1};
auto x161 = x159 + x39 + V{4.5}*x80;
auto x162 = x38 + x44 + x69 + V{4.5}*x83;
auto x163 = -V{4.5}*((x76)*(x76));
auto x164 = x142 + x163 + x59;
auto x165 = V{0.0555555555555555}*x100;
auto x166 = V{0.0555555555555555}*x100;
auto x167 = V{0.0277777777777778}*x100;
auto x168 = V{0.0555555555555556}*x100;
auto x0 = -V{0.333333333333333}*x22*(-x25*x86*x92 + V{1}) + x23*(V{0.5}*cell[10] + V{0.5}*cell[12] + V{1}*cell[15] + V{1}*cell[16] + V{0.5}*cell[1] + V{1}*cell[2] + V{0.5}*cell[3] + V{1}*cell[6] + V{1}*cell[7] + x26 - x29*x40 - x29*x45 - x29*x48 - x29*x51 - x29*x53 - x29*x61 - x29*x65 - x29*x67 - x68*x71 - x68*x75 - x68*x79 - x68*x82 - x68*x85 - x87 + V{0.833333333333333});
auto x1 = -x115*(-x25*x48*x92 + V{1}) - x23*(V{0.166666666666667}*cell[10] + V{0.166666666666667}*cell[1] + x101*x50 + x102*x78 + x102*x84 + x103*x47 + x104*x40 - x105 - x107 - x108 + x114 + x93 + x94 - x95 - x96 - x97 - x98);
auto x2 = -x115*(-x25*x71*x92 + V{1}) - x23*(-x101*x53 - x118 - x128 - x129 + V{0.00462962962962963}*x27*x60*x99 + V{0.00462962962962963}*x27*x64*x99 + V{0.00462962962962963}*x27*x66*x99 + V{0.037037037037037}*x27*x70*x99);
auto x3 = -x115*(-x25*x51*x92 + V{1}) - x23*(V{0.166666666666667}*cell[12] + V{0.166666666666667}*cell[3] + x101*x47 + x102*x74 + x102*x81 + x103*x50 + x104*x45 + x114 - x119 - x120 + x121 + x123 - x125 - x126 - x127 - x130 - x131);
auto x4 = -x140*(-x25*x82*x92 + V{1}) - x23*(x101*x81 + x139);
auto x5 = -x140*(x143*x25*x92 + V{1}) - x23*(x141*x143 - x144*x74 + x145);
auto x6 = -x140*(-x25*x67*x92 + V{1}) - x23*(x146*x53 + x147*x66 + x151);
auto x7 = -x140*(-x25*x65*x92 + V{1}) - x23*(-x146*x60 + x147*x64 + x152);
auto x8 = -x140*(-x25*x85*x92 + V{1}) - x23*(x101*x84 + x154);
auto x9 = -x140*(-x25*x79*x92 + V{1}) - x23*(x101*x78 + x155);
auto x10 = -x115*(-x25*x40*x92 + V{1}) - x23*(V{0.166666666666667}*cell[10] + V{0.166666666666667}*cell[1] - x103*x40 - x104*x47 - x118 - x156 + V{0.00925925925925926}*x27*x78*x99 + V{0.00925925925925926}*x27*x84*x99 - x97 - x98);
auto x11 = -x115*(-x160*x25*x92 + V{1}) + x23*(x116 + x117 + x119 + x120 + x122 + x124 + x129 + x157*x75 + x157*x79 + x157*x82 + x157*x85 - x158*x40 - x158*x45 - x158*x48 - x158*x51 - x158*x53 - x158*x61 - x158*x65 - x158*x67 - x160*x68 + V{0.0185185185185185}*x28*x71 + x95 + x96 + V{0.0555555555555555});
auto x12 = -x115*(-x25*x45*x92 + V{1}) - x23*(V{0.166666666666667}*cell[12] + V{0.166666666666667}*cell[3] - x103*x45 - x104*x50 - x128 - x130 - x131 - x156 + V{0.00925925925925926}*x27*x74*x99 + V{0.00925925925925926}*x27*x81*x99 + V{-0.0555555555555555});
auto x13 = -x140*(-x161*x25*x92 + V{1}) - x23*(x139 - x141*x161 - x144*x81);
auto x14 = -x140*(-x25*x75*x92 + V{1}) - x23*(x101*x74 + x145);
auto x15 = -x140*(-x25*x53*x92 + V{1}) - x23*(-x146*x66 - x147*x53 + x151);
auto x16 = -x140*(-x25*x61*x92 + V{1}) - x23*(-x146*x64 + x147*x60 + x152);
auto x17 = -x140*(-x162*x25*x92 + V{1}) - x23*(-x141*x162 - x144*x84 + x154);
auto x18 = -x140*(x164*x25*x92 + V{1}) - x23*(x141*x164 - x144*x78 + x155);
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
return { -V{1}*x99*(V{0.0555555555555555}*x100*x47 + V{0.333333333333333}*x100*x58 + V{0.0277777777777778}*x100*x66 + V{0.111111111111111}*x100*x70 + V{0.0277777777777778}*x100*(x57 + x63) + x165*x50 + x165*x84 + x165*(x163 + x77) + x166*x74 + x166*x81 - x167*x53 + x167*x60 - x168*x40 - x168*x45 + x91), x30 + x32 + x35 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
