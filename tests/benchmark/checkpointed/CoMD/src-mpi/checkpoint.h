/*
 * checkpoint.h
 *
 *  Modified on: Mar 14, 2019
 *       Author: Shashank Gugnani
 *      Contact: gugnani.2@osu.edu
 *
 *  Created on: Jun 23, 2016
 *      Author: Ignacio Laguna
 *     Contact: ilaguna@llnl.gov
 */
#ifndef SRC_MPI_CHECKPOINT_H_
#define SRC_MPI_CHECKPOINT_H_

#include "CoMDTypes.h"

void initCheckpointingEngine();
int thereIsACheckpoint();
void writeCheckpoint(SimFlat *sim);
void loadCheckpoint(SimFlat *sim);


#endif /* SRC_MPI_CHECKPOINT_H_ */
