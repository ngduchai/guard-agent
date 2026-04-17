/*  This file is part of the OpenLB library
 *
 *  Copyright (C) 2024 Christoph Gaul
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

#ifndef VTU_SURFACE_WRITER_RANKWISE_HH
#define VTU_SURFACE_WRITER_RANKWISE_HH

#include "vtuSurfaceWriterRankwise.h"

#include <cmath>
#include <unordered_set>
#include <unordered_map>

namespace olb {

template <typename T>
VTUsurfaceWriterRankwise<T>::VTUsurfaceWriterRankwise(std::string const name, CuboidDecomposition3D<T>& cuboidDecomposition,
                                      LoadBalancer<T>& loadBalancer, bool binary)
    : _name(name)
    , _cuboidDecomposition(cuboidDecomposition)
    , _loadBalancer(loadBalancer)
    , _binary(binary)
    , clout(std::cout, "VTUsurfaceWriter3D")
{}

template <typename T>
void VTUsurfaceWriterRankwise<T>::addFunctor(AnalyticalF3D<T, T>& f)
{
  _functorsA.push_back(&f);
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::addFunctor(SuperF3D<T, T>& f)
{
  _functors.push_back(&f);
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::addPoints(std::vector<Vector<T, 3>>& newPositions)
{
  for (std::size_t i = 0; i < newPositions.size(); i++) {
    addPoint(newPositions[i]);
  }
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::addPoint(const Vector<T, 3>& new_position)
{
  int rank     = getRankOfPosition(new_position);
#ifdef PARALLEL_MODE_MPI
  int rootRank = rank;
  singleton::mpi().allreduce(&rootRank, &rootRank, 1, MPI_MAX);
  singleton::mpi().bCast(&rank, 1, rootRank);
#endif
  assert(rank >= 0 && rank < singleton::mpi().getSize());

  _pos.push_back({new_position, size_t(rank)});
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::addConnectivity(std::vector<std::vector<std::size_t>>& connections)
{
  for (std::size_t i = 0; i < connections.size(); i++) {
    _connectivity.push_back(connections[i]);
  }
}

///writes vtu files and assigns values
template <typename T>
void VTUsurfaceWriterRankwise<T>::write(std::size_t iT)
{
  std::size_t rank = 0;
#ifdef PARALLEL_MODE_MPI
  rank = singleton::mpi().getRank();
#endif

  for (SuperF3D<T, T>* f : _functors) {
    f->getSuperStructure().communicate();
  }
  std::string fullNamePVDmaster = singleton::directories().getVtkOutDir() + createFileName(_name) + ".pvd";
  std::string fullNamePVTU = singleton::directories().getVtkOutDir() + "data/" + createFileName(_name, iT) + ".pvtu";
  std::string namePiece    = "data/" + createFileName(_name, iT, 0) + ".vtu";
  //master writes master .pvd file and .pvtu file of every timestep
  if (rank == 0) {
    // puts name of .vtu piece to a .pvd file [fullNamePVD]
    // adds a namePiece to master.pvd file.
    dataPVDmaster(iT, 1, fullNamePVDmaster);
    std::string fullNamePVTU = singleton::directories().getVtkOutDir() + "data/" + createFileName(_name, iT) + ".pvtu";
    preamblePVTU(fullNamePVTU); // timestep
    std::string namePiece = "data/" + createFileName(_name, iT, 0) + ".vtu";
    dataPVTU(iT, fullNamePVTU);
    closePVTU(fullNamePVTU);
    // adds a namePiece to master.pvd file.
    // To do so we overwrite closePVD() and add new entry.
  }

  std::string fullNameVTU =
      singleton::directories().getVtkOutDir() + "data/" + createFileName(_name, iT, rank) + ".vtu";
  preambleVTU(fullNameVTU, _blockPoints.size());
  //writes data arrays into vtu file. All ranks are needed for this
  this->dataArray(fullNameVTU);
  closeVTU(fullNameVTU);
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::preambleVTU(const std::string& fullName, int num)
{
  std::ofstream fout(fullName.c_str(), std::ios::trunc);
  if (!fout) {
    clout << "Error: could not open " << fullName << std::endl;
  }
  fout << "<?xml version=\"1.0\"?>" << std::endl << std::flush;
  fout << "<VTKFile type=\"UnstructuredGrid\" version=\"1.0\" byte_order=\"LittleEndian\">" << std::endl;
  fout << "<UnstructuredGrid>" << std::endl;
  fout << "<Piece NumberOfPoints=\"" << num << "\" NumberOfCells=\"" << _localConnectivity.size() << "\">" << std::endl;
  fout << "<PointData Vectors=\"Particles\">" << std::endl;
  fout.close();
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::closeVTU(const std::string& fullNamePiece)
{
  std::ofstream fout(fullNamePiece.c_str(), std::ios::app);
  if (!fout) {
    clout << "Error: could not open " << fullNamePiece << std::endl;
  }
  fout << "</UnstructuredGrid>\n";
  fout << "</VTKFile>\n";
  fout.close();
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::dataPVDmaster(int iT, int i, const std::string& fullNamePVDMaster)
{
  std::ofstream fout(fullNamePVDMaster.c_str(), std::ios::in | std::ios::out | std::ios::ate);
  if (!fout) {
    clout << "Error: could not open " << fullNamePVDMaster << std::endl;
  }
  fout.seekp(-25, std::ios::end);
  std::string namePiece = "data/" + createFileName(_name, iT) + ".pvtu";
  fout << "<DataSet timestep=\"" << iT << "\" " << "group=\"\" part=\" " << 0 << "\" " << "file=\"" << namePiece
       << "\"/>\n";
  fout.close();
  closePVD(fullNamePVDMaster);
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::createMasterFile()
{
  int rank = 0;
#ifdef PARALLEL_MODE_MPI
  rank = singleton::mpi().getRank();
#endif
  if (rank == 0) {
    std::string fullNamePVDmaster = singleton::directories().getVtkOutDir() + createFileName(_name) + ".pvd";
    preamblePVD(fullNamePVDmaster);
    closePVD(fullNamePVDmaster);
  }
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::preamblePVTU(const std::string& fullNamePVTU)
{
  std::ofstream fout(fullNamePVTU.c_str(), std::ios::trunc);
  if (!fout) {
    clout << "Error: could not open " << fullNamePVTU << std::endl;
  }
  fout << "<?xml version=\"1.0\"?>\n";
  fout << "<VTKFile type=\"PUnstructuredGrid\" version=\"0.1\" byte_order=\"LittleEndian\"> \n"
       << "<PUnstructuredGrid GhostLevel=\"0\">\n"
       << "<PPoints>\n"
       << "<PDataArray type=\"Float32\" Name=\"Position\" NumberOfComponents=\"3\"/>\n"
       << "</PPoints>\n"
       << "<PCells>\n"
       << "<PDataArray type=\"Int32\" Name=\"connectivity\" NumberOfComponents=\"1\"/>\n"
       << "<PDataArray type=\"Int32\" Name=\"offsets\" NumberOfComponents=\"1\"/>\n"
       << "<PDataArray type=\"UInt8\" Name=\"types\" NumberOfComponents=\"1\"/>\n"
       << "</PCells>\n";

    fout << "<PPointData>\n";
  for (std::size_t iFunctor = 0; iFunctor < _functors.size(); ++iFunctor) {
    fout << "<PDataArray type=\"Float32\" Name=\"" << "fromSuperF(" << _functors[iFunctor]->getName() << ")"
         << "\" NumberOfComponents=\"" << _functors[iFunctor]->getTargetDim() << "\"/>\n";

  }
  for (std::size_t iFunctor = 0; iFunctor < _functorsA.size(); ++iFunctor) {
     fout<< "<PDataArray type=\"Float32\" Name=\"" << _functorsA[iFunctor]->getName() << "\" NumberOfComponents=\""
         << _functorsA[iFunctor]->getTargetDim() << "\"/>\n";
  }
  fout << "</PPointData>\n";
  fout.close();
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::dataPVTU(int iT, const std::string& fullNamePVTU)
{
  std::ofstream fout(fullNamePVTU.c_str(), std::ios::app);
  if (!fout) {
    clout << "Error: could not open " << fullNamePVTU << std::endl;
  }

  for (int iRank = 0; iRank < singleton::mpi().getSize(); ++iRank) {
    fout << "<Piece Source =\"" << createFileName(_name, iT, iRank) + ".vtu" << "\"/>" << std::endl;
  }
  fout.close();
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::closePVTU(const std::string& fullNamePVTU)
{
  int rank = 0;
#ifdef PARALLEL_MODE_MPI
  rank = singleton::mpi().getRank();
#endif
  if (rank == 0) {

    std::ofstream fout(fullNamePVTU.c_str(), std::ios::app);
    if (!fout) {
      clout << "Error: could not open " << fullNamePVTU << std::endl;
    }
    fout << "</PUnstructuredGrid>\n";
    fout << "</VTKFile>\n";
    fout.close();
  }
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::preamblePVD(const std::string& fullNamePVD)
{
  std::ofstream fout(fullNamePVD.c_str(), std::ios::trunc);
  if (!fout) {
    clout << "Error: could not open " << fullNamePVD << std::endl;
  }
  fout << "<?xml version=\"1.0\"?>\n";
  fout << "<VTKFile type=\"Collection\" version=\"0.1\" byte_order=\"LittleEndian\">\n"
       << "<Collection>\n";
  fout.close();
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::closePVD(const std::string& fullNamePVD)
{
  int rank = 0;
#ifdef PARALLEL_MODE_MPI
  rank = singleton::mpi().getRank();
#endif
  if (rank == 0) {

    std::ofstream fout(fullNamePVD.c_str(), std::ios::app);
    if (!fout) {
      clout << "Error: could not open " << fullNamePVD << std::endl;
    }
    fout << "</Collection>\n";
    fout << "</VTKFile>\n";
    fout.close();
  }
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::dataArray(const std::string& fullName)
{

  std::ofstream fout(fullName.c_str(), std::ios::app);
  if (!fout) {
    clout << "Error: could not open " << fullName << std::endl;
  }

  for (std::size_t i = 0; i < _functors.size(); i++) {
    writeFunctor(fullName, fout, *_functors[i]);
  }

  for (std::size_t i = 0; i < _functorsA.size(); i++) {
    writeAnalyticalFunctor(fullName, fout, *_functorsA[i]);
  }

  fout << "</PointData>" << std::endl;
  fout << "<CellData /> " << std::endl;
  fout << "<Cells>" << std::endl;
  fout << "<DataArray type=\"Int32\" Name=\"connectivity\" format=\"ascii\">" << std::endl;
  // if there are no connections between the points, connectivity simply counts up
  if (_connectivity.size() == 0) {
    for (std::size_t j = 0; j < _pos.size(); ++j) {
      fout << j << " ";
    }
  }
  // if there are connections, connectivity is written out
  else {
    for (std::size_t j = 0; j < _localConnectivity.size(); ++j) {
      for (std::size_t k = 0; k < 3; ++k) {
        fout << _localConnectivity[j][k] << " ";
      }
      if (j % 2 == 0) {
        fout << std::endl;
      }
    }
  }

  fout << "</DataArray>" << std::endl;
  fout << "<DataArray type=\"Int32\" Name=\"offsets\" format=\"ascii\">" << std::endl;
  // if there are no connections, offsets just count up
  if (_connectivity.size() == 0) {
    for (std::size_t j = 1; j <= _localConnectivity.size(); ++j) {
      fout << j << " ";
      if (j % 6 == 0) {
        fout << std::endl;
      }
    }
    // if connections are present, offset is multiplied by 3
  }
  else { //_connectivity.size() != 0
    for (std::size_t i = 0; i < 1; ++i) {
      for (std::size_t j = 1; j <= _localConnectivity.size(); ++j) {
        fout << j * 3 << " ";
        if (j % 6 == 0) {
          fout << std::endl;
        }
      }
    }
  }
  // Connected points have the type 5, unconnected points have the type 3
  fout << "</DataArray>" << std::endl;
  fout << "<DataArray type=\"UInt8\" Name=\"types\" format=\"ascii\">" << std::endl;
  if (_connectivity.size() != 0) {
    for (std::size_t j = 0; j < _localConnectivity.size(); ++j) {
      fout << 5 << " ";
      if (j % 6 == 0) {
        fout << std::endl;
      }
    }
  }
  else {
    for (std::size_t j = 0; j < _pos.size(); ++j) {
      fout << 3 << " ";
      if (j % 6 == 0) {
        fout << std::endl;
      }
    }
  }

  // write out all coordinates of points
  fout << "</DataArray>" << std::endl;
  fout << "</Cells>" << std::endl;
  fout << "<Points>" << std::endl;
  writePosition(fout);
  fout << "</Points>" << std::endl;
  fout << "</Piece>" << std::endl;

  fout.close();
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::writePosition(std::ofstream& fout)
{
  fout << "<DataArray type=\"Float32\" Name=\"Point\" NumberOfComponents=\"" << 3 << "\">" << std::endl;

  for (std::size_t j = 0; j < _blockPoints.size(); ++j) {
    fout << _pos[_blockPoints[j]].coordinates[0] << " " << _pos[_blockPoints[j]].coordinates[1] << " "
         << _pos[_blockPoints[j]].coordinates[2] << " " << std::endl;
  }
  fout << "</DataArray>" << std::endl;
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::writeFunctor(const std::string& fullName, std::ofstream& fout, SuperF3D<T, T>& f)
{
  AnalyticalFfromSuperF3D<T> interpolateF(f, false);
  writeAnalyticalFunctor(fullName, fout, interpolateF);
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::writeAnalyticalFunctor(const std::string& fullName, std::ofstream& fout,
                                                 AnalyticalF3D<T, T>& f)
{
  std::size_t dimF = f.getTargetDim();

  //Header DataArray, ascii or Base64 binary
#ifdef PARALLEL_MODE_MPI
  std::size_t rank = 0;
  rank = singleton::mpi().getRank();
#endif

  if (!_binary) {
    fout << "<DataArray type=\"Float32\" Name=\"" << f.getName() << "\" NumberOfComponents=\"" << dimF << "\">"
         << std::endl;
  }
  else if (_binary) {
    fout << "<DataArray type=\"Float32\" Name=\"" << f.getName()
         << "\" format=\"binary\" encoding=\"base64\" NumberOfComponents=\"" << dimF << "\">" << std::endl;
  }

  if (_binary) {
    fout.close();
  }
  std::size_t                 numPoints = _pos.size();
  std::ofstream               ofstr(fullName.c_str(), std::ios::out | std::ios::app | std::ios::binary);
  std::size_t                 binarySize = std::size_t(numPoints * dimF * sizeof(float));
  Base64Encoder<unsigned int> sizeEncoder(ofstr, 1);
  unsigned int                uintBinarySize = (unsigned int)binarySize;
  if (_binary) {
    sizeEncoder.encode(&uintBinarySize, 1);
  }
  Base64Encoder<float> dataEncoder(ofstr, numPoints);

#ifdef PARALLEL_MODE_MPI
  std::vector<T> data{};
 // Checks for all points if this point has to be written out by the specific rank.
 // Then the owner rank evaluates the functor and sends it to all ranks that need to write it
  for (std::size_t iPoint = 0; iPoint < _pos.size(); ++iPoint) {
    bool pointInBlockPoints = contains(_blockPoints, iPoint);
    if (pointInBlockPoints || _pos[iPoint].ownerRank == rank) {
      T* val = new T[dimF]();
      if (rank == _pos[iPoint].ownerRank) {
        f(val, _pos[iPoint].coordinates.data());
        if (pointInBlockPoints && _pos[iPoint].ownerRank == rank) {
          for (std::size_t i = 0; i < dimF; ++i) {
            data.push_back(val[i]);
          }
        }
      }

      if (!_pos[iPoint].requiredRanks.empty()) { // if Point has to be communicated, do it here
        T* recvBuffer = new T[dimF]();
        if (rank == _pos[iPoint].ownerRank) {
          for (std::size_t iReceiverRank : _pos[iPoint].requiredRanks) {
            singleton::mpi().send(val, dimF, iReceiverRank, iReceiverRank);
          }
        }
        else if (contains(_pos[iPoint].requiredRanks, rank)) {
          singleton::mpi().receive(recvBuffer, dimF, _pos[iPoint].ownerRank, rank);
        }
        if(rank != _pos[iPoint].ownerRank){
          for (std::size_t i = 0; i < dimF; ++i) {
            data.push_back(recvBuffer[i]);
          }
        }
        delete[] recvBuffer;
      }
      delete[] val;
    }
  }


  for (std::size_t jPoint = 0; jPoint < data.size(); ++jPoint) {
    if (!_binary) {
      fout << data[jPoint] << " ";
    }
    else {
      const float helper = float(data[jPoint]);
      dataEncoder.encode(&helper, 1);
    }
  }

#endif
#ifndef PARALLEL_MODE_MPI
  // write the values to the file
  std::vector<T> vals(numPoints * dimF);
  for (std::size_t j = 0; j < numPoints; ++j) {
    T  point[3] = {_pos[j].coordinates[0], _pos[j].coordinates[1], _pos[j].coordinates[2]};
    T* val      = new T[dimF]();
    f(val, point);
    for (std::size_t i = 0; i < dimF; ++i) {
      vals[i * numPoints + j] = val[i];
    }
    delete[] val;
  }

  for (std::size_t j = 0; j < numPoints; ++j) {
    for (std::size_t i = 0; i < dimF; ++i) {
      if (!_binary) {
        fout << vals[i * numPoints + j] << " ";
      }
      else {
        const float helper = float(vals[i * numPoints + j]);
        dataEncoder.encode(&helper, 1);
      }
    }
  }
#endif

  if (_binary) {
    ofstr.close();
    fout.open(fullName.c_str(), std::ios::out | std::ios::app);
  }
  fout << "</DataArray>" << std::endl;
}

template <typename T>
std::vector<Vector<T, 3>> VTUsurfaceWriterRankwise<T>::removeDuplicates(const std::vector<Vector<T, 3>>& points)
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
bool VTUsurfaceWriterRankwise<T>::areVectorsEqual(const Vector<T, 3>& v1, const Vector<T, 3>& v2, T epsilon)
{
  for (std::size_t i = 0; i < v1.size(); ++i) {
    if (std::fabs(v1[i] - v2[i]) > epsilon) {
      return false;
    }
  }
  return true;
}

template <typename T>
inline bool VTUsurfaceWriterRankwise<T>::contains(const std::vector<std::size_t>& vec, std::size_t value)
{
  return std::find(vec.begin(), vec.end(), value) != vec.end();
}

template <typename T>
std::vector<std::vector<int>> VTUsurfaceWriterRankwise<T>::mapTrianglesToIndices(STLreader<T>& stlReader)
{
  STLmesh<T> mesh = stlReader.getMesh();

  struct VectorHash {
    std::size_t operator()(const std::vector<T>& v) const
    {
      return std::hash<T>()(v[0]) ^ std::hash<T>()(v[1]) ^ std::hash<T>()(v[2]);
    }
  };

  struct VectorEqual {
    bool operator()(const std::vector<T>& a, const std::vector<T>& b) const { return areVectorsEqual(a, b); }
  };

  std::unordered_map<std::vector<T>, int, VectorHash, VectorEqual> pointIndexMap;
  std::vector<std::vector<int>>                                    indexedTriangles;

  // Create a map from points to their indices
  for (std::size_t i = 0; i < _pos.size(); ++i) {
    pointIndexMap[{_pos[i].coordinates[0], _pos[i].coordinates[1], _pos[i].coordinates[2]}] = i;
  }

  // Map each triangle's points to their indices
  for (const STLtriangle<T>& triangle : mesh.getTriangles()) {
    std::vector<int> indices(3);
    for (int j = 0; j < 3; ++j) {
      std::vector<T> pt = {triangle.point[j][0], triangle.point[j][1], triangle.point[j][2]};
      auto           it = pointIndexMap.find(pt);
      if (it != pointIndexMap.end()) {
        indices[j] = it->second;
      }
      else {
        // Handle the case where the point is not found (should not happen if removeDuplicates worked correctly)
        indices[j] = -1; // Invalid index
      }
    }
    if (indices[0] != -1 && indices[1] != -1 && indices[2] != -1) {
      indexedTriangles.push_back(indices);
    }
  }

  return indexedTriangles;
}

template <typename T>
void VTUsurfaceWriterRankwise<T>::addSTL(STLreader<T>& stlReader)
{
  STLmesh<T>                mesh = stlReader.getMesh();
  std::vector<Vector<T, 3>> points;

  // Collect points from triangles
  for (const STLtriangle<T>& triangle : mesh.getTriangles()) {
    Vector<T, 3> pt = {triangle.point[0][0], triangle.point[0][1], triangle.point[0][2]};
    points.push_back(pt);
    pt = {triangle.point[1][0], triangle.point[1][1], triangle.point[1][2]};
    points.push_back(pt);
    pt = {triangle.point[2][0], triangle.point[2][1], triangle.point[2][2]};
    points.push_back(pt);
  }
  // Remove duplicate points
  points = removeDuplicates(points);

  // Add points to pos
  for (const Vector<T, 3>& point : points) {
    addPoint(Vector<T, 3>(point[0], point[1], point[2]));
  }

  std::vector<std::vector<int>> indexedTriangles = mapTrianglesToIndices(stlReader);
  std::vector<std::size_t>      triangleRanks;

  for (const STLtriangle<T>& triangle : mesh.getTriangles()) {
    auto tri = triangle;
#ifdef PARALLEL_MODE_MPI
    int triRank  = getRankOfTriangle(tri);
    int rootRank = triRank;

    singleton::mpi().allreduce(&rootRank, &rootRank, 1, MPI_MAX);
    singleton::mpi().bCast(&triRank, 1, rootRank);

    triangleRanks.push_back(triRank);
#endif
  }

  for (std::size_t i = 0; i < indexedTriangles.size(); ++i) {
    std::vector<std::size_t> connectivityWithRank = {size_t(indexedTriangles[i][0]), size_t(indexedTriangles[i][1]),
                                                     size_t(indexedTriangles[i][2]), triangleRanks[i]};
    _connectivity.push_back(connectivityWithRank);
  }
#ifdef PARALLEL_MODE_MPI
  std::size_t rank = singleton::mpi().getRank();
  ;
  // create indices of points to write out. Attention: not all these points are actually physically present on this rank
  // some have to be sent from other ranks

  std::vector<Vector<T, 3>> localPoints;
  for (std::size_t iTriangle = 0; iTriangle < _connectivity.size(); ++iTriangle) {
    if (rank == _connectivity[iTriangle][3]) {
      localPoints.push_back(Vector<T, 3>(_pos[_connectivity[iTriangle][0]].coordinates));
      localPoints.push_back(Vector<T, 3>(_pos[_connectivity[iTriangle][1]].coordinates));
      localPoints.push_back(Vector<T, 3>(_pos[_connectivity[iTriangle][2]].coordinates));
    }
  }
  localPoints = removeDuplicates(localPoints);
  // create index list of local positions
  for (std::size_t iPoint = 0; iPoint < _pos.size(); ++iPoint) {
    int helperRank = -1;
    for (Vector<T, 3>& point : localPoints) {
      if (areVectorsEqual(point, _pos[iPoint].coordinates)) {
        _blockPoints.push_back(iPoint);
        if (!_loadBalancer.isLocal(_cuboidDecomposition.getC(_pos[iPoint].coordinates).value())) {
          helperRank = rank;
        }
      }
    } // share requiredRanks with other ranks

    std::vector<int> allEntries(singleton::mpi().getSize(), 0);
    singleton::mpi().allGather(&helperRank, 1, allEntries.data(), 1);

    auto it = std::remove(allEntries.begin(), allEntries.end(), -1);
    allEntries.erase(it, allEntries.end());
    for (std::size_t i = 0; i < allEntries.size(); ++i) {
      if (size_t(allEntries[i]) != _pos[iPoint].ownerRank) {
        _pos[iPoint].requiredRanks.push_back(allEntries[i]);
      }
    }
  }

  // create local connectivity list, as not every rank writes all points, so connectivity has to be adapted
  for (std::size_t iTriangle = 0; iTriangle < _connectivity.size(); ++iTriangle) {
    if (rank == _connectivity[iTriangle][3]) {
      std::vector<std::size_t> connectivity(3);
      for (std::size_t jPoint = 0; jPoint < _blockPoints.size(); ++jPoint) {
        if (areVectorsEqual(_pos[_blockPoints[jPoint]].coordinates, _pos[_connectivity[iTriangle][0]].coordinates)) {
          connectivity[0] = jPoint;
        }
        if (areVectorsEqual(_pos[_blockPoints[jPoint]].coordinates, _pos[_connectivity[iTriangle][1]].coordinates)) {
          connectivity[1] = jPoint;
        }
        if (areVectorsEqual(_pos[_blockPoints[jPoint]].coordinates, _pos[_connectivity[iTriangle][2]].coordinates)) {
          connectivity[2] = jPoint;
        }
      }
      _localConnectivity.push_back(connectivity);
    }
  }
#endif
}

// ATTENTION: Returns the rank of the position if it is local, but -1 if it is not local.
// Pay attention to overflow when converting this output
// This function will have different behavior depending on which rank calls it.
template <typename T>
int VTUsurfaceWriterRankwise<T>::getRankOfPosition(const Vector<T, 3>& position)
{
  int rank = 0;
  if (_loadBalancer.isLocal(_cuboidDecomposition.getC(position).value())) {
    rank = singleton::mpi().getRank();
    return rank;
  }
  else {
    return -1;
  }
}

template <typename T>
int VTUsurfaceWriterRankwise<T>::getRankOfTriangle(const STLtriangle<T>& triangle)
{
  Vector<T, 3> center = (triangle.point[0] + triangle.point[1] + triangle.point[2]) / 3.0;
  return getRankOfPosition(center);
}

} // end namespace olb
#endif
