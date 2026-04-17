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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::BGK, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x9 = parameters.template get<descriptors::OMEGA>();
auto x10 = x9 + V{-1};
auto x11 = cell[0] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8];
auto x12 = x11 + V{1};
auto x13 = x11 + V{1};
auto x14 = V{1} / ((x13)*(x13));
auto x15 = V{1.5}*x14;
auto x16 = cell[1] - cell[5];
auto x17 = -cell[4] + cell[8];
auto x18 = ((-cell[3] + cell[7] + x16 + x17)*(-cell[3] + cell[7] + x16 + x17));
auto x19 = x15*x18;
auto x20 = cell[2] - cell[6];
auto x21 = cell[3] - cell[7] + x16 + x20;
auto x22 = x15*((x21)*(x21)) + V{-1};
auto x23 = x19 + x22;
auto x24 = V{0.0277777777777778}*x9;
auto x25 = V{1} / (x13);
auto x26 = V{3}*cell[3];
auto x27 = V{3}*cell[7];
auto x28 = V{3}*cell[1] - V{3}*cell[5];
auto x29 = V{3}*cell[2] - V{3}*cell[6] + x26 - x27 + x28;
auto x30 = x25*x29;
auto x31 = V{4.5}*x14;
auto x32 = V{2}*cell[1] - V{2}*cell[5] + x17 + x20;
auto x33 = V{1} - x19;
auto x34 = x25*(-V{3}*cell[4] + V{3}*cell[8] - x26 + x27 + x28);
auto x35 = ((x21)*(x21));
auto x36 = x15*x35;
auto x37 = x34 - x36;
auto x38 = x33 + x37;
auto x39 = V{0.111111111111111}*x9;
auto x40 = V{3}*x14;
auto x41 = x33 + x35*x40;
auto x42 = x31*((-2*cell[3] - cell[4] + 2*cell[7] + cell[8] - x20)*(-2*cell[3] - cell[4] + 2*cell[7] + cell[8] - x20));
auto x43 = x18*x40;
auto x44 = -x30;
auto x0 = -cell[0]*x10 - V{0.444444444444444}*x9*(x12*x23 + V{1});
auto x1 = -cell[1]*x10 + x24*(x12*(x30 + x31*((x32)*(x32)) + x38) + V{-1});
auto x2 = -cell[2]*x10 + x39*(x12*(x30 + x41) + V{-1});
auto x3 = -cell[3]*x10 - x24*(x12*(x23 - x25*x29 + x34 - x42) + V{1});
auto x4 = -cell[4]*x10 - x39*(x12*(x22 + x34 - x43) + V{1});
auto x5 = -cell[5]*x10 + x24*(-x12*(-V{4.5}*x14*((x32)*(x32)) + x19 + x30 + x34 + x36 + V{-1}) + V{-1});
auto x6 = -cell[6]*x10 + x39*(x12*(x41 + x44) + V{-1});
auto x7 = -cell[7]*x10 + x24*(x12*(x38 + x42 + x44) + V{-1});
auto x8 = -cell[8]*x10 + x39*(x12*(x37 + x43 + V{1}) + V{-1});
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { x13, V{1}*x14*(x18 + x35) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
