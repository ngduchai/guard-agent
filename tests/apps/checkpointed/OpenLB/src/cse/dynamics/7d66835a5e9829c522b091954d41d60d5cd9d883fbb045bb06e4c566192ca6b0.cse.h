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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::FixedVelocityMomentum, momenta::BulkStress, momenta::DefineUSeparately>, equilibria::FirstOrder, collision::BGK, forcing::ConservativePhaseField>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x10 = cell.template getFieldComponent<olb::descriptors::FORCE>(1);
auto x11 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(0);
auto x13 = parameters.template get<descriptors::OMEGA>();
auto x9 = cell.template getFieldComponent<olb::descriptors::FORCE>(0);
auto x12 = cell.template getFieldComponent<olb::descriptors::VELOCITY>(1);
auto x14 = x13 + V{-1};
auto x15 = cell[0] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8];
auto x16 = V{0.5}*x13 + V{-1};
auto x17 = V{0.0833333333333333}*x16;
auto x18 = x17*(x10 - x9);
auto x19 = V{3}*x11;
auto x20 = V{3}*x12;
auto x21 = x20 + V{1};
auto x22 = x15 + V{1};
auto x23 = x19 + V{-1};
auto x24 = V{0.111111111111111}*x13;
auto x25 = V{0.333333333333333}*x16;
auto x26 = x25*x9;
auto x27 = V{0.0277777777777778}*x13;
auto x28 = x17*(x10 + x9);
auto x29 = x10*x25;
auto x30 = x19 + V{1};
auto x0 = -cell[0]*x14 + V{0.444444444444444}*x13*x15;
auto x1 = -cell[1]*x14 + V{0.0277777777777778}*x13*(x22*(-x19 + x21) + V{-1}) - x18;
auto x2 = -cell[2]*x14 - x24*(x22*x23 + V{1}) + x26;
auto x3 = -cell[3]*x14 - x27*(x22*(x20 + x23) + V{1}) + x28;
auto x4 = -cell[4]*x14 - x24*(x22*(x20 + V{-1}) + V{1}) + x29;
auto x5 = -cell[5]*x14 + x18 + x27*(x22*(-x20 + x30) + V{-1});
auto x6 = -cell[6]*x14 + V{0.111111111111111}*x13*(x22*x30 + V{-1}) - x26;
auto x7 = -cell[7]*x14 + V{0.0277777777777778}*x13*(x22*(x20 + x30) + V{-1}) - x28;
auto x8 = -cell[8]*x14 + V{0.111111111111111}*x13*(x21*x22 + V{-1}) - x29;
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x15 + V{1}, ((x11)*(x11)) + ((x12)*(x12)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
