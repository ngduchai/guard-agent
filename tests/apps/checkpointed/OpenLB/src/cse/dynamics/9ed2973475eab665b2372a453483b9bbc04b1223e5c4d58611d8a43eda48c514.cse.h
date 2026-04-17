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
struct CSE<AdvectionDiffusionEdgesDynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 1, 1, 1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x23 = x26 + V{-1};
auto x24 = V{3}*x19;
auto x25 = x24 + V{1};
auto x27 = V{0.0185185185185185}*x22;
auto x28 = V{3}*x20;
auto x29 = x25 + x28;
auto x30 = V{0.00925925925925926}*x22;
auto x31 = x29*x30;
auto x32 = V{0.333333333333333}*cell[13] - x31;
auto x33 = V{0.333333333333333}*cell[14];
auto x34 = -x28;
auto x35 = x25 + x34;
auto x36 = x30*x35;
auto x37 = x33 - x36;
auto x38 = V{3}*x21;
auto x39 = x25 + x38;
auto x40 = V{0.333333333333333}*cell[15] - x30*x39;
auto x41 = V{0.166666666666667}*cell[16];
auto x42 = V{0.166666666666667}*cell[7];
auto x43 = -x24;
auto x44 = x38 + V{1};
auto x45 = x43 + x44;
auto x46 = V{0.00462962962962963}*x22;
auto x47 = x45*x46;
auto x48 = -x38;
auto x49 = x25 + x48;
auto x50 = x46*x49;
auto x51 = x41 - x42 + x47 - x50;
auto x52 = x23*(V{0.333333333333333}*cell[10] - x25*x27 + x32 + x37 + x40 + x51 + V{0.0462962962962963});
auto x53 = x24 + V{-1};
auto x54 = V{0.0555555555555556}*x22;
auto x55 = V{0.166666666666667}*cell[2];
auto x56 = V{0.333333333333333}*cell[9];
auto x57 = x28 + V{-1};
auto x58 = -x57;
auto x59 = x34 + x44;
auto x60 = x30*x59;
auto x61 = x28 + V{1};
auto x62 = x30*x61;
auto x63 = x38 + x61;
auto x64 = x30*x63;
auto x65 = V{0.333333333333333}*cell[17] - x64;
auto x66 = x56 - x60;
auto x67 = x40 + V{0.0462962962962963};
auto x68 = x23*(V{0.333333333333333}*cell[12] - x27*x44 - x41 + x42 - x47 + x50 + x65 + x66 + x67);
auto x69 = V{0.166666666666667}*cell[10];
auto x70 = V{0.166666666666667}*cell[17];
auto x71 = x46*x63;
auto x72 = x25*x30;
auto x73 = -x72;
auto x74 = x69 + x70 - x71 + x73;
auto x75 = V{0.166666666666667}*cell[9];
auto x76 = x46*x59;
auto x77 = -x75 + x76;
auto x78 = V{0.0833333333333333}*cell[11];
auto x79 = V{0.0833333333333333}*cell[2];
auto x80 = x46*x61;
auto x81 = x39*x46;
auto x82 = V{0.166666666666667}*cell[15] - x81;
auto x83 = x46*x58 + x78 - x79 - x80 + x82;
auto x84 = V{0.0833333333333333}*cell[16];
auto x85 = V{0.0833333333333333}*cell[7];
auto x86 = V{0.00231481481481481}*x22;
auto x87 = x45*x86;
auto x88 = x49*x86;
auto x89 = x84 - x85 + x87 - x88;
auto x90 = x89 + V{0.0231481481481482};
auto x91 = V{0.0277777777777778}*x22;
auto x92 = x75 - x76;
auto x93 = -x70 + x71;
auto x94 = x69 + x73 + x93;
auto x95 = x46*x57 - x78 + x79 + x80;
auto x96 = x82 + x95;
auto x97 = x23*(x37 + x90 + x92 + x94 + x96);
auto x98 = V{0.166666666666667}*cell[14];
auto x99 = x35*x46;
auto x100 = x98 - x99;
auto x101 = V{0.166666666666667}*cell[12];
auto x102 = V{0.166666666666667}*cell[13];
auto x103 = x29*x46;
auto x104 = -x103;
auto x105 = x30*x44;
auto x106 = -x105;
auto x107 = x101 + x102 + x104 + x106;
auto x108 = x23*(x100 + x107 + x67 + x74 + x92);
auto x109 = x100 - x101 + x105;
auto x110 = x23*(x102 + x104 + x109 + x51 + x77 + x94 + V{4.62592926927149e-18});
auto x111 = -x84 + x85 - x87 + x88;
auto x112 = x111 + V{0.0231481481481481};
auto x113 = -x102 + x103;
auto x114 = x23*(x100 + x101 + x106 + x112 + x113 + x66 + x96);
auto x115 = -V{0.333333333333333}*cell[13] + x31;
auto x116 = -V{0.333333333333333}*cell[17] + x64;
auto x117 = -V{0.166666666666667}*cell[15] + x81 + x95;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = x52 - x53*x54 + V{-0.0555555555555556};
cell[2] = x23*(V{0.166666666666667}*cell[11] + x30*x58 + x32 - x33 + x36 - x55 - x56 + x60 - x62 + x65) - x54*x57 + V{-0.0555555555555556};
cell[3] = -x54*(x38 + V{-1}) + x68 + V{-0.0555555555555556};
cell[4] = x23*(x32 + x74 + x77 + x83 + x90) - x91*(x28 + x53) + V{-0.0277777777777778};
cell[5] = x91*(x43 + x61) + x97 + V{-0.0277777777777778};
cell[6] = x108 - x91*(x38 + x53) + V{-0.0277777777777778};
cell[7] = x110 + x45*x91 + V{-0.0277777777777778};
cell[8] = x23*(x107 + x112 + x65 + x83 - x98 + x99) - x91*(x38 + x57) + V{-0.0277777777777778};
cell[9] = -x114 + V{0.0277777777777778}*x22*x59 + V{-0.0277777777777778};
cell[10] = V{0.0555555555555556}*x22*x25 - x52 + V{-0.0555555555555556};
cell[11] = V{0.0555555555555556}*x22*x61 - x23*(V{0.166666666666667}*cell[11] - x115 - x116 - x30*x57 - x37 - x55 - x62 - x66) + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x44 - x68 + V{-0.0555555555555556};
cell[13] = V{0.0277777777777778}*x22*x29 - x23*(V{0.166666666666667}*cell[10] - x111 - x115 - x117 - x72 - x92 - x93 + V{0.0231481481481482}) + V{-0.0277777777777778};
cell[14] = V{0.0277777777777778}*x22*x35 - x97 + V{-0.0277777777777778};
cell[15] = -x108 + V{0.0277777777777778}*x22*x39 + V{-0.0277777777777778};
cell[16] = -x110 + V{0.0277777777777778}*x22*x49 + V{-0.0277777777777778};
cell[17] = V{0.0277777777777778}*x22*x63 - x23*(-x109 - x113 - x116 - x117 - x89 + V{0.0231481481481481}) + V{-0.0277777777777778};
cell[18] = x114 + x91*(x48 + x61) + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
