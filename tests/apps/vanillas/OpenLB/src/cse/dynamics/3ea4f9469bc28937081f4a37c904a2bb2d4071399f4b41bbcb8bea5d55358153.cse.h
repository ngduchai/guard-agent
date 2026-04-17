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
struct CSE<AdvectionDiffusionCornerDynamics3D<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, -1, -1, -1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x23 = x26 + V{-1};
auto x24 = V{0.166666666666667}*cell[5];
auto x25 = V{0.166666666666667}*cell[7];
auto x27 = V{0.166666666666667}*cell[14];
auto x28 = V{0.166666666666667}*cell[16];
auto x29 = V{3}*x20;
auto x30 = -x29;
auto x31 = V{3}*x19;
auto x32 = x31 + V{1};
auto x33 = x30 + x32;
auto x34 = V{0.00462962962962963}*x22;
auto x35 = x33*x34;
auto x36 = V{3}*x21;
auto x37 = -x36;
auto x38 = x32 + x37;
auto x39 = x34*x38;
auto x40 = x31 + V{-1};
auto x41 = x22*x40;
auto x42 = -x31;
auto x43 = x29 + V{1};
auto x44 = x42 + x43;
auto x45 = x34*x44;
auto x46 = x36 + V{1};
auto x47 = x42 + x46;
auto x48 = x34*x47;
auto x49 = x36 + x40;
auto x50 = V{0.00925925925925926}*x22;
auto x51 = V{0.333333333333333}*cell[6] + x49*x50;
auto x52 = x29 + x40;
auto x53 = V{0.333333333333333}*cell[4] + x50*x52 + V{0.037037037037037};
auto x54 = x23*(V{0.333333333333333}*cell[1] + x24 + x25 - x27 - x28 + x35 + x39 + V{0.0185185185185185}*x41 - x45 - x48 + x51 + x53);
auto x55 = V{0.166666666666667}*cell[9];
auto x56 = V{0.166666666666667}*cell[18];
auto x57 = x37 + x43;
auto x58 = x34*x57;
auto x59 = x29 + V{-1};
auto x60 = x22*x59;
auto x61 = x30 + x46;
auto x62 = x34*x61;
auto x63 = x36 + x59;
auto x64 = V{0.333333333333333}*cell[8] + x50*x63;
auto x65 = -x24 + x27 - x35 + x45;
auto x66 = x23*(V{0.333333333333333}*cell[2] + x53 + x55 - x56 + x58 + V{0.0185185185185185}*x60 - x62 + x64 + x65);
auto x67 = x36 + V{-1};
auto x68 = x22*x67;
auto x69 = -x25 + x28 - x39 + x48;
auto x70 = -x55 + x56 - x58 + x62;
auto x71 = x23*(V{0.333333333333333}*cell[3] + x51 + x64 + V{0.0185185185185185}*x68 + x69 + x70 + V{0.037037037037037});
auto x72 = V{0.0833333333333333}*cell[7];
auto x73 = V{0.0833333333333333}*cell[16];
auto x74 = V{0.00231481481481481}*x22;
auto x75 = x38*x74;
auto x76 = x47*x74;
auto x77 = V{0.166666666666667}*cell[1];
auto x78 = x40*x50;
auto x79 = V{0.166666666666667}*cell[8] + x34*x63;
auto x80 = x77 + x78 + x79;
auto x81 = V{0.166666666666667}*cell[2];
auto x82 = x50*x59;
auto x83 = V{0.166666666666667}*cell[6];
auto x84 = x34*x49;
auto x85 = x83 + x84;
auto x86 = x81 + x82 + x85;
auto x87 = V{0.0833333333333333}*cell[9];
auto x88 = V{0.0833333333333333}*cell[18];
auto x89 = x57*x74;
auto x90 = x61*x74;
auto x91 = x87 - x88 + x89 - x90;
auto x92 = x23*(x53 + x72 - x73 + x75 - x76 + x80 + x86 + x91);
auto x93 = V{0.0277777777777778}*x22;
auto x94 = -x72 + x73 - x75 + x76;
auto x95 = -x77 - x78 + x79;
auto x96 = x23*(x65 + x81 + x82 - x83 - x84 + x91 + x94 + x95);
auto x97 = V{0.166666666666667}*cell[3];
auto x98 = V{0.166666666666667}*cell[4];
auto x99 = x34*x52;
auto x100 = x50*x67;
auto x101 = x100 + x97 + x98 + x99 + V{0.037037037037037};
auto x102 = -x87 + x88 - x89 + x90;
auto x103 = V{0.0833333333333333}*cell[5];
auto x104 = V{0.0833333333333333}*cell[14];
auto x105 = x33*x74;
auto x106 = x44*x74;
auto x107 = x103 - x104 + x105 - x106;
auto x108 = x23*(x101 + x102 + x107 + x51 + x80);
auto x109 = -x103 + x104 - x105 + x106;
auto x110 = x100 + x97 - x98 - x99 + V{4.62592926927149e-18};
auto x111 = x23*(x102 + x109 + x110 + x69 + x95);
auto x112 = x23*(x101 + x109 + x64 + x86 + x94);
auto x113 = x23*(x107 + x110 + x70 - x81 - x82 + x85 + x94);
auto x114 = V{0.0555555555555556}*x22;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = -V{0.0555555555555556}*x41 - x54 + V{-0.0555555555555556};
cell[2] = -V{0.0555555555555556}*x60 - x66 + V{-0.0555555555555556};
cell[3] = -V{0.0555555555555556}*x68 - x71 + V{-0.0555555555555556};
cell[4] = -x52*x93 - x92 + V{-0.0277777777777778};
cell[5] = x44*x93 + x96 + V{-0.0277777777777778};
cell[6] = -x108 - x49*x93 + V{-0.0277777777777778};
cell[7] = x111 + x47*x93 + V{-0.0277777777777778};
cell[8] = -x112 - x63*x93 + V{-0.0277777777777778};
cell[9] = x113 + x61*x93 + V{-0.0277777777777778};
cell[10] = x114*x32 + x54 + V{-0.0555555555555556};
cell[11] = x114*x43 + x66 + V{-0.0555555555555556};
cell[12] = x114*x46 + x71 + V{-0.0555555555555556};
cell[13] = x92 + x93*(x29 + x32) + V{-0.0277777777777778};
cell[14] = V{0.0277777777777778}*x22*x33 - x96 + V{-0.0277777777777778};
cell[15] = x108 + x93*(x32 + x36) + V{-0.0277777777777778};
cell[16] = -x111 + V{0.0277777777777778}*x22*x38 + V{-0.0277777777777778};
cell[17] = x112 + x93*(x36 + x43) + V{-0.0277777777777778};
cell[18] = -x113 + V{0.0277777777777778}*x22*x57 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
