from cellstar_db.models import MeshComponentNumbers

from cellstar_preprocessor.flows.common import (
    get_downsamplings,
    open_zarr_structure_from_path,
)
from cellstar_preprocessor.flows.constants import SEGMENTATION_DATA_GROUPNAME
from cellstar_preprocessor.model.input import SegmentationPrimaryDescriptor
from cellstar_preprocessor.model.segmentation import InternalSegmentation

def extract_metadata_geometric_segmentation(internal_segmentation: InternalSegmentation):
    root = open_zarr_structure_from_path(
        internal_segmentation.intermediate_zarr_structure_path
    )
    metadata_dict = root.attrs["metadata_dict"]

    metadata_dict['geometric_segmentation'] = {
        'exists': True
    }

    # if (
    #     internal_segmentation.primary_descriptor
    #     == SegmentationPrimaryDescriptor.three_d_volume
    # ):
    #     # sff has one channel
    #     channel_ids = [0]
    #     start_time = 0
    #     end_time = 0
    #     time_units = "millisecond"
    #     lattice_ids = []

    #     # TODO: check - some units are defined (spatial?)
    #     source_axes_units = {}

    #     for lattice_id, lattice_gr in root[SEGMENTATION_DATA_GROUPNAME].groups():
    #         downsamplings = get_downsamplings(data_group=lattice_gr)
    #         lattice_ids.append(lattice_id)

    #         metadata_dict["segmentation_lattices"]["segmentation_sampling_info"][
    #             str(lattice_id)
    #         ] = {
    #             # Info about "downsampling dimension"
    #             "spatial_downsampling_levels": downsamplings,
    #             # the only thing with changes with SPATIAL downsampling is box!
    #             "boxes": {},
    #             "time_transformations": [],
    #             "source_axes_units": source_axes_units,
    #         }
    #         _get_segmentation_sampling_info(
    #             root_data_group=lattice_gr,
    #             sampling_info_dict=metadata_dict["segmentation_lattices"][
    #                 "segmentation_sampling_info"
    #             ][str(lattice_id)],
    #             volume_sampling_info_dict=metadata_dict["volumes"][
    #                 "volume_sampling_info"
    #             ],
    #         )

    #         metadata_dict["segmentation_lattices"]["channel_ids"][
    #             lattice_id
    #         ] = channel_ids

    #         metadata_dict["segmentation_lattices"]["time_info"][lattice_id] = {
    #             "kind": "range",
    #             "start": start_time,
    #             "end": end_time,
    #             "units": time_units,
    #         }

    #     metadata_dict["segmentation_lattices"]["segmentation_lattice_ids"] = lattice_ids

    # elif (
    #     internal_segmentation.primary_descriptor
    #     == SegmentationPrimaryDescriptor.mesh_list
    # ):
    #     # from metadata_methods

    #     mesh_comp_num: MeshComponentNumbers = {}
    #     detail_lvl_to_fraction_dict = {}

    #     mesh_comp_num["segment_ids"] = {}

    #     # NOTE: mesh has no time and channel (both equal zero)
    #     # order: segment_ids, detail_lvls, time, channel, mesh_ids
    #     for segment_id, segment in root[SEGMENTATION_DATA_GROUPNAME].groups():
    #         mesh_comp_num["segment_ids"][segment_id] = {"detail_lvls": {}}
    #         for detail_lvl, detail_lvl_gr in segment.groups():
    #             mesh_comp_num["segment_ids"][segment_id]["detail_lvls"][detail_lvl] = {
    #                 "mesh_ids": {}
    #             }
    #             # NOTE: mesh has no time and channel (both equal zero)
    #             for mesh_id, mesh in detail_lvl_gr["0"]["0"].groups():
    #                 mesh_comp_num["segment_ids"][segment_id]["detail_lvls"][detail_lvl][
    #                     "mesh_ids"
    #                 ][mesh_id] = {}
    #                 for mesh_component_name, mesh_component in mesh.arrays():
    #                     d_ref = mesh_comp_num["segment_ids"][segment_id]["detail_lvls"][
    #                         detail_lvl
    #                     ]["mesh_ids"][mesh_id]
    #                     d_ref[f"num_{mesh_component_name}"] = mesh_component.attrs[
    #                         f"num_{mesh_component_name}"
    #                     ]

    #     detail_lvl_to_fraction_dict = internal_segmentation.simplification_curve

    #     metadata_dict["segmentation_meshes"]["mesh_component_numbers"] = mesh_comp_num
    #     metadata_dict["segmentation_meshes"][
    #         "detail_lvl_to_fraction"
    #     ] = detail_lvl_to_fraction_dict

    root.attrs["metadata_dict"] = metadata_dict
    return metadata_dict