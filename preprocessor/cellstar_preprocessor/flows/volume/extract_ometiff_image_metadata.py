from decimal import Decimal
import re
from cellstar_db.models import SegmentationLatticesMetadata, TimeInfo, VolumeSamplingInfo, VolumesMetadata
from cellstar_preprocessor.flows.common import get_downsamplings, open_zarr_structure_from_path
from cellstar_preprocessor.flows.constants import LATTICE_SEGMENTATION_DATA_GROUPNAME, QUANTIZATION_DATA_DICT_ATTR_NAME, VOLUME_DATA_GROUPNAME
from cellstar_preprocessor.flows.volume.extract_omezarr_metadata import _convert_to_angstroms
from cellstar_preprocessor.model.volume import InternalVolume
from cellstar_preprocessor.tools.quantize_data.quantize_data import decode_quantized_data
import dask.array as da
import numpy as np
import zarr

SHORT_UNIT_NAMES_TO_LONG = {
    'µm': 'micrometer',
    # TODO: support other units
}

def _get_source_axes_units():
    # NOTE: hardcoding this for now
    spatial_units = 'micrometer'
    d = {
        "x": spatial_units,
        "y": spatial_units,
        "z": spatial_units
    }
    # d = {}
    return d

def _convert_short_units_to_long(short_unit_name: str):
    # TODO: support conversion of other axes units (currently only µm to micrometer).
    # https://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2016-06/ome_xsd.html#Pixels_PhysicalSizeXUnit
    if short_unit_name in SHORT_UNIT_NAMES_TO_LONG:
        return SHORT_UNIT_NAMES_TO_LONG[short_unit_name]
    else:
        raise Exception('Short unit name is not supported')

def _get_ometiff_physical_size(ome_tiff_metadata):
    d = {}
    if 'PhysicalSizeX' in ome_tiff_metadata:
        d['x'] = ome_tiff_metadata['PhysicalSizeX']
    else:
        d['x'] = 1.0

    if 'PhysicalSizeY' in ome_tiff_metadata:
        d['y'] = ome_tiff_metadata['PhysicalSizeY']
    else:
        d['y'] = 1.0

    if 'PhysicalSizeZ' in ome_tiff_metadata:
        d['z'] = ome_tiff_metadata['PhysicalSizeZ']
    else:
        d['z'] = 1.0
    
    return d


def _get_segmentation_sampling_info(root_data_group, sampling_info_dict):
    for res_gr_name, res_gr in root_data_group.groups():
        # create layers (time gr, channel gr)
        sampling_info_dict["boxes"][res_gr_name] = {
            "origin": None,
            "voxel_size": None,
            "grid_dimensions": None,
            # 'force_dtype': None
        }

        for time_gr_name, time_gr in res_gr.groups():
            sampling_info_dict["boxes"][res_gr_name]["grid_dimensions"] = time_gr.grid.shape

def _get_ometiff_axes_units(ome_tiff_metadata):
    axes_units = {}
    if 'PhysicalSizeXUnit' in ome_tiff_metadata:
        axes_units['x'] = _convert_short_units_to_long(ome_tiff_metadata['PhysicalSizeXUnit'])
    else:
        axes_units['x'] = 'micrometer'

    if 'PhysicalSizeYUnit' in ome_tiff_metadata:
        axes_units['y'] = _convert_short_units_to_long(ome_tiff_metadata['PhysicalSizeYUnit'])
    else:
        axes_units['y'] = 'micrometer'

    if 'PhysicalSizeZUnit' in ome_tiff_metadata:
        axes_units['z'] = _convert_short_units_to_long(ome_tiff_metadata['PhysicalSizeZUnit'])
    else:
        axes_units['z'] = 'micrometer'
    
    return axes_units
    

def _get_ome_tiff_voxel_sizes_in_downsamplings(root: zarr.Group, boxes_dict, downsamplings, ometiff_metadata):
    
    ometiff_physical_size_dict: dict[str, str] = {}
    if root.attrs['extra_data']:
        # TODO: this is in micrometers
        # we anyway do not support other units
        l = root.attrs['extra_data']['scale_micron']
        ometiff_physical_size_dict['x'] = l[0]
        ometiff_physical_size_dict['y'] = l[1]
        ometiff_physical_size_dict['z'] = l[2]
    else:
        # TODO: try to get from ometiff itself
        ometiff_physical_size_dict = _get_ometiff_physical_size(ometiff_metadata)



    ometiff_axes_units_dict = _get_ometiff_axes_units(ometiff_metadata)
    # ometiff_physical_size_dict = _get_ometiff_physical_size(ometiff_metadata)

    for level in downsamplings:
        downsampling_level = str(level)
        if downsampling_level == '1':
            boxes_dict[downsampling_level]['voxel_size'] = [
                _convert_to_angstroms(ometiff_physical_size_dict['x'], ometiff_axes_units_dict['x']),
                _convert_to_angstroms(ometiff_physical_size_dict['y'], ometiff_axes_units_dict['y']),
                _convert_to_angstroms(ometiff_physical_size_dict['z'], ometiff_axes_units_dict['z'])
            ]
        else:
            # NOTE: rounding error - if one of dimensions in original data is odd
            boxes_dict[downsampling_level]['voxel_size'] = [
                _convert_to_angstroms(ometiff_physical_size_dict['x'] * int(downsampling_level), ometiff_axes_units_dict['x']),
                _convert_to_angstroms(ometiff_physical_size_dict['y'] * int(downsampling_level), ometiff_axes_units_dict['y']),
                _convert_to_angstroms(ometiff_physical_size_dict['z'] * int(downsampling_level), ometiff_axes_units_dict['z'])
            ]

def _get_ome_tiff_origins(boxes_dict: dict, downsamplings):
    # NOTE: origins seem to be 0, 0, 0, as they are not specified
    for level in downsamplings:
        downsampling_level = str(level)
        boxes_dict[downsampling_level]['origin'] = [0, 0, 0]

def _get_volume_sampling_info(root_data_group: zarr.Group, sampling_info_dict):
    for res_gr_name, res_gr in root_data_group.groups():
        # create layers (time gr, channel gr)
        sampling_info_dict["boxes"][res_gr_name] = {
            "origin": None,
            "voxel_size": None,
            "grid_dimensions": None,
            # 'force_dtype': None
        }

        sampling_info_dict["descriptive_statistics"][res_gr_name] = {}

        for time_gr_name, time_gr in res_gr.groups():
            first_group_key = sorted(time_gr.array_keys())[0]

            sampling_info_dict["boxes"][res_gr_name]["grid_dimensions"] = time_gr[
                first_group_key
            ].shape
            # sampling_info_dict['boxes'][res_gr_name]['force_dtype'] = time_gr[first_group_key].dtype.str

            sampling_info_dict["descriptive_statistics"][res_gr_name][time_gr_name] = {}
            for channel_arr_name, channel_arr in time_gr.arrays():
                assert (
                    sampling_info_dict["boxes"][res_gr_name]["grid_dimensions"]
                    == channel_arr.shape
                )
                # assert sampling_info_dict['boxes'][res_gr_name]['force_dtype'] == channel_arr.dtype.str

                arr_view = channel_arr[...]
                # if QUANTIZATION_DATA_DICT_ATTR_NAME in arr.attrs:
                #     data_dict = arr.attrs[QUANTIZATION_DATA_DICT_ATTR_NAME]
                #     data_dict['data'] = arr_view
                #     arr_view = decode_quantized_data(data_dict)
                #     if isinstance(arr_view, da.Array):
                #         arr_view = arr_view.compute()

                mean_val = float(str(np.mean(arr_view)))
                std_val = float(str(np.std(arr_view)))
                max_val = float(str(arr_view.max()))
                min_val = float(str(arr_view.min()))

                sampling_info_dict["descriptive_statistics"][res_gr_name][time_gr_name][
                    channel_arr_name
                ] = {
                    "mean": mean_val,
                    "std": std_val,
                    "max": max_val,
                    "min": min_val,
                }

def _get_allencell_image_channel_ids(root: zarr.Group):
    return root.attrs['extra_data']['name_dict']['crop_raw']

def _get_allencell_voxel_size(root: zarr.Group) -> list[float, float, float]:
    return root.attrs['extra_data']['scale_micron']

def _parse_ome_tiff_channel_id(ometiff_channel_id: str):
    channel_id = re.sub(r'\W+', '', ometiff_channel_id)
    return channel_id

def _get_ome_tiff_channel_ids(root: zarr.Group, ome_tiff_metadata):
    # TODO: if custom data = get it from custom_data
    if root.attrs['extra_data']:
        return root.attrs['extra_data']['name_dict']['crop_raw']
    else:
        channels = ome_tiff_metadata['Channels']
        # for now just return 0
        # return [0]
        channel_ids = []
        for key in channels:
            channel = channels[key]
            channel_id = _parse_ome_tiff_channel_id(channel['ID'])
            channel_ids.append(channel_id)

        return channel_ids

def extract_ometiff_image_metadata(internal_volume: InternalVolume):
    root = open_zarr_structure_from_path(
        internal_volume.intermediate_zarr_structure_path
    )
    ometiff_metadata = internal_volume.custom_data['ometiff_metadata']

    source_db_name = internal_volume.entry_data.source_db_name
    source_db_id = internal_volume.entry_data.source_db_id
    
    # NOTE: sample ometiff has no time
    # TODO: get channel ids same way as in preprocessor_old
    # channel_ids = _get_allencell_image_channel_ids(root)
    channel_ids = _get_ome_tiff_channel_ids(root, ometiff_metadata)
    
    start_time = 0
    end_time = 0
    time_units = "millisecond"

    volume_downsamplings = get_downsamplings(data_group=root[VOLUME_DATA_GROUPNAME])

    source_axes_units = _get_source_axes_units()
    metadata_dict = root.attrs["metadata_dict"]
    metadata_dict["entry_id"]["source_db_name"] = source_db_name
    metadata_dict["entry_id"]["source_db_id"] = source_db_id
    metadata_dict["volumes"] = VolumesMetadata(
        channel_ids=channel_ids,
        time_info=TimeInfo(
            kind="range", start=start_time, end=end_time, units=time_units
        ),
        volume_sampling_info=VolumeSamplingInfo(
            spatial_downsampling_levels=volume_downsamplings,
            boxes={},
            descriptive_statistics={},
            time_transformations=[],
            source_axes_units=source_axes_units,
            # TODO: get it from metadata
            original_axis_order=(0, 1, 2),
        ),
    )
    _get_volume_sampling_info(
        root_data_group=root[VOLUME_DATA_GROUPNAME],
        sampling_info_dict=metadata_dict["volumes"]["volume_sampling_info"]
    )

    _get_ome_tiff_voxel_sizes_in_downsamplings(
        root=root,
        boxes_dict=metadata_dict['volumes']['volume_sampling_info']['boxes'],
        downsamplings=volume_downsamplings,
        ometiff_metadata=ometiff_metadata
    )
    # _get_allencell_voxel_sizes_in_downsamplings(
    #     boxes_dict=metadata_dict['volumes']['volume_sampling_info']['boxes'],
    #     downsamplings=volume_downsamplings,
    #     original_voxel_size_in_micrometers=original_voxel_size_in_micrometers
    # )

    _get_ome_tiff_origins(
        boxes_dict=metadata_dict['volumes']['volume_sampling_info']['boxes'],
        downsamplings=volume_downsamplings
    )

    root.attrs["metadata_dict"] = metadata_dict
    return metadata_dict
