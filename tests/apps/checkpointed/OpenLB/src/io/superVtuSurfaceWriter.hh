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

#ifndef SUPER_VTU_SURFACE_WRITER_HH
#define SUPER_VTU_SURFACE_WRITER_HH

#include "superVtuSurfaceWriter.h"

#include <cmath>
#include <numeric>

namespace olb {

template <typename T>
SuperVtuSurfaceWriter<T>::SuperVtuSurfaceWriter(std::string const name, CuboidDecomposition3D<T>& cuboidDecomposition,
                                                LoadBalancer<T>& loadBalancer, STLreader<T>& stlReader, bool binary)
    : _name(name)
    , _cuboidDecomposition(cuboidDecomposition)
    , _loadBalancer(loadBalancer)
    , _binary(binary)
    , clout(std::cout, "VTUsurfaceWriter3D")
{
  createBlockWriters(stlReader);
}

template <typename T>
void SuperVtuSurfaceWriter<T>::createBlockWriters(STLreader<T>& stlReader)
{
  for (std::size_t cuboidNumber = 0; cuboidNumber < std::size_t(_cuboidDecomposition.size()); cuboidNumber++) {
    if (_loadBalancer.isLocal(cuboidNumber)) {
      _blockWriters.push_back(
          BlockVtuSurfaceWriter<T>(_name, cuboidNumber, stlReader, _cuboidDecomposition, _loadBalancer, _binary));
    }
  }
}

template <typename T>
void SuperVtuSurfaceWriter<T>::addFunctor(AnalyticalF3D<T, T>& f)
{
  if (std::find(_functorsA.begin(), _functorsA.end(), &f) != _functorsA.end()) {
    return;
  }
  _functorsA.push_back(&f);
}

template <typename T>
void SuperVtuSurfaceWriter<T>::addFunctor(SuperF3D<T, T>& f)
{
  if (std::find(_functors.begin(), _functors.end(), &f) != _functors.end()) {
    return;
  }
  _functors.push_back(&f);
}

///writes vtu files and assigns values
template <typename T>
void SuperVtuSurfaceWriter<T>::write(const std::size_t& iT)
{
  std::size_t rank = 0;
#ifdef PARALLEL_MODE_MPI
  rank = singleton::mpi().getRank();
#endif
  for (auto& blockWriter : _blockWriters) {
    blockWriter.createFullName(iT);
  }

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
  }

  std::string fullNameVTU =
      singleton::directories().getVtkOutDir() + "data/" + createFileName(_name, iT, rank) + ".vtu";
  for (auto& blockWriter : _blockWriters) {
    blockWriter.preambleVTU();
  }
  //writes data arrays into vtu file. All ranks are needed for this
  dataArray(fullNameVTU);
  for (auto& blockWriter : _blockWriters) {
    blockWriter.closeVTU();
  }
}

template <typename T>
void SuperVtuSurfaceWriter<T>::dataPVDmaster(const int iT, int i, const std::string& fullNamePVDMaster)
{
  std::ofstream fout(fullNamePVDMaster.c_str(), std::ios::in | std::ios::out | std::ios::ate);
  fout.seekp(-25, std::ios::end);
  std::string namePiece = "data/" + createFileName(_name, iT) + ".pvtu";
  fout << "<DataSet timestep=\"" << iT << "\" " << "group=\"\" part=\" " << 0 << "\" " << "file=\"" << namePiece
       << "\"/>\n";
  fout.close();
  closePVD(fullNamePVDMaster);
}

template <typename T>
void SuperVtuSurfaceWriter<T>::createMasterFile()
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
void SuperVtuSurfaceWriter<T>::preamblePVTU(const std::string& fullNamePVTU)
{
  std::ofstream fout(fullNamePVTU.c_str(), std::ios::trunc);
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
    fout << "<PDataArray type=\"Float32\" Name=\"" << _functorsA[iFunctor]->getName() << "\" NumberOfComponents=\""
         << _functorsA[iFunctor]->getTargetDim() << "\"/>\n";
  }
  fout << "</PPointData>\n";
  fout.close();
}

template <typename T>
void SuperVtuSurfaceWriter<T>::dataPVTU(int iT, const std::string& fullNamePVTU)
{
  std::ofstream fout(fullNamePVTU.c_str(), std::ios::app);
  for (std::size_t iBlock = 0; iBlock < std::size_t(_cuboidDecomposition.size()); ++iBlock) {
    fout << "<Piece Source =\"" << createFileName(_name, iT, iBlock) + ".vtu" << "\"/>" << std::endl;
  }
  fout.close();
}

template <typename T>
void SuperVtuSurfaceWriter<T>::closePVTU(const std::string& fullNamePVTU)
{
  int rank = 0;
#ifdef PARALLEL_MODE_MPI
  rank = singleton::mpi().getRank();
#endif
  if (rank == 0) {

    std::ofstream fout(fullNamePVTU.c_str(), std::ios::app);
    fout << "</PUnstructuredGrid>\n";
    fout << "</VTKFile>\n";
    fout.close();
  }
}

template <typename T>
void SuperVtuSurfaceWriter<T>::preamblePVD(const std::string& fullNamePVD)
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
void SuperVtuSurfaceWriter<T>::closePVD(const std::string& fullNamePVD)
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
void SuperVtuSurfaceWriter<T>::dataArray(const std::string& fullName)
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
  for (auto& blockWriter : _blockWriters) {
    blockWriter.writeConnectivity();
  }
  fout.close();
}

template <typename T>
void SuperVtuSurfaceWriter<T>::writeFunctor(const std::string& fullName, std::ofstream& fout, SuperF3D<T, T>& f)
{
  AnalyticalFfromSuperF3D<T> interpolateF(f, false);
  writeAnalyticalFunctor(fullName, fout, interpolateF);
}

template <typename T>
void SuperVtuSurfaceWriter<T>::writeAnalyticalFunctor(const std::string& fullName, std::ofstream& fout,
                                                      AnalyticalF3D<T, T>& f)
{
  std::size_t dimF = f.getTargetDim();


  for (auto& blockWriter : _blockWriters) {
    blockWriter.writeDataHeader(dimF, f.getName());
    blockWriter.writeLocalData(f);
  }
  // gather all remote points from all blocks
  std::vector<std::vector<Vector<T, 3>>> remotePoints(_cuboidDecomposition.size());
  for (std::size_t blockIndex = 0; blockIndex < std::size_t(_cuboidDecomposition.size()); ++blockIndex) {
    unsigned numRemotePoints = 0;
    int      rootRank        = 0;

    if (_loadBalancer.isLocal(blockIndex)) {
      for (auto& blockWriter : _blockWriters) {
        if (blockWriter.getBlockNumber() == blockIndex) {
#ifdef PARALLEL_MODE_MPI
          rootRank        = singleton::mpi().getRank();
#endif
          numRemotePoints = blockWriter.getRemotePoints().size();
          remotePoints[blockIndex].resize(numRemotePoints);
          for (std::size_t i = 0; i < numRemotePoints; i++) {
            remotePoints[blockIndex][i] = blockWriter.getRemotePoints()[i];
          }
        }
      }
    }
#ifdef PARALLEL_MODE_MPI
    singleton::mpi().allreduce(&rootRank, &rootRank, 1, MPI_MAX);
    singleton::mpi().allreduce(&numRemotePoints, &numRemotePoints, 1, MPI_MAX);
    remotePoints[blockIndex].resize(numRemotePoints);
    singleton::mpi().bCast(reinterpret_cast<double*>(remotePoints[blockIndex].data()),
                           remotePoints[blockIndex].size() * 3, rootRank);
#endif
  }
  // evaluate functor at remote points
  // and accumulate results for each block
  std::vector<std::vector<T>> remoteDataCummulated(_cuboidDecomposition.size());
  for (std::size_t blockIndex = 0; blockIndex < remotePoints.size(); ++blockIndex) {
    auto& blockRemotePoints = remotePoints[blockIndex];

    remoteDataCummulated[blockIndex].resize(dimF * blockRemotePoints.size());
    std::vector<T> remoteData;

    for (auto& point : blockRemotePoints) {
      if (_loadBalancer.isLocal(_cuboidDecomposition.getC(point).value())) {
        T vals_local[dimF];
        f(vals_local, point.data());
        for (std::size_t dim = 0; dim < dimF; ++dim) {
          remoteData.push_back(std::move(vals_local[dim]));
        }
      }
      else {
        for (std::size_t dim = 0; dim < dimF; ++dim) {
          remoteData.emplace_back(T());
        }
      }
    }
#ifdef PARALLEL_MODE_MPI
    singleton::mpi().allreduce(remoteData.data(), remoteDataCummulated[blockIndex].data(), remoteData.size(), MPI_SUM);
#endif
#ifndef PARALLEL_MODE_MPI
    remoteDataCummulated[blockIndex] = std::move(remoteData);
#endif
  }

  for (std::size_t blockIndex = 0; blockIndex < remoteDataCummulated.size(); blockIndex++) {
    for (auto& writer : _blockWriters) {
      if (writer.getBlockNumber() == blockIndex) {
        writer.writeRemoteData(remoteDataCummulated[blockIndex]);
      }
    }
  }
  for (auto& writer : _blockWriters) {
    writer.closeDataArray();
  }
}

// ATTENTION: Returns the rank of the position if it is local, but -1 if it is not local.
// Pay attention to overflow when converting this output
// This function will have different behavior depending on which rank calls it.
template <typename T>
int SuperVtuSurfaceWriter<T>::getRankOfPosition(const Vector<T, 3>& position)
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
int SuperVtuSurfaceWriter<T>::getRankOfTriangle(const STLtriangle<T>& triangle)
{
  Vector<T, 3> center = (triangle.point[0] + triangle.point[1] + triangle.point[2]) / 3.0;
  return getRankOfPosition(center);
}

} // end namespace olb
#endif
