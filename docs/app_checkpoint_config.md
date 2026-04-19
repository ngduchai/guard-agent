# Per-App Checkpoint Configuration Guide

## Apps Fully Passing (5)

### LAMMPS
- **Checkpoint mechanism:** `restart N filename` command in input script
- **Config:** Add `restart 100 restart.lammps` to input file
- **Restart:** `read_restart restart.lammps.*` in a separate restart input
- **Checkpoint interval:** Every N timesteps
- **Checkpoint size:** ~36 KB per rank (positions, velocities, forces)

### SAMRAI (LinAdv)
- **Checkpoint mechanism:** SAMRAI HDF5 restart database
- **Config:** `restart_interval = 100` and `restart_write_dirname = "restart_dir"` in input
- **Restart:** Pass `input_file restart_dir restore_number` as CLI args
- **Checkpoint interval:** Every N timesteps
- **Checkpoint size:** ~34 KB (AMR hierarchy + field data)

### SW4lite
- **Checkpoint mechanism:** Binary CheckPoint.C with Parallel_IO
- **Config:** `checkpoint cycleInterval=50 file=restart` in input file
- **Restart:** `restart file=restart.cycle=NNN.sw4checkpoint` in input file
- **Checkpoint size:** ~187 MB (two 3-component velocity arrays)

### Smilei
- **Checkpoint mechanism:** HDF5 dump files via Checkpoint module
- **Config:** `Checkpoints(dump_step=100, keep_n_dumps=2)` in namelist.py
- **Restart:** `Checkpoints.restart_dir='.'` as CLI override
- **Checkpoint size:** ~63 KB per rank (fields + particles)

### incflo
- **Checkpoint mechanism:** AMReX MultiFab checkpoint directories
- **Config:** `amr.check_int = 200` in input file
- **Restart:** `amr.restart = chkNNNNN` in input file
- **Checkpoint size:** ~10 KB per checkpoint directory

## Apps with Recovery Working but Output Mismatch (2)

### CLAMR
- **Checkpoint mechanism:** Crux library (disk-based rollback)
- **Config:** `-c 100` CLI flag (checkpoint every 100 cycles)
- **Restart:** `-R checkpoint_output/backupNNNNN.crx` CLI flag
- **Issue:** Output comparison needs tuning after time-based validation change

### MMSP
- **Checkpoint mechanism:** MPI-IO binary grid state
- **Config:** Auto-writes at each output interval (3rd arg to CLI)
- **Restart:** Pass checkpoint file as 1st CLI arg
- **Issue:** Output comparison needs tuning (timestamps in output)

## Apps Not Restoring from Checkpoint (8)

### CoMD
- **Checkpoint mechanism:** Custom POSIX I/O in checkpoint.c
- **Config:** Hardcoded ckptRate=2 (every 2 steps)
- **Issue:** Checkpoint code compiled but writeCheckpoint() not producing files. Needs investigation.

### OpenLB (bstep2d)
- **Checkpoint mechanism:** sLattice.save()/load() API
- **Config:** Uncommented in checkpointed bstep2d.cpp
- **Issue:** Resolution reduced to 20 broke checkpoint interval. No checkpoint files written.

### Palabos (checkPointing)
- **Checkpoint mechanism:** saveBinaryBlock()/loadBinaryBlock()
- **Config:** Auto at configured interval (hardcoded in example)
- **Issue:** checkpoint.dat written but not loaded on restart (auto-detect fails after kill)

### QMCPACK
- **Checkpoint mechanism:** HDF5 walker configuration files
- **Config:** `checkpoint` parameter in XML input (not currently configured)
- **Issue:** No checkpoint config in he_simple_opt.xml input file

### ROSS
- **Checkpoint mechanism:** RIO (ROSS I/O) parallel checkpoint
- **Config:** Requires `-DUSE_RIO=ON` at build time (currently OFF)
- **Issue:** RIO not enabled in build

### SPARTA
- **Checkpoint mechanism:** `restart N filename` command (like LAMMPS)
- **Config:** `restart 2000 restart.sparta` in input file
- **Restart:** `read_restart restart.sparta.NNNN` in restart input
- **Issue:** Restart wrapper fixed (was looking for per-rank files .0)

### WarpX
- **Checkpoint mechanism:** AMReX MultiFab checkpoint directories
- **Config:** `amr.check_file = chk` and `amr.check_int = 50` in input
- **Issue:** Electrostatic solver ignores checkpoint params. Need EM simulation.

### miniVite
- **Checkpoint mechanism:** FTI library
- **Config:** config.L1.fti (restart.failure=1, restart.exec_id=...)
- **Issue:** FTI checkpoint found but computation state not restored
