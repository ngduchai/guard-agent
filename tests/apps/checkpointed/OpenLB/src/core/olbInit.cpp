/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2008 Jonas Latt
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

#include "olbInit.h"
#include <exception>
#include <iostream>
#include <cstdlib>

namespace olb {

namespace singleton {

ThreadPool& pool()
{
  static ThreadPool instance;
  return instance;
}

}

void terminateHandler() {
  int rank = singleton::mpi().getRank();

  std::cerr << "[core] (Rank " << rank << "): Terminating..." << std::endl;
  try {
    std::exception_ptr p = std::current_exception();
    if (p) {
      std::rethrow_exception(p);
    } else {
      std::cerr << "Called without active exception." << std::endl;
    }
  } catch (const std::exception& e) {
    std::cerr << "Uncaught exception: " << e.what() << std::endl;
  } catch (...) {
    std::cerr << "Unknown uncaught exception." << std::endl;
  }

  std::cerr << R"(
This is an unexpected error.
If you believe this is a bug in OpenLB, please open an issue at:
  https://gitlab.com/openlb/public

Other support channels:
  - User Forum:       https://www.openlb.net/forum
  - Spring School:    https://www.openlb.net/spring-school
  - Consortium:       https://www.openlb.net/consortium
)" << std::endl;

  std::abort();
}

}
