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
struct CSE<dynamics::Tuple<T, descriptors::D2Q9<FIELDS...>, momenta::Tuple<momenta::BulkDensity, momenta::BulkMomentum, momenta::BulkStress, momenta::DefineToNEq>, equilibria::SecondOrder, collision::ConstRhoBGK, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x10 = parameters.template get<statistics::AVERAGE_RHO>();
auto x9 = parameters.template get<descriptors::OMEGA>();
auto x11 = x9 + V{-1};
auto x12 = cell[0] + cell[1] + cell[2] + cell[3] + cell[4] + cell[5] + cell[6] + cell[7] + cell[8];
auto x13 = x12 + V{1};
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
auto x24 = V{1} / (x13);
auto x25 = -x24*(x10 + V{-1}) + V{1};
auto x26 = x12 + V{1};
auto x27 = x25*x26;
auto x28 = V{0.0277777777777778}*cell[0] + V{0.0277777777777778}*cell[1] + V{0.0277777777777778}*cell[2] + V{0.0277777777777778}*cell[3] + V{0.0277777777777778}*cell[4] + V{0.0277777777777778}*cell[5] + V{0.0277777777777778}*cell[6] + V{0.0277777777777778}*cell[7] + V{0.0277777777777778}*cell[8] + V{0.0277777777777778};
auto x29 = V{3}*cell[3];
auto x30 = V{3}*cell[7];
auto x31 = V{3}*cell[1] - V{3}*cell[5];
auto x32 = V{3}*cell[2] - V{3}*cell[6] + x29 - x30 + x31;
auto x33 = x24*x32;
auto x34 = V{4.5}*x14;
auto x35 = V{2}*cell[1] - V{2}*cell[5] + x17 + x20;
auto x36 = V{1} - x19;
auto x37 = x24*(-V{3}*cell[4] + V{3}*cell[8] - x29 + x30 + x31);
auto x38 = ((x21)*(x21));
auto x39 = x15*x38;
auto x40 = x37 - x39;
auto x41 = x36 + x40;
auto x42 = x33 + x34*((x35)*(x35)) + x41;
auto x43 = V{0.111111111111111}*cell[0] + V{0.111111111111111}*cell[1] + V{0.111111111111111}*cell[2] + V{0.111111111111111}*cell[3] + V{0.111111111111111}*cell[4] + V{0.111111111111111}*cell[5] + V{0.111111111111111}*cell[6] + V{0.111111111111111}*cell[7] + V{0.111111111111111}*cell[8] + V{0.111111111111111};
auto x44 = V{3}*x14;
auto x45 = x36 + x38*x44;
auto x46 = x33 + x45;
auto x47 = x34*((-2*cell[3] - cell[4] + 2*cell[7] + cell[8] - x20)*(-2*cell[3] - cell[4] + 2*cell[7] + cell[8] - x20));
auto x48 = x23 - x24*x32 + x37 - x47;
auto x49 = x18*x44;
auto x50 = x22 + x37 - x49;
auto x51 = -(-V{4.5}*x14*((x35)*(x35)) + x19 + x33 + x37 + x39 + V{-1});
auto x52 = -x33;
auto x53 = x45 + x52;
auto x54 = x41 + x47 + x52;
auto x55 = x40 + x49 + V{1};
auto x0 = -x11*(cell[0] + x23*(V{0.444444444444444}*cell[0] + V{0.444444444444444}*cell[1] + V{0.444444444444444}*cell[2] + V{0.444444444444444}*cell[3] + V{0.444444444444444}*cell[4] + V{0.444444444444444}*cell[5] + V{0.444444444444444}*cell[6] + V{0.444444444444444}*cell[7] + V{0.444444444444444}*cell[8] + V{0.444444444444444}) + V{0.444444444444444}) - V{0.444444444444444}*x23*x27 + V{-0.444444444444444};
auto x1 = -x11*(cell[1] - x28*x42 + V{0.0277777777777778}) + V{0.0277777777777778}*x25*x26*x42 + V{-0.0277777777777778};
auto x2 = -x11*(cell[2] - x43*x46 + V{0.111111111111111}) + V{0.111111111111111}*x25*x26*x46 + V{-0.111111111111111};
auto x3 = -x11*(cell[3] + x28*x48 + V{0.0277777777777778}) - V{0.0277777777777778}*x27*x48 + V{-0.0277777777777778};
auto x4 = -x11*(cell[4] + x43*x50 + V{0.111111111111111}) - V{0.111111111111111}*x27*x50 + V{-0.111111111111111};
auto x5 = -x11*(cell[5] - x28*x51 + V{0.0277777777777778}) + V{0.0277777777777778}*x25*x26*x51 + V{-0.0277777777777778};
auto x6 = -x11*(cell[6] - x43*x53 + V{0.111111111111111}) + V{0.111111111111111}*x25*x26*x53 + V{-0.111111111111111};
auto x7 = -x11*(cell[7] - x28*x54 + V{0.0277777777777778}) + V{0.0277777777777778}*x25*x26*x54 + V{-0.0277777777777778};
auto x8 = -x11*(cell[8] - x43*x55 + V{0.111111111111111}) + V{0.111111111111111}*x25*x26*x55 + V{-0.111111111111111};
cell[0] = x0;
cell[1] = x1;
cell[2] = x2;
cell[3] = x3;
cell[4] = x4;
cell[5] = x5;
cell[6] = x6;
cell[7] = x7;
cell[8] = x8;
return { -x10 + x12 + V{2}, V{1}*x14*(x18 + x38) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
