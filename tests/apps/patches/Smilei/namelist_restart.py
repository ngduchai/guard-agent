# Recovery-attempt namelist for Smilei reference bench (attempt_2+).
# Identical to namelist_minimal.py but with restart_dir="." in the
# Checkpoints block.  Smilei's pycontrol.py auto-globs
# `<restart_dir>/checkpoints/dump-*-*.h5` matching the current MPI
# rank and resumes from the highest dump step
# (src/Checkpoint/Checkpoint.cpp).  No CLI flag exists for this; it
# must be in the namelist.
#
# attempt_1 uses the original namelist_minimal.py (no restart_dir)
# so Smilei runs fresh, writing ./checkpoints/dump-*.h5 every 100
# steps.  attempt_2 uses this file: same physical setup, restart_dir
# set, so Smilei finds the dumps and resumes.
#
# IMPORTANT: file must be pure ASCII.  Smilei's PyRun_String
# (src/Params/Params.cpp:1602) does not declare an encoding, so
# UTF-8 characters in comments cause a Python parse-time error
# reported as `NameError: name 'namelist_restart' is not defined`.
import math
L  = 1.12
dn = 0.001

Main(
    geometry = "1Dcartesian",
    interpolation_order = 2,
    cell_length = [0.01],
    grid_length  = [L],
    number_of_patches = [ 16 ],
    timestep = 0.0095,
    # IMPORTANT: simulation_time = 35. must match patches/Smilei/namelist_minimal.py
    # (the primary input attempt_1 uses), NOT the upstream's 10.  The
    # patched primary extended the workload to 35 so benchmark has a
    # meaningful runtime; restart MUST use the same absolute target or
    # attempt_2 immediately exits because the loaded state's time has
    # already exceeded 10.
    simulation_time = 35.,
    EM_boundary_conditions = [ ['periodic'] ],
)

Species(
    name = 'ion',
    position_initialization = 'regular',
    momentum_initialization = 'cold',
    particles_per_cell = 10,
    mass = 1836.0,
    charge = 1.0,
    number_density = 1.,
    time_frozen = 0.1,
    boundary_conditions = [['periodic']],
)
Species(
    name = 'eon',
    position_initialization = 'regular',
    momentum_initialization = 'cold',
    particles_per_cell = 10,
    mass = 1.0,
    charge = -1.0,
    number_density = cosine(1.,xamplitude=dn,xlength=L),
    boundary_conditions = [['periodic']],
)

Checkpoints(
    dump_step = 100,
    dump_minutes = 0.,
    exit_after_dump = False,
    keep_n_dumps = 2,
    restart_dir = ".",
)
