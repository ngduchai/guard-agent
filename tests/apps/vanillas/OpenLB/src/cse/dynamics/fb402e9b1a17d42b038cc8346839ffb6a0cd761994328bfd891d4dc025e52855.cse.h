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
struct CSE<CombinedRLBdynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>, momenta::Tuple<momenta::VelocityBoundaryDensity<1, 1>, momenta::FixedVelocityMomentumGeneric, momenta::RegularizedBoundaryStress<1, 1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x22 = parameters.template get<descriptors::OMEGA>();
auto x20 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x21 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(2);
auto x23 = x22 + V{-1};
auto x24 = V{1} / (x20 + V{1});
auto x25 = V{2}*cell[13] + V{2}*cell[17] + V{2}*cell[18] + V{2}*cell[5];
auto x26 = cell[0] + cell[10] + V{2}*cell[11] + cell[12] + cell[15] + cell[16] + cell[1] + cell[3] + cell[6] + cell[7] + x25 + V{1};
auto x27 = x24*x26;
auto x28 = V{0.0277777777777778}*x27;
auto x29 = ((x19)*(x19));
auto x30 = V{3}*x19;
auto x31 = ((x21)*(x21));
auto x32 = V{1.5}*x31;
auto x33 = -x32;
auto x34 = ((x20)*(x20));
auto x35 = V{1.5}*x34;
auto x36 = V{1} - x35;
auto x37 = x33 + x36;
auto x38 = x30 + x37;
auto x39 = V{3}*x29 + x38;
auto x40 = V{3}*x21;
auto x41 = V{1.5}*x29;
auto x42 = -x41;
auto x43 = x40 + x42;
auto x44 = V{3}*x31 + x36 + x43;
auto x45 = x32 + x35 + V{-1};
auto x46 = -V{3}*x29 + x30 + x45;
auto x47 = -x46;
auto x48 = x41 + V{-1};
auto x49 = -V{3}*x31 + x35 + x40 + x48;
auto x50 = -x49;
auto x51 = ((x19 + x21)*(x19 + x21));
auto x52 = x38 + x43 + V{4.5}*x51;
auto x53 = -x30;
auto x54 = -x21;
auto x55 = x19 + x54;
auto x56 = -V{4.5}*((x55)*(x55));
auto x57 = x41 + x45;
auto x58 = x40 + x57;
auto x59 = x53 + x56 + x58;
auto x60 = -x59;
auto x61 = -x40;
auto x62 = x30 + x57;
auto x63 = x61 + x62;
auto x64 = x63 - V{4.5}*((x55)*(x55));
auto x65 = -x64;
auto x66 = x30 - V{4.5}*x51 + x58;
auto x67 = -x66;
auto x68 = V{0.0555555555555556}*x27;
auto x69 = V{3}*x20;
auto x70 = x42 + x69;
auto x71 = x33 + V{3}*x34 + x70 + V{1};
auto x72 = V{4.5}*((x19 + x20)*(x19 + x20));
auto x73 = x38 + x70 + x72;
auto x74 = V{4.5}*((x20 + x21)*(x20 + x21));
auto x75 = x37 + x43 + x69 + x74;
auto x76 = x19 - x20;
auto x77 = -x69;
auto x78 = x62 + x77;
auto x79 = x78 - V{4.5}*((x76)*(x76));
auto x80 = -x79;
auto x81 = x20 + x54;
auto x82 = x58 + x77 - V{4.5}*((x81)*(x81));
auto x83 = -x82;
auto x84 = V{0.333333333333333}*x27;
auto x85 = -x57;
auto x86 = x84*x85;
auto x87 = V{0.0277777777777778}*x27;
auto x88 = V{0.0555555555555555}*x27;
auto x89 = V{0.0555555555555555}*x27;
auto x90 = V{0.0277777777777778}*x27;
auto x91 = V{0.0555555555555555}*x27;
auto x92 = V{0.0277777777777778}*x27;
auto x93 = V{1.66533453693773e-16}*cell[10] + V{4.44089209850063e-16}*cell[11] + V{1.11022302462516e-16}*cell[12] + V{6.66133814775094e-16}*cell[13] + V{4.71844785465692e-16}*cell[15] + V{5.27355936696949e-16}*cell[16] + V{8.88178419700125e-16}*cell[17] + V{4.44089209850063e-16}*cell[18] + V{1.66533453693773e-16}*cell[1] + V{1.11022302462516e-16}*cell[3] + V{6.66133814775094e-16}*cell[5] + V{4.71844785465692e-16}*cell[6] + V{5.27355936696949e-16}*cell[7] + V{0.111111111111111}*x27*x71 + x39*x68 + x44*x68 + x52*x92 + x73*x91 + x75*x88 + V{2.22044604925031e-16};
auto x94 = x47*x89 + x50*x88 + x60*x92 + x65*x87 + x67*x90 + x80*x91 + x83*x88 + x86 + x93;
auto x95 = V{0.0462962962962963}*x27;
auto x96 = V{0.00925925925925926}*x27;
auto x97 = V{0.166666666666667}*cell[13];
auto x98 = V{0.166666666666667}*cell[5];
auto x99 = V{0.0833333333333333}*cell[12];
auto x100 = V{0.0833333333333333}*cell[3];
auto x101 = V{0.00462962962962963}*x27;
auto x102 = x101*x44;
auto x103 = V{0.00925925925925926}*x27;
auto x104 = V{0.00462962962962963}*x27;
auto x105 = x101*x49;
auto x106 = x104*x73;
auto x107 = V{0.00231481481481482}*x27;
auto x108 = -V{0.166666666666667}*cell[11] + V{0.0833333333333334}*cell[15] + V{0.0833333333333334}*cell[16] + V{0.0833333333333334}*cell[6] + V{0.0833333333333334}*cell[7] + x103*x71 - x107*x52 + x107*x59 + x107*x64 + x107*x66 + V{-0.0555555555555555};
auto x109 = V{0.166666666666667}*cell[10] - V{0.333333333333333}*cell[17] - V{0.333333333333333}*cell[18] + V{0.166666666666667}*cell[1] - x100 + x102 + x103*x75 - x103*x82 + x104*x79 - x105 - x106 + x108 + x97 + x98 - x99;
auto x110 = V{0.0555555555555556}*x22;
auto x111 = -x32 + V{3}*x34 - x48 - x69;
auto x112 = V{0.0833333333333333}*cell[10];
auto x113 = V{0.0833333333333333}*cell[1];
auto x114 = V{0.166666666666667}*cell[17];
auto x115 = V{0.166666666666667}*cell[18];
auto x116 = x104*x75;
auto x117 = x101*x39;
auto x118 = -V{0.333333333333333}*cell[11] + V{0.166666666666667}*cell[15] + V{0.166666666666667}*cell[16] + V{0.166666666666667}*cell[6] + V{0.166666666666667}*cell[7] + x100 - x101*x52 - x102 + x106 + x112 + x113 - x114 - x115 + x116 - x117 - x97 - x98 + x99 + V{0.0555555555555555};
auto x119 = x101*x46;
auto x120 = V{0.166666666666667}*cell[12] - V{0.333333333333333}*cell[13] + V{0.166666666666667}*cell[3] - V{0.333333333333333}*cell[5] + x103*x73 - x103*x79 + x104*x82 + x108 - x112 - x113 + x114 + x115 - x116 + x117 - x119;
auto x121 = x62 + x69 - x72;
auto x122 = V{0.0231481481481481}*x27;
auto x123 = V{0.00462962962962963}*x27;
auto x124 = V{0.00231481481481481}*x27;
auto x125 = V{0.00462962962962963}*x27;
auto x126 = V{0.0833333333333333}*cell[10] + V{0.0833333333333334}*cell[17] + V{0.0833333333333334}*cell[18] + V{0.0833333333333333}*cell[1] - x107*x75 + x107*x82 - x125*x39 + x125*x46 + V{0.0138888888888889};
auto x127 = V{0.00115740740740741}*x27;
auto x128 = V{0.166666666666667}*cell[11] + V{0.0416666666666667}*cell[15] + V{0.0416666666666667}*cell[16] + V{0.0416666666666667}*cell[6] + V{0.0416666666666667}*cell[7] - x127*x52 + x127*x59 + x127*x64 + x127*x66 - x71*x96;
auto x129 = -V{0.0416666666666667}*cell[12] - V{0.0416666666666667}*cell[3] + x124*x44 - x124*x49 + x126 + x128;
auto x130 = V{0.833333333333333}*cell[13] - V{0.166666666666667}*cell[5] - x123*x79 + x129;
auto x131 = V{0.0277777777777778}*x22;
auto x132 = -V{0.166666666666667}*cell[13] + V{0.833333333333333}*cell[5] + x123*x73 + x129;
auto x133 = V{0.0115740740740741}*x27;
auto x134 = V{0.0162037037037037}*x27;
auto x135 = V{0.00231481481481481}*x27;
auto x136 = V{0.0833333333333333}*cell[12] + V{0.0833333333333334}*cell[13] + V{0.0833333333333333}*cell[3] + V{0.0833333333333334}*cell[5] - x107*x73 + x107*x79 - x125*x44 + x125*x49;
auto x137 = -V{0.0833333333333333}*cell[11] + x101*x71 + x126 + x136;
auto x138 = V{0.416666666666667}*cell[15] - V{0.0833333333333333}*cell[16] + V{0.416666666666667}*cell[6] - V{0.0833333333333333}*cell[7] - x135*x59 - x135*x64 + x137;
auto x139 = -V{0.0833333333333333}*cell[15] + V{0.416666666666667}*cell[16] - V{0.0833333333333333}*cell[6] + V{0.416666666666667}*cell[7] + x135*x52 - x135*x66 + x137;
auto x140 = x58 + x69 - x74;
auto x141 = -V{0.0416666666666667}*cell[10] - V{0.0416666666666667}*cell[1] + x124*x39 - x124*x46 + x128 + x136 + V{0.0138888888888889};
auto x142 = V{0.833333333333333}*cell[17] - V{0.166666666666667}*cell[18] - x123*x82 + x141;
auto x143 = x57 + x69;
auto x144 = x143 + x61 - V{4.5}*((x81)*(x81));
auto x145 = -V{0.166666666666667}*cell[17] + V{0.833333333333333}*cell[18] + x123*x75 + x141;
auto x146 = -V{4.5}*((x76)*(x76));
auto x147 = x143 + x146 + x53;
auto x0 = -V{0.333333333333333}*x22*(-x24*x85*x94 + V{1}) + x23*(V{0.5}*cell[10] + V{1}*cell[11] + V{0.5}*cell[12] + V{1}*cell[15] + V{1}*cell[16] + V{0.5}*cell[1] + V{0.5}*cell[3] + V{1}*cell[6] + V{1}*cell[7] + x25 - x28*x39 - x28*x44 - x28*x47 - x28*x50 - x28*x52 - x28*x60 - x28*x65 - x28*x67 - x68*x71 - x68*x73 - x68*x75 - x68*x80 - x68*x83 - x86 + V{0.833333333333333});
auto x1 = -x110*(-x24*x47*x94 + V{1}) - x23*(x109 - x39*x96 - x46*x95);
auto x2 = -x110*(-x111*x24*x94 + V{1}) + x23*(-x101*x47 - x101*x50 - x101*x60 - x101*x65 - x101*x67 + x104*x80 + x104*x83 - x111*x68 + x118 + V{0.0185185185185185}*x27*x71);
auto x3 = -x110*(-x24*x50*x94 + V{1}) - x23*(x120 - x44*x96 - x49*x95);
auto x4 = -x131*(x121*x24*x94 + V{1}) - x23*(-x121*x28 - x122*x73 + x130);
auto x5 = -x131*(-x24*x80*x94 + V{1}) - x23*(-x101*x79 + x132);
auto x6 = -x131*(-x24*x67*x94 + V{1}) - x23*(-x133*x52 - x134*x66 + x138);
auto x7 = -x131*(-x24*x65*x94 + V{1}) - x23*(x133*x59 - x134*x64 + x139);
auto x8 = -x131*(x140*x24*x94 + V{1}) - x23*(-x122*x75 - x140*x28 + x142);
auto x9 = -x131*(x144*x24*x94 + V{1}) - x23*(x122*x82 - x144*x28 + x145);
auto x10 = -x110*(-x24*x39*x94 + V{1}) - x23*(x109 + x39*x95 + x46*x96);
auto x11 = -x110*(-x24*x71*x94 + V{1}) - x23*(-x101*x59 - x101*x64 - x101*x66 - x105 - x118 - x119 + V{0.037037037037037}*x24*x26*x71 + V{0.00462962962962963}*x24*x26*x79 + V{0.00462962962962963}*x24*x26*x82);
auto x12 = -x110*(-x24*x44*x94 + V{1}) - x23*(x120 + x44*x95 + x49*x96);
auto x13 = -x131*(-x24*x73*x94 + V{1}) - x23*(x101*x73 + x130);
auto x14 = -x131*(x147*x24*x94 + V{1}) - x23*(x122*x79 + x132 - x147*x28);
auto x15 = -x131*(-x24*x52*x94 + V{1}) - x23*(x133*x66 + x134*x52 + x138);
auto x16 = -x131*(-x24*x60*x94 + V{1}) - x23*(x133*x64 - x134*x59 + x139);
auto x17 = -x131*(-x24*x75*x94 + V{1}) - x23*(x101*x75 + x142);
auto x18 = -x131*(-x24*x83*x94 + V{1}) - x23*(-x101*x82 + x145);
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
return { V{1}*x24*(-x46*x89 - x49*x88 - x57*x84 - x59*x92 - x66*x90 - x82*x88 - x87*(x56 + x63) - x91*(x146 + x78) + x93), x29 + x31 + x34 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
