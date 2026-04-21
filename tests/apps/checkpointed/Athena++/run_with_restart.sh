#!/bin/bash
NPROCS=${1:-1}
INPUT="inputs/hydro/athinput.blast_ckpt"

# Create AMR-enabled 2D input from the checkpointed 3D input
AMR_INPUT="/tmp/athinput.blast_amr"
cat > "$AMR_INPUT" << 'ENDOFINPUT'
<comment>
problem   = spherical blast wave (2D with AMR)
configure = --prob=blast

<job>
problem_id = Blast

<output1>
file_type  = hst
dt         = 0.1

<output2>
file_type  = vtk
variable   = prim
dt         = 10.0

<output3>
file_type  = rst
dt         = 0.1

<time>
cfl_number = 0.3
nlim       = -1
tlim        = 1.0
integrator  = vl2
xorder      = 2
ncycle_out  = 100

<mesh>
nx1        = 100
x1min      = -0.5
x1max      = 0.5
ix1_bc     = periodic
ox1_bc     = periodic

nx2        = 100
x2min      = -0.5
x2max      = 0.5
ix2_bc     = periodic
ox2_bc     = periodic

nx3        = 1
x3min      = -0.5
x3max      = 0.5
ix3_bc     = periodic
ox3_bc     = periodic

refinement     = adaptive
numlevel       = 2
derefine_count = 5

<meshblock>
nx1        = 20
nx2        = 20
nx3        = 1

<hydro>
gamma           = 1.666666666667
iso_sound_speed = 0.4082482905

<problem>
compute_error = false
pamb          = 0.1
prat          = 100.
radius        = 0.1
thr           = 0.5
ENDOFINPUT

RST_FILE=$(ls -t Blast.*.rst 2>/dev/null | grep -v 'final' | head -1)

if [ -n "$RST_FILE" ]; then
    echo "Restarting from checkpoint: $RST_FILE"
    ./bin/athena -r "$RST_FILE"
else
    echo "Starting fresh simulation"
    ./bin/athena -i "$AMR_INPUT"
fi
