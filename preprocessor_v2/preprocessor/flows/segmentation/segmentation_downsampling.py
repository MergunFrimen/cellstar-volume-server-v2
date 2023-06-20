
import math
from preprocessor_v2.preprocessor.flows.common import compute_downsamplings_to_be_stored, compute_number_of_downsampling_steps, open_zarr_structure_from_path
from preprocessor_v2.preprocessor.flows.constants import MESH_VERTEX_DENSITY_THRESHOLD, MIN_GRID_SIZE, SEGMENTATION_DATA_GROUPNAME
from preprocessor_v2.preprocessor.flows.segmentation.category_set_downsampling_methods import downsample_categorical_data, store_downsampling_levels_in_zarr
from preprocessor_v2.preprocessor.flows.segmentation.downsampling_level_dict import DownsamplingLevelDict
from preprocessor_v2.preprocessor.flows.segmentation.helper_methods import store_mesh_data_in_zarr, compute_vertex_density, simplify_meshes
from preprocessor_v2.preprocessor.flows.segmentation.segmentation_set_table import SegmentationSetTable
from preprocessor_v2.preprocessor.model.input import SegmentationPrimaryDescriptor
from preprocessor_v2.preprocessor.model.segmentation import InternalSegmentation
import zarr
import numpy as np

from preprocessor_v2.preprocessor.tools.magic_kernel_downsampling_3d.magic_kernel_downsampling_3d import MagicKernel3dDownsampler

def sff_segmentation_downsampling(internal_segmentation: InternalSegmentation):
    zarr_structure = open_zarr_structure_from_path(internal_segmentation.intermediate_zarr_structure_path)
    if internal_segmentation.primary_descriptor == SegmentationPrimaryDescriptor.three_d_volume:
        for lattice_gr_name, lattice_gr in zarr_structure[SEGMENTATION_DATA_GROUPNAME].groups():
            original_data_arr = lattice_gr['1']['0']['0'].grid
            lattice_id = int(lattice_gr_name)

            segmentation_downsampling_steps = compute_number_of_downsampling_steps(
                int_vol_or_seg=internal_segmentation,
                min_grid_size=MIN_GRID_SIZE,
                input_grid_size=math.prod(original_data_arr.shape),
                force_dtype=original_data_arr.dtype,
                factor=2 ** 3
            )

            ratios_to_be_stored = compute_downsamplings_to_be_stored(
                int_vol_or_seg=internal_segmentation,
                number_of_downsampling_steps=segmentation_downsampling_steps,
                input_grid_size=math.prod(original_data_arr.shape),
                dtype=original_data_arr.dtype,
                factor=2 ** 3
            )

            _create_category_set_downsamplings(
                magic_kernel=MagicKernel3dDownsampler(),
                original_data=original_data_arr[...],
                downsampling_steps=segmentation_downsampling_steps,
                ratios_to_be_stored=ratios_to_be_stored,
                data_group=lattice_gr,
                value_to_segment_id_dict_for_specific_lattice_id=internal_segmentation.value_to_segment_id_dict[lattice_id],
                params_for_storing=internal_segmentation.params_for_storing,
                time_frame='0',
                channel='0'
            )

    elif internal_segmentation.primary_descriptor == SegmentationPrimaryDescriptor.mesh_list:
        simplification_curve: dict[int, float] = internal_segmentation.simplification_curve
        calc_mode = 'area'
        density_threshold = MESH_VERTEX_DENSITY_THRESHOLD[calc_mode]
        # segment_ids, detail_lvls, time, channel, mesh_ids
        
        segm_data_gr = zarr_structure[SEGMENTATION_DATA_GROUPNAME]
        
        for segment_name_id, segment in segm_data_gr.groups():
            original_detail_lvl_mesh_list_group = segment['1']['0']['0']
            group_ref = original_detail_lvl_mesh_list_group
            for level, fraction in simplification_curve.items():
                if density_threshold != 0 and compute_vertex_density(group_ref, mode=calc_mode) <= density_threshold:
                    break
                if fraction == 1:
                    continue  # original data, don't need to compute anything
                mesh_data_dict = simplify_meshes(original_detail_lvl_mesh_list_group, ratio=fraction, segment_id=segment_name_id)
                # TODO: potentially simplify meshes may output mesh with 0 vertices, normals, triangles
                # it should not be stored?
                # check each mesh in mesh_data_dict if it contains 0 vertices
                # remove all such meshes from dict
                for mesh_id in list(mesh_data_dict.keys()):
                    if mesh_data_dict[mesh_id]['attrs']['num_vertices'] == 0:
                        del mesh_data_dict[mesh_id]

                # if there is no meshes left in dict - break from while loop
                if not bool(mesh_data_dict):
                    break
                
                group_ref = store_mesh_data_in_zarr(
                    mesh_data_dict, segment, detail_level=level,
                    time_frame='0',
                    channel='0',
                    params_for_storing=internal_segmentation.params_for_storing)




    print('Segmentation downsampled')


def _create_category_set_downsamplings(
        *,
        magic_kernel: MagicKernel3dDownsampler,
        original_data: np.ndarray,
        downsampling_steps: int,
        ratios_to_be_stored: list,
        data_group: zarr.hierarchy.Group,
        value_to_segment_id_dict_for_specific_lattice_id: dict,
        params_for_storing: dict,
        time_frame: str,
        channel: str
):
    '''
    Take original segmentation data, do all downsampling levels, create zarr datasets for each
    '''
    # table with just singletons, e.g. "104": {104}, "94" :{94}
    initial_set_table = SegmentationSetTable(original_data, value_to_segment_id_dict_for_specific_lattice_id)

    # for now contains just x1 downsampling lvl dict, in loop new dicts for new levels are appended
    levels = [
        DownsamplingLevelDict({'ratio': 1, 'grid': original_data, 'set_table': initial_set_table})
    ]
    for i in range(downsampling_steps):
        current_set_table = SegmentationSetTable(original_data, value_to_segment_id_dict_for_specific_lattice_id)
        # on first iteration (i.e. when doing x2 downsampling), it takes original_data and initial_set_table with set of singletons 
        levels.append(downsample_categorical_data(magic_kernel, levels[i], current_set_table))


    # remove original data, as they are already stored
    levels.pop(0)
    # remove all with ratios that are not in ratios_to_be_stored
    levels = [level for level in levels if level.get_ratio() in ratios_to_be_stored]
    # store levels list in zarr structure (can be separate function)
    store_downsampling_levels_in_zarr(
        levels,
        lattice_data_group=data_group,
        params_for_storing=params_for_storing,
        time_frame=time_frame,
        channel=channel
        )

