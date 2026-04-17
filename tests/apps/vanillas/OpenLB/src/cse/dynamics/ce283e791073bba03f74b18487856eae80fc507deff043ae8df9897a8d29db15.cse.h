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
struct CSE<AdvectionDiffusionCornerDynamics3D<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 1, 1, -1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x23 = x26 + V{-1};
auto x24 = V{3}*x19;
auto x25 = x24 + V{1};
auto x27 = V{0.0185185185185185}*x22;
auto x28 = x25*x27;
auto x29 = V{3}*x20;
auto x30 = x25 + x29;
auto x31 = V{0.00925925925925926}*x22;
auto x32 = x30*x31;
auto x33 = V{0.333333333333333}*cell[13] - x32;
auto x34 = V{3}*x21;
auto x35 = -x34;
auto x36 = x25 + x35;
auto x37 = x31*x36;
auto x38 = V{0.333333333333333}*cell[16] - x37 + V{0.037037037037037};
auto x39 = V{0.166666666666667}*cell[14];
auto x40 = V{0.166666666666667}*cell[5];
auto x41 = -x24;
auto x42 = x29 + V{1};
auto x43 = x41 + x42;
auto x44 = V{0.00462962962962963}*x22;
auto x45 = x43*x44;
auto x46 = -x29;
auto x47 = x25 + x46;
auto x48 = x44*x47;
auto x49 = x39 - x40 + x45 - x48;
auto x50 = V{0.166666666666667}*cell[15];
auto x51 = V{0.166666666666667}*cell[6];
auto x52 = x24 + V{-1};
auto x53 = x34 + x52;
auto x54 = -x53;
auto x55 = x25 + x34;
auto x56 = x44*x55;
auto x57 = x44*x54 + x50 - x51 - x56;
auto x58 = V{0.0555555555555556}*x22;
auto x59 = V{0.166666666666667}*cell[17];
auto x60 = V{0.166666666666667}*cell[8];
auto x61 = x29 + V{-1};
auto x62 = x34 + x61;
auto x63 = -x62;
auto x64 = x34 + x42;
auto x65 = x44*x64;
auto x66 = x27*x42;
auto x67 = x35 + x42;
auto x68 = x31*x67;
auto x69 = V{0.333333333333333}*cell[18] - x68;
auto x70 = x33 + V{0.037037037037037};
auto x71 = -x39 + x40 - x45 + x48;
auto x72 = x34 + V{-1};
auto x73 = x44*x53 - x50 + x51 + x56;
auto x74 = x44*x62 - x59 + x60 + x65;
auto x75 = x23*(V{0.333333333333333}*cell[3] + x27*x72 + x38 + x69 + x73 + x74);
auto x76 = V{0.00231481481481481}*x22;
auto x77 = V{0.166666666666667}*cell[10];
auto x78 = x25*x31;
auto x79 = -x78;
auto x80 = V{0.166666666666667}*cell[18];
auto x81 = x44*x67;
auto x82 = x80 - x81;
auto x83 = x77 + x79 + x82;
auto x84 = V{0.166666666666667}*cell[11];
auto x85 = x31*x42;
auto x86 = x36*x44;
auto x87 = V{0.166666666666667}*cell[16] - x86;
auto x88 = x84 - x85 + x87;
auto x89 = V{0.0833333333333333}*cell[17];
auto x90 = V{0.0833333333333333}*cell[8];
auto x91 = x64*x76;
auto x92 = x63*x76 + x89 - x90 - x91;
auto x93 = V{0.0833333333333333}*cell[15];
auto x94 = V{0.0833333333333333}*cell[6];
auto x95 = x55*x76;
auto x96 = x93 - x94 - x95;
auto x97 = V{0.0277777777777778}*x22;
auto x98 = -x84;
auto x99 = x53*x76;
auto x100 = x62*x76 - x89 + x90 + x91;
auto x101 = -x80 + x81;
auto x102 = x101 + x77 + x79;
auto x103 = x87 + V{4.62592926927149e-18};
auto x104 = x23*(x100 + x102 + x103 + x49 + x85 + x96 + x98 - x99);
auto x105 = V{0.166666666666667}*cell[13];
auto x106 = x30*x44;
auto x107 = -x106;
auto x108 = V{0.166666666666667}*cell[3];
auto x109 = V{0.0833333333333333}*cell[14];
auto x110 = V{0.0833333333333333}*cell[5];
auto x111 = x43*x76;
auto x112 = x47*x76;
auto x113 = x109 - x110 + x111 - x112;
auto x114 = x31*x72;
auto x115 = x105 + x107 + x108 + x114;
auto x116 = x23*(x100 + x113 + x115 + x38 + x83);
auto x117 = x34 + V{1};
auto x118 = -x93 + x94 + x95 + x99;
auto x119 = x118 + x85 + x98;
auto x120 = -x105 + x106 + x108 + x114;
auto x121 = x23*(x103 + x113 + x119 + x120 + x74);
auto x122 = -x109 + x110 - x111 + x112;
auto x123 = x23*(x115 + x118 + x122 + x69 + x88 + V{0.037037037037037});
auto x124 = -V{0.333333333333333}*cell[13] + x32;
auto x125 = x124 + V{-0.037037037037037};
auto x126 = -V{0.166666666666667}*cell[10] + x100 + x78;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = x23*(V{0.333333333333333}*cell[10] - x28 + x33 + x38 + x49 + x57) - x52*x58 + V{-0.0555555555555556};
cell[2] = x23*(V{0.333333333333333}*cell[11] + x44*x63 + x59 - x60 - x65 - x66 + x69 + x70 + x71) - x58*x61 + V{-0.0555555555555556};
cell[3] = -x58*x72 - x75 + V{-0.0555555555555556};
cell[4] = x23*(x54*x76 + x70 + x83 + x88 + x92 + x96) - x97*(x29 + x52) + V{-0.0277777777777778};
cell[5] = x104 + x43*x97 + V{-0.0277777777777778};
cell[6] = x23*(x102 + x105 + x107 - x108 + x113 - x31*x72 + x57 + x92) - x53*x97 + V{-0.0277777777777778};
cell[7] = x116 + x97*(x117 + x41) + V{-0.0277777777777778};
cell[8] = -x121 - x62*x97 + V{-0.0277777777777778};
cell[9] = x123 + x97*(x117 + x46) + V{-0.0277777777777778};
cell[10] = V{0.0555555555555556}*x22*x25 - x23*(V{0.333333333333333}*cell[10] + V{0.333333333333333}*cell[16] - x124 - x28 - x37 - x71 - x73 + V{0.037037037037037}) + V{-0.0555555555555556};
cell[11] = V{0.0555555555555556}*x22*x42 - x23*(V{0.333333333333333}*cell[11] + V{0.333333333333333}*cell[18] - x125 - x49 - x66 - x68 - x74) + V{-0.0555555555555556};
cell[12] = x117*x58 + x75 + V{-0.0555555555555556};
cell[13] = V{0.0277777777777778}*x22*x30 - x23*(V{0.166666666666667}*cell[16] - x101 - x119 - x125 - x126 - x86) + V{-0.0277777777777778};
cell[14] = -x104 + V{0.0277777777777778}*x22*x47 + V{-0.0277777777777778};
cell[15] = V{0.0277777777777778}*x22*x55 - x23*(-x120 - x122 - x126 - x73 - x82) + V{-0.0277777777777778};
cell[16] = -x116 + V{0.0277777777777778}*x22*x36 + V{-0.0277777777777778};
cell[17] = x121 + x64*x97 + V{-0.0277777777777778};
cell[18] = -x123 + V{0.0277777777777778}*x22*x67 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
