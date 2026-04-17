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
struct CSE<AdvectionDiffusionCornerDynamics3D<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 1, -1, 1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x23 = x26 + V{-1};
auto x24 = V{3}*x19;
auto x25 = x24 + V{1};
auto x27 = V{0.0185185185185185}*x22;
auto x28 = x25*x27;
auto x29 = V{3}*x21;
auto x30 = x25 + x29;
auto x31 = V{0.00925925925925926}*x22;
auto x32 = x30*x31;
auto x33 = V{0.333333333333333}*cell[15] - x32;
auto x34 = V{3}*x20;
auto x35 = -x34;
auto x36 = x25 + x35;
auto x37 = x31*x36;
auto x38 = V{0.333333333333333}*cell[14] - x37 + V{0.037037037037037};
auto x39 = V{0.166666666666667}*cell[16];
auto x40 = V{0.166666666666667}*cell[7];
auto x41 = -x24;
auto x42 = x29 + V{1};
auto x43 = x41 + x42;
auto x44 = V{0.00462962962962963}*x22;
auto x45 = x43*x44;
auto x46 = -x29;
auto x47 = x25 + x46;
auto x48 = x44*x47;
auto x49 = x39 - x40 + x45 - x48;
auto x50 = V{0.166666666666667}*cell[13];
auto x51 = V{0.166666666666667}*cell[4];
auto x52 = x24 + V{-1};
auto x53 = x34 + x52;
auto x54 = -x53;
auto x55 = x25 + x34;
auto x56 = x44*x55;
auto x57 = x44*x54 + x50 - x51 - x56;
auto x58 = V{0.0555555555555556}*x22;
auto x59 = x34 + V{-1};
auto x60 = x35 + x42;
auto x61 = x31*x60;
auto x62 = V{0.333333333333333}*cell[9] - x61;
auto x63 = x44*x53 - x50 + x51 + x56;
auto x64 = V{0.166666666666667}*cell[8];
auto x65 = V{0.166666666666667}*cell[17];
auto x66 = x34 + x42;
auto x67 = x44*x66;
auto x68 = x29 + x59;
auto x69 = x44*x68 + x64 - x65 + x67;
auto x70 = x23*(V{0.333333333333333}*cell[2] + x27*x59 + x38 + x62 + x63 + x69);
auto x71 = -x68;
auto x72 = x27*x42;
auto x73 = x33 + V{0.037037037037037};
auto x74 = -x39 + x40 - x45 + x48;
auto x75 = V{0.166666666666667}*cell[15];
auto x76 = x30*x44;
auto x77 = -x76;
auto x78 = V{0.166666666666667}*cell[2];
auto x79 = V{0.0833333333333333}*cell[16];
auto x80 = V{0.0833333333333333}*cell[7];
auto x81 = V{0.00231481481481481}*x22;
auto x82 = x43*x81;
auto x83 = x47*x81;
auto x84 = x79 - x80 + x82 - x83;
auto x85 = V{0.0833333333333333}*cell[17];
auto x86 = V{0.0833333333333333}*cell[8];
auto x87 = x66*x81;
auto x88 = x71*x81 + x85 - x86 - x87;
auto x89 = V{0.166666666666667}*cell[10];
auto x90 = x25*x31;
auto x91 = -x90;
auto x92 = V{0.166666666666667}*cell[9];
auto x93 = x44*x60;
auto x94 = -x92 + x93;
auto x95 = x89 + x91 + x94;
auto x96 = V{0.0277777777777778}*x22;
auto x97 = -x93;
auto x98 = x89 + x91 + x92 + x97;
auto x99 = x31*x59;
auto x100 = x75 + x77 + x78 + x99;
auto x101 = x68*x81 - x85 + x86 + x87;
auto x102 = x23*(x100 + x101 + x38 + x84 + x98);
auto x103 = x34 + V{1};
auto x104 = V{0.166666666666667}*cell[12];
auto x105 = x31*x42;
auto x106 = x36*x44;
auto x107 = V{0.166666666666667}*cell[14] - x106;
auto x108 = x104 - x105 + x107;
auto x109 = V{0.0833333333333333}*cell[13];
auto x110 = V{0.0833333333333333}*cell[4];
auto x111 = x55*x81;
auto x112 = x109 - x110 - x111;
auto x113 = -x104;
auto x114 = x53*x81;
auto x115 = x107 + V{4.62592926927149e-18};
auto x116 = x23*(x101 + x105 + x112 + x113 - x114 + x115 + x49 + x95);
auto x117 = -x109 + x110 + x111 + x114;
auto x118 = x105 + x113 + x117;
auto x119 = -x75 + x76 + x78 + x99;
auto x120 = x23*(x115 + x118 + x119 + x69 + x84);
auto x121 = -x79 + x80 - x82 + x83;
auto x122 = x23*(x100 + x108 + x117 + x121 + x62 + V{0.037037037037037});
auto x123 = -V{0.333333333333333}*cell[15] + x32;
auto x124 = x123 + V{-0.037037037037037};
auto x125 = -V{0.166666666666667}*cell[10] + x101 + x90;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = x23*(V{0.333333333333333}*cell[10] - x28 + x33 + x38 + x49 + x57) - x52*x58 + V{-0.0555555555555556};
cell[2] = -x58*x59 - x70 + V{-0.0555555555555556};
cell[3] = x23*(V{0.333333333333333}*cell[12] + x44*x71 + x62 - x64 + x65 - x67 - x72 + x73 + x74) - x58*(x29 + V{-1}) + V{-0.0555555555555556};
cell[4] = x23*(-x31*x59 + x57 + x75 + x77 - x78 + x84 + x88 + x95) - x53*x96 + V{-0.0277777777777778};
cell[5] = x102 + x96*(x103 + x41) + V{-0.0277777777777778};
cell[6] = x23*(x108 + x112 + x54*x81 + x73 + x88 + x98) - x96*(x29 + x52) + V{-0.0277777777777778};
cell[7] = x116 + x43*x96 + V{-0.0277777777777778};
cell[8] = -x120 - x68*x96 + V{-0.0277777777777778};
cell[9] = -x122 + V{0.0277777777777778}*x22*x60 + V{-0.0277777777777778};
cell[10] = V{0.0555555555555556}*x22*x25 - x23*(V{0.333333333333333}*cell[10] + V{0.333333333333333}*cell[14] - x123 - x28 - x37 - x63 - x74 + V{0.037037037037037}) + V{-0.0555555555555556};
cell[11] = x103*x58 + x70 + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x42 - x23*(V{0.333333333333333}*cell[12] + V{0.333333333333333}*cell[9] - x124 - x49 - x61 - x69 - x72) + V{-0.0555555555555556};
cell[13] = V{0.0277777777777778}*x22*x55 - x23*(-x119 - x121 - x125 - x63 - x92 - x97) + V{-0.0277777777777778};
cell[14] = -x102 + V{0.0277777777777778}*x22*x36 + V{-0.0277777777777778};
cell[15] = V{0.0277777777777778}*x22*x30 - x23*(V{0.166666666666667}*cell[14] - x106 - x118 - x124 - x125 - x94) + V{-0.0277777777777778};
cell[16] = -x116 + V{0.0277777777777778}*x22*x47 + V{-0.0277777777777778};
cell[17] = x120 + x66*x96 + V{-0.0277777777777778};
cell[18] = x122 + x96*(x103 + x46) + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
