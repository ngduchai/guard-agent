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
struct CSE<AdvectionDiffusionEdgesDynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 2, 1, 1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x23 = x26 + V{-1};
auto x24 = V{3}*x19;
auto x25 = x24 + V{1};
auto x27 = V{0.0185185185185185}*x22;
auto x28 = V{3}*x21;
auto x29 = x25 + x28;
auto x30 = V{0.00925925925925926}*x22;
auto x31 = x29*x30;
auto x32 = V{0.333333333333333}*cell[15] - x31;
auto x33 = V{0.333333333333333}*cell[16];
auto x34 = -x28;
auto x35 = x25 + x34;
auto x36 = x30*x35;
auto x37 = x33 - x36;
auto x38 = V{3}*x20;
auto x39 = x25 + x38;
auto x40 = V{0.333333333333333}*cell[13] - x30*x39 + V{0.0462962962962963};
auto x41 = V{0.166666666666667}*cell[14];
auto x42 = V{0.166666666666667}*cell[5];
auto x43 = -x24;
auto x44 = x38 + V{1};
auto x45 = x43 + x44;
auto x46 = V{0.00462962962962963}*x22;
auto x47 = x45*x46;
auto x48 = -x38;
auto x49 = x25 + x48;
auto x50 = x46*x49;
auto x51 = x41 - x42 + x47 - x50;
auto x52 = x23*(V{0.333333333333333}*cell[10] - x25*x27 + x32 + x37 + x40 + x51);
auto x53 = x24 + V{-1};
auto x54 = V{0.0555555555555556}*x22;
auto x55 = x28 + x44;
auto x56 = x30*x55;
auto x57 = V{0.333333333333333}*cell[17] - x56;
auto x58 = V{0.333333333333333}*cell[18];
auto x59 = x34 + x44;
auto x60 = x30*x59;
auto x61 = x58 - x60;
auto x62 = x23*(V{0.333333333333333}*cell[11] - x27*x44 + x40 - x41 + x42 - x47 + x50 + x57 + x61);
auto x63 = x38 + V{-1};
auto x64 = V{0.166666666666667}*cell[3];
auto x65 = x28 + V{-1};
auto x66 = -x65;
auto x67 = x28 + V{1};
auto x68 = x30*x67;
auto x69 = V{0.166666666666667}*cell[18];
auto x70 = x46*x59;
auto x71 = x69 - x70;
auto x72 = V{0.166666666666667}*cell[16];
auto x73 = x35*x46;
auto x74 = x72 - x73;
auto x75 = V{0.166666666666667}*cell[10];
auto x76 = V{0.166666666666667}*cell[17];
auto x77 = x46*x55;
auto x78 = x25*x30;
auto x79 = -x78;
auto x80 = x75 + x76 - x77 + x79;
auto x81 = V{0.166666666666667}*cell[11];
auto x82 = V{0.166666666666667}*cell[15];
auto x83 = x29*x46;
auto x84 = -x83;
auto x85 = x30*x44;
auto x86 = -x85;
auto x87 = x81 + x82 + x84 + x86;
auto x88 = x23*(x40 + x71 + x74 + x80 + x87);
auto x89 = V{0.0277777777777778}*x22;
auto x90 = -x69 + x70;
auto x91 = x74 - x81 + x85;
auto x92 = -x76 + x77;
auto x93 = x75 + x79 + x92;
auto x94 = x23*(x51 + x82 + x84 + x90 + x91 + x93);
auto x95 = x39*x46;
auto x96 = V{0.166666666666667}*cell[13] - x95 + V{0.0231481481481481};
auto x97 = V{0.0833333333333333}*cell[14];
auto x98 = V{0.0833333333333333}*cell[5];
auto x99 = V{0.00231481481481481}*x22;
auto x100 = x45*x99;
auto x101 = x49*x99;
auto x102 = x100 - x101 + x97 - x98;
auto x103 = x102 + x96;
auto x104 = V{0.0833333333333333}*cell[12];
auto x105 = V{0.0833333333333333}*cell[3];
auto x106 = x46*x67;
auto x107 = x104 - x105 - x106 + x46*x66;
auto x108 = -x104 + x105 + x106 + x46*x65;
auto x109 = x108 + x71;
auto x110 = x23*(x103 + x109 + x37 + x93);
auto x111 = -x100 + x101 - x97 + x98;
auto x112 = x111 + x96;
auto x113 = x108 - x82 + x83;
auto x114 = x23*(x112 + x113 + x61 + x74 + x81 + x86);
auto x115 = -V{0.333333333333333}*cell[15] + x31;
auto x116 = -V{0.333333333333333}*cell[17] + x56;
auto x117 = -V{0.166666666666667}*cell[13] + x95 + V{-0.0231481481481481};
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = x52 - x53*x54 + V{-0.0555555555555556};
cell[2] = -x54*x63 + x62 + V{-0.0555555555555556};
cell[3] = x23*(V{0.166666666666667}*cell[12] + x30*x66 + x32 - x33 + x36 + x57 - x58 + x60 - x64 - x68) - x54*x65 + V{-0.0555555555555556};
cell[4] = x88 - x89*(x38 + x53) + V{-0.0277777777777778};
cell[5] = x45*x89 + x94 + V{-0.0277777777777778};
cell[6] = x23*(x103 + x107 + x32 + x80 + x90) - x89*(x28 + x53) + V{-0.0277777777777778};
cell[7] = x110 + x89*(x43 + x67) + V{-0.0277777777777778};
cell[8] = x23*(x107 + x112 + x57 - x72 + x73 + x87) - x89*(x28 + x63) + V{-0.0277777777777778};
cell[9] = x114 + x89*(x48 + x67) + V{-0.0277777777777778};
cell[10] = V{0.0555555555555556}*x22*x25 - x52 + V{-0.0555555555555556};
cell[11] = V{0.0555555555555556}*x22*x44 - x62 + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x67 - x23*(V{0.166666666666667}*cell[12] - x115 - x116 - x30*x65 - x37 - x61 - x64 - x68) + V{-0.0555555555555556};
cell[13] = V{0.0277777777777778}*x22*x39 - x88 + V{-0.0277777777777778};
cell[14] = V{0.0277777777777778}*x22*x49 - x94 + V{-0.0277777777777778};
cell[15] = V{0.0277777777777778}*x22*x29 - x23*(V{0.166666666666667}*cell[10] - x109 - x111 - x115 - x117 - x78 - x92) + V{-0.0277777777777778};
cell[16] = -x110 + V{0.0277777777777778}*x22*x35 + V{-0.0277777777777778};
cell[17] = V{0.0277777777777778}*x22*x55 - x23*(-x102 - x113 - x116 - x117 - x91) + V{-0.0277777777777778};
cell[18] = -x114 + V{0.0277777777777778}*x22*x59 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
