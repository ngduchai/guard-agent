import numpy as np

def convert_berea_raw_to_ascii(raw_file, ascii_file):
    # Metadata from header
    sizes = (400, 400, 400)
    voxel_size_meters = 5.345e-6  # 5.345 µm in meters

    # Read the raw voxel data
    voxel_data = np.fromfile(raw_file, dtype=np.uint8)
    if voxel_data.size != np.prod(sizes):
        raise ValueError(f"Expected {np.prod(sizes)} voxels, got {voxel_data.size}")

    # Convert voxel values to 0 or 1
    voxel_data = (voxel_data > 0).astype(np.uint8)  # Non-zero → 1, zero → 0

    # Write ASCII file
    with open(ascii_file, 'w') as f:
        # Line 1: sizes
        f.write(f"{sizes[0]} {sizes[1]} {sizes[2]}\n")
        # Line 2: voxel size in meters
        f.write(f"{voxel_size_meters}\n")
        # Line 3: linearized geometry with spaces
        voxel_str = ' '.join(map(str, voxel_data))
        f.write(voxel_str + '\n')

if __name__ == "__main__":
    convert_berea_raw_to_ascii("Berea.raw", "Berea.ascii")

