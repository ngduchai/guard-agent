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
struct CSE<AdvectionDiffusionCornerDynamics3D<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, -1, 1, -1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x23 = x26 + V{-1};
auto x24 = V{3}*x19;
auto x25 = x24 + V{-1};
auto x27 = x22*x25;
auto x28 = V{3}*x21;
auto x29 = x25 + x28;
auto x30 = V{0.00925925925925926}*x22;
auto x31 = V{0.333333333333333}*cell[6] + x29*x30;
auto x32 = -x24;
auto x33 = V{3}*x20;
auto x34 = x33 + V{1};
auto x35 = x32 + x34;
auto x36 = x30*x35;
auto x37 = V{0.333333333333333}*cell[5] - x36 + V{0.037037037037037};
auto x38 = V{0.166666666666667}*cell[4];
auto x39 = V{0.166666666666667}*cell[13];
auto x40 = x24 + x34;
auto x41 = V{0.00462962962962963}*x22;
auto x42 = x40*x41;
auto x43 = x25 + x33;
auto x44 = x38 - x39 + x41*x43 + x42;
auto x45 = V{0.166666666666667}*cell[7];
auto x46 = V{0.166666666666667}*cell[16];
auto x47 = -x28;
auto x48 = x24 + V{1};
auto x49 = x47 + x48;
auto x50 = x41*x49;
auto x51 = x28 + V{1};
auto x52 = x32 + x51;
auto x53 = x41*x52;
auto x54 = x45 - x46 + x50 - x53;
auto x55 = x23*(V{0.333333333333333}*cell[1] + V{0.0185185185185185}*x27 + x31 + x37 + x44 + x54);
auto x56 = V{0.0185185185185185}*x22;
auto x57 = x34*x56;
auto x58 = x34 + x47;
auto x59 = x30*x58;
auto x60 = V{0.333333333333333}*cell[18] - x59;
auto x61 = -x43;
auto x62 = -x38 + x39 + x41*x61 - x42;
auto x63 = V{0.166666666666667}*cell[17];
auto x64 = V{0.166666666666667}*cell[8];
auto x65 = x33 + V{-1};
auto x66 = x28 + x65;
auto x67 = -x66;
auto x68 = x28 + x34;
auto x69 = x41*x68;
auto x70 = x41*x67 + x63 - x64 - x69;
auto x71 = V{0.0555555555555556}*x22;
auto x72 = x28 + V{-1};
auto x73 = x31 + V{0.037037037037037};
auto x74 = x41*x66 - x63 + x64 + x69;
auto x75 = x23*(V{0.333333333333333}*cell[3] - x45 + x46 - x50 + x53 + x56*x72 + x60 + x73 + x74);
auto x76 = V{0.0833333333333333}*cell[17];
auto x77 = V{0.166666666666667}*cell[18];
auto x78 = V{0.0833333333333333}*cell[8];
auto x79 = -x78;
auto x80 = V{0.00231481481481481}*x22;
auto x81 = x68*x80;
auto x82 = -x81;
auto x83 = x41*x58;
auto x84 = -x83;
auto x85 = V{0.166666666666667}*cell[1];
auto x86 = V{0.0833333333333333}*cell[16];
auto x87 = V{0.0833333333333333}*cell[7];
auto x88 = x52*x80;
auto x89 = x49*x80;
auto x90 = x86 - x87 + x88 - x89;
auto x91 = V{0.166666666666667}*cell[11];
auto x92 = x30*x34;
auto x93 = -x92;
auto x94 = V{0.166666666666667}*cell[6];
auto x95 = -x29*x41 + x91 + x93 - x94;
auto x96 = V{0.0277777777777778}*x22;
auto x97 = x25*x30;
auto x98 = x77 + x84 + x85 + x97;
auto x99 = x29*x41 + x94;
auto x100 = x91 + x93 + x99;
auto x101 = x66*x80;
auto x102 = -x101 + x76 + x79 + x82;
auto x103 = -x86 + x87 - x88 + x89;
auto x104 = x23*(x100 + x102 + x103 + x37 + x98);
auto x105 = V{0.166666666666667}*cell[3];
auto x106 = x30*x72;
auto x107 = x35*x41;
auto x108 = V{0.166666666666667}*cell[5] - x107;
auto x109 = x105 + x106 + x108;
auto x110 = x101 - x76 + x78 + x81;
auto x111 = V{0.0833333333333333}*cell[4];
auto x112 = V{0.0833333333333333}*cell[13];
auto x113 = x40*x80;
auto x114 = x43*x80;
auto x115 = x111 - x112 + x113 + x114;
auto x116 = x23*(x109 + x110 + x115 + x73 + x98);
auto x117 = -x77 + x83 + x85 + x97;
auto x118 = -x105 + x108 + V{4.62592926927149e-18};
auto x119 = x23*(x102 - x106 + x115 + x117 + x118 + x54);
auto x120 = -x111 + x112 - x113;
auto x121 = x23*(x100 + x109 - x114 + x120 + x60 + x90 + V{0.037037037037037});
auto x122 = -x33;
auto x123 = -V{0.166666666666667}*cell[11] + x92 + x99;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = -V{0.0555555555555556}*x27 - x55 + V{-0.0555555555555556};
cell[2] = x23*(V{0.333333333333333}*cell[11] + x37 - x57 + x60 + x62 + x70) - x65*x71 + V{-0.0555555555555556};
cell[3] = -x71*x72 - x75 + V{-0.0555555555555556};
cell[4] = x23*(-x25*x30 + x62 + x67*x80 + x76 + x77 + x79 + x82 + x84 - x85 + x90 + x95) - x43*x96 + V{-0.0277777777777778};
cell[5] = -x104 + V{0.0277777777777778}*x22*x35 + V{-0.0277777777777778};
cell[6] = -x116 - x29*x96 + V{-0.0277777777777778};
cell[7] = -x119 + V{0.0277777777777778}*x22*x52 + V{-0.0277777777777778};
cell[8] = x23*(x103 + x118 + x120 - x30*x72 + x61*x80 + x70 + x95) - x66*x96 + V{-0.0277777777777778};
cell[9] = x121 + x96*(x122 + x51) + V{-0.0277777777777778};
cell[10] = x48*x71 + x55 + V{-0.0555555555555556};
cell[11] = V{0.0555555555555556}*x22*x34 - x23*(V{0.333333333333333}*cell[11] + V{0.333333333333333}*cell[18] + V{0.333333333333333}*cell[5] - x36 - x44 - x57 - x59 - x74 + V{0.037037037037037}) + V{-0.0555555555555556};
cell[12] = x51*x71 + x75 + V{-0.0555555555555556};
cell[13] = V{0.0277777777777778}*x22*x40 - x23*(-x103 - x110 - x117 - x123 - x44) + V{-0.0277777777777778};
cell[14] = x104 + x96*(x122 + x48) + V{-0.0277777777777778};
cell[15] = x116 + x96*(x28 + x48) + V{-0.0277777777777778};
cell[16] = x119 + x49*x96 + V{-0.0277777777777778};
cell[17] = V{0.0277777777777778}*x22*x68 - x23*(V{0.166666666666667}*cell[5] - x105 - x106 - x107 - x115 - x123 - x74 - x90 + V{4.62592926927149e-18}) + V{-0.0277777777777778};
cell[18] = -x121 + V{0.0277777777777778}*x22*x58 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
