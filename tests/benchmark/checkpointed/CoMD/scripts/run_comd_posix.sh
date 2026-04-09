#!/bin/bash
### Run CoMD with POSIX backend
### Usage: sbatch [options] run_comd_posix.sh [weak | strong]

# Default sbatch options
# Will be overridden by command line options
#SBATCH --job-name comd-posix
#SBATCH --nodes 1
#SBATCH --time 04:00:00
#SBATCH --output comd-posix-%j.out

# Configuration parameters
PPN=("1" "2" "4" "8" "16" "32") # ppn to test
COMD_INSTALL_DIR=/opt/comd
TEST_RECOVERY=1
CHKPT_DIR=/data/ssd1/$USER # dir to store checkpoints
MODE="ssd" # storage device or fs used (e.g. ssd, lustre, ramdisk)
OPT_ENV_VARS="" # optional env vars for mpirun

# Derived parameters
SCALING="$1" # weak or strong
NNODES=$(scontrol show hostnames | wc -l)
NODES=$(scontrol show hostnames)
HOSTS_FILE=$COMD_INSTALL_DIR/hosts_$SLURM_JOB_ID
PDSH_HOSTS_FILE=$COMD_INSTALL_DIR/pdsh_hosts_$SLURM_JOB_ID
COMD_BIN=$COMD_INSTALL_DIR/bin/CoMD-mpi

### Calculate CoMD parameters (i, j, k) based on NPROCS.
### CoMD requirement is that i * j * k = NPROCS. We try
### to keep the values of i, j, k as close as possible
### to minimize communication cost.
calculate_ijk() {
    CUBRT=$(perl -e "use POSIX; print ceil($NPROCS**(1/3))")
    REM=1
    while [ $REM -ne 0 ]; do
        REM=$(perl -e "print $NPROCS%$CUBRT")
	CUBRT=$(( $CUBRT + 1 ))
    done
    i=$(( $CUBRT - 1 ))
    SQRT=$(perl -e "use POSIX; print ceil(sqrt($NPROCS/$i))")
    REM=1
    while [ $REM -ne 0 ]; do
        REM=$(perl -e "print $NPROCS/$i%$SQRT")
        SQRT=$(( $SQRT + 1 ))
    done
    j=$(( $SQRT - 1 ))
    k=$(echo "x=$NPROCS/$i/$j; scale=0; x/1" | bc -l)
}

### Calculate CoMD parameters (x, y, z) for weak scaling.
### 4 * x * y * z = nAtoms (or problem size). Scale nAtoms
### linearly with NPROCS to achieve "weak scaling". Since
### i * j * k = NPROCS, simply set (x, y, z) to the scalar
### product of base values with (i, j, k).
calculate_xyz_weak() {
    # Use base values of 40
    X=$(( $i * 40 ))
    Y=$(( $j * 40 ))
    Z=$(( $k * 40 ))
}

### Calculate CoMD parameters (x, y, z) for strong scaling.
### We just need to keep the values constant.
calculate_xyz_strong() {
    X=160; Y=160; Z=160
}

### Calculate CoMD parameters (x, y, z) based on NPROCS.
calculate_xyz() {
    if [ "$SCALING" == "weak" ]; then
        calculate_xyz_weak
    else # strong
        calculate_xyz_strong
    fi
}

scontrol show hostnames > $PDSH_HOSTS_FILE
cd $COMD_INSTALL_DIR

for ppn in "${PPN[@]}"; do
    # Calculate nprocs
    NPROCS=$(( $ppn * $NNODES ))

    # Calculate CoMD parameters
    calculate_ijk
    calculate_xyz
    echo "CoMD parameters: i=$i, j=$j, k=$k"
    echo "CoMD parameters: x=$X, y=$Y, z=$Z"

    # Create host file
    echo -n "" > $HOSTS_FILE
    for node in $NODES; do
        for (( n = 0; n < $ppn; n++ )); do
            echo $node >> $HOSTS_FILE
        done
    done

    # Remove old checkpoint data
    pdsh -R ssh -w ^$PDSH_HOSTS_FILE rm -rf $CHKPT_DIR
    pdsh -R ssh -w ^$PDSH_HOSTS_FILE mkdir -p $CHKPT_DIR
    sleep 5

    # Run test
    mpirun -ppn $ppn --hostfile $HOSTS_FILE                       \
        -env CHKPT_DIR=$CHKPT_DIR                                 \
        $OPT_ENV_VARS                                             \
        $COMD_BIN -e -i $i -j $j -k $k -x $X -y $Y -z $Z          \
        | tee comd-posix-"$SCALING"-"$MODE"-"$NNODES"-"$ppn".log

    # Flush checkpoint data
    pdsh -R ssh -w ^$PDSH_HOSTS_FILE sync

    if [ $TEST_RECOVERY -ne 0 ]; then
        sleep 5
        mpirun -ppn $ppn --hostfile $HOSTS_FILE                   \
            -env CHKPT_DIR=$CHKPT_DIR                             \
            $OPT_ENV_VARS                                         \
            $COMD_BIN -e -N 0 -i $i -j $j -k $k -x $X -y $Y -z $Z \
            | tee -a comd-posix-"$SCALING"-"$MODE"-"$NNODES"-"$ppn".log
    fi
done

# Cleanup
pdsh -R ssh -w ^$PDSH_HOSTS_FILE rm -rf $CHKPT_DIR
rm -f $PDSH_HOSTS_FILE
rm -f $HOSTS_FILE
