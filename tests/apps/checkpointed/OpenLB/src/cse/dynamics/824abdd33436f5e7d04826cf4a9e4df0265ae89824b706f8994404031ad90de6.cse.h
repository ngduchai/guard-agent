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
struct CSE<CombinedRLBdynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::SaveVelocity<collision::BGK>, dynamics::DefaultCombination>, momenta::Tuple<momenta::VelocityBoundaryDensity<0, -1>, momenta::FixedVelocityMomentumGeneric, momenta::RegularizedBoundaryStress<0, -1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x23 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x25 = parameters.template get<descriptors::OMEGA>();
auto x24 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(2);
auto x19 = x25 + V{-1};
auto x20 = x22 + V{-1};
auto x21 = -1/x20;
auto x26 = V{2}*cell[4] + V{2}*cell[5] + V{2}*cell[6] + V{2}*cell[7];
auto x27 = cell[0] + cell[11] + cell[12] + cell[17] + cell[18] + V{2}*cell[1] + cell[2] + cell[3] + cell[8] + cell[9] + x26 + V{1};
auto x28 = x21*x27;
auto x29 = V{0.0277777777777778}*x28;
auto x30 = ((x23)*(x23));
auto x31 = V{3}*x23;
auto x32 = ((x24)*(x24));
auto x33 = V{1.5}*x32;
auto x34 = -x33;
auto x35 = ((x22)*(x22));
auto x36 = V{1.5}*x35;
auto x37 = V{1} - x36;
auto x38 = x34 + x37;
auto x39 = x31 + x38;
auto x40 = V{3}*x30 + x39;
auto x41 = V{3}*x24;
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
auto x52 = ((x23 + x24)*(x23 + x24));
auto x53 = x39 + x44 + V{4.5}*x52;
auto x54 = -x31;
auto x55 = -x24;
auto x56 = x23 + x55;
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
auto x69 = V{3}*x22;
auto x70 = x33 - V{3}*x35 + x49 + x69;
auto x71 = -x70;
auto x72 = x22 - x23;
auto x73 = x58 + x69;
auto x74 = x54 + x73;
auto x75 = x74 - V{4.5}*((x72)*(x72));
auto x76 = -x75;
auto x77 = x22 + x55;
auto x78 = x62 + x69;
auto x79 = x78 - V{4.5}*((x77)*(x77));
auto x80 = -x79;
auto x81 = ((x22 + x23)*(x22 + x23));
auto x82 = x31 + x73 - V{4.5}*x81;
auto x83 = -x82;
auto x84 = ((x22 + x24)*(x22 + x24));
auto x85 = x59 + x69 - V{4.5}*x84;
auto x86 = -x85;
auto x87 = -x58;
auto x88 = V{0.333333333333333}*x28*x87;
auto x89 = V{0.0555555555555555}*x28;
auto x90 = V{0.0555555555555555}*x28;
auto x91 = V{0.0277777777777778}*x28;
auto x92 = V{1.66533453693773e-16}*cell[11] + V{1.11022302462516e-16}*cell[12] + V{4.71844785465692e-16}*cell[17] + V{5.27355936696949e-16}*cell[18] + V{4.44089209850063e-16}*cell[1] + V{1.66533453693773e-16}*cell[2] + V{1.11022302462516e-16}*cell[3] + V{6.66133814775094e-16}*cell[4] + V{6.66133814775094e-16}*cell[5] + V{8.88178419700125e-16}*cell[6] + V{4.44089209850063e-16}*cell[7] + V{4.71844785465692e-16}*cell[8] + V{5.27355936696949e-16}*cell[9] + V{2.22044604925031e-16};
auto x93 = V{0.0555555555555555}*x28*x48 + V{0.0277777777777778}*x28*x65 + V{0.0277777777777778}*x28*x67 + V{0.111111111111111}*x28*x71 + x40*x68 + x45*x68 + x51*x89 + x53*x91 + x61*x91 + x76*x90 + x80*x89 + x83*x90 + x86*x89 + x88 + x92;
auto x94 = V{1} / (x20);
auto x95 = x27*x94;
auto x96 = V{0.00462962962962963}*x95;
auto x97 = V{0.0833333333333333}*cell[12];
auto x98 = V{0.0833333333333333}*cell[3];
auto x99 = V{0.166666666666667}*cell[4];
auto x100 = -x99;
auto x101 = V{0.166666666666667}*cell[5];
auto x102 = -x101;
auto x103 = x45*x96;
auto x104 = V{0.00462962962962963}*x95;
auto x105 = x104*x82;
auto x106 = x104*x75;
auto x107 = x100 + x102 + x103 + x105 + x106 - V{0.00462962962962963}*x27*x50*x94 + x97 + x98 + V{0.0555555555555555};
auto x108 = V{0.0833333333333333}*cell[11];
auto x109 = V{0.0833333333333333}*cell[2];
auto x110 = V{0.166666666666667}*cell[6];
auto x111 = -x110;
auto x112 = V{0.166666666666667}*cell[7];
auto x113 = -x112;
auto x114 = x40*x96;
auto x115 = x104*x85;
auto x116 = x104*x79;
auto x117 = x108 + x109 + x111 + x113 + x114 + x115 + x116 - V{0.00462962962962963}*x27*x47*x94;
auto x118 = V{0.166666666666667}*cell[17] + V{0.166666666666667}*cell[18] - V{0.333333333333333}*cell[1] + V{0.166666666666667}*cell[8] + V{0.166666666666667}*cell[9];
auto x119 = V{0.0555555555555556}*x25;
auto x120 = V{0.333333333333333}*cell[6];
auto x121 = V{0.333333333333333}*cell[7];
auto x122 = V{0.00925925925925926}*x95;
auto x123 = V{0.0462962962962963}*x95;
auto x124 = V{0.00925925925925926}*x95;
auto x125 = V{0.166666666666667}*cell[1];
auto x126 = V{0.00231481481481482}*x95;
auto x127 = x126*x66;
auto x128 = x126*x64;
auto x129 = x126*x60;
auto x130 = V{0.0833333333333334}*cell[17] + V{0.0833333333333334}*cell[18] + V{0.0833333333333334}*cell[8] + V{0.0833333333333334}*cell[9] + x122*x70 - x125 + x126*x53 - x127 - x128 - x129 + V{-0.0555555555555555};
auto x131 = V{0.333333333333333}*cell[4];
auto x132 = V{0.333333333333333}*cell[5];
auto x133 = V{0.00462962962962963}*x95;
auto x134 = V{0.00231481481481481}*x95;
auto x135 = V{0.00462962962962963}*x95;
auto x136 = V{0.0833333333333333}*cell[11] + V{0.0833333333333333}*cell[2] + V{0.0833333333333334}*cell[6] + V{0.0833333333333334}*cell[7] - x126*x79 - x126*x85 + x135*x40 - x135*x47 + V{0.0138888888888889};
auto x137 = V{0.00115740740740741}*x95;
auto x138 = V{0.0416666666666667}*cell[17] + V{0.0416666666666667}*cell[18] + V{0.166666666666667}*cell[1] + V{0.0416666666666667}*cell[8] + V{0.0416666666666667}*cell[9] - x124*x70 + x137*x53 - x137*x60 - x137*x64 - x137*x66;
auto x139 = -V{0.0416666666666667}*cell[12] - V{0.0416666666666667}*cell[3] - x134*x45 + x134*x50 + x136 + x138;
auto x140 = V{0.833333333333333}*cell[4] - V{0.166666666666667}*cell[5] + x133*x75 + x139;
auto x141 = V{0.0277777777777778}*x25;
auto x142 = -V{0.166666666666667}*cell[4] + V{0.833333333333333}*cell[5] + x133*x82 + x139;
auto x143 = V{0.0833333333333333}*cell[12] + V{0.0833333333333333}*cell[3] + V{0.0833333333333334}*cell[4] + V{0.0833333333333334}*cell[5] - x126*x75 - x126*x82 + x135*x45 - x135*x50;
auto x144 = -V{0.0416666666666667}*cell[11] - V{0.0416666666666667}*cell[2] - x134*x40 + x134*x47 + x138 + x143 + V{0.0138888888888889};
auto x145 = V{0.833333333333333}*cell[6] - V{0.166666666666667}*cell[7] + x133*x79 + x144;
auto x146 = -V{0.166666666666667}*cell[6] + V{0.833333333333333}*cell[7] + x133*x85 + x144;
auto x147 = V{0.0115740740740741}*x95;
auto x148 = V{0.0162037037037037}*x95;
auto x149 = V{0.00231481481481481}*x95;
auto x150 = -V{0.0833333333333333}*cell[1] + x136 + x143 + x70*x96;
auto x151 = V{0.416666666666667}*cell[17] - V{0.0833333333333333}*cell[18] + V{0.416666666666667}*cell[8] - V{0.0833333333333333}*cell[9] + x149*x60 + x149*x64 + x150;
auto x152 = -V{0.0833333333333333}*cell[17] + V{0.416666666666667}*cell[18] - V{0.0833333333333333}*cell[8] + V{0.416666666666667}*cell[9] - x149*x53 + x149*x66 + x150;
auto x153 = V{0.00462962962962963}*x28;
auto x154 = V{0.00462962962962963}*x28;
auto x155 = x43 + x69;
auto x156 = x155 + x34 + V{3}*x35 + V{1};
auto x157 = -V{0.0833333333333334}*cell[17] - V{0.0833333333333334}*cell[18] - V{0.0833333333333334}*cell[8] - V{0.0833333333333334}*cell[9] + x125 + x127 + x128 + x129 - V{0.00231481481481482}*x27*x53*x94 - V{0.00925925925925926}*x27*x70*x94;
auto x158 = V{0.0277777777777778}*x95;
auto x159 = x155 + x39 + V{4.5}*x81;
auto x160 = V{0.0231481481481481}*x95;
auto x161 = -x69;
auto x162 = -V{4.5}*((x72)*(x72));
auto x163 = x161 + x162 + x31 + x58;
auto x164 = x38 + x44 + x69 + V{4.5}*x84;
auto x165 = -V{4.5}*((x77)*(x77));
auto x166 = x161 + x165 + x59;
auto x167 = V{0.0555555555555555}*x95;
auto x168 = V{0.0555555555555555}*x95;
auto x169 = V{0.0277777777777778}*x95;
auto x170 = V{0.0555555555555556}*x95;
auto x0 = x19*(V{0.5}*cell[11] + V{0.5}*cell[12] + V{1}*cell[17] + V{1}*cell[18] + V{1}*cell[1] + V{0.5}*cell[2] + V{0.5}*cell[3] + V{1}*cell[8] + V{1}*cell[9] + x26 - x29*x40 - x29*x45 - x29*x48 - x29*x51 - x29*x53 - x29*x61 - x29*x65 - x29*x67 - x68*x71 - x68*x76 - x68*x80 - x68*x83 - x68*x86 - x88 + V{0.833333333333333}) - V{0.333333333333333}*x25*(-x21*x87*x93 + V{1});
auto x1 = -x119*(-x21*x71*x93 + V{1}) - x19*(-x107 - x117 - x118 + V{0.00462962962962963}*x27*x60*x94 + V{0.00462962962962963}*x27*x64*x94 + V{0.00462962962962963}*x27*x66*x94 + V{0.037037037037037}*x27*x70*x94 - x53*x96);
auto x2 = -x119*(-x21*x48*x93 + V{1}) - x19*(V{0.166666666666667}*cell[11] + V{0.166666666666667}*cell[2] + x101 - x103 - x105 - x106 - x120 - x121 + x122*x79 + x122*x85 + x123*x47 + x124*x40 + x130 + x50*x96 - x97 - x98 + x99);
auto x3 = -x119*(-x21*x51*x93 + V{1}) - x19*(V{0.166666666666667}*cell[12] + V{0.166666666666667}*cell[3] - x108 - x109 + x110 + x112 - x114 - x115 - x116 + x122*x75 + x122*x82 + x123*x50 + x124*x45 + x130 - x131 - x132 + x47*x96);
auto x4 = -x141*(-x21*x83*x93 + V{1}) - x19*(x140 + x82*x96);
auto x5 = -x141*(-x21*x76*x93 + V{1}) - x19*(x142 + x75*x96);
auto x6 = -x141*(-x21*x86*x93 + V{1}) - x19*(x145 + x85*x96);
auto x7 = -x141*(-x21*x80*x93 + V{1}) - x19*(x146 + x79*x96);
auto x8 = -x141*(-x21*x67*x93 + V{1}) - x19*(x147*x53 + x148*x66 + x151);
auto x9 = -x141*(-x21*x65*x93 + V{1}) - x19*(-x147*x60 + x148*x64 + x152);
auto x10 = -x119*(-x156*x21*x93 + V{1}) + x19*(x100 + x102 + x108 + x109 + x111 + x113 + x118 + x153*x76 + x153*x80 + x153*x83 + x153*x86 - x154*x40 - x154*x45 - x154*x48 - x154*x51 - x154*x53 - x154*x61 - x154*x65 - x154*x67 - x156*x68 + V{0.0185185185185185}*x28*x71 + x97 + x98 + V{0.0555555555555555});
auto x11 = -x119*(-x21*x40*x93 + V{1}) - x19*(V{0.166666666666667}*cell[11] + V{0.166666666666667}*cell[2] - x107 - x120 - x121 - x123*x40 - x124*x47 - x157 + V{0.00925925925925926}*x27*x79*x94 + V{0.00925925925925926}*x27*x85*x94);
auto x12 = -x119*(-x21*x45*x93 + V{1}) - x19*(V{0.166666666666667}*cell[12] + V{0.166666666666667}*cell[3] - x117 - x123*x45 - x124*x50 - x131 - x132 - x157 + V{0.00925925925925926}*x27*x75*x94 + V{0.00925925925925926}*x27*x82*x94 + V{-0.0555555555555555});
auto x13 = -x141*(-x159*x21*x93 + V{1}) - x19*(x140 - x158*x159 - x160*x82);
auto x14 = -x141*(x163*x21*x93 + V{1}) - x19*(x142 + x158*x163 - x160*x75);
auto x15 = -x141*(-x164*x21*x93 + V{1}) - x19*(x145 - x158*x164 - x160*x85);
auto x16 = -x141*(x166*x21*x93 + V{1}) - x19*(x146 + x158*x166 - x160*x79);
auto x17 = -x141*(-x21*x53*x93 + V{1}) - x19*(-x147*x66 - x148*x53 + x151);
auto x18 = -x141*(-x21*x61*x93 + V{1}) - x19*(-x147*x64 + x148*x60 + x152);
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[0] = x22;
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[1] = x23;
cell.template getFieldPointer<olb::descriptors::VELOCITY>()[2] = x24;
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
return { -V{1}*x94*(x167*x50 + x167*x85 + x167*(x165 + x78) + x168*x82 + x168*(x162 + x74) - x169*x53 + x169*x60 - x170*x40 - x170*x45 + V{0.0555555555555555}*x47*x95 + V{0.333333333333333}*x58*x95 + V{0.0277777777777778}*x66*x95 + V{0.111111111111111}*x70*x95 + x92 + V{0.0277777777777778}*x95*(x57 + x63)), x30 + x32 + x35 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
