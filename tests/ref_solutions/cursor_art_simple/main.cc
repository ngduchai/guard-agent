#include <iostream>
#include <sstream>
#include <algorithm>
#include <iomanip>
#include <cstdlib>
#include <cerrno>
#include <sys/stat.h>
#include "art_simple.h"
#include "hdf5.h"

#include <mpi.h>

#include <veloc.h>

#include <unistd.h>
#include <limits.h>

// Function to swap dimensions of a flat 3D array
float* swapDimensions(float* original, int x, int y, int z, int dim1, int dim2) {
    float* transposed= new float[x*y*z];

    for (int i = 0; i < x; ++i) {
        for (int j = 0; j < y; ++j) {
            for (int k = 0; k < z; ++k) {
                int original_index = i * (y * z) + j * z + k;

                int transposed_index;
                if (dim1 == 1 && dim2 == 2) {  // Swap y and z
                    transposed_index = i * (z * y) + k * y + j;
                } else if (dim1 == 0 && dim2 == 2) {  // Swap x and z
                    transposed_index = k * (y * x) + j * x + i;
                } else if (dim1 == 0 && dim2 == 1) {  // Swap x and y
                    transposed_index = j * (x * z) + i * z + k;
                } else {
                    continue;  // No valid swap detected
                }

                transposed[transposed_index] = original[original_index];
            }
        }
    }

    return transposed;
}

int saveAsHDF5(const char* fname, float* recon, hsize_t* output_dims) {
    hid_t output_file_id = H5Fcreate(fname, H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT);
    if (output_file_id < 0) {
        return 1;
    }
    hid_t output_dataspace_id = H5Screate_simple(3, output_dims, NULL);
    hid_t output_dataset_id = H5Dcreate(output_file_id, "/data", H5T_NATIVE_FLOAT, output_dataspace_id, H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
    H5Dwrite(output_dataset_id, H5T_NATIVE_FLOAT, H5S_ALL, H5S_ALL, H5P_DEFAULT, recon);
    H5Dclose(output_dataset_id);
    H5Sclose(output_dataspace_id);
    H5Fclose(output_file_id);
    return 0;
}

int main(int argc, char* argv[])
{

    if(argc < 7 || argc > 9) {
        std::cerr << "Usage: " << argv[0]
                  << " <filename> <center> <num_outer_iter> <num_iter> <beginning_sino> <num_sino>"
                  << " [veloc_cfg]" << std::endl;
        return 1;
    }

    std::cout << "argc: " << argc << std::endl;

    const char* filename = argv[1];
    float center = atof(argv[2]);
    int num_outer_iter = atoi(argv[3]);
    int num_iter = atoi(argv[4]);
    int beg_index = atoi(argv[5]);
    int nslices = atoi(argv[6]);

    // Optional: allow overriding VeloC configuration.
    // Any additional CLI arg (legacy) is ignored.
    const char* veloc_cfg_file = (argc >= 8) ? argv[7] : "veloc.cfg";

    // Name used by VeloC for the checkpoint namespace (must be alphanumeric).
    const char* veloc_ckpt_name = "artsimple";

    std::cout << "Reading data..." << std::endl;

    // Open tomo_00058_all_subsampled1p_ HDF5 file
    //const char* filename = "../../data/tomo_00058_all_subsampled1p_s1079s1081.h5";
    hid_t file_id = H5Fopen(filename, H5F_ACC_RDONLY, H5P_DEFAULT);
    if (file_id < 0) {
        std::cerr << "Error: Unable to open file " << filename << std::endl;
        return 1;
    }

    // Read the data from the HDF5 file
    const char* dataset_name = "exchange/data";
    hid_t dataset_id = H5Dopen(file_id, dataset_name, H5P_DEFAULT);
    if (dataset_id < 0) {
        std::cerr << "Error: Unable to open dataset " << dataset_name << std::endl;
        return 1;
    }

    //// read the data
    hid_t dataspace_id = H5Dget_space(dataset_id);
    hsize_t dims[3];
    H5Sget_simple_extent_dims(dataspace_id, dims, NULL);
    std::cout << "Data dimensions: " << dims[0] << " x " << dims[1] << " x " << dims[2] << std::endl;

    int dt = static_cast<int>(dims[0]);
    int dx = static_cast<int>(dims[2]);

    // Determine how many slices can be read directly from the dataset
    hsize_t available_slices = (beg_index >= 0 && static_cast<hsize_t>(beg_index) < dims[1])
                                   ? (dims[1] - static_cast<hsize_t>(beg_index))
                                   : 0;
    int base_slices = std::min<int>(nslices, static_cast<int>(available_slices));

    // read slices from the dataset
    std::cout << "Target dimensions: " << dims[0] << " x [" << beg_index << "-" << beg_index+nslices << "] x " << dims[2] << std::endl;
    std::cout << "Reading " << base_slices << " slice(s) from dataset, will replicate "
              << (nslices - base_slices) << " missing slice(s)." << std::endl;

    if (base_slices <= 0) {
        std::cerr << "Error: No available slices in dataset starting from index " << beg_index << std::endl;
        H5Dclose(dataset_id);
        H5Sclose(dataspace_id);
        return 1;
    }

    // Temporary buffer for the slices we can actually read
    float* base_data = new float[dt * base_slices * dx];

    hsize_t start[3] = {0, static_cast<hsize_t>(beg_index), 0};
    hsize_t count[3] = {dims[0], static_cast<hsize_t>(base_slices), dims[2]};
    H5Sselect_hyperslab(dataspace_id, H5S_SELECT_SET, start, NULL, count, NULL);

    // Memory dataspace for the base slices
    hsize_t base_mem_dims[3] = {dims[0], static_cast<hsize_t>(base_slices), dims[2]};
    hid_t base_memspace_id = H5Screate_simple(3, base_mem_dims, NULL);

    // Read the data for the base slices
    H5Dread(dataset_id, H5T_NATIVE_FLOAT, base_memspace_id, dataspace_id, H5P_DEFAULT, base_data);

    H5Sclose(base_memspace_id);
    H5Dclose(dataset_id);
    H5Sclose(dataspace_id);

    // Final buffer for nslices, laid out as [dt, nslices, dx]
    float* data = new float[dt * nslices * dx];

    // Copy and replicate slices: cycle through base_slices to fill nslices
    for (int i = 0; i < dt; ++i) {
        for (int j = 0; j < nslices; ++j) {
            int src_j = j % base_slices;
            for (int k = 0; k < dx; ++k) {
                int src_idx = i * (base_slices * dx) + src_j * dx + k;
                int dst_idx = i * (nslices * dx) + j * dx + k;
                data[dst_idx] = base_data[src_idx];
            }
        }
    }

    delete[] base_data;

    // read the theta
    const char* theta_name = "exchange/theta";
    hid_t theta_id = H5Dopen(file_id, theta_name, H5P_DEFAULT);
    if (theta_id < 0) {
        std::cerr << "Error: Unable to open dataset " << theta_name << std::endl;
        return 1;
    }
    // read the data
    hid_t theta_dataspace_id = H5Dget_space(theta_id);
    hsize_t theta_dims[1];
    H5Sget_simple_extent_dims(theta_dataspace_id, theta_dims, NULL);
    std::cout << "Theta dimensions: " << theta_dims[0] << std::endl;
    float* theta = new float[theta_dims[0]];
    H5Dread(theta_id, H5T_NATIVE_FLOAT, H5S_ALL, H5S_ALL, H5P_DEFAULT, theta);
    // close the dataset
    H5Dclose(theta_id);

    // Close the HDF5 file
    H5Fclose(file_id);

    // reconstruct using art
    int dy = nslices; //dims[1];
    int ngridx = dx;
    int ngridy = dx;
    //int num_iter = 2;
    //int num_outer_iter = 5;
    //float center = 294.078;

    // swap axis in data dt dy
    float *data_swap = swapDimensions(data, dt, dy, dx, 0, 1);

    std::cout << "Completed reading the data, starting the reconstruction..." << std::endl;
    std::cout << "dt: " << dt << ", dy: " << dy << ", dx: " << dx << ", ngridx: " << ngridx << ", ngridy: " << ngridy << ", num_iter: " << num_iter << ", center: " << center << std::endl;

    const unsigned int recon_size = dy*ngridx*ngridy;
    float *recon = new float[recon_size];

    /* Initiate MPI Communication */
    MPI_Init(&argc, &argv);
    int id;
    MPI_Comm_rank(MPI_COMM_WORLD, &id);
    int num_workers;
    MPI_Comm_size(MPI_COMM_WORLD, &num_workers);
    const unsigned int mpi_root = 0;
    
    char hostname[HOST_NAME_MAX];
    gethostname(hostname, HOST_NAME_MAX);
    std::cout << "Task ID " << id << " from " << hostname << std::endl; 

    /* Calculating the working area based on worker id */
    int rows_per_worker = dy / num_workers;
    int extra_rows = dy % num_workers;
    int w_offset = rows_per_worker*id + std::min(id, extra_rows);
    if (extra_rows != 0 && id < extra_rows) {
        rows_per_worker++;
    }
    hsize_t w_dt = dt;
    hsize_t w_dy = rows_per_worker;
    hsize_t w_dx = dx;
    hsize_t w_ngridx = ngridx;
    hsize_t w_ngridy = ngridy;
    
    const unsigned int w_recon_size = rows_per_worker*ngridx*ngridy;
    // float * w_recon = recon + w_offset*ngridx*ngridy;
    float * w_recon = new float [w_recon_size];
    float * w_data = data_swap + w_offset*dt*dx;
    std::cout << "[task-" << id << "]: offset: " << w_offset << ", w_dt: " << w_dt << ", w_dy: " << w_dy << ", w_dx: " << w_dx << ", w_ngridx: " << w_ngridx << ", w_ngridy: " << w_ngridy << ", num_iter: " << num_iter << ", center: " << center << std::endl;

    // --- VeloC state to checkpoint/restart ---
    // next_outer_iter represents the outer-loop index to start from.
    int next_outer_iter = 0;
    std::fill(w_recon, w_recon + w_recon_size, 0.0f);

    // Initialize VeloC (collective across all MPI ranks).
    int veloc_rc = VELOC_Init(MPI_COMM_WORLD, veloc_cfg_file);
    if (veloc_rc != VELOC_SUCCESS) {
        if (id == (int)mpi_root) {
            std::cerr << "VELOC_Init failed (rc=" << veloc_rc << ") cfg=" << veloc_cfg_file << std::endl;
        }
        MPI_Abort(MPI_COMM_WORLD, veloc_rc);
    }

    // Register memory regions we want to checkpoint/restart.
    veloc_rc = VELOC_Mem_protect(0, &next_outer_iter, 1, sizeof(next_outer_iter));
    if (veloc_rc != VELOC_SUCCESS) {
        if (id == (int)mpi_root) {
            std::cerr << "VELOC_Mem_protect(next_outer_iter) failed (rc=" << veloc_rc << ")" << std::endl;
        }
        MPI_Abort(MPI_COMM_WORLD, veloc_rc);
    }
    veloc_rc = VELOC_Mem_protect(1, w_recon, static_cast<size_t>(w_recon_size), sizeof(float));
    if (veloc_rc != VELOC_SUCCESS) {
        if (id == (int)mpi_root) {
            std::cerr << "VELOC_Mem_protect(w_recon) failed (rc=" << veloc_rc << ")" << std::endl;
        }
        MPI_Abort(MPI_COMM_WORLD, veloc_rc);
    }

    // Probe for the latest checkpoint and restore state if available.
    int latest_version = VELOC_Restart_test(veloc_ckpt_name, 0);
    if (latest_version > 0) {
        veloc_rc = VELOC_Restart(veloc_ckpt_name, latest_version);
        if (veloc_rc != VELOC_SUCCESS) {
            if (id == (int)mpi_root) {
                std::cerr << "VELOC_Restart failed (rc=" << veloc_rc << ") version=" << latest_version << std::endl;
            }
            MPI_Abort(MPI_COMM_WORLD, veloc_rc);
        }
        std::cout << "[task-" << id << "]: Resumed from VeloC version " << latest_version
                  << ", starting outer iteration #" << next_outer_iter << std::endl;
    } else {
        if (id == (int)mpi_root) {
            std::cout << "[task-" << id << "]: No checkpoint found; starting from outer iteration #0" << std::endl;
        }
    }

    std::cout << "[task-" << id << "]: Start the reconstruction from outer iteration #" << next_outer_iter << std::endl;

    const double checkpoint_period_sec = 5.0;
    double last_checkpoint_time = MPI_Wtime();
    int last_checkpoint_version = next_outer_iter; // next_outer_iter is how far we've completed

    // run the reconstruction
    for (int i = next_outer_iter; i < num_outer_iter; i++)
    {
        std::cout << "[task-" << id << "]: Outer iteration: " << i << std::endl;
        art(w_data, w_dy, w_dt, w_dx, &center, theta, w_recon, w_ngridx, w_ngridy, num_iter);
        
        MPI_Allgather(w_recon, w_recon_size, MPI_FLOAT, recon, w_recon_size, MPI_FLOAT, MPI_COMM_WORLD);

        // Update restartable state so a future failure can resume safely.
        next_outer_iter = i + 1;

        // Time-based checkpointing. Decision must be collective-safe across ranks.
        const int local_should_checkpoint = (MPI_Wtime() - last_checkpoint_time >= checkpoint_period_sec) ? 1 : 0;
        int global_should_checkpoint = 0;
        MPI_Allreduce(&local_should_checkpoint, &global_should_checkpoint, 1, MPI_INT, MPI_LOR, MPI_COMM_WORLD);

        if (global_should_checkpoint) {
            // Version is monotonic and equals "next_outer_iter" after this outer iteration.
            veloc_rc = VELOC_Checkpoint(veloc_ckpt_name, next_outer_iter);
            if (veloc_rc != VELOC_SUCCESS) {
                if (id == (int)mpi_root) {
                    std::cerr << "VELOC_Checkpoint failed (rc=" << veloc_rc << ") version=" << next_outer_iter << std::endl;
                }
                MPI_Abort(MPI_COMM_WORLD, veloc_rc);
            }

            last_checkpoint_time = MPI_Wtime();
            last_checkpoint_version = next_outer_iter;
        }
    }

    // Always checkpoint the final completed iteration (if not already covered).
    if (last_checkpoint_version != num_outer_iter) {
        veloc_rc = VELOC_Checkpoint(veloc_ckpt_name, num_outer_iter);
        if (veloc_rc != VELOC_SUCCESS) {
            if (id == (int)mpi_root) {
                std::cerr << "VELOC_Checkpoint(final) failed (rc=" << veloc_rc << ")" << std::endl;
            }
            MPI_Abort(MPI_COMM_WORLD, veloc_rc);
        }
    }

    if (id == mpi_root) {
        std::cout << "Reconstructed data from workers" << std::endl;
    }
    MPI_Gather(w_recon, w_recon_size, MPI_FLOAT, recon, w_recon_size, MPI_FLOAT, mpi_root, MPI_COMM_WORLD);

    const char * img_name = "recon.h5";
    if (id == mpi_root) {
        // write the reconstructed data to a file
        std::ostringstream oss;
        oss << img_name;
        std::string output_filename = oss.str();
        const char* output_filename_cstr = output_filename.c_str();

        hsize_t output_dims[3] = {static_cast<hsize_t>(dy),
                                  static_cast<hsize_t>(ngridy),
                                  static_cast<hsize_t>(ngridx)};
        if (saveAsHDF5(output_filename_cstr, recon, output_dims) != 0) {
            std::cerr << "Error: Unable to create file " << output_filename << std::endl;
            return 1;
        }
        else{
            std::cout << "Save the reconstruction image as " << img_name << std::endl;
        }

    }

    // Finalize VeloC collectively before shutting down MPI.
    veloc_rc = VELOC_Finalize(1);
    if (veloc_rc != VELOC_SUCCESS) {
        if (id == (int)mpi_root) {
            std::cerr << "VELOC_Finalize failed (rc=" << veloc_rc << ")" << std::endl;
        }
        MPI_Abort(MPI_COMM_WORLD, veloc_rc);
    }

    // free the memory
    delete[] data;
    delete[] data_swap;
    delete[] theta;
    delete[] recon;
    delete[] w_recon;

    MPI_Finalize();

    return 0;
}
