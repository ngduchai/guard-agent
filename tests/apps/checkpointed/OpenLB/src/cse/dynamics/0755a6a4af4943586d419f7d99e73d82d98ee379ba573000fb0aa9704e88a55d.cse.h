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
struct CSE<AdvectionDiffusionCornerDynamics3D<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, -1, 1, 1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x23 = x26 + V{-1};
auto x24 = V{3}*x19;
auto x25 = x24 + V{-1};
auto x27 = x22*x25;
auto x28 = -x24;
auto x29 = V{3}*x21;
auto x30 = x29 + V{1};
auto x31 = x28 + x30;
auto x32 = V{0.00925925925925926}*x22;
auto x33 = x31*x32;
auto x34 = V{0.333333333333333}*cell[7] - x33;
auto x35 = V{3}*x20;
auto x36 = x35 + V{1};
auto x37 = x28 + x36;
auto x38 = x32*x37;
auto x39 = V{0.333333333333333}*cell[5] - x38 + V{0.037037037037037};
auto x40 = V{0.166666666666667}*cell[4];
auto x41 = V{0.166666666666667}*cell[13];
auto x42 = x24 + x36;
auto x43 = V{0.00462962962962963}*x22;
auto x44 = x42*x43;
auto x45 = x25 + x35;
auto x46 = x40 - x41 + x43*x45 + x44;
auto x47 = V{0.166666666666667}*cell[6];
auto x48 = V{0.166666666666667}*cell[15];
auto x49 = x24 + x30;
auto x50 = x43*x49;
auto x51 = x25 + x29;
auto x52 = x43*x51 + x47 - x48 + x50;
auto x53 = x23*(V{0.333333333333333}*cell[1] + V{0.0185185185185185}*x27 + x34 + x39 + x46 + x52);
auto x54 = V{0.0185185185185185}*x22;
auto x55 = x36*x54;
auto x56 = x29 + x36;
auto x57 = x32*x56;
auto x58 = V{0.333333333333333}*cell[17] - x57;
auto x59 = V{0.166666666666667}*cell[18];
auto x60 = V{0.166666666666667}*cell[9];
auto x61 = -x35;
auto x62 = x30 + x61;
auto x63 = x43*x62;
auto x64 = -x29;
auto x65 = x36 + x64;
auto x66 = x43*x65;
auto x67 = x59 - x60 + x63 - x66;
auto x68 = -x45;
auto x69 = -x40 + x41 + x43*x68 - x44;
auto x70 = x35 + V{-1};
auto x71 = V{0.0555555555555556}*x22;
auto x72 = -x51;
auto x73 = x30*x54;
auto x74 = x34 + V{0.037037037037037};
auto x75 = -x59 + x60 - x63 + x66;
auto x76 = V{0.166666666666667}*cell[17];
auto x77 = x43*x56;
auto x78 = -x77;
auto x79 = V{0.166666666666667}*cell[1];
auto x80 = V{0.0833333333333333}*cell[18];
auto x81 = V{0.0833333333333333}*cell[9];
auto x82 = V{0.00231481481481481}*x22;
auto x83 = x62*x82;
auto x84 = x65*x82;
auto x85 = x80 - x81 + x83 - x84;
auto x86 = V{0.0833333333333333}*cell[15];
auto x87 = V{0.0833333333333333}*cell[6];
auto x88 = x49*x82;
auto x89 = x72*x82 + x86 - x87 - x88;
auto x90 = V{0.166666666666667}*cell[11];
auto x91 = x32*x36;
auto x92 = -x91;
auto x93 = V{0.166666666666667}*cell[7];
auto x94 = x31*x43;
auto x95 = -x93 + x94;
auto x96 = x90 + x92 + x95;
auto x97 = V{0.0277777777777778}*x22;
auto x98 = V{0.00925925925925926}*x27;
auto x99 = x76 + x78 + x79 + x98;
auto x100 = -x94;
auto x101 = x100 + x90 + x92 + x93;
auto x102 = x51*x82 - x86 + x87 + x88;
auto x103 = x23*(x101 + x102 + x39 + x85 + x99);
auto x104 = V{0.166666666666667}*cell[12];
auto x105 = -x104;
auto x106 = x30*x32;
auto x107 = V{0.0833333333333333}*cell[4];
auto x108 = V{0.0833333333333333}*cell[13];
auto x109 = x42*x82;
auto x110 = x45*x82;
auto x111 = x107 - x108 + x109 + x110;
auto x112 = x105 + x106 + x111;
auto x113 = -x76 + x77 + x79 + x98;
auto x114 = x37*x43;
auto x115 = V{0.166666666666667}*cell[5] - x114;
auto x116 = x115 + V{4.62592926927149e-18};
auto x117 = x23*(x112 + x113 + x116 + x52 + x85);
auto x118 = x104 - x106 + x115;
auto x119 = -x80 + x81 - x83 + x84;
auto x120 = x23*(x111 + x118 + x119 + x74 + x99);
auto x121 = -x107 + x108 - x109;
auto x122 = x23*(x102 + x105 + x106 - x110 + x116 + x121 + x67 + x96);
auto x123 = x24 + V{1};
auto x124 = -V{0.333333333333333}*cell[17] + x57;
auto x125 = x124 + V{-0.037037037037037};
auto x126 = -V{0.166666666666667}*cell[11] + x102 + x91;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = -V{0.0555555555555556}*x27 - x53 + V{-0.0555555555555556};
cell[2] = x23*(V{0.333333333333333}*cell[11] + x39 - x55 + x58 + x67 + x69) - x70*x71 + V{-0.0555555555555556};
cell[3] = x23*(V{0.333333333333333}*cell[12] + x43*x72 - x47 + x48 - x50 + x58 - x73 + x74 + x75) - x71*(x29 + V{-1}) + V{-0.0555555555555556};
cell[4] = x23*(-x25*x32 + x69 + x76 + x78 - x79 + x85 + x89 + x96) - x45*x97 + V{-0.0277777777777778};
cell[5] = -x103 + V{0.0277777777777778}*x22*x37 + V{-0.0277777777777778};
cell[6] = -x117 - x51*x97 + V{-0.0277777777777778};
cell[7] = -x120 + V{0.0277777777777778}*x22*x31 + V{-0.0277777777777778};
cell[8] = x23*(x101 + x118 + x121 + x58 + x68*x82 + x89 + V{0.037037037037037}) - x97*(x29 + x70) + V{-0.0277777777777778};
cell[9] = x122 + x62*x97 + V{-0.0277777777777778};
cell[10] = x123*x71 + x53 + V{-0.0555555555555556};
cell[11] = V{0.0555555555555556}*x22*x36 - x23*(V{0.333333333333333}*cell[11] + V{0.333333333333333}*cell[5] - x124 - x38 - x46 - x55 - x75 + V{0.037037037037037}) + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x30 - x23*(V{0.333333333333333}*cell[12] + V{0.333333333333333}*cell[7] - x125 - x33 - x52 - x67 - x73) + V{-0.0555555555555556};
cell[13] = V{0.0277777777777778}*x22*x42 - x23*(-x100 - x113 - x119 - x126 - x46 - x93) + V{-0.0277777777777778};
cell[14] = x103 + x97*(x123 + x61) + V{-0.0277777777777778};
cell[15] = x117 + x49*x97 + V{-0.0277777777777778};
cell[16] = x120 + x97*(x123 + x64) + V{-0.0277777777777778};
cell[17] = V{0.0277777777777778}*x22*x56 - x23*(V{0.166666666666667}*cell[5] - x112 - x114 - x125 - x126 - x95) + V{-0.0277777777777778};
cell[18] = -x122 + V{0.0277777777777778}*x22*x65 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
