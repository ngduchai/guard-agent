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
struct CSE<AdvectionDiffusionCornerDynamics3D<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, -1, -1, 1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x23 = x26 + V{-1};
auto x24 = V{0.166666666666667}*cell[5];
auto x25 = V{0.166666666666667}*cell[14];
auto x27 = V{3}*x20;
auto x28 = -x27;
auto x29 = V{3}*x19;
auto x30 = x29 + V{1};
auto x31 = x28 + x30;
auto x32 = V{0.00462962962962963}*x22;
auto x33 = x31*x32;
auto x34 = x29 + V{-1};
auto x35 = x22*x34;
auto x36 = -x29;
auto x37 = x27 + V{1};
auto x38 = x36 + x37;
auto x39 = x32*x38;
auto x40 = V{3}*x21;
auto x41 = x40 + V{1};
auto x42 = x36 + x41;
auto x43 = V{0.00925925925925926}*x22;
auto x44 = x42*x43;
auto x45 = V{0.333333333333333}*cell[7] - x44;
auto x46 = x27 + x34;
auto x47 = V{0.333333333333333}*cell[4] + x43*x46 + V{0.037037037037037};
auto x48 = V{0.166666666666667}*cell[6];
auto x49 = V{0.166666666666667}*cell[15];
auto x50 = x29 + x41;
auto x51 = x32*x50;
auto x52 = x34 + x40;
auto x53 = x32*x52 + x48 - x49 + x51;
auto x54 = x23*(V{0.333333333333333}*cell[1] + x24 - x25 + x33 + V{0.0185185185185185}*x35 - x39 + x45 + x47 + x53);
auto x55 = x27 + V{-1};
auto x56 = x22*x55;
auto x57 = x28 + x41;
auto x58 = x43*x57;
auto x59 = V{0.333333333333333}*cell[9] - x58;
auto x60 = V{0.166666666666667}*cell[8];
auto x61 = V{0.166666666666667}*cell[17];
auto x62 = x27 + x41;
auto x63 = x32*x62;
auto x64 = x40 + x55;
auto x65 = x32*x64 + x60 - x61 + x63;
auto x66 = -x24 + x25 - x33 + x39;
auto x67 = x23*(V{0.333333333333333}*cell[2] + x47 + V{0.0185185185185185}*x56 + x59 + x65 + x66);
auto x68 = V{0.0185185185185185}*x22*x41;
auto x69 = -x52;
auto x70 = x32*x69 - x48 + x49 - x51;
auto x71 = -x64;
auto x72 = x32*x71 - x60 + x61 - x63;
auto x73 = V{0.0555555555555556}*x22;
auto x74 = V{0.166666666666667}*cell[1];
auto x75 = x34*x43;
auto x76 = x32*x57;
auto x77 = V{0.166666666666667}*cell[9] - x76;
auto x78 = x74 + x75 + x77;
auto x79 = V{0.166666666666667}*cell[2];
auto x80 = x43*x55;
auto x81 = V{0.166666666666667}*cell[7];
auto x82 = x32*x42;
auto x83 = x81 - x82;
auto x84 = x79 + x80 + x83;
auto x85 = V{0.0833333333333333}*cell[8];
auto x86 = V{0.0833333333333333}*cell[17];
auto x87 = V{0.00231481481481481}*x22;
auto x88 = x62*x87;
auto x89 = x64*x87;
auto x90 = x85 - x86 + x88 + x89;
auto x91 = V{0.0833333333333333}*cell[6];
auto x92 = V{0.0833333333333333}*cell[15];
auto x93 = x50*x87;
auto x94 = x52*x87;
auto x95 = x91 - x92 + x93 + x94;
auto x96 = x23*(x47 + x78 + x84 + x90 + x95);
auto x97 = V{0.0277777777777778}*x22;
auto x98 = -x91 + x92 - x93;
auto x99 = -x94 + x98;
auto x100 = -x74 + x77;
auto x101 = x79 + x80 - x81 + x82;
auto x102 = x23*(x100 + x101 + x66 - x75 + x90 + x99);
auto x103 = -x85 + x86 - x88;
auto x104 = V{0.0833333333333333}*cell[14];
auto x105 = V{0.0833333333333333}*cell[5];
auto x106 = x38*x87;
auto x107 = x31*x87;
auto x108 = x104 - x105 + x106 - x107;
auto x109 = V{0.166666666666667}*cell[12];
auto x110 = x41*x43;
auto x111 = -x110;
auto x112 = V{0.166666666666667}*cell[4];
auto x113 = x109 + x111 - x112 - x32*x46 + V{4.62592926927149e-18};
auto x114 = x112 + x32*x46;
auto x115 = x109 + x111 + x114 + V{0.037037037037037};
auto x116 = -x104 + x105 - x106 + x107;
auto x117 = x23*(x103 + x115 + x116 + x45 + x78 - x89);
auto x118 = x23*(x108 + x115 + x59 + x84 + x99);
auto x119 = -V{0.166666666666667}*cell[12] + x110 + x114 + V{-4.62592926927149e-18};
auto x120 = -x40;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = -V{0.0555555555555556}*x35 - x54 + V{-0.0555555555555556};
cell[2] = -V{0.0555555555555556}*x56 - x67 + V{-0.0555555555555556};
cell[3] = x23*(V{0.333333333333333}*cell[12] + x45 + x59 - x68 + x70 + x72 + V{0.037037037037037}) - x73*(x40 + V{-1}) + V{-0.0555555555555556};
cell[4] = -x46*x97 - x96 + V{-0.0277777777777778};
cell[5] = x102 + x38*x97 + V{-0.0277777777777778};
cell[6] = x23*(x100 + x103 + x108 + x113 - x34*x43 + x70 + x71*x87) - x52*x97 + V{-0.0277777777777778};
cell[7] = -x117 + V{0.0277777777777778}*x22*x42 + V{-0.0277777777777778};
cell[8] = x23*(x113 + x116 - x43*x55 + x69*x87 + x72 - x79 + x83 + x98) - x64*x97 + V{-0.0277777777777778};
cell[9] = -x118 + V{0.0277777777777778}*x22*x57 + V{-0.0277777777777778};
cell[10] = x30*x73 + x54 + V{-0.0555555555555556};
cell[11] = x37*x73 + x67 + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x41 - x23*(V{0.333333333333333}*cell[12] + V{0.333333333333333}*cell[7] + V{0.333333333333333}*cell[9] - x44 - x53 - x58 - x65 - x68 + V{0.037037037037037}) + V{-0.0555555555555556};
cell[13] = x96 + x97*(x27 + x30) + V{-0.0277777777777778};
cell[14] = -x102 + V{0.0277777777777778}*x22*x31 + V{-0.0277777777777778};
cell[15] = V{0.0277777777777778}*x22*x50 - x23*(V{0.166666666666667}*cell[9] - x116 - x119 - x53 - x74 - x75 - x76 - x90) + V{-0.0277777777777778};
cell[16] = x117 + x97*(x120 + x30) + V{-0.0277777777777778};
cell[17] = V{0.0277777777777778}*x22*x62 - x23*(-x101 - x108 - x119 - x65 - x95) + V{-0.0277777777777778};
cell[18] = x118 + x97*(x120 + x37) + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
