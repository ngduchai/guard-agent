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
struct CSE<AdvectionDiffusionEdgesDynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 1, -1, -1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x23 = x26 + V{-1};
auto x24 = V{0.166666666666667}*cell[7];
auto x25 = V{0.166666666666667}*cell[16];
auto x27 = V{3}*x21;
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
auto x40 = V{3}*x20;
auto x41 = x40 + V{1};
auto x42 = x36 + x41;
auto x43 = V{0.00925925925925926}*x22;
auto x44 = x42*x43;
auto x45 = V{0.333333333333333}*cell[5] - x44;
auto x46 = V{0.333333333333333}*cell[4];
auto x47 = x34 + x40;
auto x48 = x43*x47 + x46;
auto x49 = x27 + x34;
auto x50 = V{0.333333333333333}*cell[6] + x43*x49 + V{0.0462962962962963};
auto x51 = x23*(V{0.333333333333333}*cell[1] + x24 - x25 + x33 + V{0.0185185185185185}*x35 - x39 + x45 + x48 + x50);
auto x52 = V{0.166666666666667}*cell[2];
auto x53 = V{0.333333333333333}*cell[8];
auto x54 = x40 + V{-1};
auto x55 = x27 + x54;
auto x56 = x41*x43;
auto x57 = x28 + x41;
auto x58 = x43*x57;
auto x59 = V{0.333333333333333}*cell[18] - x58;
auto x60 = V{0.0555555555555556}*x22;
auto x61 = x27 + V{-1};
auto x62 = x43*x55 + x53;
auto x63 = -x24 + x25 - x33 + x39;
auto x64 = x23*(V{0.333333333333333}*cell[3] + V{0.0185185185185185}*x22*x61 + x50 + x59 + x62 + x63);
auto x65 = V{0.166666666666667}*cell[18];
auto x66 = x32*x57;
auto x67 = V{0.166666666666667}*cell[1];
auto x68 = V{0.166666666666667}*cell[8];
auto x69 = x32*x55;
auto x70 = x34*x43;
auto x71 = x67 + x68 + x69 + x70;
auto x72 = V{0.0833333333333333}*cell[7];
auto x73 = V{0.0833333333333333}*cell[16];
auto x74 = V{0.00231481481481481}*x22;
auto x75 = x31*x74;
auto x76 = x38*x74;
auto x77 = V{0.166666666666667}*cell[6] + x32*x49 + V{0.0231481481481481};
auto x78 = x72 - x73 + x75 - x76 + x77;
auto x79 = V{0.0833333333333333}*cell[2];
auto x80 = V{0.0833333333333333}*cell[11];
auto x81 = x32*x41;
auto x82 = x32*x54;
auto x83 = x79 - x80 + x81 + x82;
auto x84 = x23*(x48 - x65 + x66 + x71 + x78 + x83);
auto x85 = V{0.0277777777777778}*x22;
auto x86 = x65 - x66;
auto x87 = -x79 + x80 - x81 - x82;
auto x88 = x23*(x45 + x67 - x68 - x69 + x70 + x78 + x86 + x87);
auto x89 = V{0.166666666666667}*cell[3];
auto x90 = V{0.166666666666667}*cell[4];
auto x91 = x32*x47;
auto x92 = x43*x61;
auto x93 = x89 + x90 + x91 + x92;
auto x94 = V{0.166666666666667}*cell[5];
auto x95 = x32*x42;
auto x96 = x94 - x95;
auto x97 = x23*(x50 + x71 + x86 + x93 + x96);
auto x98 = -x94 + x95;
auto x99 = x89 - x90 - x91 + x92;
auto x100 = x23*(x63 - x67 + x68 + x69 - x70 + x86 + x98 + x99);
auto x101 = -x72 + x73 - x75 + x76 + x77;
auto x102 = x23*(x101 + x62 + x83 + x93 + x98);
auto x103 = x23*(x101 + x59 + x87 + x96 + x99);
auto x104 = -x40;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = -V{0.0555555555555556}*x35 - x51 + V{-0.0555555555555556};
cell[2] = x23*(V{0.166666666666667}*cell[11] - x43*x47 - x43*x54 - x43*x55 + x45 - x46 - x52 - x53 - x56 + x59) - x54*x60 + V{-0.0555555555555556};
cell[3] = -x60*x61 - x64 + V{-0.0555555555555556};
cell[4] = -x47*x85 - x84 + V{-0.0277777777777778};
cell[5] = V{0.0277777777777778}*x22*x42 - x88 + V{-0.0277777777777778};
cell[6] = -x49*x85 - x97 + V{-0.0277777777777778};
cell[7] = x100 + x38*x85 + V{-0.0277777777777778};
cell[8] = -x102 - x55*x85 + V{-0.0277777777777778};
cell[9] = x103 + x85*(x104 + x37) + V{-0.0277777777777778};
cell[10] = x30*x60 + x51 + V{-0.0555555555555556};
cell[11] = V{0.0555555555555556}*x22*x41 - x23*(V{0.166666666666667}*cell[11] + V{0.333333333333333}*cell[18] + V{0.333333333333333}*cell[5] - x43*x54 - x44 - x48 - x52 - x56 - x58 - x62) + V{-0.0555555555555556};
cell[12] = x37*x60 + x64 + V{-0.0555555555555556};
cell[13] = x84 + x85*(x29 + x41) + V{-0.0277777777777778};
cell[14] = x85*(x104 + x30) + x88 + V{-0.0277777777777778};
cell[15] = x85*(x27 + x30) + x97 + V{-0.0277777777777778};
cell[16] = -x100 + V{0.0277777777777778}*x22*x31 + V{-0.0277777777777778};
cell[17] = x102 + x85*(x27 + x41) + V{-0.0277777777777778};
cell[18] = -x103 + V{0.0277777777777778}*x22*x57 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
