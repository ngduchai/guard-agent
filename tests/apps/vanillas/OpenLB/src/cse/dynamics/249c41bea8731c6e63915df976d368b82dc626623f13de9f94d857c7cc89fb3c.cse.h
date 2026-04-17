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
struct CSE<CombinedRLBdynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>, momenta::Tuple<momenta::VelocityBoundaryDensity<0, 1>, momenta::FixedVelocityMomentumGeneric, momenta::RegularizedBoundaryStress<0, 1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x22 = parameters.template get<descriptors::OMEGA>();
auto x19 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x21 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(2);
auto x20 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x23 = x22 + V{-1};
auto x24 = V{1} / (x19 + V{1});
auto x25 = V{2}*cell[13] + V{2}*cell[14] + V{2}*cell[15] + V{2}*cell[16];
auto x26 = cell[0] + V{2}*cell[10] + cell[11] + cell[12] + cell[17] + cell[18] + cell[2] + cell[3] + cell[8] + cell[9] + x25 + V{1};
auto x27 = x24*x26;
auto x28 = V{0.0277777777777778}*x27;
auto x29 = ((x20)*(x20));
auto x30 = V{3}*x20;
auto x31 = ((x21)*(x21));
auto x32 = V{1.5}*x31;
auto x33 = -x32;
auto x34 = ((x19)*(x19));
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
auto x51 = ((x20 + x21)*(x20 + x21));
auto x52 = x38 + x43 + V{4.5}*x51;
auto x53 = -x30;
auto x54 = -x21;
auto x55 = x20 + x54;
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
auto x69 = V{3}*x34;
auto x70 = V{3}*x19;
auto x71 = x42 + x70;
auto x72 = x33 + x69 + x71 + V{1};
auto x73 = V{4.5}*((x19 + x20)*(x19 + x20));
auto x74 = x38 + x71 + x73;
auto x75 = V{4.5}*((x19 + x21)*(x19 + x21));
auto x76 = x37 + x43 + x70 + x75;
auto x77 = -x70;
auto x78 = x19 - x20;
auto x79 = x62 + x77 - V{4.5}*((x78)*(x78));
auto x80 = -x79;
auto x81 = x19 + x54;
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
auto x93 = V{4.44089209850063e-16}*cell[10] + V{1.66533453693773e-16}*cell[11] + V{1.11022302462516e-16}*cell[12] + V{6.66133814775094e-16}*cell[13] + V{6.66133814775094e-16}*cell[14] + V{8.88178419700125e-16}*cell[15] + V{4.44089209850063e-16}*cell[16] + V{4.71844785465692e-16}*cell[17] + V{5.27355936696949e-16}*cell[18] + V{1.66533453693773e-16}*cell[2] + V{1.11022302462516e-16}*cell[3] + V{4.71844785465692e-16}*cell[8] + V{5.27355936696949e-16}*cell[9] + V{0.111111111111111}*x27*x72 + x39*x68 + x44*x68 + x52*x92 + x74*x91 + x76*x88 + V{2.22044604925031e-16};
auto x94 = x47*x89 + x50*x88 + x60*x92 + x65*x87 + x67*x90 + x80*x91 + x83*x88 + x86 + x93;
auto x95 = x32 + x48 - x69 + x70;
auto x96 = V{0.0833333333333333}*cell[11];
auto x97 = V{0.0833333333333333}*cell[12];
auto x98 = V{0.0833333333333333}*cell[2];
auto x99 = V{0.0833333333333333}*cell[3];
auto x100 = V{0.00462962962962963}*x27;
auto x101 = x100*x49;
auto x102 = x100*x46;
auto x103 = V{0.00462962962962963}*x27;
auto x104 = x103*x74;
auto x105 = x103*x76;
auto x106 = -V{0.333333333333333}*cell[10] - V{0.166666666666667}*cell[13] - V{0.166666666666667}*cell[14] - V{0.166666666666667}*cell[15] - V{0.166666666666667}*cell[16] + V{0.166666666666667}*cell[17] + V{0.166666666666667}*cell[18] + V{0.166666666666667}*cell[8] + V{0.166666666666667}*cell[9] + x100*x59 + x100*x64 + x100*x66 + x101 + x102 + x104 + x105 - V{0.00462962962962963}*x24*x26*x39 - V{0.00462962962962963}*x24*x26*x44 - V{0.00462962962962963}*x24*x26*x52 - V{0.00462962962962963}*x24*x26*x79 - V{0.00462962962962963}*x24*x26*x82 + x96 + x97 + x98 + x99 + V{0.0555555555555555};
auto x107 = V{0.0555555555555556}*x22;
auto x108 = V{0.0462962962962963}*x27;
auto x109 = V{0.00925925925925926}*x27;
auto x110 = V{0.00925925925925926}*x27;
auto x111 = V{0.00231481481481482}*x27;
auto x112 = -V{0.166666666666667}*cell[10] + V{0.0833333333333334}*cell[17] + V{0.0833333333333334}*cell[18] + V{0.0833333333333334}*cell[8] + V{0.0833333333333334}*cell[9] + x110*x72 - x111*x52 + x111*x59 + x111*x64 + x111*x66 + V{-0.0555555555555555};
auto x113 = V{0.166666666666667}*cell[11] + V{0.166666666666667}*cell[13] + V{0.166666666666667}*cell[14] - V{0.333333333333333}*cell[15] - V{0.333333333333333}*cell[16] + V{0.166666666666667}*cell[2] + x100*x44 - x101 + x103*x79 - x104 + x110*x76 - x110*x82 + x112 - x97 - x99;
auto x114 = V{0.166666666666667}*cell[12] - V{0.333333333333333}*cell[13] - V{0.333333333333333}*cell[14] + V{0.166666666666667}*cell[15] + V{0.166666666666667}*cell[16] + V{0.166666666666667}*cell[3] + x100*x39 - x102 + x103*x82 - x105 + x110*x74 - x110*x79 + x112 - x96 - x98;
auto x115 = x62 + x70 - x73;
auto x116 = V{0.0231481481481481}*x27;
auto x117 = V{0.00462962962962963}*x27;
auto x118 = V{0.00231481481481481}*x27;
auto x119 = V{0.00462962962962963}*x27;
auto x120 = V{0.0833333333333333}*cell[11] + V{0.0833333333333334}*cell[15] + V{0.0833333333333334}*cell[16] + V{0.0833333333333333}*cell[2] - x111*x76 + x111*x82 - x119*x39 + x119*x46 + V{0.0138888888888889};
auto x121 = V{0.00115740740740741}*x27;
auto x122 = V{0.166666666666667}*cell[10] + V{0.0416666666666667}*cell[17] + V{0.0416666666666667}*cell[18] + V{0.0416666666666667}*cell[8] + V{0.0416666666666667}*cell[9] - x109*x72 - x121*x52 + x121*x59 + x121*x64 + x121*x66;
auto x123 = -V{0.0416666666666667}*cell[12] - V{0.0416666666666667}*cell[3] + x118*x44 - x118*x49 + x120 + x122;
auto x124 = V{0.833333333333333}*cell[13] - V{0.166666666666667}*cell[14] - x117*x79 + x123;
auto x125 = V{0.0277777777777778}*x22;
auto x126 = x57 + x70;
auto x127 = x126 + x53 - V{4.5}*((x78)*(x78));
auto x128 = -V{0.166666666666667}*cell[13] + V{0.833333333333333}*cell[14] + x117*x74 + x123;
auto x129 = x58 + x70 - x75;
auto x130 = V{0.0833333333333333}*cell[12] + V{0.0833333333333334}*cell[13] + V{0.0833333333333334}*cell[14] + V{0.0833333333333333}*cell[3] - x111*x74 + x111*x79 - x119*x44 + x119*x49;
auto x131 = -V{0.0416666666666667}*cell[11] - V{0.0416666666666667}*cell[2] + x118*x39 - x118*x46 + x122 + x130 + V{0.0138888888888889};
auto x132 = V{0.833333333333333}*cell[15] - V{0.166666666666667}*cell[16] - x117*x82 + x131;
auto x133 = x126 + x61 - V{4.5}*((x81)*(x81));
auto x134 = -V{0.166666666666667}*cell[15] + V{0.833333333333333}*cell[16] + x117*x76 + x131;
auto x135 = V{0.0115740740740741}*x27;
auto x136 = V{0.0162037037037037}*x27;
auto x137 = V{0.00231481481481481}*x27;
auto x138 = -V{0.0833333333333333}*cell[10] + x100*x72 + x120 + x130;
auto x139 = V{0.416666666666667}*cell[17] - V{0.0833333333333333}*cell[18] + V{0.416666666666667}*cell[8] - V{0.0833333333333333}*cell[9] - x137*x59 - x137*x64 + x138;
auto x140 = -V{0.0833333333333333}*cell[17] + V{0.416666666666667}*cell[18] - V{0.0833333333333333}*cell[8] + V{0.416666666666667}*cell[9] + x137*x52 - x137*x66 + x138;
auto x0 = -V{0.333333333333333}*x22*(-x24*x85*x94 + V{1}) + x23*(V{1}*cell[10] + V{0.5}*cell[11] + V{0.5}*cell[12] + V{1}*cell[17] + V{1}*cell[18] + V{0.5}*cell[2] + V{0.5}*cell[3] + V{1}*cell[8] + V{1}*cell[9] + x25 - x28*x39 - x28*x44 - x28*x47 - x28*x50 - x28*x52 - x28*x60 - x28*x65 - x28*x67 - x68*x72 - x68*x74 - x68*x76 - x68*x80 - x68*x83 - x86 + V{0.833333333333333});
auto x1 = -x107*(x24*x94*x95 + V{1}) - x23*(-x106 - V{0.0185185185185185}*x27*x72 - x68*x95);
auto x2 = -x107*(-x24*x47*x94 + V{1}) - x23*(-x108*x46 - x109*x39 + x113);
auto x3 = -x107*(-x24*x50*x94 + V{1}) - x23*(-x108*x49 - x109*x44 + x114);
auto x4 = -x125*(x115*x24*x94 + V{1}) - x23*(-x115*x28 - x116*x74 + x124);
auto x5 = -x125*(x127*x24*x94 + V{1}) - x23*(x116*x79 - x127*x28 + x128);
auto x6 = -x125*(x129*x24*x94 + V{1}) - x23*(-x116*x76 - x129*x28 + x132);
auto x7 = -x125*(x133*x24*x94 + V{1}) - x23*(x116*x82 - x133*x28 + x134);
auto x8 = -x125*(-x24*x67*x94 + V{1}) - x23*(-x135*x52 - x136*x66 + x139);
auto x9 = -x125*(-x24*x65*x94 + V{1}) - x23*(x135*x59 - x136*x64 + x140);
auto x10 = -x107*(-x24*x72*x94 + V{1}) - x23*(-x106 + V{0.037037037037037}*x24*x26*x72);
auto x11 = -x107*(-x24*x39*x94 + V{1}) - x23*(x108*x39 + x109*x46 + x113);
auto x12 = -x107*(-x24*x44*x94 + V{1}) - x23*(x108*x44 + x109*x49 + x114);
auto x13 = -x125*(-x24*x74*x94 + V{1}) - x23*(x100*x74 + x124);
auto x14 = -x125*(-x24*x80*x94 + V{1}) - x23*(-x100*x79 + x128);
auto x15 = -x125*(-x24*x76*x94 + V{1}) - x23*(x100*x76 + x132);
auto x16 = -x125*(-x24*x83*x94 + V{1}) - x23*(-x100*x82 + x134);
auto x17 = -x125*(-x24*x52*x94 + V{1}) - x23*(x135*x66 + x136*x52 + x139);
auto x18 = -x125*(-x24*x60*x94 + V{1}) - x23*(x135*x64 - x136*x59 + x140);
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
return { V{1}*x24*(-x46*x89 - x49*x88 - x57*x84 - x59*x92 - x66*x90 - x79*x91 - x82*x88 - x87*(x56 + x63) + x93), x29 + x31 + x34 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
