

from pathlib import Path
import shutil
from cellstar_preprocessor.flows.common import open_zarr_structure_from_path
from cellstar_preprocessor.flows.constants import VOLUME_DATA_GROUPNAME
from cellstar_preprocessor.flows.volume.map_preprocessing import map_preprocessing
from cellstar_preprocessor.model.input import DownsamplingParams, EntryData, QuantizationDtype, StoringParams
from cellstar_preprocessor.model.volume import InternalVolume
from cellstar_preprocessor.tests.helper_methods import initialize_intermediate_zarr_structure_for_tests
from cellstar_preprocessor.tests.input_for_tests import INTERMEDIATE_ZARR_STRUCTURE_PATH_FOR_TESTS, INTERNAL_VOLUME_FOR_TESTING
import zarr


def test_map_preprocessing():
    # TODO: create sample internal volume with all params
    # TODO: test different functions (map preprocessing, quantization, downsampling)
    # using  the same internal volume 
    initialize_intermediate_zarr_structure_for_tests()

    internal_volume = INTERNAL_VOLUME_FOR_TESTING
    map_preprocessing(internal_volume=internal_volume)

    # check if zarr structure has right format
    # 1. open zarr structure
    # 2. check if 1st level zarr group (resolution) is group and if there is just one group (1)
    # 3. check if 2nd level zarr group (time) is group and if there is just one group (0)
    # 4. check if 3rd level in zarr (channel) is array and if there is just one array (0)
    zarr_structure = open_zarr_structure_from_path(internal_volume.intermediate_zarr_structure_path)
    
    assert VOLUME_DATA_GROUPNAME in zarr_structure
    volume_gr = zarr_structure[VOLUME_DATA_GROUPNAME]
    assert isinstance(volume_gr, zarr.hierarchy.Group)
    assert len(volume_gr) == 1
    
    assert '1' in volume_gr
    assert isinstance(volume_gr['1'], zarr.hierarchy.Group)
    assert len(volume_gr['1']) == 1

    assert '0' in volume_gr['1']
    assert isinstance(volume_gr['1']['0'], zarr.hierarchy.Group)
    assert len(volume_gr['1']['0']) == 1
    
    assert '0' in volume_gr['1']['0']
    assert isinstance(volume_gr['1']['0']['0'], zarr.core.Array)

    # check dtype
    assert volume_gr['1']['0']['0'].dtype == internal_volume.volume_force_dtype

    # check if map header exist
    assert internal_volume.map_header is not None

    # check the data shape
    assert volume_gr['1']['0']['0'].shape == (64, 64, 64)