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
struct CSE<AdvectionDiffusionEdgesDynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 0, 1, 1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x23 = x26 + V{-1};
auto x24 = V{0.166666666666667}*cell[1];
auto x25 = V{0.333333333333333}*cell[5];
auto x27 = V{0.333333333333333}*cell[7];
auto x28 = V{3}*x19;
auto x29 = x28 + V{-1};
auto x30 = -x29;
auto x31 = V{0.00925925925925926}*x22;
auto x32 = -x28;
auto x33 = V{3}*x20;
auto x34 = x33 + V{1};
auto x35 = x32 + x34;
auto x36 = x31*x35;
auto x37 = V{3}*x21;
auto x38 = x37 + V{1};
auto x39 = x32 + x38;
auto x40 = x31*x39;
auto x41 = x28 + V{1};
auto x42 = x31*x41;
auto x43 = x33 + x41;
auto x44 = x31*x43;
auto x45 = V{0.333333333333333}*cell[13] - x44;
auto x46 = x37 + x41;
auto x47 = x31*x46;
auto x48 = V{0.333333333333333}*cell[15] - x47;
auto x49 = V{0.0555555555555556}*x22;
auto x50 = V{0.0185185185185185}*x22;
auto x51 = x25 - x36;
auto x52 = x34 + x37;
auto x53 = V{0.333333333333333}*cell[17] - x31*x52;
auto x54 = V{0.166666666666667}*cell[18];
auto x55 = V{0.166666666666667}*cell[9];
auto x56 = -x33;
auto x57 = x38 + x56;
auto x58 = V{0.00462962962962963}*x22;
auto x59 = x57*x58;
auto x60 = -x37;
auto x61 = x34 + x60;
auto x62 = x58*x61;
auto x63 = x54 - x55 + x59 - x62;
auto x64 = x23*(V{0.333333333333333}*cell[11] - x34*x50 + x45 + x51 + x53 + x63 + V{0.0462962962962963});
auto x65 = x33 + V{-1};
auto x66 = x27 - x40;
auto x67 = x53 + V{0.0462962962962963};
auto x68 = x23*(V{0.333333333333333}*cell[12] - x38*x50 + x48 - x54 + x55 - x59 + x62 + x66 + x67);
auto x69 = V{0.166666666666667}*cell[11];
auto x70 = V{0.166666666666667}*cell[15];
auto x71 = x46*x58;
auto x72 = x31*x34;
auto x73 = -x72;
auto x74 = x69 + x70 - x71 + x73;
auto x75 = V{0.166666666666667}*cell[7];
auto x76 = x39*x58;
auto x77 = -x75 + x76;
auto x78 = V{0.0833333333333333}*cell[10];
auto x79 = V{0.0833333333333333}*cell[1];
auto x80 = x41*x58;
auto x81 = x52*x58;
auto x82 = V{0.166666666666667}*cell[17] - x81;
auto x83 = x30*x58 + x78 - x79 - x80 + x82;
auto x84 = V{0.0833333333333333}*cell[18];
auto x85 = V{0.0833333333333333}*cell[9];
auto x86 = V{0.00231481481481481}*x22;
auto x87 = x57*x86;
auto x88 = x61*x86;
auto x89 = x84 - x85 + x87 - x88;
auto x90 = x89 + V{0.0231481481481482};
auto x91 = V{0.0277777777777778}*x22;
auto x92 = x75 - x76;
auto x93 = -x70 + x71;
auto x94 = x69 + x73 + x93;
auto x95 = x29*x58 - x78 + x79 + x80;
auto x96 = x82 + x95;
auto x97 = x23*(x51 + x90 + x92 + x94 + x96);
auto x98 = V{0.166666666666667}*cell[5];
auto x99 = x35*x58;
auto x100 = V{0.166666666666667}*cell[12];
auto x101 = V{0.166666666666667}*cell[13];
auto x102 = x43*x58;
auto x103 = -x102;
auto x104 = x31*x38;
auto x105 = -x104;
auto x106 = x100 + x101 + x103 + x105;
auto x107 = -x84 + x85 - x87 + x88;
auto x108 = x107 + V{0.0231481481481481};
auto x109 = x98 - x99;
auto x110 = -x101 + x102;
auto x111 = x23*(x100 + x105 + x108 + x109 + x110 + x66 + x96);
auto x112 = x23*(x106 + x109 + x67 + x74 + x92);
auto x113 = -x100 + x104 + x109;
auto x114 = x23*(x101 + x103 + x113 + x63 + x77 + x94 + V{4.62592926927149e-18});
auto x115 = -V{0.333333333333333}*cell[13] + x44;
auto x116 = -V{0.333333333333333}*cell[15] + x47;
auto x117 = -V{0.166666666666667}*cell[17] + x81 + x95;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = x23*(V{0.166666666666667}*cell[10] - x24 - x25 - x27 + x30*x31 + x36 + x40 - x42 + x45 + x48) - x29*x49 + V{-0.0555555555555556};
cell[2] = -x49*x65 + x64 + V{-0.0555555555555556};
cell[3] = -x49*(x37 + V{-1}) + x68 + V{-0.0555555555555556};
cell[4] = x23*(x45 + x74 + x77 + x83 + x90) - x91*(x29 + x33) + V{-0.0277777777777778};
cell[5] = V{0.0277777777777778}*x22*x35 - x97 + V{-0.0277777777777778};
cell[6] = x23*(x106 + x108 + x48 + x83 - x98 + x99) - x91*(x29 + x37) + V{-0.0277777777777778};
cell[7] = -x111 + V{0.0277777777777778}*x22*x39 + V{-0.0277777777777778};
cell[8] = x112 - x91*(x37 + x65) + V{-0.0277777777777778};
cell[9] = x114 + x57*x91 + V{-0.0277777777777778};
cell[10] = V{0.0555555555555556}*x22*x41 - x23*(V{0.166666666666667}*cell[10] - x115 - x116 - x24 - x29*x31 - x42 - x51 - x66) + V{-0.0555555555555556};
cell[11] = V{0.0555555555555556}*x22*x34 - x64 + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x38 - x68 + V{-0.0555555555555556};
cell[13] = V{0.0277777777777778}*x22*x43 - x23*(V{0.166666666666667}*cell[11] - x107 - x115 - x117 - x72 - x92 - x93 + V{0.0231481481481482}) + V{-0.0277777777777778};
cell[14] = x91*(x41 + x56) + x97 + V{-0.0277777777777778};
cell[15] = V{0.0277777777777778}*x22*x46 - x23*(-x110 - x113 - x116 - x117 - x89 + V{0.0231481481481481}) + V{-0.0277777777777778};
cell[16] = x111 + x91*(x41 + x60) + V{-0.0277777777777778};
cell[17] = -x112 + V{0.0277777777777778}*x22*x52 + V{-0.0277777777777778};
cell[18] = -x114 + V{0.0277777777777778}*x22*x61 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
