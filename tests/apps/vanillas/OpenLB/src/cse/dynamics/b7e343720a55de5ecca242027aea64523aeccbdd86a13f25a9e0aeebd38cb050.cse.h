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
struct CSE<AdvectionDiffusionEdgesDynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 0, 1, -1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x23 = x26 + V{-1};
auto x24 = V{0.166666666666667}*cell[1];
auto x25 = V{0.333333333333333}*cell[6];
auto x27 = V{3}*x19;
auto x28 = x27 + V{-1};
auto x29 = -x28;
auto x30 = V{0.00925925925925926}*x22;
auto x31 = V{3}*x21;
auto x32 = x28 + x31;
auto x33 = -x32;
auto x34 = x27 + V{1};
auto x35 = x30*x34;
auto x36 = V{3}*x20;
auto x37 = x34 + x36;
auto x38 = x30*x37;
auto x39 = V{0.333333333333333}*cell[13] - x38;
auto x40 = -x31;
auto x41 = x34 + x40;
auto x42 = x30*x41;
auto x43 = V{0.333333333333333}*cell[16] - x42;
auto x44 = V{0.333333333333333}*cell[5];
auto x45 = -x27;
auto x46 = x36 + V{1};
auto x47 = x45 + x46;
auto x48 = x30*x47;
auto x49 = -x44 + x48;
auto x50 = V{0.0555555555555556}*x22;
auto x51 = V{0.0185185185185185}*x22;
auto x52 = x46*x51;
auto x53 = x44 - x48;
auto x54 = x40 + x46;
auto x55 = x30*x54;
auto x56 = V{0.333333333333333}*cell[18] - x55 + V{0.0462962962962963};
auto x57 = V{0.166666666666667}*cell[17];
auto x58 = V{0.166666666666667}*cell[8];
auto x59 = x36 + V{-1};
auto x60 = x31 + x59;
auto x61 = -x60;
auto x62 = V{0.00462962962962963}*x22;
auto x63 = x31 + x46;
auto x64 = x62*x63;
auto x65 = x57 - x58 + x61*x62 - x64;
auto x66 = x31 + V{-1};
auto x67 = x25 + x30*x32;
auto x68 = -x57 + x58 + x60*x62 + x64;
auto x69 = x23*(V{0.333333333333333}*cell[3] + x43 + x51*x66 + x56 + x67 + x68);
auto x70 = V{0.00231481481481481}*x22;
auto x71 = V{0.166666666666667}*cell[11];
auto x72 = V{0.166666666666667}*cell[16];
auto x73 = x41*x62;
auto x74 = -x73;
auto x75 = x30*x46;
auto x76 = -x75;
auto x77 = x71 + x72 + x74 + x76;
auto x78 = V{0.166666666666667}*cell[6];
auto x79 = x33*x62 - x78;
auto x80 = V{0.0833333333333333}*cell[17];
auto x81 = V{0.0833333333333333}*cell[8];
auto x82 = x63*x70;
auto x83 = x54*x62;
auto x84 = V{0.166666666666667}*cell[18] - x83 + V{0.0231481481481481};
auto x85 = x80 - x81 - x82 + x84;
auto x86 = V{0.0833333333333333}*cell[10];
auto x87 = V{0.0833333333333333}*cell[1];
auto x88 = x34*x62;
auto x89 = x86 - x87 - x88;
auto x90 = V{0.0277777777777778}*x22;
auto x91 = x60*x70;
auto x92 = x32*x62 + x78;
auto x93 = -x72 + x73;
auto x94 = x71 + x76 + x93;
auto x95 = x28*x62;
auto x96 = -x86 + x87 + x88 + x95;
auto x97 = x23*(x53 + x85 - x91 + x92 + x94 + x96);
auto x98 = V{0.166666666666667}*cell[3];
auto x99 = V{0.166666666666667}*cell[5];
auto x100 = x30*x66;
auto x101 = x47*x62;
auto x102 = -x101;
auto x103 = x100 + x102 + x98 + x99;
auto x104 = V{0.166666666666667}*cell[13];
auto x105 = x37*x62;
auto x106 = -x104 + x105;
auto x107 = -x80;
auto x108 = x107 + x81 + x82 + x84 + x91;
auto x109 = x23*(x103 + x106 + x108 + x67 + x96);
auto x110 = x104 - x105;
auto x111 = x100 + x101 + x98 - x99;
auto x112 = x23*(x108 + x110 + x111 + x43 + x89 - x95);
auto x113 = x31 + V{1};
auto x114 = x23*(x103 + x110 + x56 + x77 + x92);
auto x115 = -x36;
auto x116 = -V{0.333333333333333}*cell[13] + x38;
auto x117 = -V{0.166666666666667}*cell[11] + x75 + x92;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = x23*(V{0.166666666666667}*cell[10] - x24 - x25 + x29*x30 + x30*x33 - x35 + x39 + x43 + x49) - x28*x50 + V{-0.0555555555555556};
cell[2] = x23*(V{0.333333333333333}*cell[11] + x39 - x52 + x53 + x56 + x65) - x50*x59 + V{-0.0555555555555556};
cell[3] = -x50*x66 - x69 + V{-0.0555555555555556};
cell[4] = x23*(x29*x62 + x39 + x61*x70 + x77 + x79 + x85 + x89) - x90*(x28 + x36) + V{-0.0277777777777778};
cell[5] = V{0.0277777777777778}*x22*x47 - x97 + V{-0.0277777777777778};
cell[6] = -x109 - x32*x90 + V{-0.0277777777777778};
cell[7] = x112 + x90*(x113 + x45) + V{-0.0277777777777778};
cell[8] = x23*(x102 + x110 - x30*x66 + x65 + x79 + x94 - x98 + x99) - x60*x90 + V{-0.0277777777777778};
cell[9] = x114 + x90*(x113 + x115) + V{-0.0277777777777778};
cell[10] = V{0.0555555555555556}*x22*x34 - x23*(V{0.166666666666667}*cell[10] + V{0.333333333333333}*cell[16] - x116 - x24 - x28*x30 - x35 - x42 - x53 - x67) + V{-0.0555555555555556};
cell[11] = V{0.0555555555555556}*x22*x46 - x23*(V{0.333333333333333}*cell[11] + V{0.333333333333333}*cell[18] - x116 - x49 - x52 - x55 - x68 + V{0.0462962962962963}) + V{-0.0555555555555556};
cell[12] = x113*x50 + x69 + V{-0.0555555555555556};
cell[13] = V{0.0277777777777778}*x22*x37 - x23*(V{0.166666666666667}*cell[18] - x107 - x116 - x117 - x81 - x82 - x83 - x91 - x93 - x96 + V{0.0231481481481481}) + V{-0.0277777777777778};
cell[14] = x90*(x115 + x34) + x97 + V{-0.0277777777777778};
cell[15] = x109 + x90*(x31 + x34) + V{-0.0277777777777778};
cell[16] = -x112 + V{0.0277777777777778}*x22*x41 + V{-0.0277777777777778};
cell[17] = V{0.0277777777777778}*x22*x63 - x23*(-x106 - x111 - x117 - x68 - x72 - x74) + V{-0.0277777777777778};
cell[18] = -x114 + V{0.0277777777777778}*x22*x54 + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
