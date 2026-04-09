/*
 * checkpoint.c
 *
 *  Modified on: Mar 14, 2019
 *       Author: Shashank Gugnani
 *      Contact: gugnani.2@osu.edu
 *
 *  Created on: Jun 23, 2016
 *      Author: Ignacio Laguna
 *     Contact: ilaguna@llnl.gov
 */

#include "checkpoint.h"
#include "parallel.h"
#include "CoMDTypes.h"

#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h> // for uintptr_t
#include <fcntl.h> // for open
#include <unistd.h> // for close
#include <errno.h> // for ENOMEM
#include <sys/stat.h>
#include <sys/types.h>

#define writeToBuf(buf, ...) do {   \
  buf += sprintf(buf, __VA_ARGS__); \
} while (0)

#define copyToBuf(buf, src, size) do { \
  memcpy(buf, src, size);              \
  buf += size;                         \
} while (0)

#define copyFromBuf(dst, buf, size) do { \
  memcpy(dst, buf, size);                \
  buf += size;                           \
} while (0)

#define ALIGN 4096 /* 4KB */

/**
 * Allocate memory using the glibc malloc function with
 * alignment and error checking.
 */
static void *aligned_malloc(size_t size)
{
	void *mem = malloc(size + ALIGN + sizeof(void *));
	if (mem == NULL) {
		printf("ERROR: aligned_malloc failed\n");
		exit(ENOMEM);
	}
	void **ptr = (void **)((uintptr_t)(mem + ALIGN + sizeof(void *)) &
			       ~(ALIGN - 1));
	ptr[-1] = mem;
	return ptr;
}

/**
 * Free memory allocated using aligned_malloc.
 */
static void aligned_free(void *ptr)
{
	free(((void **)ptr)[-1]);
}

static char ckptFileName[50];

void initCheckpointingEngine()
{
  char *CHKPT_DIR = getenv("CHKPT_DIR");
  if (!CHKPT_DIR) CHKPT_DIR = ".";
  ckptFileName[0] = '\0';
  sprintf(ckptFileName, "%s/CoMD_state-%d.txt", CHKPT_DIR, getMyRank());
}

int thereIsACheckpoint()
{
  struct stat buffer;
  return (stat(ckptFileName, &buffer) == 0);
}

void writeCheckpoint(SimFlat *sim)
{
  int fd;
  int nTotalBoxes = sim->boxes->nTotalBoxes;
  int maxTotalAtoms = MAXATOMS * nTotalBoxes;

  char *buf;
  char *orig_buf;

  size_t size;
  size_t size_of_int = 3 * sizeof(int) + 2;
  size_t size_of_float = 3 * sizeof(float) + 2;

  ssize_t rc;

#ifdef DO_DIRECT_IO
  fd = open(ckptFileName, O_WRONLY | O_CREAT | O_TRUNC | O_DIRECT,
#else
  fd = open(ckptFileName, O_WRONLY | O_CREAT | O_TRUNC,
#endif
            S_IRUSR | S_IWUSR);
  assert(fd > 0 && "Could not open checkpoint file (to write)");

  // Allocate buffer for checkpoint data
  size = (17 * size_of_int) + (34 * size_of_float) +
         (nTotalBoxes * sizeof(int)) +
         (maxTotalAtoms * 2 * sizeof(int)) +
         (maxTotalAtoms * 10 * sizeof(real_t)) + 1;
  size += (size % ALIGN == 0 ? 0 : (ALIGN - (size % ALIGN)));
  buf = orig_buf = (char *)aligned_malloc(size);
  assert(buf && "Could not allocate buffer");

  // Save steps & rate parameters
  writeToBuf(buf, "%d ", sim->nSteps);
  writeToBuf(buf, "%d ", sim->printRate);
  writeToBuf(buf, "%f ", sim->dt);

  // Save Domain structure
  writeToBuf(buf, "%d ", sim->domain->procGrid[0]);
  writeToBuf(buf, "%d ", sim->domain->procGrid[1]);
  writeToBuf(buf, "%d ", sim->domain->procGrid[2]);

  writeToBuf(buf, "%d ", sim->domain->procCoord[0]);
  writeToBuf(buf, "%d ", sim->domain->procCoord[1]);
  writeToBuf(buf, "%d ", sim->domain->procCoord[2]);

  writeToBuf(buf, "%f ", sim->domain->globalMin[0]);
  writeToBuf(buf, "%f ", sim->domain->globalMin[1]);
  writeToBuf(buf, "%f ", sim->domain->globalMin[2]);

  writeToBuf(buf, "%f ", sim->domain->globalMax[0]);
  writeToBuf(buf, "%f ", sim->domain->globalMax[1]);
  writeToBuf(buf, "%f ", sim->domain->globalMax[2]);

  writeToBuf(buf, "%f ", sim->domain->globalExtent[0]);
  writeToBuf(buf, "%f ", sim->domain->globalExtent[1]);
  writeToBuf(buf, "%f ", sim->domain->globalExtent[2]);

  writeToBuf(buf, "%f ", sim->domain->localMin[0]);
  writeToBuf(buf, "%f ", sim->domain->localMin[1]);
  writeToBuf(buf, "%f ", sim->domain->localMin[2]);

  writeToBuf(buf, "%f ", sim->domain->localMax[0]);
  writeToBuf(buf, "%f ", sim->domain->localMax[1]);
  writeToBuf(buf, "%f ", sim->domain->localMax[2]);

  writeToBuf(buf, "%f ", sim->domain->localExtent[0]);
  writeToBuf(buf, "%f ", sim->domain->localExtent[1]);
  writeToBuf(buf, "%f ", sim->domain->localExtent[2]);

  // Save LinkCell structure
  writeToBuf(buf, "%d ", sim->boxes->gridSize[0]);
  writeToBuf(buf, "%d ", sim->boxes->gridSize[1]);
  writeToBuf(buf, "%d ", sim->boxes->gridSize[2]);

  writeToBuf(buf, "%d ", sim->boxes->nLocalBoxes);
  writeToBuf(buf, "%d ", sim->boxes->nHaloBoxes);
  writeToBuf(buf, "%d ", sim->boxes->nTotalBoxes);

  writeToBuf(buf, "%f ", sim->boxes->localMin[0]);
  writeToBuf(buf, "%f ", sim->boxes->localMin[1]);
  writeToBuf(buf, "%f ", sim->boxes->localMin[2]);

  writeToBuf(buf, "%f ", sim->boxes->localMax[0]);
  writeToBuf(buf, "%f ", sim->boxes->localMax[1]);
  writeToBuf(buf, "%f ", sim->boxes->localMax[2]);

  writeToBuf(buf, "%f ", sim->boxes->boxSize[0]);
  writeToBuf(buf, "%f ", sim->boxes->boxSize[1]);
  writeToBuf(buf, "%f ", sim->boxes->boxSize[2]);

  writeToBuf(buf, "%f ", sim->boxes->invBoxSize[0]);
  writeToBuf(buf, "%f ", sim->boxes->invBoxSize[1]);
  writeToBuf(buf, "%f ", sim->boxes->invBoxSize[2]);

  copyToBuf(buf, sim->boxes->nAtoms, nTotalBoxes * sizeof(int));

  // Save Atoms structure
  writeToBuf(buf, "%d ", sim->atoms->nLocal);
  writeToBuf(buf, "%d ", sim->atoms->nGlobal);

  copyToBuf(buf, sim->atoms->gid, maxTotalAtoms * sizeof(int));
  copyToBuf(buf, sim->atoms->iSpecies, maxTotalAtoms * sizeof(int));
  copyToBuf(buf, sim->atoms->r, maxTotalAtoms * sizeof(real3));
  copyToBuf(buf, sim->atoms->p, maxTotalAtoms * sizeof(real3));
  copyToBuf(buf, sim->atoms->f, maxTotalAtoms * sizeof(real3));
  copyToBuf(buf, sim->atoms->U, maxTotalAtoms * sizeof(real_t));

  // Save SpeciesDataSt structure
  writeToBuf(buf, "%c", sim->species->name[0]);
  writeToBuf(buf, "%c", sim->species->name[1]);
  writeToBuf(buf, "%c", sim->species->name[2]);

  writeToBuf(buf, "%d ", sim->species->atomicNo);

  writeToBuf(buf, "%f ", sim->species->mass);

  // Save other params
  writeToBuf(buf, "%f ", sim->ePotential);
  writeToBuf(buf, "%f ", sim->eKinetic);
  writeToBuf(buf, "%d ", sim->iteration);

  // Write all data to file
  rc = write(fd, orig_buf, size);
  assert(rc == size && "Error writing to file");

  // Flush contents of file
  rc = fsync(fd);
  assert(rc == 0 && "Error syncing file");

  // Close file
  rc = close(fd);
  assert(rc == 0 && "Error closing file");

  // Free buffer
  aligned_free(orig_buf);
}

void loadCheckpoint(SimFlat *sim)
{
  int fd;
  int nTotalBoxes = sim->boxes->nTotalBoxes;
  int maxTotalAtoms = MAXATOMS * nTotalBoxes;

  char *data;
  char *orig_data;

  size_t size = 0;
  ssize_t rc;
  struct stat buffer;

  // First verify file existence and integrity
  stat(ckptFileName, &buffer);
  size = buffer.st_size;
  assert((size > 0) && "No data found in checkpoint");

#ifdef DO_DIRECT_IO
  fd = open(ckptFileName, O_RDONLY | O_DIRECT);
#else
  fd = open(ckptFileName, O_RDONLY);
#endif
  assert(fd > 0 && "Could not open checkpoint file (to read)");

  // Save all lines in memory
  if (getMyRank() == 0) printf("Checkpoint size: %zu\n", size);
  data = orig_data = (char *)aligned_malloc(size);
  rc = read(fd, data, size);
  assert((rc == size) && "Error reading from file");

  rc = close(fd);
  assert(rc == 0 && "Error closing file");

  // Load steps & rate parameters
  sim->nSteps = strtol(data, &data, 10);
  sim->printRate = strtol(data, &data, 10);
  sim->dt = strtof(data, &data);

  // Load Domain structure
  sim->domain->procGrid[0] = strtol(data, &data, 10);
  sim->domain->procGrid[1] = strtol(data, &data, 10);
  sim->domain->procGrid[2] = strtol(data, &data, 10);

  sim->domain->procCoord[0] = strtol(data, &data, 10);
  sim->domain->procCoord[1] = strtol(data, &data, 10);
  sim->domain->procCoord[2] = strtol(data, &data, 10);

  sim->domain->globalMin[0] = strtof(data, &data);
  sim->domain->globalMin[1] = strtof(data, &data);
  sim->domain->globalMin[2] = strtof(data, &data);

  sim->domain->globalMax[0] = strtof(data, &data);
  sim->domain->globalMax[1] = strtof(data, &data);
  sim->domain->globalMax[2] = strtof(data, &data);

  sim->domain->globalExtent[0] = strtof(data, &data);
  sim->domain->globalExtent[1] = strtof(data, &data);
  sim->domain->globalExtent[2] = strtof(data, &data);

  sim->domain->localMin[0] = strtof(data, &data);
  sim->domain->localMin[1] = strtof(data, &data);
  sim->domain->localMin[2] = strtof(data, &data);

  sim->domain->localMax[0] = strtof(data, &data);
  sim->domain->localMax[1] = strtof(data, &data);
  sim->domain->localMax[2] = strtof(data, &data);

  sim->domain->localExtent[0] = strtof(data, &data);
  sim->domain->localExtent[1] = strtof(data, &data);
  sim->domain->localExtent[2] = strtof(data, &data);

  // Load LinkCell structure
  sim->boxes->gridSize[0] = strtol(data, &data, 10);
  sim->boxes->gridSize[1] = strtol(data, &data, 10);
  sim->boxes->gridSize[2] = strtol(data, &data, 10);

  sim->boxes->nLocalBoxes = strtol(data, &data, 10);
  sim->boxes->nHaloBoxes = strtol(data, &data, 10);
  sim->boxes->nTotalBoxes = strtol(data, &data, 10);

  sim->boxes->localMin[0] = strtof(data, &data);
  sim->boxes->localMin[1] = strtof(data, &data);
  sim->boxes->localMin[2] = strtof(data, &data);

  sim->boxes->localMax[0] = strtof(data, &data);
  sim->boxes->localMax[1] = strtof(data, &data);
  sim->boxes->localMax[2] = strtof(data, &data);

  sim->boxes->boxSize[0] = strtof(data, &data);
  sim->boxes->boxSize[1] = strtof(data, &data);
  sim->boxes->boxSize[2] = strtof(data, &data);

  sim->boxes->invBoxSize[0] = strtof(data, &data);
  sim->boxes->invBoxSize[1] = strtof(data, &data);
  sim->boxes->invBoxSize[2] = strtof(data, &data);

  ++data;
  copyFromBuf(sim->boxes->nAtoms, data, nTotalBoxes * sizeof(int));

  // Load Atoms structure
  sim->atoms->nLocal = strtol(data, &data, 10);
  sim->atoms->nGlobal = strtol(data, &data, 10);

  ++data;
  copyFromBuf(sim->atoms->gid, data, maxTotalAtoms * sizeof(int));
  copyFromBuf(sim->atoms->iSpecies, data, maxTotalAtoms * sizeof(int));
  copyFromBuf(sim->atoms->r, data, maxTotalAtoms * sizeof(real3));
  copyFromBuf(sim->atoms->p, data, maxTotalAtoms * sizeof(real3));
  copyFromBuf(sim->atoms->f, data, maxTotalAtoms * sizeof(real3));
  copyFromBuf(sim->atoms->U, data, maxTotalAtoms * sizeof(real_t));

  // Load SpeciesDataSt structure
  sim->species->name[0] = data[0];
  ++data;
  sim->species->name[1] = data[0];
  ++data;
  sim->species->name[2] = data[0];
  ++data;

  sim->species->atomicNo = strtol(data, &data, 10);

  sim->species->mass = strtof(data, &data);

  // Load other params
  sim->ePotential = strtof(data, &data);
  sim->eKinetic = strtof(data, &data);
  sim->iteration = strtol(data, &data, 10);

  // Free data
  aligned_free(orig_data);
}
