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
struct CSE<dynamics::Tuple<T, descriptors::D3Q27<FIELDS...>, momenta::Tuple<momenta::FixedDensity, momenta::FixedVelocityMomentumGeneric, momenta::ZeroStress, momenta::DefineSeparately>, equilibria::FirstOrder, collision::FixedEquilibrium, dynamics::DefaultCombination>> {
template <concepts::Cell CELL, concepts::Parameters PARAMETERS, concepts::BaseType V=typename CELL::value_t>
CellStatistic<V> collide(CELL& cell, PARAMETERS& parameters) any_platform {
auto x27 = cell.template getFieldComponent<olb::momenta::FixedDensity::RHO>(0);
auto x29 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(1);
auto x28 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(0);
auto x30 = cell.template getFieldComponent<olb::momenta::FixedVelocityMomentumGeneric::VELOCITY>(2);
auto x31 = V{3}*x28;
auto x32 = x31 + V{-1};
auto x33 = V{3}*x29;
auto x34 = x33 + V{-1};
auto x35 = V{3}*x30;
auto x36 = x32 + x33;
auto x37 = -x31;
auto x38 = x33 + V{1};
auto x39 = x37 + x38;
auto x40 = x32 + x35;
auto x41 = x35 + V{1};
auto x42 = -x33;
auto x43 = -x35;
auto x44 = x31 + V{1};
auto x45 = x33 + x44;
auto x46 = x42 + x44;
cell[0] = V{0.296296296296296}*x27 + V{-0.296296296296296};
cell[1] = -V{0.0740740740740741}*x27*x32 + V{-0.0740740740740741};
cell[2] = -V{0.0740740740740741}*x27*x34 + V{-0.0740740740740741};
cell[3] = -V{0.0740740740740741}*x27*(x35 + V{-1}) + V{-0.0740740740740741};
cell[4] = -V{0.0185185185185185}*x27*x36 + V{-0.0185185185185185};
cell[5] = V{0.0185185185185185}*x27*x39 + V{-0.0185185185185185};
cell[6] = -V{0.0185185185185185}*x27*x40 + V{-0.0185185185185185};
cell[7] = V{0.0185185185185185}*x27*(x37 + x41) + V{-0.0185185185185185};
cell[8] = -V{0.0185185185185185}*x27*(x34 + x35) + V{-0.0185185185185185};
cell[9] = V{0.0185185185185185}*x27*(x41 + x42) + V{-0.0185185185185185};
cell[10] = -V{0.00462962962962963}*x27*(x35 + x36) + V{-0.00462962962962963};
cell[11] = -V{0.00462962962962963}*x27*(x36 + x43) + V{-0.00462962962962963};
cell[12] = -V{0.00462962962962963}*x27*(x40 + x42) + V{-0.00462962962962963};
cell[13] = V{0.00462962962962963}*x27*(x35 + x39) + V{-0.00462962962962963};
cell[14] = V{0.0740740740740741}*x27*x44 + V{-0.0740740740740741};
cell[15] = V{0.0740740740740741}*x27*x38 + V{-0.0740740740740741};
cell[16] = V{0.0740740740740741}*x27*x41 + V{-0.0740740740740741};
cell[17] = V{0.0185185185185185}*x27*x45 + V{-0.0185185185185185};
cell[18] = V{0.0185185185185185}*x27*x46 + V{-0.0185185185185185};
cell[19] = V{0.0185185185185185}*x27*(x35 + x44) + V{-0.0185185185185185};
cell[20] = V{0.0185185185185185}*x27*(x43 + x44) + V{-0.0185185185185185};
cell[21] = V{0.0185185185185185}*x27*(x35 + x38) + V{-0.0185185185185185};
cell[22] = V{0.0185185185185185}*x27*(x38 + x43) + V{-0.0185185185185185};
cell[23] = V{0.00462962962962963}*x27*(x35 + x45) + V{-0.00462962962962963};
cell[24] = V{0.00462962962962963}*x27*(x43 + x45) + V{-0.00462962962962963};
cell[25] = V{0.00462962962962963}*x27*(x35 + x46) + V{-0.00462962962962963};
cell[26] = V{0.00462962962962963}*x27*(x43 + x46) + V{-0.00462962962962963};
return { x27, ((x28)*(x28)) + ((x29)*(x29)) + ((x30)*(x30)) };
}
};

}

}

// Generation Info: commit=2a9f114ed32e2878e1a64a356eda56d13e508f7d
