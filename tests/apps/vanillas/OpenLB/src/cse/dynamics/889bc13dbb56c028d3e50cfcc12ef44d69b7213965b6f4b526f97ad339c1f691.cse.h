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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::ConstRhoBGK, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x20 = parameters.template get<statistics::AVERAGE_RHO>();
auto x19 = parameters.template get<descriptors::OMEGA>();
auto x21 = x19 + V{-1};
auto x22 = cell[10] + cell[14];
auto x23 = cell[12] + cell[7];
auto x24 = cell[0] + cell[11] + cell[13] + cell[15] + cell[16] + cell[17] + cell[18] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[8] + cell[9] + x22 + x23;
auto x25 = x24 + V{1};
auto x26 = V{1} / ((x25)*(x25));
auto x27 = V{1.5}*x26;
auto x28 = cell[13] - cell[4];
auto x29 = cell[15] - cell[6];
auto x30 = x28 + x29;
auto x31 = -cell[1];
auto x32 = cell[16] - cell[7];
auto x33 = x31 + x32;
auto x34 = -cell[5] + x22;
auto x35 = ((x30 + x33 + x34)*(x30 + x33 + x34));
auto x36 = x27*x35;
auto x37 = cell[17] - cell[8];
auto x38 = x28 + x37;
auto x39 = cell[18] - cell[9];
auto x40 = -cell[2];
auto x41 = cell[11] - cell[14] + cell[5] + x40;
auto x42 = ((x38 + x39 + x41)*(x38 + x39 + x41));
auto x43 = x27*x42;
auto x44 = x29 + x37;
auto x45 = -cell[3];
auto x46 = -cell[18] + cell[9];
auto x47 = x45 + x46;
auto x48 = -cell[16] + x23;
auto x49 = ((x44 + x47 + x48)*(x44 + x47 + x48));
auto x50 = x27*x49;
auto x51 = x43 + x50 + V{-1};
auto x52 = x36 + x51;
auto x53 = V{1} / (x25);
auto x54 = -x53*(x20 + V{-1}) + V{1};
auto x55 = x24 + V{1};
auto x56 = x54*x55;
auto x57 = V{0.0555555555555556}*cell[0] + V{0.0555555555555556}*cell[10] + V{0.0555555555555556}*cell[11] + V{0.0555555555555556}*cell[12] + V{0.0555555555555556}*cell[13] + V{0.0555555555555556}*cell[14] + V{0.0555555555555556}*cell[15] + V{0.0555555555555556}*cell[16] + V{0.0555555555555556}*cell[17] + V{0.0555555555555556}*cell[18] + V{0.0555555555555556}*cell[1] + V{0.0555555555555556}*cell[2] + V{0.0555555555555556}*cell[3] + V{0.0555555555555556}*cell[4] + V{0.0555555555555556}*cell[5] + V{0.0555555555555556}*cell[6] + V{0.0555555555555556}*cell[7] + V{0.0555555555555556}*cell[8] + V{0.0555555555555556}*cell[9] + V{0.0555555555555556};
auto x58 = V{3}*cell[14];
auto x59 = V{3}*cell[16];
auto x60 = V{3}*cell[5];
auto x61 = V{3}*cell[7];
auto x62 = V{3}*cell[13] - V{3}*cell[4];
auto x63 = V{3}*cell[15] - V{3}*cell[6];
auto x64 = x53*(V{3}*cell[10] - V{3}*cell[1] + x58 + x59 - x60 - x61 + x62 + x63);
auto x65 = V{3}*x26;
auto x66 = x35*x65;
auto x67 = x51 + x64 - x66;
auto x68 = V{0.0555555555555556}*x56;
auto x69 = V{3}*cell[18];
auto x70 = V{3}*cell[9];
auto x71 = V{3}*cell[17] - V{3}*cell[8];
auto x72 = x53*(V{3}*cell[11] - V{3}*cell[2] - x58 + x60 + x62 + x69 - x70 + x71);
auto x73 = x42*x65;
auto x74 = x36 + V{-1};
auto x75 = x50 + x72 - x73 + x74;
auto x76 = x53*(V{3}*cell[12] - V{3}*cell[3] - x59 + x61 + x63 - x69 + x70 + x71);
auto x77 = x49*x65;
auto x78 = x43 + x74 + x76 - x77;
auto x79 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[10] + V{0.0277777777777778}*cell[11] + V{0.0277777777777778}*cell[12] + V{0.0277777777777778}*cell[13] + V{0.0277777777777778}*cell[14] + V{0.0277777777777778}*cell[15] + V{0.0277777777777778}*cell[16] + V{0.0277777777777778}*cell[17] + V{0.0277777777777778}*cell[18] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778}*cell[9] + V{0.0277777777777778};
auto x80 = V{4.5}*x26;
auto x81 = cell[10] + x33;
auto x82 = x80*((cell[11] + 2*cell[13] - 2*cell[4] + x39 + x40 + x44 + x81)*(cell[11] + 2*cell[13] - 2*cell[4] + x39 + x40 + x44 + x81));
auto x83 = x52 + x64;
auto x84 = x72 - x82 + x83;
auto x85 = V{0.0277777777777778}*x56;
auto x86 = -x72;
auto x87 = -cell[17] + cell[8];
auto x88 = -cell[11] + V{2}*cell[14] + cell[2] - V{2}*cell[5] + x29 + x46 + x81 + x87;
auto x89 = -x80*((x88)*(x88)) + x83 + x86;
auto x90 = x31 + x34;
auto x91 = x80*((cell[12] + 2*cell[15] - 2*cell[6] + x38 + x47 + x90)*(cell[12] + 2*cell[15] - 2*cell[6] + x38 + x47 + x90));
auto x92 = x76 + x83 - x91;
auto x93 = -x76;
auto x94 = -cell[12] + cell[3] + x28;
auto x95 = V{2}*cell[16] - V{2}*cell[7] + x39 + x87 + x90 + x94;
auto x96 = -x80*((x95)*(x95)) + x83 + x93;
auto x97 = x80*((2*cell[17] - 2*cell[8] + x30 + x41 + x45 + x48)*(2*cell[17] - 2*cell[8] + x30 + x41 + x45 + x48));
auto x98 = x52 + x72;
auto x99 = x76 - x97 + x98;
auto x100 = -cell[15] + V{2}*cell[18] + cell[6] - V{2}*cell[9] + x32 + x41 + x94;
auto x101 = -x80*((x100)*(x100)) + x93 + x98;
auto x102 = -x43;
auto x103 = V{1} - x50;
auto x104 = x102 + x103;
auto x105 = x104 + x64;
auto x106 = x105 + x66;
auto x107 = -x36;
auto x108 = x107 + x72;
auto x109 = x103 + x108 + x73;
auto x110 = x107 + x76;
auto x111 = x102 + x110 + x77 + V{1};
auto x112 = x105 + x108 + x82;
auto x113 = -x64;
auto x114 = x113 - x80*((x88)*(x88)) + x98;
auto x115 = x105 + x110 + x91;
auto x116 = x52 + x76;
auto x117 = x113 + x116 - x80*((x95)*(x95));
auto x118 = x104 + x108 + x76 + x97;
auto x119 = x116 - x80*((x100)*(x100)) + x86;
auto x0 = -x21*(cell[0] + x52*(V{0.333333333333333}*cell[0] + V{0.333333333333333}*cell[10] + V{0.333333333333333}*cell[11] + V{0.333333333333333}*cell[12] + V{0.333333333333333}*cell[13] + V{0.333333333333333}*cell[14] + V{0.333333333333333}*cell[15] + V{0.333333333333333}*cell[16] + V{0.333333333333333}*cell[17] + V{0.333333333333333}*cell[18] + V{0.333333333333333}*cell[1] + V{0.333333333333333}*cell[2] + V{0.333333333333333}*cell[3] + V{0.333333333333333}*cell[4] + V{0.333333333333333}*cell[5] + V{0.333333333333333}*cell[6] + V{0.333333333333333}*cell[7] + V{0.333333333333333}*cell[8] + V{0.333333333333333}*cell[9] + V{0.333333333333333}) + V{0.333333333333333}) - V{0.333333333333333}*x52*x56 + V{-0.333333333333333};
auto x1 = -x21*(cell[1] + x57*x67 + V{0.0555555555555556}) - x67*x68 + V{-0.0555555555555556};
auto x2 = -x21*(cell[2] + x57*x75 + V{0.0555555555555556}) - x68*x75 + V{-0.0555555555555556};
auto x3 = -x21*(cell[3] + x57*x78 + V{0.0555555555555556}) - x68*x78 + V{-0.0555555555555556};
auto x4 = -x21*(cell[4] + x79*x84 + V{0.0277777777777778}) - x84*x85 + V{-0.0277777777777778};
auto x5 = -x21*(cell[5] + x79*x89 + V{0.0277777777777778}) - x85*x89 + V{-0.0277777777777778};
auto x6 = -x21*(cell[6] + x79*x92 + V{0.0277777777777778}) - x85*x92 + V{-0.0277777777777778};
auto x7 = -x21*(cell[7] + x79*x96 + V{0.0277777777777778}) - x85*x96 + V{-0.0277777777777778};
auto x8 = -x21*(cell[8] + x79*x99 + V{0.0277777777777778}) - x85*x99 + V{-0.0277777777777778};
auto x9 = -x101*x85 - x21*(cell[9] + x101*x79 + V{0.0277777777777778}) + V{-0.0277777777777778};
auto x10 = V{0.0555555555555556}*x106*x54*x55 - x21*(cell[10] - x106*x57 + V{0.0555555555555556}) + V{-0.0555555555555556};
auto x11 = V{0.0555555555555556}*x109*x54*x55 - x21*(cell[11] - x109*x57 + V{0.0555555555555556}) + V{-0.0555555555555556};
auto x12 = V{0.0555555555555556}*x111*x54*x55 - x21*(cell[12] - x111*x57 + V{0.0555555555555556}) + V{-0.0555555555555556};
auto x13 = V{0.0277777777777778}*x112*x54*x55 - x21*(cell[13] - x112*x79 + V{0.0277777777777778}) + V{-0.0277777777777778};
auto x14 = -x114*x85 - x21*(cell[14] + x114*x79 + V{0.0277777777777778}) + V{-0.0277777777777778};
auto x15 = V{0.0277777777777778}*x115*x54*x55 - x21*(cell[15] - x115*x79 + V{0.0277777777777778}) + V{-0.0277777777777778};
auto x16 = -x117*x85 - x21*(cell[16] + x117*x79 + V{0.0277777777777778}) + V{-0.0277777777777778};
auto x17 = V{0.0277777777777778}*x118*x54*x55 - x21*(cell[17] - x118*x79 + V{0.0277777777777778}) + V{-0.0277777777777778};
auto x18 = -x119*x85 - x21*(cell[18] + x119*x79 + V{0.0277777777777778}) + V{-0.0277777777777778};
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
return { -x20 + x24 + V{2}, V{1}*x26*(x35 + x42 + x49) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
