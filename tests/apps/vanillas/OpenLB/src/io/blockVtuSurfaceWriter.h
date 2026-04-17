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
#ifndef BLOCK_VTU_SURFACE_WRITER_H
#define BLOCK_VTU_SURFACE_WRITER_H
#include <string>
namespace olb {

template <typename T>
class BlockVtuSurfaceWriter {
protected:
  std::string                           _name;
  std::string                           _fullName;
  std::vector<Vector<T, 3>>             _localPoints;
  std::vector<Vector<T, 3>>             _remotePoints; // points that are not local but have to be written by this rank
  std::vector<std::vector<std::size_t>> _blockConnectivity;
  std::size_t                           _blockNumber {};
  CuboidDecomposition3D<T>&             _cuboidDecomposition;
  LoadBalancer<T>&                      _loadBalancer;
  bool                                  _binary {};
  OstreamManager                        clout;
  std::vector<float>                    _dataBuffer; // temporary storage for point data
  ///  performes <VTKFile ...>, <ImageData ...> and <PieceExtent ...>
  void preambleVTU(int num);
  ///  performes </ImageData> and </VTKFile>

  ///  interpolates and writes functors stored at functors
  void writeFunctor(const std::string& fullName, std::ofstream& fout, SuperF3D<T, T>& f);
  /// writes functors.
  void writeAnalyticalFunctor(const std::string& fullName, std::ofstream& fout, AnalyticalF3D<T, T>& f);
  /// writes coordinates of points
  void                      writePosition(std::ofstream& fout);
  std::vector<Vector<T, 3>> removeDuplicates(const std::vector<Vector<T, 3>>& points);
  void                      decomposeStl(STLreader<T>& stlReader);
  static bool               areVectorsEqual(const Vector<T, 3>& v1, const Vector<T, 3>& v2,
                                            T epsilon = util::numericLimits::epsilon<T>());
  bool                      isPointLocal(const Vector<T, 3>& point);
  int                       getBlockPointIndex(const Vector<T, 3>& point);

public:
  BlockVtuSurfaceWriter(std::string& name, size_t& blockNumber, STLreader<T>& stlReader,
                        CuboidDecomposition3D<T>& cuboidDecomposition, LoadBalancer<T>& loadBalancer,
                        bool binary = false);
  /// main function, writes the vtu file
  void                      writeFunctorData(std::vector<T>& data, std::size_t& dimF, std::string& name);
  void                      preambleVTU();
  void                      closeVTU();
  void                      createFullName(const std::size_t& iT);
  void                      writeDataHeader(std::size_t& dimF, std::string& functorName);
  void                      writeLocalData(AnalyticalF3D<T, T>& f);
  void                      writeRemoteData(std::vector<T>& data);
  void                      closeDataArray();
  void                      writeConnectivity();
  std::vector<Vector<T, 3>> getRemotePoints() { return _remotePoints; }
  std::size_t               getBlockNumber() { return _blockNumber; }
  std::size_t               getNumBlockPoints() { return (_localPoints.size() + _remotePoints.size()); }
};

} // namespace olb
#endif
