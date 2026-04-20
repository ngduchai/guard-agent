#ifndef SIMPLE_CHECKPOINT_H
#define SIMPLE_CHECKPOINT_H

#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include <mpi.h>

// Simple file-based checkpoint for miniVite
// Replaces FTI with POSIX I/O per rank

static std::string _ckpt_filename(int rank) {
    return "miniVite_ckpt_" + std::to_string(rank) + ".bin";
}

static bool checkpoint_exists(int rank) {
    FILE* f = fopen(_ckpt_filename(rank).c_str(), "rb");
    if (f) { fclose(f); return true; }
    return false;
}

template<typename T>
static bool write_checkpoint(int rank, int numIters,
                              const std::vector<T>& currComm,
                              const std::vector<double>& clusterWeight) {
    FILE* f = fopen(_ckpt_filename(rank).c_str(), "wb");
    if (!f) return false;
    // Write iteration
    fwrite(&numIters, sizeof(int), 1, f);
    // Write currComm size and data
    size_t sz = currComm.size();
    fwrite(&sz, sizeof(size_t), 1, f);
    fwrite(currComm.data(), sizeof(T), sz, f);
    // Write clusterWeight
    sz = clusterWeight.size();
    fwrite(&sz, sizeof(size_t), 1, f);
    fwrite(clusterWeight.data(), sizeof(double), sz, f);
    fclose(f);
    return true;
}

template<typename T>
static bool read_checkpoint(int rank, int& numIters,
                             std::vector<T>& currComm,
                             std::vector<double>& clusterWeight) {
    FILE* f = fopen(_ckpt_filename(rank).c_str(), "rb");
    if (!f) return false;
    fread(&numIters, sizeof(int), 1, f);
    size_t sz;
    fread(&sz, sizeof(size_t), 1, f);
    currComm.resize(sz);
    fread(currComm.data(), sizeof(T), sz, f);
    fread(&sz, sizeof(size_t), 1, f);
    clusterWeight.resize(sz);
    fread(clusterWeight.data(), sizeof(double), sz, f);
    fclose(f);
    return true;
}

#endif
