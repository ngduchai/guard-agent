#!/bin/bash
### Run CoMD with NVMe-CR backend
### Usage: sbatch [options] run_comd_nvme_cr.sh <nvmf-node-cnt> [weak | strong]

# Default sbatch options
# Will be overridden by command line options
#SBATCH --job-name comd-nvme-cr
#SBATCH --nodes 1
#SBATCH --time 04:00:00
#SBATCH --output comd-nvme-cr-%j.out

set -o pipefail

# Configuration parameters
PPN=("1" "2" "4" "8" "16" "32") # ppn to test
COMD_INSTALL_DIR=/opt/comd
NVME_CR_HOME=/opt/nvme-cr
SPDK_HOME=/opt/spdk
TEST_RECOVERY=1
RETRY_CNT=5
ld_preload=$NVME_CR_HOME/preload/libdsfs.so # Comment to disable ld_preload mode
OPT_ENV_VARS="" # optional env vars for mpirun

# Derived parameters
NVMF_NODE_CNT=$1 # 0 to disable NVMf
SCALING="$2" # weak or strong
NNODES=$(scontrol show hostnames | wc -l)
NNODES=$(( $NNODES - $NVMF_NODE_CNT ))
NODES=$(scontrol show hostnames | head -n $NNODES)
NVMF_NODES=$(scontrol show hostnames | tail -n $NVMF_NODE_CNT)
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

if [ $NVMF_NODE_CNT -eq 0 ]; then
    MODE="local"
else
    MODE="remote"
fi

# Setup NVMe driver
scontrol show hostnames > $PDSH_HOSTS_FILE
pdsh -R exec -w ^$PDSH_HOSTS_FILE ssh -tt %h \
    sudo $SPDK_HOME/scripts/setup.sh
sleep 5

cd $COMD_INSTALL_DIR

# Launch NVMf target application
NVMF_NODE_IPS=""
for node in $NVMF_NODES; do
    # Setup nvmf conf file
    cp $NVME_CR_HOME/conf/nvmf.conf.in $NVME_CR_HOME/conf/nvmf-"$node".conf
    IPADDR=$(ssh $node /usr/sbin/ifconfig 2> /dev/null | grep -A 1 "ib0" | \
             tail -n 1 | grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" |      \
             head -n 1)
    NVMF_NODE_IPS="$NVMF_NODE_IPS$IPADDR "
    HOST=$(ssh $node hostname -s)
    sed -i -- "s/IPADDR/$IPADDR/g" $NVME_CR_HOME/conf/nvmf-"$node".conf
    sed -i -- "s/HOST/$HOST/g" $NVME_CR_HOME/conf/nvmf-"$node".conf

    # Launch nvmf_tgt daemon
    ssh $node nohup $SPDK_HOME/app/nvmf_tgt/nvmf_tgt        \
        -c $NVME_CR_HOME/conf/nvmf-"$node".conf -m 0xFFFFFFF \
        > nvmf-"$node".log 2>&1 < /dev/null &
done
sleep 10

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

    for (( r = 0; r < $(( 2 * $RETRY_CNT )); r++ )); do
        sleep 10
        # Format SSD
        timeout 60 mpirun -ppn $ppn --hostfile $HOSTS_FILE            \
            -env XDG_RUNTIME_DIR=/dev/shm                             \
            -env NVMF_NODE_CNT=$NVMF_NODE_CNT                         \
            -env NVMF_NODELIST="$NVMF_NODE_IPS"                       \
            $OPT_ENV_VARS                                             \
            $NVME_CR_HOME/format/ds_format
        if [ $? -eq 0 ]; then
            sleep 10
            # Run test
            timeout 600 mpirun -ppn $ppn --hostfile $HOSTS_FILE       \
                -env XDG_RUNTIME_DIR=/dev/shm                         \
                -env LD_PRELOAD=$ld_preload                           \
                -env CHKPT_DIR=/mnt/ds                                \
                -env NVMF_NODE_CNT=$NVMF_NODE_CNT                     \
                -env NVMF_NODELIST="$NVMF_NODE_IPS"                   \
                $OPT_ENV_VARS                                         \
                $COMD_BIN -e -i $i -j $j -k $k -x $X -y $Y -z $Z      \
                | tee comd-nvme_cr-"$SCALING"-"$MODE"-"$NNODES"-"$ppn".log
            if [ $? -ne 0 ]; then
                sleep 10
            else
                break
            fi
        fi
    done

    if [ $TEST_RECOVERY -ne 0 ]; then
        for (( r = 0; r < $RETRY_CNT; r++ )); do
            sleep 10
            timeout 120 mpirun -ppn $ppn --hostfile $HOSTS_FILE       \
                -env XDG_RUNTIME_DIR=/dev/shm                         \
                -env LD_PRELOAD=$ld_preload                           \
                -env CHKPT_DIR=/mnt/ds                                \
                -env NVMF_NODE_CNT=$NVMF_NODE_CNT                     \
                -env NVMF_NODELIST="$NVMF_NODE_IPS"                   \
                $OPT_ENV_VARS                                         \
                $COMD_BIN -e -N 0 -i $i -j $j -k $k -x $X -y $Y -z $Z \
                | tee -a comd-nvme-cr-"$SCALING"-"$MODE"-"$NNODES"-"$ppn".log
            if [ $? -eq 0 ]; then
                break
            fi
        done
    fi
done

# Cleanup
for node in $NVMF_NODES; do
    ssh $node killall -9 $SPDK_HOME/app/nvmf_tgt/nvmf_tgt
done
pdsh -R exec -w ^$PDSH_HOSTS_FILE ssh -tt %h \
    sudo $SPDK_HOME/scripts/setup.sh reset
pdsh -R ssh -w ^$PDSH_HOSTS_FILE rm -rf /dev/shm/dpdk
rm -f $PDSH_HOSTS_FILE
rm -f $HOSTS_FILE
