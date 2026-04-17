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
struct CSE<CombinedRLBdynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>, momenta::Tuple<momenta::VelocityBoundaryDensity<2, 1>, momenta::FixedVelocityMomentumGeneric, momenta::RegularizedBoundaryStress<2, 1>, momenta::DefineSeparately> >> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x22 = parameters.template get<descriptors::OMEGA>();
auto x20 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x21 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(2);
auto x23 = x22 + V{-1};
auto x24 = V{1} / (x21 + V{1});
auto x25 = V{2}*cell[15] + V{2}*cell[17] + V{2}*cell[7] + V{2}*cell[9];
auto x26 = cell[0] + cell[10] + cell[11] + V{2}*cell[12] + cell[13] + cell[14] + cell[1] + cell[2] + cell[4] + cell[5] + x25 + V{1};
auto x27 = x24*x26;
auto x28 = V{0.0277777777777778}*x27;
auto x29 = ((x19)*(x19));
auto x30 = V{3}*x19;
auto x31 = ((x20)*(x20));
auto x32 = V{1.5}*x31;
auto x33 = -x32;
auto x34 = ((x21)*(x21));
auto x35 = V{1.5}*x34;
auto x36 = V{1} - x35;
auto x37 = x33 + x36;
auto x38 = x30 + x37;
auto x39 = V{3}*x29 + x38;
auto x40 = V{3}*x20;
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
auto x51 = ((x19 + x20)*(x19 + x20));
auto x52 = x38 + x43 + V{4.5}*x51;
auto x53 = -x30;
auto x54 = x19 - x20;
auto x55 = -V{4.5}*((x54)*(x54));
auto x56 = x41 + x45;
auto x57 = x40 + x56;
auto x58 = x53 + x55 + x57;
auto x59 = -x58;
auto x60 = -x40;
auto x61 = x30 + x56;
auto x62 = x60 + x61;
auto x63 = x62 - V{4.5}*((x54)*(x54));
auto x64 = -x63;
auto x65 = x30 - V{4.5}*x51 + x57;
auto x66 = -x65;
auto x67 = V{0.0555555555555556}*x27;
auto x68 = V{3}*x21;
auto x69 = x42 + x68;
auto x70 = x33 + V{3}*x34 + x69 + V{1};
auto x71 = V{4.5}*((x19 + x21)*(x19 + x21));
auto x72 = x38 + x69 + x71;
auto x73 = V{4.5}*((x20 + x21)*(x20 + x21));
auto x74 = x37 + x43 + x68 + x73;
auto x75 = -x21;
auto x76 = x19 + x75;
auto x77 = -x68;
auto x78 = x61 + x77;
auto x79 = x78 - V{4.5}*((x76)*(x76));
auto x80 = -x79;
auto x81 = x20 + x75;
auto x82 = x57 + x77;
auto x83 = x82 - V{4.5}*((x81)*(x81));
auto x84 = -x83;
auto x85 = V{0.333333333333333}*x27;
auto x86 = -x56;
auto x87 = x85*x86;
auto x88 = V{0.0277777777777778}*x27;
auto x89 = V{0.0555555555555555}*x27;
auto x90 = V{0.0555555555555555}*x27;
auto x91 = V{0.0277777777777778}*x27;
auto x92 = V{0.0555555555555555}*x27;
auto x93 = V{0.0277777777777778}*x27;
auto x94 = V{1.66533453693773e-16}*cell[10] + V{1.11022302462516e-16}*cell[11] + V{4.44089209850063e-16}*cell[12] + V{4.44089209850063e-16}*cell[13] + V{4.9960036108132e-16}*cell[14] + V{6.66133814775094e-16}*cell[15] + V{4.44089209850063e-16}*cell[17] + V{1.66533453693773e-16}*cell[1] + V{1.11022302462516e-16}*cell[2] + V{4.44089209850063e-16}*cell[4] + V{4.9960036108132e-16}*cell[5] + V{6.66133814775094e-16}*cell[7] + V{0.111111111111111}*x27*x70 + x39*x67 + x44*x67 + x52*x93 + x72*x92 + x74*x89 + V{2.22044604925031e-16};
auto x95 = x47*x90 + x50*x89 + x59*x93 + x64*x88 + x66*x91 + x80*x92 + x84*x89 + x87 + x94;
auto x96 = V{0.0462962962962963}*x27;
auto x97 = V{0.00925925925925926}*x27;
auto x98 = V{0.166666666666667}*cell[15];
auto x99 = V{0.166666666666667}*cell[7];
auto x100 = V{0.0833333333333333}*cell[11];
auto x101 = V{0.0833333333333333}*cell[2];
auto x102 = V{0.00462962962962963}*x27;
auto x103 = x102*x44;
auto x104 = V{0.00925925925925926}*x27;
auto x105 = V{0.00462962962962963}*x27;
auto x106 = x102*x49;
auto x107 = x105*x72;
auto x108 = V{0.00231481481481482}*x27;
auto x109 = -V{0.166666666666667}*cell[12] + V{0.0833333333333334}*cell[13] + V{0.0833333333333334}*cell[14] + V{0.0833333333333334}*cell[4] + V{0.0833333333333334}*cell[5] + x104*x70 - x108*x52 + x108*x58 + x108*x63 + x108*x65 + V{-0.0555555555555555};
auto x110 = V{0.166666666666667}*cell[10] - V{0.333333333333333}*cell[17] + V{0.166666666666667}*cell[1] - V{0.333333333333333}*cell[9] - x100 - x101 + x103 + x104*x74 - x104*x83 + x105*x79 - x106 - x107 + x109 + x98 + x99;
auto x111 = V{0.0555555555555556}*x22;
auto x112 = V{0.166666666666667}*cell[17];
auto x113 = V{0.166666666666667}*cell[9];
auto x114 = V{0.0833333333333333}*cell[10];
auto x115 = V{0.0833333333333333}*cell[1];
auto x116 = x102*x39;
auto x117 = x102*x46;
auto x118 = x105*x74;
auto x119 = V{0.166666666666667}*cell[11] - V{0.333333333333333}*cell[15] + V{0.166666666666667}*cell[2] - V{0.333333333333333}*cell[7] + x104*x72 - x104*x79 + x105*x83 + x109 + x112 + x113 - x114 - x115 + x116 - x117 - x118;
auto x120 = -x32 + V{3}*x34 - x48 - x68;
auto x121 = -V{0.333333333333333}*cell[12] + V{0.166666666666667}*cell[13] + V{0.166666666666667}*cell[14] + V{0.166666666666667}*cell[4] + V{0.166666666666667}*cell[5] + x100 + x101 - x102*x52 - x103 + x107 - x112 - x113 + x114 + x115 - x116 + x118 - x98 - x99 + V{0.0555555555555555};
auto x122 = V{0.0115740740740741}*x27;
auto x123 = V{0.0162037037037037}*x27;
auto x124 = V{0.00231481481481481}*x27;
auto x125 = V{0.00462962962962963}*x27;
auto x126 = V{0.0833333333333333}*cell[10] + V{0.0833333333333334}*cell[17] + V{0.0833333333333333}*cell[1] + V{0.0833333333333334}*cell[9] - x108*x74 + x108*x83 - x125*x39 + x125*x46 + V{0.0138888888888889};
auto x127 = V{0.0833333333333333}*cell[11] + V{0.0833333333333334}*cell[15] + V{0.0833333333333333}*cell[2] + V{0.0833333333333334}*cell[7] - x108*x72 + x108*x79 - x125*x44 + x125*x49;
auto x128 = -V{0.0833333333333333}*cell[12] + x102*x70 + x126 + x127;
auto x129 = V{0.416666666666667}*cell[13] - V{0.0833333333333333}*cell[14] + V{0.416666666666667}*cell[4] - V{0.0833333333333333}*cell[5] - x124*x58 - x124*x63 + x128;
auto x130 = V{0.0277777777777778}*x22;
auto x131 = -V{0.0833333333333333}*cell[13] + V{0.416666666666667}*cell[14] - V{0.0833333333333333}*cell[4] + V{0.416666666666667}*cell[5] + x124*x52 - x124*x65 + x128;
auto x132 = x61 + x68 - x71;
auto x133 = V{0.0231481481481481}*x27;
auto x134 = V{0.00462962962962963}*x27;
auto x135 = V{0.00231481481481481}*x27;
auto x136 = V{0.00115740740740741}*x27;
auto x137 = V{0.166666666666667}*cell[12] + V{0.0416666666666667}*cell[13] + V{0.0416666666666667}*cell[14] + V{0.0416666666666667}*cell[4] + V{0.0416666666666667}*cell[5] - x136*x52 + x136*x58 + x136*x63 + x136*x65 - x70*x97;
auto x138 = -V{0.0416666666666667}*cell[11] - V{0.0416666666666667}*cell[2] + x126 + x135*x44 - x135*x49 + x137;
auto x139 = V{0.833333333333333}*cell[15] - V{0.166666666666667}*cell[7] - x134*x79 + x138;
auto x140 = -V{0.166666666666667}*cell[15] + V{0.833333333333333}*cell[7] + x134*x72 + x138;
auto x141 = x57 + x68 - x73;
auto x142 = -V{0.0416666666666667}*cell[10] - V{0.0416666666666667}*cell[1] + x127 + x135*x39 - x135*x46 + x137 + V{0.0138888888888889};
auto x143 = V{0.833333333333333}*cell[17] - V{0.166666666666667}*cell[9] - x134*x83 + x142;
auto x144 = -V{0.166666666666667}*cell[17] + V{0.833333333333333}*cell[9] + x134*x74 + x142;
auto x145 = -V{4.5}*((x76)*(x76));
auto x146 = x56 + x68;
auto x147 = x145 + x146 + x53;
auto x148 = -V{4.5}*((x81)*(x81));
auto x149 = x146 + x148 + x60;
auto x0 = -V{0.333333333333333}*x22*(-x24*x86*x95 + V{1}) + x23*(V{0.5}*cell[10] + V{0.5}*cell[11] + V{1}*cell[12] + V{1}*cell[13] + V{1}*cell[14] + V{0.5}*cell[1] + V{0.5}*cell[2] + V{1}*cell[4] + V{1}*cell[5] + x25 - x28*x39 - x28*x44 - x28*x47 - x28*x50 - x28*x52 - x28*x59 - x28*x64 - x28*x66 - x67*x70 - x67*x72 - x67*x74 - x67*x80 - x67*x84 - x87 + V{0.833333333333333});
auto x1 = -x111*(-x24*x47*x95 + V{1}) - x23*(x110 - x39*x97 - x46*x96);
auto x2 = -x111*(-x24*x50*x95 + V{1}) - x23*(x119 - x44*x97 - x49*x96);
auto x3 = -x111*(-x120*x24*x95 + V{1}) + x23*(-x102*x47 - x102*x50 - x102*x59 - x102*x64 - x102*x66 + x105*x80 + x105*x84 - x120*x67 + x121 + V{0.0185185185185185}*x27*x70);
auto x4 = -x130*(-x24*x66*x95 + V{1}) - x23*(-x122*x52 - x123*x65 + x129);
auto x5 = -x130*(-x24*x64*x95 + V{1}) - x23*(x122*x58 - x123*x63 + x131);
auto x6 = -x130*(x132*x24*x95 + V{1}) - x23*(-x132*x28 - x133*x72 + x139);
auto x7 = -x130*(-x24*x80*x95 + V{1}) - x23*(-x102*x79 + x140);
auto x8 = -x130*(x141*x24*x95 + V{1}) - x23*(-x133*x74 - x141*x28 + x143);
auto x9 = -x130*(-x24*x84*x95 + V{1}) - x23*(-x102*x83 + x144);
auto x10 = -x111*(-x24*x39*x95 + V{1}) - x23*(x110 + x39*x96 + x46*x97);
auto x11 = -x111*(-x24*x44*x95 + V{1}) - x23*(x119 + x44*x96 + x49*x97);
auto x12 = -x111*(-x24*x70*x95 + V{1}) - x23*(-x102*x58 - x102*x63 - x102*x65 - x106 - x117 - x121 + V{0.037037037037037}*x24*x26*x70 + V{0.00462962962962963}*x24*x26*x79 + V{0.00462962962962963}*x24*x26*x83);
auto x13 = -x130*(-x24*x52*x95 + V{1}) - x23*(x122*x65 + x123*x52 + x129);
auto x14 = -x130*(-x24*x59*x95 + V{1}) - x23*(x122*x63 - x123*x58 + x131);
auto x15 = -x130*(-x24*x72*x95 + V{1}) - x23*(x102*x72 + x139);
auto x16 = -x130*(x147*x24*x95 + V{1}) - x23*(x133*x79 + x140 - x147*x28);
auto x17 = -x130*(-x24*x74*x95 + V{1}) - x23*(x102*x74 + x143);
auto x18 = -x130*(x149*x24*x95 + V{1}) - x23*(x133*x83 + x144 - x149*x28);
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
return { V{1}*x24*(-x46*x90 - x49*x89 - x56*x85 - x58*x93 - x65*x91 - x88*(x55 + x62) - x89*(x148 + x82) - x92*(x145 + x78) + x94), x29 + x31 + x34 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
