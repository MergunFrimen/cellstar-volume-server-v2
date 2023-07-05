import math
from pathlib import Path
import mrcfile
from preprocessor_old.src.preprocessors.implementations.sff.preprocessor.constants import DOWNSAMPLING_KERNEL
from scipy import signal, ndimage
import numpy as np
from preprocessor_old.src.preprocessors.implementations.sff.preprocessor.downsampling.downsampling import generate_kernel_3d_arr
from timeit import default_timer as timer
import dask.array as da
from dask_image.ndfilters import convolve as dask_convolve


def downsample_map(input_path: Path, output_path: Path, size_limit: int):
    kernel = generate_kernel_3d_arr(list(DOWNSAMPLING_KERNEL))
    
    with mrcfile.mmap(str(input_path.resolve())) as mrc_original:
        original_cella = mrc_original.header.cella
        original_nstart = mrc_original.nstart
        data: np.memmap = mrc_original.data
        print('original header')
        mrc_original.print_header()

    size = data.nbytes
    print(f'{input_path.name} - size of original data: ~ {size / 1000000} MB')
    downsampled_data = data

    downsampled_data = da.from_array(downsampled_data)

    num_steps = 0
    while size > size_limit:
        num_steps = num_steps + 1
        # ndimage.convolve(downsampled_data, kernel, mode='mirror', cval=0.0, output=downsampled_data)
        downsampled_data = dask_convolve(downsampled_data, kernel, mode='mirror', cval=0.0)
        downsampled_data = downsampled_data[::2, ::2, ::2]
        size = downsampled_data.nbytes
        print(f'downsampled to: {size / 1000000} MB')
        
    with mrcfile.new(str(output_path.resolve()), overwrite=True) as mrc:
        nstart_divisor = 2 ** num_steps
        mrc.set_data(downsampled_data)
        mrc.header.cella = original_cella
        mrc.nstart = (
            math.floor(original_nstart.x / nstart_divisor),
            math.floor(original_nstart.y / nstart_divisor),
            math.floor(original_nstart.z / nstart_divisor),
            )

        mrc.print_header()
        mrc.update_header_from_data()
        mrc.update_header_stats()    
        

def _check_if_map_is_ok(map_path: Path):
    with mrcfile.open(str(map_path.resolve())) as mrc:
        data = mrc.data
        print(f'shape of new file is {data.shape}')
        mrc.print_header()


        
if __name__ == '__main__':
    INPUT_MAP = 'preprocessor\data\sample_volumes\emdb_sff\emd_13856.map'
    # INPUT_MAP = 'preprocessor\data\sample_volumes\emdb_sff\emd_9199.map'
    # INPUT_MAP = 'preprocessor\data\sample_volumes\emdb_sff\EMD-1832.map'
    OUTPUT_MAP = 'temp/downsampled_13856.map'
    SIZE_LIMIT = 9 * (10**9)
    downsample_map(input_path=Path(INPUT_MAP), output_path=Path(OUTPUT_MAP), size_limit=SIZE_LIMIT)
    _check_if_map_is_ok(Path(OUTPUT_MAP))
    
        