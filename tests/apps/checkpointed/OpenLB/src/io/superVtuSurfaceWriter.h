/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2025 Christoph Gaul
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

#ifndef SUPER_VTU_SURFACE_WRITER_H
#define SUPER_VTU_SURFACE_WRITER_H

#include "functors/lattice/superBaseF3D.h"
#include "functors/analytical/interpolationF3D.h"
#include "io/base64.hh"
#include "io/stlReader.h"
#include "communication/mpiManager.h"
#include "blockVtuSurfaceWriter.h"

namespace olb {

template <typename T>
class SuperVtuSurfaceWriter {
protected:
  std::string                       _name;
  std::vector<SuperF3D<T, T>*>      _functors;
  std::vector<AnalyticalF3D<T, T>*> _functorsA;

  CuboidDecomposition3D<T>&             _cuboidDecomposition;
  LoadBalancer<T>&                      _loadBalancer;
  bool                                  _binary {};
  std::vector<BlockVtuSurfaceWriter<T>> _blockWriters;
  OstreamManager                        clout;
  ///  performes <VTKFile ...> and <Collection>
  void preamblePVD(const std::string& fullNamePVD);
  ///  performes </Collection> and </VTKFile>
  void closePVD(const std::string& fullNamePVD);
  void dataPVDmaster(int iT, int i, const std::string& fullNamePVDMaster);
  /// writes pvtu file to link multiple vtu files
  void preamblePVTU(const std::string& fullNameVTM);

  void dataPVTU(int iT, const std::string& fullNameVTM);
  /// closes pvtu file
  void closePVTU(const std::string& fullNameVTM);
  ///  performes <DataSet timestep= ... file=namePiece />
  void dataArray(const std::string& fullName);
  ///  interpolates and writes functors stored at functors
  void writeFunctor(const std::string& fullName, std::ofstream& fout, SuperF3D<T, T>& f);
  /// writes functors.
  void writeAnalyticalFunctor(const std::string& fullName, std::ofstream& fout, AnalyticalF3D<T, T>& f);

  int  getRankOfPosition(const Vector<T, 3>& position);
  int  getRankOfTriangle(const STLtriangle<T>& triangle);
  void createBlockWriters(STLreader<T>& stlReader);

public:
  SuperVtuSurfaceWriter(std::string name, CuboidDecomposition3D<T>& cuboidDecomposition, LoadBalancer<T>& loadBalancer,
                        STLreader<T>& stlReader, bool binary = false);
  void createMasterFile();
  void write(const std::size_t& iT);
  /// Schedule analytical functor for output
  void addFunctor(AnalyticalF3D<T, T>& f);
  /// Schedule lattice functor for output (interpolates)
  void addFunctor(SuperF3D<T, T>& f);
};

} // namespace olb

#endif
