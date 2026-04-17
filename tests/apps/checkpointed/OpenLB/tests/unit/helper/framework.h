/*  This file is part of the OpenLB library
*
*  Copyright (C) 2018 Markus Mohrhard
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

#include <gtest/gtest.h>

#include <olb.h>

#include <iostream>

class OlbInitTestEnvironment : public ::testing::Environment {
private:

  char** argv;

public:
  OlbInitTestEnvironment()
  {
    argv = new char*[1];
    argv[0] = new char[5];
    strncpy(argv[0], "test", 5);
  }

  ~OlbInitTestEnvironment() override
  {
    delete[] argv[0];
    delete[] argv;
  }

  void SetUp() override
  {
    int argc = 1;
    olb::initialize(&argc, &argv);
  }

};
