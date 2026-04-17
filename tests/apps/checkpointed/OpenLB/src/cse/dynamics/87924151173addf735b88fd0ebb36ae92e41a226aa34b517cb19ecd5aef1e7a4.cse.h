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
struct CSE<AdvectionDiffusionCornerDynamics3D<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 1, 1, 1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x23 = x26 + V{-1};
auto x24 = V{3}*x19;
auto x25 = x24 + V{1};
auto x27 = V{0.0185185185185185}*x22;
auto x28 = V{3}*x21;
auto x29 = x25 + x28;
auto x30 = V{0.00925925925925926}*x22;
auto x31 = V{0.333333333333333}*cell[15] - x29*x30;
auto x32 = V{3}*x20;
auto x33 = x25 + x32;
auto x34 = V{0.333333333333333}*cell[13] - x30*x33 + V{0.037037037037037};
auto x35 = V{0.166666666666667}*cell[14];
auto x36 = V{0.166666666666667}*cell[5];
auto x37 = -x24;
auto x38 = x32 + V{1};
auto x39 = x37 + x38;
auto x40 = V{0.00462962962962963}*x22;
auto x41 = x39*x40;
auto x42 = -x32;
auto x43 = x25 + x42;
auto x44 = x40*x43;
auto x45 = x35 - x36 + x41 - x44;
auto x46 = V{0.166666666666667}*cell[16];
auto x47 = V{0.166666666666667}*cell[7];
auto x48 = x28 + V{1};
auto x49 = x37 + x48;
auto x50 = x40*x49;
auto x51 = -x28;
auto x52 = x25 + x51;
auto x53 = x40*x52;
auto x54 = x46 - x47 + x50 - x53;
auto x55 = x23*(V{0.333333333333333}*cell[10] - x25*x27 + x31 + x34 + x45 + x54);
auto x56 = x24 + V{-1};
auto x57 = V{0.0555555555555556}*x22;
auto x58 = x28 + x38;
auto x59 = V{0.333333333333333}*cell[17] - x30*x58;
auto x60 = V{0.166666666666667}*cell[18];
auto x61 = V{0.166666666666667}*cell[9];
auto x62 = x42 + x48;
auto x63 = x40*x62;
auto x64 = x38 + x51;
auto x65 = x40*x64;
auto x66 = x60 - x61 + x63 - x65;
auto x67 = x23*(V{0.333333333333333}*cell[11] - x27*x38 + x34 - x35 + x36 - x41 + x44 + x59 + x66);
auto x68 = x32 + V{-1};
auto x69 = x31 + V{0.037037037037037};
auto x70 = x23*(V{0.333333333333333}*cell[12] - x27*x48 - x46 + x47 - x50 + x53 + x59 - x60 + x61 - x63 + x65 + x69);
auto x71 = V{0.166666666666667}*cell[10];
auto x72 = V{0.166666666666667}*cell[17];
auto x73 = x40*x58;
auto x74 = -x25*x30;
auto x75 = x71 + x72 - x73 + x74;
auto x76 = V{0.166666666666667}*cell[11];
auto x77 = V{0.166666666666667}*cell[15];
auto x78 = x29*x40;
auto x79 = -x78;
auto x80 = x30*x38;
auto x81 = -x80;
auto x82 = x76 + x77 + x79 + x81;
auto x83 = V{0.0833333333333333}*cell[18];
auto x84 = V{0.0833333333333333}*cell[9];
auto x85 = V{0.00231481481481481}*x22;
auto x86 = x62*x85;
auto x87 = x64*x85;
auto x88 = x83 - x84 + x86 - x87;
auto x89 = V{0.0833333333333333}*cell[16];
auto x90 = V{0.0833333333333333}*cell[7];
auto x91 = x49*x85;
auto x92 = x52*x85;
auto x93 = x89 - x90 + x91 - x92;
auto x94 = x23*(x34 + x75 + x82 + x88 + x93);
auto x95 = V{0.0277777777777778}*x22;
auto x96 = -x83 + x84 - x86 + x87;
auto x97 = x71 - x72 + x73 + x74;
auto x98 = x23*(x45 - x76 + x77 + x79 + x80 + x93 + x96 + x97);
auto x99 = V{0.166666666666667}*cell[12];
auto x100 = x30*x48;
auto x101 = V{0.166666666666667}*cell[13] - x33*x40;
auto x102 = -x100 + x101 + x99;
auto x103 = V{0.0833333333333333}*cell[14];
auto x104 = V{0.0833333333333333}*cell[5];
auto x105 = x39*x85;
auto x106 = x43*x85;
auto x107 = x103 - x104 + x105 - x106;
auto x108 = x23*(x102 + x107 + x69 + x75 + x96);
auto x109 = x100 + x101 - x99 + V{4.62592926927149e-18};
auto x110 = x23*(x107 + x109 + x54 + x88 + x97);
auto x111 = -x103 + x104 - x105 + x106;
auto x112 = x23*(x102 + x111 + x59 + x82 - x89 + x90 - x91 + x92 + V{0.037037037037037});
auto x113 = x23*(x109 + x111 + x66 + x76 - x77 + x78 + x81 + x93);
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = x55 - x56*x57 + V{-0.0555555555555556};
cell[2] = -x57*x68 + x67 + V{-0.0555555555555556};
cell[3] = -x57*(x28 + V{-1}) + x70 + V{-0.0555555555555556};
cell[4] = x94 - x95*(x32 + x56) + V{-0.0277777777777778};
cell[5] = x39*x95 + x98 + V{-0.0277777777777778};
cell[6] = x108 - x95*(x28 + x56) + V{-0.0277777777777778};
cell[7] = x110 + x49*x95 + V{-0.0277777777777778};
cell[8] = x112 - x95*(x28 + x68) + V{-0.0277777777777778};
cell[9] = x113 + x62*x95 + V{-0.0277777777777778};
cell[10] = V{0.0555555555555556}*x22*x25 - x55 + V{-0.0555555555555556};
cell[11] = V{0.0555555555555556}*x22*x38 - x67 + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x48 - x70 + V{-0.0555555555555556};
cell[13] = V{0.0277777777777778}*x22*x33 - x94 + V{-0.0277777777777778};
cell[14] = V{0.0277777777777778}*x22*x43 - x98 + V{-0.0277777777777778};
cell[15] = -x108 + V{0.0277777777777778}*x22*x29 + V{-0.0277777777777778};
cell[16] = -x110 + V{0.0277777777777778}*x22*x52 + V{-0.0277777777777778};
cell[17] = -x112 + V{0.0277777777777778}*x22*x58 + V{-0.0277777777777778};
cell[18] = -x113 + V{0.0277777777777778}*x22*x64 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
