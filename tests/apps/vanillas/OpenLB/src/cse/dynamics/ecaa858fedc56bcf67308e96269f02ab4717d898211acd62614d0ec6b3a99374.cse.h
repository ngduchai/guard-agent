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
struct CSE<AdvectionDiffusionEdgesDynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 2, -1, -1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x23 = x26 + V{-1};
auto x24 = V{0.166666666666667}*cell[5];
auto x25 = V{0.166666666666667}*cell[14];
auto x27 = V{3}*x20;
auto x28 = -x27;
auto x29 = V{3}*x19;
auto x30 = x29 + V{1};
auto x31 = x28 + x30;
auto x32 = V{0.00462962962962963}*x22;
auto x33 = x31*x32;
auto x34 = x29 + V{-1};
auto x35 = x22*x34;
auto x36 = -x29;
auto x37 = x27 + V{1};
auto x38 = x36 + x37;
auto x39 = x32*x38;
auto x40 = V{3}*x21;
auto x41 = x40 + V{1};
auto x42 = x36 + x41;
auto x43 = V{0.00925925925925926}*x22;
auto x44 = x42*x43;
auto x45 = V{0.333333333333333}*cell[7] - x44;
auto x46 = V{0.333333333333333}*cell[6];
auto x47 = x34 + x40;
auto x48 = x43*x47 + x46;
auto x49 = x27 + x34;
auto x50 = V{0.333333333333333}*cell[4] + x43*x49 + V{0.0462962962962963};
auto x51 = x23*(V{0.333333333333333}*cell[1] + x24 - x25 + x33 + V{0.0185185185185185}*x35 - x39 + x45 + x48 + x50);
auto x52 = x27 + V{-1};
auto x53 = x22*x52;
auto x54 = x28 + x41;
auto x55 = x43*x54;
auto x56 = V{0.333333333333333}*cell[9] - x55;
auto x57 = V{0.333333333333333}*cell[8];
auto x58 = x40 + x52;
auto x59 = x43*x58 + x57;
auto x60 = -x24 + x25 - x33 + x39;
auto x61 = x23*(V{0.333333333333333}*cell[2] + x50 + V{0.0185185185185185}*x53 + x56 + x59 + x60);
auto x62 = V{0.166666666666667}*cell[3];
auto x63 = x40 + V{-1};
auto x64 = x41*x43;
auto x65 = V{0.0555555555555556}*x22;
auto x66 = V{0.166666666666667}*cell[1];
auto x67 = V{0.166666666666667}*cell[8];
auto x68 = x32*x58;
auto x69 = x34*x43;
auto x70 = x66 + x67 + x68 + x69;
auto x71 = V{0.166666666666667}*cell[9];
auto x72 = x32*x54;
auto x73 = x71 - x72;
auto x74 = V{0.166666666666667}*cell[2];
auto x75 = V{0.166666666666667}*cell[6];
auto x76 = x32*x47;
auto x77 = x43*x52;
auto x78 = x74 + x75 + x76 + x77;
auto x79 = V{0.166666666666667}*cell[7];
auto x80 = x32*x42;
auto x81 = x79 - x80;
auto x82 = x23*(x50 + x70 + x73 + x78 + x81);
auto x83 = V{0.0277777777777778}*x22;
auto x84 = -x79 + x80;
auto x85 = x74 - x75 - x76 + x77;
auto x86 = x23*(x60 - x66 + x67 + x68 - x69 + x73 + x84 + x85);
auto x87 = V{0.0833333333333333}*cell[5];
auto x88 = V{0.0833333333333333}*cell[14];
auto x89 = V{0.00231481481481481}*x22;
auto x90 = x31*x89;
auto x91 = x38*x89;
auto x92 = V{0.166666666666667}*cell[4] + x32*x49 + V{0.0231481481481481};
auto x93 = x87 - x88 + x90 - x91 + x92;
auto x94 = V{0.0833333333333333}*cell[3];
auto x95 = V{0.0833333333333333}*cell[12];
auto x96 = x32*x41;
auto x97 = x32*x63;
auto x98 = x94 - x95 + x96 + x97;
auto x99 = x23*(x48 + x70 - x71 + x72 + x93 + x98);
auto x100 = -x94 + x95 - x96 - x97;
auto x101 = x23*(x100 + x45 + x66 - x67 - x68 + x69 + x73 + x93);
auto x102 = -x87 + x88 - x90 + x91 + x92;
auto x103 = x23*(x102 + x59 + x78 + x84 + x98);
auto x104 = x23*(x100 + x102 + x56 + x81 + x85);
auto x105 = -x40;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = -V{0.0555555555555556}*x35 - x51 + V{-0.0555555555555556};
cell[2] = -V{0.0555555555555556}*x53 - x61 + V{-0.0555555555555556};
cell[3] = x23*(V{0.166666666666667}*cell[12] - x43*x47 - x43*x58 - x43*x63 + x45 - x46 + x56 - x57 - x62 - x64) - x63*x65 + V{-0.0555555555555556};
cell[4] = -x49*x83 - x82 + V{-0.0277777777777778};
cell[5] = x38*x83 + x86 + V{-0.0277777777777778};
cell[6] = -x47*x83 - x99 + V{-0.0277777777777778};
cell[7] = -x101 + V{0.0277777777777778}*x22*x42 + V{-0.0277777777777778};
cell[8] = -x103 - x58*x83 + V{-0.0277777777777778};
cell[9] = -x104 + V{0.0277777777777778}*x22*x54 + V{-0.0277777777777778};
cell[10] = x30*x65 + x51 + V{-0.0555555555555556};
cell[11] = x37*x65 + x61 + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x41 - x23*(V{0.166666666666667}*cell[12] + V{0.333333333333333}*cell[7] + V{0.333333333333333}*cell[9] - x43*x63 - x44 - x48 - x55 - x59 - x62 - x64) + V{-0.0555555555555556};
cell[13] = x82 + x83*(x27 + x30) + V{-0.0277777777777778};
cell[14] = V{0.0277777777777778}*x22*x31 - x86 + V{-0.0277777777777778};
cell[15] = x83*(x29 + x41) + x99 + V{-0.0277777777777778};
cell[16] = x101 + x83*(x105 + x30) + V{-0.0277777777777778};
cell[17] = x103 + x83*(x27 + x41) + V{-0.0277777777777778};
cell[18] = x104 + x83*(x105 + x37) + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
