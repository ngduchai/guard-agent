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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::FreeEnergyMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::FreeEnergy, collision::FreeEnergy, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x22 = cell.template getFieldComponent<olb::descriptors::FORCE>(2);
auto x24 = parameters.template get<collision::FreeEnergy::GAMMA>();
auto x23 = parameters.template get<descriptors::OMEGA>();
auto x20 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x19 = cell.template getFieldComponent<olb::descriptors::CHEM_POTENTIAL>(0);
auto x21 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x25 = x23 + V{-1};
auto x26 = cell[0] + cell[10] + cell[11] + cell[12] + cell[13] + cell[14] + cell[15] + cell[16] + cell[17] + cell[18] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8] + cell[9];
auto x27 = x26 + V{1};
auto x28 = ((x20)*(x20));
auto x29 = V{1.5}*x28;
auto x30 = ((x21)*(x21));
auto x31 = V{1.5}*x30;
auto x32 = ((x22)*(x22));
auto x33 = V{1.5}*x32;
auto x34 = x31 + x33 + V{-1};
auto x35 = x29 + x34;
auto x36 = x26 + V{1};
auto x37 = -V{3}*x19*x24 + x36;
auto x38 = V{0.0555555555555556}*x23;
auto x39 = V{3}*x20;
auto x40 = V{3}*x28;
auto x41 = x37*x38;
auto x42 = V{3}*x21;
auto x43 = V{3}*x30;
auto x44 = x29 + V{-1};
auto x45 = V{3}*x22;
auto x46 = V{3}*x32;
auto x47 = V{0.0277777777777778}*x23;
auto x48 = V{4.5}*((x20 + x21)*(x20 + x21));
auto x49 = x35 + x39;
auto x50 = x37*x47;
auto x51 = -x42;
auto x52 = x20 - x21;
auto x53 = V{4.5}*((x20 + x22)*(x20 + x22));
auto x54 = -x45;
auto x55 = -x22;
auto x56 = x20 + x55;
auto x57 = V{4.5}*((x21 + x22)*(x21 + x22));
auto x58 = x35 + x42;
auto x59 = x21 + x55;
auto x60 = -x31;
auto x61 = V{1} - x33;
auto x62 = x60 + x61;
auto x63 = x39 + x62;
auto x64 = -x29;
auto x65 = x42 + x64;
auto x66 = x45 + x64;
auto x67 = -x39;
auto x68 = x35 + x45;
auto x0 = -cell[0]*x25 + V{0.666666666666667}*x23*x37 - V{0.333333333333333}*x23*(x27*x35 + V{1});
auto x1 = -cell[1]*x25 - x38*(x27*(x34 + x39 - x40) + V{1}) - x41;
auto x2 = -cell[2]*x25 - x38*(x27*(x33 + x42 - x43 + x44) + V{1}) - x41;
auto x3 = -cell[3]*x25 - x38*(x27*(x31 + x44 + x45 - x46) + V{1}) - x41;
auto x4 = -cell[4]*x25 - x47*(x27*(x42 - x48 + x49) + V{1}) - x50;
auto x5 = -(cell[5]*x25 + x47*(x27*(x49 + x51 - V{4.5}*((x52)*(x52))) + V{1}) + x50);
auto x6 = -cell[6]*x25 - x47*(x27*(x45 + x49 - x53) + V{1}) - x50;
auto x7 = -(cell[7]*x25 + x47*(x27*(x49 + x54 - V{4.5}*((x56)*(x56))) + V{1}) + x50);
auto x8 = -cell[8]*x25 - x47*(x27*(x45 - x57 + x58) + V{1}) - x50;
auto x9 = -(cell[9]*x25 + x47*(x27*(x54 + x58 - V{4.5}*((x59)*(x59))) + V{1}) + x50);
auto x10 = -cell[10]*x25 + V{0.0555555555555556}*x23*(x27*(x40 + x63) + V{-1}) - x41;
auto x11 = -cell[11]*x25 + V{0.0555555555555556}*x23*(x27*(x43 + x61 + x65) + V{-1}) - x41;
auto x12 = -cell[12]*x25 + V{0.0555555555555556}*x23*(x27*(x46 + x60 + x66 + V{1}) + V{-1}) - x41;
auto x13 = -cell[13]*x25 + V{0.0277777777777778}*x23*(x27*(x48 + x63 + x65) + V{-1}) - x50;
auto x14 = -(cell[14]*x25 + x47*(x27*(x58 + x67 - V{4.5}*((x52)*(x52))) + V{1}) + x50);
auto x15 = -cell[15]*x25 + V{0.0277777777777778}*x23*(x27*(x53 + x63 + x66) + V{-1}) - x50;
auto x16 = -(cell[16]*x25 + x47*(x27*(x67 + x68 - V{4.5}*((x56)*(x56))) + V{1}) + x50);
auto x17 = -cell[17]*x25 + V{0.0277777777777778}*x23*(x27*(x45 + x57 + x62 + x65) + V{-1}) - x50;
auto x18 = -(cell[18]*x25 + x47*(x27*(x51 + x68 - V{4.5}*((x59)*(x59))) + V{1}) + x50);
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
cell[9] = x9;
cell[10] = x10;
cell[11] = x11;
cell[12] = x12;
cell[13] = x13;
cell[14] = x14;
cell[15] = x15;
cell[16] = x16;
cell[17] = x17;
cell[18] = x18;
return { x36, x28 + x30 + x32 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
