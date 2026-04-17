/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Adrian Kummerlaender
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

#ifndef REFINEMENT_CELL_CENTERED_H
#define REFINEMENT_CELL_CENTERED_H

namespace olb {

namespace refinement {

/// Proxy class for accessing fine childs of a coarse cell in cell-centered refinement
template <typename CELL>
class CellCenteredFineCells {
private:
  CELL _cell;

public:
  using value_t = typename CELL::value_t;
  using descriptor_t = typename CELL::descriptor_t;

  /// Expects fine cell of the lower left orthant of the coarse cell volume
  CellCenteredFineCells(CELL&& cell) any_platform
  : _cell{std::move(cell)} { }

  /// Returns fine representing the orthant of the present coarse cell volume
  /**
   * Indexing from the perspective a virtual fine vertex co-incident with the coarse vertex.
   * i.e. the lower left orthant in 2d is (-1,-1) while the upper right orthant is (1,1).
   **/
  auto child(Vector<int,CELL::descriptor_t::d> orthant) any_platform {
    return _cell.neighbor(minv(orthant + 1, Vector<int,CELL::descriptor_t::d>(1)));
  }

};

}

}

#endif
