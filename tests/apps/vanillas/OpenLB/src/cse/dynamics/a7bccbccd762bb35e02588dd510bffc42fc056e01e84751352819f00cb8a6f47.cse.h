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
struct CSE<AdvectionDiffusionEdgesDynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 2, 1, -1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x23 = x26 + V{-1};
auto x24 = V{0.166666666666667}*cell[13];
auto x25 = V{0.166666666666667}*cell[4];
auto x27 = V{3}*x20;
auto x28 = V{3}*x19;
auto x29 = x28 + V{-1};
auto x30 = x27 + x29;
auto x31 = -x30;
auto x32 = V{0.00462962962962963}*x22;
auto x33 = x28 + V{1};
auto x34 = x27 + x33;
auto x35 = x32*x34;
auto x36 = V{0.0185185185185185}*x22;
auto x37 = x33*x36;
auto x38 = V{3}*x21;
auto x39 = x33 + x38;
auto x40 = V{0.00925925925925926}*x22;
auto x41 = x39*x40;
auto x42 = V{0.333333333333333}*cell[15] - x41;
auto x43 = V{0.333333333333333}*cell[16];
auto x44 = -x38;
auto x45 = x33 + x44;
auto x46 = x40*x45;
auto x47 = x43 - x46;
auto x48 = -x27;
auto x49 = x33 + x48;
auto x50 = x40*x49;
auto x51 = V{0.333333333333333}*cell[14] - x50;
auto x52 = x51 + V{0.0462962962962963};
auto x53 = V{0.0555555555555556}*x22;
auto x54 = x27 + V{-1};
auto x55 = x38 + V{1};
auto x56 = x48 + x55;
auto x57 = x40*x56;
auto x58 = V{0.333333333333333}*cell[9] - x57;
auto x59 = V{0.333333333333333}*cell[8];
auto x60 = x38 + x54;
auto x61 = x40*x60 + x59;
auto x62 = -x24 + x25 + x30*x32 + x35;
auto x63 = x23*(V{0.333333333333333}*cell[2] + x36*x54 + x51 + x58 + x61 + x62 + V{0.0462962962962963});
auto x64 = V{0.166666666666667}*cell[3];
auto x65 = x38 + V{-1};
auto x66 = -x65;
auto x67 = -x60;
auto x68 = x40*x55;
auto x69 = -x43 + x46;
auto x70 = V{0.166666666666667}*cell[9];
auto x71 = x32*x56;
auto x72 = -x71;
auto x73 = V{0.166666666666667}*cell[15];
auto x74 = x32*x39;
auto x75 = -x73 + x74;
auto x76 = V{0.166666666666667}*cell[10];
auto x77 = x33*x40;
auto x78 = V{0.166666666666667}*cell[8];
auto x79 = x32*x60 + x78;
auto x80 = -x76 + x77 + x79;
auto x81 = V{0.166666666666667}*cell[2];
auto x82 = x40*x54;
auto x83 = V{0.166666666666667}*cell[16];
auto x84 = x32*x45;
auto x85 = x81 + x82 - x83 + x84;
auto x86 = x23*(x62 + x70 + x72 + x75 + x80 + x85 + V{4.62592926927149e-18});
auto x87 = V{0.0277777777777778}*x22;
auto x88 = -x77;
auto x89 = x70 + x72 + x76 + x88;
auto x90 = x81 + x82 + x83 - x84;
auto x91 = x73 - x74;
auto x92 = x23*(x52 + x79 + x89 + x90 + x91);
auto x93 = -x28;
auto x94 = x27 + V{1};
auto x95 = V{0.00231481481481481}*x22;
auto x96 = V{0.0833333333333333}*cell[12];
auto x97 = V{0.0833333333333333}*cell[3];
auto x98 = x32*x55;
auto x99 = x32*x49;
auto x100 = V{0.166666666666667}*cell[14] - x99;
auto x101 = x100 + x96 - x97 - x98;
auto x102 = V{0.0833333333333333}*cell[13];
auto x103 = V{0.0833333333333333}*cell[4];
auto x104 = x34*x95;
auto x105 = x102 - x103 - x104 + V{0.0231481481481481};
auto x106 = x30*x95;
auto x107 = -x96;
auto x108 = x32*x65;
auto x109 = x100 + x107 + x108 + x97 + x98;
auto x110 = -x70 + x71;
auto x111 = x23*(x105 - x106 + x109 + x110 + x47 + x76 + x79 + x88);
auto x112 = -x102 + x103 + x104 + x106;
auto x113 = x112 + V{0.0231481481481482};
auto x114 = x23*(x109 + x113 + x61 + x75 + x90);
auto x115 = x23*(x101 - x108 + x113 + x58 + x85 + x91);
auto x116 = -V{0.333333333333333}*cell[15] + x41;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = x23*(V{0.333333333333333}*cell[10] + x24 - x25 + x31*x32 - x35 - x37 + x42 + x47 + x52) - x29*x53 + V{-0.0555555555555556};
cell[2] = -x53*x54 - x63 + V{-0.0555555555555556};
cell[3] = x23*(V{0.166666666666667}*cell[12] + x40*x66 + x40*x67 + x42 + x58 - x59 - x64 - x68 + x69) - x53*x65 + V{-0.0555555555555556};
cell[4] = -x30*x87 - x86 + V{-0.0277777777777778};
cell[5] = x87*(x93 + x94) + x92 + V{-0.0277777777777778};
cell[6] = x23*(x101 + x105 + x31*x95 + x32*x66 + x32*x67 + x42 - x78 + x89) - x87*(x29 + x38) + V{-0.0277777777777778};
cell[7] = x111 + x87*(x55 + x93) + V{-0.0277777777777778};
cell[8] = -x114 - x60*x87 + V{-0.0277777777777778};
cell[9] = -x115 + V{0.0277777777777778}*x22*x56 + V{-0.0277777777777778};
cell[10] = V{0.0555555555555556}*x22*x33 - x23*(V{0.333333333333333}*cell[10] + V{0.333333333333333}*cell[14] - x116 - x37 - x50 - x62 - x69 + V{0.0462962962962963}) + V{-0.0555555555555556};
cell[11] = x53*x94 + x63 + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x55 - x23*(V{0.166666666666667}*cell[12] + V{0.333333333333333}*cell[9] - x116 - x40*x65 - x47 - x57 - x61 - x64 - x68) + V{-0.0555555555555556};
cell[13] = x34*x87 + x86 + V{-0.0277777777777778};
cell[14] = V{0.0277777777777778}*x22*x49 - x92 + V{-0.0277777777777778};
cell[15] = V{0.0277777777777778}*x22*x39 - x23*(V{0.166666666666667}*cell[14] - x107 - x108 - x110 - x112 - x116 - x80 - x97 - x98 - x99 + V{0.0231481481481481}) + V{-0.0277777777777778};
cell[16] = -x111 + V{0.0277777777777778}*x22*x45 + V{-0.0277777777777778};
cell[17] = x114 + x87*(x27 + x55) + V{-0.0277777777777778};
cell[18] = x115 + x87*(x44 + x94) + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
