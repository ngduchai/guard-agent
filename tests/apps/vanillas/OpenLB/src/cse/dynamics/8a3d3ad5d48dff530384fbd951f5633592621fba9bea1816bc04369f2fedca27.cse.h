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
struct CSE<AdvectionDiffusionEdgesDynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 0, -1, -1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x23 = x26 + V{-1};
auto x24 = V{0.166666666666667}*cell[1];
auto x25 = V{0.333333333333333}*cell[4];
auto x27 = V{0.333333333333333}*cell[6];
auto x28 = V{3}*x19;
auto x29 = x28 + V{-1};
auto x30 = V{0.00925925925925926}*x22;
auto x31 = V{3}*x20;
auto x32 = x29 + x31;
auto x33 = V{3}*x21;
auto x34 = x29 + x33;
auto x35 = x28 + V{1};
auto x36 = x30*x35;
auto x37 = -x31;
auto x38 = x35 + x37;
auto x39 = x30*x38;
auto x40 = V{0.333333333333333}*cell[14] - x39;
auto x41 = -x33;
auto x42 = x35 + x41;
auto x43 = x30*x42;
auto x44 = V{0.333333333333333}*cell[16] - x43;
auto x45 = V{0.0555555555555556}*x22;
auto x46 = V{0.166666666666667}*cell[9];
auto x47 = V{0.166666666666667}*cell[18];
auto x48 = x31 + V{1};
auto x49 = x41 + x48;
auto x50 = V{0.00462962962962963}*x22;
auto x51 = x49*x50;
auto x52 = x31 + V{-1};
auto x53 = V{0.0185185185185185}*x22;
auto x54 = x33 + V{1};
auto x55 = x37 + x54;
auto x56 = x50*x55;
auto x57 = x25 + x30*x32;
auto x58 = x33 + x52;
auto x59 = V{0.333333333333333}*cell[8] + x30*x58;
auto x60 = x59 + V{0.0462962962962963};
auto x61 = x23*(V{0.333333333333333}*cell[2] + x40 + x46 - x47 + x51 + x52*x53 - x56 + x57 + x60);
auto x62 = x33 + V{-1};
auto x63 = x27 + x30*x34;
auto x64 = -x46 + x47 - x51 + x56;
auto x65 = x23*(V{0.333333333333333}*cell[3] + x44 + x53*x62 + x59 + x63 + x64 + V{0.0462962962962963});
auto x66 = V{0.166666666666667}*cell[16];
auto x67 = x42*x50;
auto x68 = V{0.166666666666667}*cell[2];
auto x69 = V{0.166666666666667}*cell[6];
auto x70 = x34*x50;
auto x71 = x30*x52;
auto x72 = x68 + x69 + x70 + x71;
auto x73 = V{0.0833333333333333}*cell[1];
auto x74 = V{0.0833333333333333}*cell[10];
auto x75 = x35*x50;
auto x76 = x29*x50;
auto x77 = V{0.166666666666667}*cell[8] + x50*x58;
auto x78 = x73 - x74 + x75 + x76 + x77;
auto x79 = V{0.0833333333333333}*cell[9];
auto x80 = V{0.0833333333333333}*cell[18];
auto x81 = V{0.00231481481481481}*x22;
auto x82 = x49*x81;
auto x83 = x55*x81;
auto x84 = x79 - x80 + x82 - x83 + V{0.0231481481481481};
auto x85 = x23*(x57 - x66 + x67 + x72 + x78 + x84);
auto x86 = V{0.0277777777777778}*x22;
auto x87 = x66 - x67;
auto x88 = -x73 + x74 - x75 - x76 + x77;
auto x89 = x23*(x40 + x68 - x69 - x70 + x71 + x84 + x87 + x88);
auto x90 = -x28;
auto x91 = V{0.166666666666667}*cell[3];
auto x92 = V{0.166666666666667}*cell[4];
auto x93 = x32*x50;
auto x94 = x30*x62;
auto x95 = x91 + x92 + x93 + x94;
auto x96 = V{0.166666666666667}*cell[14];
auto x97 = x38*x50;
auto x98 = -x96 + x97;
auto x99 = -x79 + x80 - x82 + x83 + V{0.0231481481481482};
auto x100 = x23*(x63 + x78 + x95 + x98 + x99);
auto x101 = x96 - x97;
auto x102 = x91 - x92 - x93 + x94;
auto x103 = x23*(x101 + x102 + x44 + x88 + x99);
auto x104 = x23*(x101 + x60 + x72 + x87 + x95);
auto x105 = x23*(x102 + x64 - x68 + x69 + x70 - x71 + x87 + x98 + V{4.62592926927149e-18});
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = x23*(V{0.166666666666667}*cell[10] - x24 - x25 - x27 - x29*x30 - x30*x32 - x30*x34 - x36 + x40 + x44) - x29*x45 + V{-0.0555555555555556};
cell[2] = -x45*x52 - x61 + V{-0.0555555555555556};
cell[3] = -x45*x62 - x65 + V{-0.0555555555555556};
cell[4] = -x32*x86 - x85 + V{-0.0277777777777778};
cell[5] = x86*(x48 + x90) + x89 + V{-0.0277777777777778};
cell[6] = -x100 - x34*x86 + V{-0.0277777777777778};
cell[7] = x103 + x86*(x54 + x90) + V{-0.0277777777777778};
cell[8] = -x104 - x58*x86 + V{-0.0277777777777778};
cell[9] = x105 + x55*x86 + V{-0.0277777777777778};
cell[10] = V{0.0555555555555556}*x22*x35 - x23*(V{0.166666666666667}*cell[10] + V{0.333333333333333}*cell[14] + V{0.333333333333333}*cell[16] - x24 - x29*x30 - x36 - x39 - x43 - x57 - x63) + V{-0.0555555555555556};
cell[11] = x45*x48 + x61 + V{-0.0555555555555556};
cell[12] = x45*x54 + x65 + V{-0.0555555555555556};
cell[13] = x85 + x86*(x31 + x35) + V{-0.0277777777777778};
cell[14] = V{0.0277777777777778}*x22*x38 - x89 + V{-0.0277777777777778};
cell[15] = x100 + x86*(x33 + x35) + V{-0.0277777777777778};
cell[16] = -x103 + V{0.0277777777777778}*x22*x42 + V{-0.0277777777777778};
cell[17] = x104 + x86*(x33 + x48) + V{-0.0277777777777778};
cell[18] = -x105 + V{0.0277777777777778}*x22*x49 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
