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

#ifndef BLOCK_VTU_SURFACE_WRITER_HH
#define BLOCK_VTU_SURFACE_WRITER_HH
#include <string>
#include "blockVtuSurfaceWriter.h"
#include <ranges>

namespace olb {

template <typename T>
BlockVtuSurfaceWriter<T>::BlockVtuSurfaceWriter(std::string& name, std::size_t& blockNumber, STLreader<T>& stlReader,
                                                CuboidDecomposition3D<T>& cuboidDecomposition,
                                                LoadBalancer<T>& loadBalancer, bool binary)
    : _name(name)
    , _blockNumber(blockNumber)
    , _cuboidDecomposition(cuboidDecomposition)
    , _loadBalancer(loadBalancer)
    , _binary(binary)
    , clout(std::cout, "VTUsurfaceWriter3D")
{
  decomposeStl(stlReader);
}

template <typename T>
void BlockVtuSurfaceWriter<T>::preambleVTU()
{
  std::ofstream fout(_fullName.c_str(), std::ios::trunc);
  if (!fout) {
    clout << "Error: could not open " << _fullName << std::endl;
  }
  fout << "<?xml version=\"1.0\"?>\n";
  fout << "<VTKFile type=\"UnstructuredGrid\" version=\"1.0\" byte_order=\"LittleEndian\">\n";
  fout << "<UnstructuredGrid>\n";
  fout << "<Piece NumberOfPoints=\"" << _localPoints.size() + _remotePoints.size() << "\" NumberOfCells=\""
       << _blockConnectivity.size() << "\">" << std::endl;
  fout << "<PointData Vectors=\"Particles\">\n";
  fout.close();
}

template <typename T>
void BlockVtuSurfaceWriter<T>::writeDataHeader(std::size_t& dimF, std::string& functorName)
{
  std::ofstream fout(_fullName.c_str(), std::ios::app);
  if (!fout) {
    clout << "Error: could not open " << _fullName << std::endl;
  }

  if (!_binary) {
    fout << "<DataArray type=\"Float32\" Name=\"" << functorName << "\" NumberOfComponents=\"" << dimF << "\">"
         << std::endl;
  }
  else if (_binary) {
    fout << "<DataArray type=\"Float32\" Name=\"" << functorName
         << "\" format=\"binary\" encoding=\"base64\" NumberOfComponents=\"" << dimF << "\">" << std::endl;
  }
}

template <typename T>
void BlockVtuSurfaceWriter<T>::writeLocalData(AnalyticalF3D<T, T>& f)
{
  if (!_binary) {
    std::vector<T>    data;
    const std::size_t dimF = f.getTargetDim();
    for (auto& point : _localPoints) {
      T* val = new T[dimF]();
      f(val, point.data());
      data.insert(data.end(), val, val + dimF);
      delete[] val;
    }
    std::ofstream fout(_fullName.c_str(), std::ios::app);
    for (auto& entry : data) {
      fout << entry << " ";
    }
    fout.close();
  }
  if (_binary) {
    std::vector<T>    data;
    const std::size_t dimF = f.getTargetDim();
    data.reserve(_localPoints.size() * dimF);

    std::vector<T> val(dimF);
    for (auto& point : _localPoints) {
      f(val.data(), point.data());
      data.insert(data.end(),  std::make_move_iterator(val.begin()), std::make_move_iterator(val.end()));
    }

    std::ofstream binFout(_fullName, std::ios::app | std::ios::binary);

    unsigned int binarySize =
        static_cast<unsigned int>((_remotePoints.size() + _localPoints.size()) * dimF * sizeof(float));

    Base64Encoder<unsigned int> sizeEncoder(binFout, 1);
    sizeEncoder.encode(&binarySize, 1);

    if (!_remotePoints.empty()) {
      _dataBuffer.insert(_dataBuffer.end(), std::make_move_iterator(data.begin()), std::make_move_iterator(data.end()));
    }
    else {
      Base64Encoder<float> dataEncoder(binFout, data.size());
      dataEncoder.encode(reinterpret_cast<const float*>(data.data()), data.size());
    }

    binFout.close();
  }
}

template <typename T>
void BlockVtuSurfaceWriter<T>::writeRemoteData(std::vector<T>& data)
{
  if (!_binary) {
    std::ofstream fout(_fullName.c_str(), std::ios::app);
    for (auto& entry : data) {
      fout << entry << " ";
    }
    fout.close();
  }
  if (_binary) {
    std::ofstream binFout(_fullName.c_str(), std::ios::app | std::ios::binary);
    _dataBuffer.insert(_dataBuffer.end(), std::make_move_iterator(data.begin()), std::make_move_iterator(data.end()));

    Base64Encoder<float> dataEncoder(binFout, data.size());
    dataEncoder.encode(reinterpret_cast<const float*>(_dataBuffer.data()), _dataBuffer.size());
    binFout.close();
    _dataBuffer.clear();
  }
}

template <typename T>
void BlockVtuSurfaceWriter<T>::closeDataArray()
{
  std::ofstream fout(_fullName.c_str(), std::ios::app);
  fout << "</DataArray>\n";
  fout.close();
}

template <typename T>
void BlockVtuSurfaceWriter<T>::writeConnectivity()
{
  std::ofstream fout(_fullName.c_str(), std::ios::app);
  if (!fout) {
    clout << "Error: could not open " << _fullName << std::endl;
  }

  fout << "</PointData>\n";
  fout << "<CellData />\n";
  fout << "<Cells>\n";
  fout << "<DataArray type=\"Int32\" Name=\"connectivity\" format=\"ascii\">\n";
  // if there are no connections between the points, connectivity simply counts up
  if (_blockConnectivity.size() == 0) {
    for (std::size_t j = 0; j < _localPoints.size() + _remotePoints.size(); ++j) {
      fout << j << " ";
    }
  }
  // if there are connections, connectivity is written out
  else {
    for (std::size_t j = 0; j < _blockConnectivity.size(); ++j) {
      for (std::size_t k = 0; k < 3; ++k) {
        fout << _blockConnectivity[j][k] << " ";
      }
      if (j % 2 == 1) {
        fout << "\n";
      }
    }
  }

  fout << "</DataArray>\n";
  fout << "<DataArray type=\"Int32\" Name=\"offsets\" format=\"ascii\">\n";
  // if there are no connections, offsets just count up
  if (_blockConnectivity.size() == 0) {
    for (std::size_t j = 1; j <= _blockConnectivity.size(); ++j) {
      fout << j << " ";
      if (j % 6 == 0) {
        fout << "\n";
      }
    }
    // if connections are present, offset is multiplied by 3
  }
  else { //_connectivity.size() != 0
    for (std::size_t i = 0; i < 1; ++i) {
      for (std::size_t j = 1; j <= _blockConnectivity.size(); ++j) {
        fout << j * 3 << " ";
        if (j % 6 == 0) {
          fout << "\n";
        }
      }
    }
  }
  // Connected points have the type 5, unconnected points have the type 3
  fout << "</DataArray>\n";
  fout << "<DataArray type=\"UInt8\" Name=\"types\" format=\"ascii\">\n";
  if (_blockConnectivity.size() != 0) {
    for (std::size_t j = 0; j < _blockConnectivity.size(); ++j) {
      fout << 5 << " ";
      if (j % 6 == 0) {
        fout << "\n";
      }
    }
  }
  else {
    for (std::size_t j = 0; j < _localPoints.size() + _remotePoints.size(); ++j) {
      fout << 3 << " ";
      if (j % 6 == 0) {
        fout << "\n";
      }
    }
  }

  // write out all coordinates of points
  fout << "</DataArray>\n";
  fout << "</Cells>\n";
  fout << "<Points>\n";
  writePosition(fout);
  fout << "</Points>\n";
  fout << "</Piece>\n";
}

template <typename T>
void BlockVtuSurfaceWriter<T>::writePosition(std::ofstream& fout)
{
  fout << "<DataArray type=\"Float32\" Name=\"Point\" NumberOfComponents=\"" << 3 << "\">\n";
  for (auto& point : _localPoints) {
    fout << point[0] << " " << point[1] << " " << point[2] << "\n";
  }
  for (auto& point : _remotePoints) {
    fout << point[0] << " " << point[1] << " " << point[2] << "\n";
  }
  fout << "</DataArray>" << std::endl;
}

template <typename T>
void BlockVtuSurfaceWriter<T>::closeVTU()
{
  std::ofstream fout(_fullName.c_str(), std::ios::app);
  if (!fout) {
    clout << "Error: could not open " << _fullName << std::endl;
  }
  fout << "</UnstructuredGrid>\n";
  fout << "</VTKFile>\n";
  fout.close();
}

template <typename T>
void BlockVtuSurfaceWriter<T>::createFullName(const std::size_t& iT)
{
  _fullName = singleton::directories().getVtkOutDir() + "data/" + createFileName(_name, iT, _blockNumber) + ".vtu";
}

template <typename T>
std::vector<Vector<T, 3>> BlockVtuSurfaceWriter<T>::removeDuplicates(const std::vector<Vector<T, 3>>& points)
{
  struct VectorHash {
    std::size_t operator()(const std::vector<T>& v) const
    {
      return std::hash<T>()(v[0]) ^ std::hash<T>()(v[1]) ^ std::hash<T>()(v[2]);
    }
  };

  struct VectorEqual {
    bool operator()(const std::vector<T>& a, const std::vector<T>& b) const
    {
      return a[0] == b[0] && a[1] == b[1] && a[2] == b[2];
    }
  };
  std::vector<std::vector<T>> pointsVec;
  for (const Vector<T, 3>& point : points) {
    pointsVec.push_back({point[0], point[1], point[2]});
  }
  std::unordered_set<std::vector<T>, VectorHash, VectorEqual> uniquePoints(pointsVec.begin(), pointsVec.end());
  std::vector<Vector<T, 3>>                                   uniquePointsVec;
  for (const auto& pt : uniquePoints) {
    uniquePointsVec.emplace_back(pt[0], pt[1], pt[2]);
  }

  return std::vector<Vector<T, 3>>(uniquePointsVec.begin(), uniquePointsVec.end());
}

template <typename T>
void BlockVtuSurfaceWriter<T>::decomposeStl(STLreader<T>& stlReader)
{
  STLmesh<T>& mesh = stlReader.getMesh();
  for (const STLtriangle<T>& triangle : mesh.getTriangles()) {
    Vector<T, 3> center = (triangle.point[0] + triangle.point[1] + triangle.point[2]) / 3.0;
    if (isPointLocal(center)) {
      if (isPointLocal(triangle.point[0])) {
        _localPoints.emplace_back(triangle.point[0]);
      }
      else {
        _remotePoints.emplace_back(triangle.point[0]);
      }
      if (isPointLocal(triangle.point[1])) {
        _localPoints.emplace_back(triangle.point[1]);
      }
      else {
        _remotePoints.emplace_back(triangle.point[1]);
      }
      if (isPointLocal(triangle.point[2])) {
        _localPoints.emplace_back(triangle.point[2]);
      }
      else {
        _remotePoints.emplace_back(triangle.point[2]);
      }
    }
  }
  _localPoints  = removeDuplicates(_localPoints);
  _remotePoints = removeDuplicates(_remotePoints);

  for (STLtriangle<T>& triangle : mesh.getTriangles()) {
    Vector<T, 3> center = (triangle.point[0] + triangle.point[1] + triangle.point[2]) / 3.0;
    if (isPointLocal(center)) {
      std::vector<std::size_t> connectivity(3);
      connectivity[0] = getBlockPointIndex(triangle.point[0]);
      connectivity[1] = getBlockPointIndex(triangle.point[1]);
      connectivity[2] = getBlockPointIndex(triangle.point[2]);
      _blockConnectivity.emplace_back(std::move(connectivity));
    }
  }
}

template <typename T>
bool BlockVtuSurfaceWriter<T>::areVectorsEqual(const Vector<T, 3>& v1, const Vector<T, 3>& v2, T epsilon)
{
  for (std::size_t i = 0; i < v1.size(); ++i) {
    if (std::fabs(v1[i] - v2[i]) > epsilon) {
      return false;
    }
  }
  return true;
}

template <typename T>
int BlockVtuSurfaceWriter<T>::getBlockPointIndex(const Vector<T, 3>& point)
{
  auto it = std::find_if(_localPoints.begin(), _localPoints.end(), [&point](const Vector<T, 3>& p) {
    return areVectorsEqual(p, point);
  });
  if (it != _localPoints.end()) {
    return std::distance(_localPoints.begin(), it);
  }

  auto remoteIt = std::find_if(_remotePoints.begin(), _remotePoints.end(), [&point](const Vector<T, 3>& p) {
    return areVectorsEqual(p, point);
  });
  if (remoteIt != _remotePoints.end()) {
    return _localPoints.size() + std::distance(_remotePoints.begin(), remoteIt);
  }

  return -1;
}

template <typename T>
bool BlockVtuSurfaceWriter<T>::isPointLocal(const Vector<T, 3>& point)
{
  return (_blockNumber == std::size_t(_cuboidDecomposition.getC(point).value()));
}

} // namespace olb
#endif
