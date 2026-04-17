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
struct CSE<dynamics::Tuple<T, descriptors::D3Q19<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::FixedVelocityMomentumGeneric, momenta::BulkStress, momenta::DefineUSeparatelyTrace>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x21 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(2);
auto x22 = parameters.template get<descriptors::OMEGA>();
auto x20 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x19 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x23 = x22 + V{-1};
auto x24 = cell[0] + cell[10] + cell[11] + cell[12] + cell[13] + cell[14] + cell[15] + cell[16] + cell[17] + cell[18] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8] + cell[9];
auto x25 = x24 + V{1};
auto x26 = ((x19)*(x19));
auto x27 = V{1.5}*x26;
auto x28 = ((x20)*(x20));
auto x29 = V{1.5}*x28;
auto x30 = ((x21)*(x21));
auto x31 = V{1.5}*x30;
auto x32 = x29 + x31 + V{-1};
auto x33 = x27 + x32;
auto x34 = V{0.0555555555555556}*x22;
auto x35 = V{3}*x19;
auto x36 = V{3}*x26;
auto x37 = V{3}*x20;
auto x38 = V{3}*x28;
auto x39 = x27 + V{-1};
auto x40 = V{3}*x21;
auto x41 = V{3}*x30;
auto x42 = V{0.0277777777777778}*x22;
auto x43 = V{4.5}*((x19 + x20)*(x19 + x20));
auto x44 = x33 + x35;
auto x45 = -x37;
auto x46 = x19 - x20;
auto x47 = V{4.5}*((x19 + x21)*(x19 + x21));
auto x48 = -x40;
auto x49 = -x21;
auto x50 = x19 + x49;
auto x51 = V{4.5}*((x20 + x21)*(x20 + x21));
auto x52 = x33 + x37;
auto x53 = x20 + x49;
auto x54 = -x29;
auto x55 = V{1} - x31;
auto x56 = x54 + x55;
auto x57 = x35 + x56;
auto x58 = -x27;
auto x59 = x37 + x58;
auto x60 = x40 + x58;
auto x61 = -x35;
auto x62 = x33 + x40;
auto x0 = -cell[0]*x23 - V{0.333333333333333}*x22*(x25*x33 + V{1});
auto x1 = -cell[1]*x23 - x34*(x25*(x32 + x35 - x36) + V{1});
auto x2 = -cell[2]*x23 - x34*(x25*(x31 + x37 - x38 + x39) + V{1});
auto x3 = -cell[3]*x23 - x34*(x25*(x29 + x39 + x40 - x41) + V{1});
auto x4 = -cell[4]*x23 - x42*(x25*(x37 - x43 + x44) + V{1});
auto x5 = -(cell[5]*x23 + x42*(x25*(x44 + x45 - V{4.5}*((x46)*(x46))) + V{1}));
auto x6 = -cell[6]*x23 - x42*(x25*(x40 + x44 - x47) + V{1});
auto x7 = -(cell[7]*x23 + x42*(x25*(x44 + x48 - V{4.5}*((x50)*(x50))) + V{1}));
auto x8 = -cell[8]*x23 - x42*(x25*(x40 - x51 + x52) + V{1});
auto x9 = -(cell[9]*x23 + x42*(x25*(x48 + x52 - V{4.5}*((x53)*(x53))) + V{1}));
auto x10 = -cell[10]*x23 + x34*(x25*(x36 + x57) + V{-1});
auto x11 = -cell[11]*x23 + x34*(x25*(x38 + x55 + x59) + V{-1});
auto x12 = -cell[12]*x23 + x34*(x25*(x41 + x54 + x60 + V{1}) + V{-1});
auto x13 = -cell[13]*x23 + x42*(x25*(x43 + x57 + x59) + V{-1});
auto x14 = -(cell[14]*x23 + x42*(x25*(x52 + x61 - V{4.5}*((x46)*(x46))) + V{1}));
auto x15 = -cell[15]*x23 + x42*(x25*(x47 + x57 + x60) + V{-1});
auto x16 = -(cell[16]*x23 + x42*(x25*(x61 + x62 - V{4.5}*((x50)*(x50))) + V{1}));
auto x17 = -cell[17]*x23 + x42*(x25*(x40 + x51 + x56 + x59) + V{-1});
auto x18 = -(cell[18]*x23 + x42*(x25*(x45 + x62 - V{4.5}*((x53)*(x53))) + V{1}));
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
return { x24 + V{1}, x26 + x28 + x30 };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
