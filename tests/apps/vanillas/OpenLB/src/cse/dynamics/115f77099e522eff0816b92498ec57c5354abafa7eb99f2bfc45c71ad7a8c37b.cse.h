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
struct CSE<AdvectionDiffusionEdgesDynamics<T, descriptors::D3Q19<FIELDS...>, dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::NoStress, momenta::DefineToEq>, equilibria::FirstOrder, collision::AdvectionDiffusionRLB, AdvectionDiffusionExternalVelocityCollision>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, 0, -1, 1>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x20 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x22 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x19 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x21 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(2);
auto x26 = parameters.template get<descriptors::OMEGA>();
auto x23 = x26 + V{-1};
auto x24 = V{0.166666666666667}*cell[1];
auto x25 = V{0.333333333333333}*cell[4];
auto x27 = V{3}*x19;
auto x28 = x27 + V{-1};
auto x29 = -x28;
auto x30 = V{0.00925925925925926}*x22;
auto x31 = V{3}*x20;
auto x32 = x28 + x31;
auto x33 = -x32;
auto x34 = x27 + V{1};
auto x35 = x30*x34;
auto x36 = -x31;
auto x37 = x34 + x36;
auto x38 = x30*x37;
auto x39 = V{0.333333333333333}*cell[14] - x38;
auto x40 = V{3}*x21;
auto x41 = x34 + x40;
auto x42 = x30*x41;
auto x43 = V{0.333333333333333}*cell[15] - x42;
auto x44 = V{0.333333333333333}*cell[7];
auto x45 = -x27;
auto x46 = x40 + V{1};
auto x47 = x45 + x46;
auto x48 = x30*x47;
auto x49 = -x44 + x48;
auto x50 = V{0.0555555555555556}*x22;
auto x51 = x31 + V{-1};
auto x52 = V{0.0185185185185185}*x22;
auto x53 = x25 + x30*x32;
auto x54 = x36 + x46;
auto x55 = x30*x54;
auto x56 = V{0.333333333333333}*cell[9] - x55 + V{0.0462962962962963};
auto x57 = V{0.166666666666667}*cell[8];
auto x58 = V{0.166666666666667}*cell[17];
auto x59 = x31 + x46;
auto x60 = V{0.00462962962962963}*x22;
auto x61 = x59*x60;
auto x62 = x40 + x51;
auto x63 = x57 - x58 + x60*x62 + x61;
auto x64 = x23*(V{0.333333333333333}*cell[2] + x39 + x51*x52 + x53 + x56 + x63);
auto x65 = x46*x52;
auto x66 = x44 - x48;
auto x67 = -x62;
auto x68 = -x57 + x58 + x60*x67 - x61;
auto x69 = V{0.166666666666667}*cell[2];
auto x70 = V{0.166666666666667}*cell[7];
auto x71 = x30*x51;
auto x72 = x47*x60;
auto x73 = -x72;
auto x74 = x69 + x70 + x71 + x73;
auto x75 = V{0.166666666666667}*cell[15];
auto x76 = x41*x60;
auto x77 = -x75 + x76;
auto x78 = V{0.0833333333333333}*cell[8];
auto x79 = V{0.0833333333333333}*cell[17];
auto x80 = -x79;
auto x81 = V{0.00231481481481481}*x22;
auto x82 = x59*x81;
auto x83 = x62*x81;
auto x84 = x54*x60;
auto x85 = V{0.166666666666667}*cell[9] - x84 + V{0.0231481481481481};
auto x86 = x78 + x80 + x82 + x83 + x85;
auto x87 = V{0.0833333333333333}*cell[1];
auto x88 = V{0.0833333333333333}*cell[10];
auto x89 = x34*x60;
auto x90 = x28*x60;
auto x91 = x87 - x88 + x89 + x90;
auto x92 = x23*(x53 + x74 + x77 + x86 + x91);
auto x93 = V{0.0277777777777778}*x22;
auto x94 = x75 - x76;
auto x95 = x69 - x70 + x71 + x72;
auto x96 = -x87 + x88 - x89;
auto x97 = x23*(x39 + x86 - x90 + x94 + x95 + x96);
auto x98 = x31 + V{1};
auto x99 = V{0.166666666666667}*cell[12];
auto x100 = V{0.166666666666667}*cell[14];
auto x101 = x37*x60;
auto x102 = -x101;
auto x103 = x30*x46;
auto x104 = -x103;
auto x105 = x100 + x102 + x104 + x99;
auto x106 = V{0.166666666666667}*cell[4];
auto x107 = -x106 + x33*x60;
auto x108 = -x78 + x79 - x82 + x85;
auto x109 = x106 + x32*x60;
auto x110 = -x100 + x101;
auto x111 = x104 + x110 + x99;
auto x112 = x23*(x108 + x109 + x111 + x66 - x83 + x91);
auto x113 = x23*(x105 + x109 + x56 + x74 + x94);
auto x114 = -V{0.333333333333333}*cell[15] + x42;
auto x115 = -V{0.166666666666667}*cell[12] + x103 + x109;
auto x116 = -x40;
cell[0] = V{0.333333333333333}*x22 + V{-0.333333333333333};
cell[1] = x23*(V{0.166666666666667}*cell[10] - x24 - x25 + x29*x30 + x30*x33 - x35 + x39 + x43 + x49) - x28*x50 + V{-0.0555555555555556};
cell[2] = -x50*x51 - x64 + V{-0.0555555555555556};
cell[3] = x23*(V{0.333333333333333}*cell[12] + x43 + x56 - x65 + x66 + x68) - x50*(x40 + V{-1}) + V{-0.0555555555555556};
cell[4] = -x32*x93 - x92 + V{-0.0277777777777778};
cell[5] = x93*(x45 + x98) + x97 + V{-0.0277777777777778};
cell[6] = x23*(x105 + x107 + x108 + x29*x60 + x43 + x67*x81 + x96) - x93*(x28 + x40) + V{-0.0277777777777778};
cell[7] = -x112 + V{0.0277777777777778}*x22*x47 + V{-0.0277777777777778};
cell[8] = x23*(x107 + x111 - x30*x51 + x68 - x69 + x70 + x73 + x94) - x62*x93 + V{-0.0277777777777778};
cell[9] = -x113 + V{0.0277777777777778}*x22*x54 + V{-0.0277777777777778};
cell[10] = V{0.0555555555555556}*x22*x34 - x23*(V{0.166666666666667}*cell[10] + V{0.333333333333333}*cell[14] - x114 - x24 - x28*x30 - x35 - x38 - x53 - x66) + V{-0.0555555555555556};
cell[11] = x50*x98 + x64 + V{-0.0555555555555556};
cell[12] = V{0.0555555555555556}*x22*x46 - x23*(V{0.333333333333333}*cell[12] + V{0.333333333333333}*cell[9] - x114 - x49 - x55 - x63 - x65 + V{0.0462962962962963}) + V{-0.0555555555555556};
cell[13] = x92 + x93*(x31 + x34) + V{-0.0277777777777778};
cell[14] = V{0.0277777777777778}*x22*x37 - x97 + V{-0.0277777777777778};
cell[15] = V{0.0277777777777778}*x22*x41 - x23*(V{0.166666666666667}*cell[9] - x110 - x114 - x115 - x78 - x80 - x82 - x83 - x84 - x91 + V{0.0231481481481481}) + V{-0.0277777777777778};
cell[16] = x112 + x93*(x116 + x34) + V{-0.0277777777777778};
cell[17] = V{0.0277777777777778}*x22*x59 - x23*(-x100 - x102 - x115 - x63 - x77 - x95) + V{-0.0277777777777778};
cell[18] = x113 + x93*(x116 + x98) + V{-0.0277777777777778};
return { x22, ((x19)*(x19)) + ((x20)*(x20)) + ((x21)*(x21)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
