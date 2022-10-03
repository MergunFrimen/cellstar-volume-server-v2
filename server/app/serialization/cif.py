from typing import Union

import numpy as np
from ciftools.binary import BinaryCIFWriter
from ciftools.writer.base import OutputStream
from db.models import VolumeSliceData, VolumeMetadata, MeshesData

from app.core.models import GridSliceBox
from app.serialization.data.volume_info import VolumeInfo
from app.serialization.data.segment_set_table import SegmentSetTable
from app.serialization.data.meshes_for_cif import MeshesForCif

from app.serialization.volume_cif_categories.volume_data_3d_info import CategoryWriterProvider_VolumeData3dInfo
from app.serialization.volume_cif_categories.volume_data_3d import CategoryWriterProvider_VolumeData3d
from app.serialization.volume_cif_categories.segmentation_table import CategoryWriterProvider_SegmentationDataTable
from app.serialization.volume_cif_categories.segmentation_data_3d import CategoryWriterProvider_SegmentationData3d
from app.serialization.volume_cif_categories.meshes import CategoryWriterProvider_Mesh, CategoryWriterProvider_MeshVertex, CategoryWriterProvider_MeshTriangle

from app.core.timing import Timing


class ConverterOutputStream(OutputStream):
    result_binary: bytes = b''
    result_text: str = ""

    def write_string(self, data: str) -> bool:
        self.result_text = data
        return True

    def write_binary(self, data: bytes) -> bool:
        self.result_binary = data
        return True


def get_bytes_from_cif_writer(writer: BinaryCIFWriter) -> bytes:
    writer.encode()
    output_stream = ConverterOutputStream()
    writer.flush(output_stream)
    return output_stream.result_binary


def serialize_volume_slice(
    slice: VolumeSliceData, metadata: VolumeMetadata, box: GridSliceBox
) -> Union[bytes, str]:  # TODO: add binary cif to the project
    writer = BinaryCIFWriter("volume_server")

    writer.start_data_block("SERVER")
    # NOTE: the SERVER category left empty for now
    # TODO: create new category with request and responce info (e.g. query region, timing info, etc.)
    # writer.write_category(volume_info_category, [volume_info])

    volume_info = VolumeInfo(name="volume", metadata=metadata, box=box)
    volume_info_category = CategoryWriterProvider_VolumeData3dInfo()

    # volume
    if "volume_slice" in slice:
        writer.start_data_block("volume")  # Currently needs to be EM for
        writer.write_category(volume_info_category, [volume_info])

        data_category = CategoryWriterProvider_VolumeData3d()
        writer.write_category(data_category, [np.ravel(slice["volume_slice"])])

    # segmentation
    if "segmentation_slice" in slice and slice["segmentation_slice"]["category_set_ids"] is not None:
        writer.start_data_block("segmentation_data")
        writer.write_category(volume_info_category, [volume_info])

        segmentation = slice["segmentation_slice"]

        # table
        set_dict = segmentation["category_set_dict"]
        segment_set_table = SegmentSetTable.from_dict(set_dict)
        table_writer_provider = CategoryWriterProvider_SegmentationDataTable()
        writer.write_category(table_writer_provider, [segment_set_table])

        # 3d_ids
        # uint32
        ids_writer_provider = CategoryWriterProvider_SegmentationData3d()
        writer.write_category(ids_writer_provider, [np.ravel(segmentation["category_set_ids"])])

    # binary = True
    # writer.encode()
    # output_stream = ConverterOutputStream()
    # writer.flush(output_stream)
    # return output_stream.result_binary if binary else output_stream.result_text
    return get_bytes_from_cif_writer(writer)


def serialize_volume_info(metadata: VolumeMetadata, box: GridSliceBox) -> bytes:
    writer = BinaryCIFWriter("volume_server")

    writer.start_data_block("volume_info")
    volume_info = VolumeInfo(name="volume", metadata=metadata, box=box)
    writer.write_category(CategoryWriterProvider_VolumeData3dInfo(), [volume_info])

    return get_bytes_from_cif_writer(writer)


def serialize_meshes(meshes: MeshesData,  metadata: VolumeMetadata, box: GridSliceBox) -> bytes:
    with Timing('  prepare meshes for cif'):
        meshes_for_cif = MeshesForCif(meshes)

    with Timing('  write categories'):
        writer = BinaryCIFWriter("volume_server")

        writer.start_data_block("volume_info")
        volume_info = VolumeInfo(name="volume", metadata=metadata, box=box)
        writer.write_category(CategoryWriterProvider_VolumeData3dInfo(), [volume_info])

        writer.start_data_block("meshes")
        writer.write_category(CategoryWriterProvider_Mesh(), [meshes_for_cif])
        writer.write_category(CategoryWriterProvider_MeshVertex(), [meshes_for_cif])
        writer.write_category(CategoryWriterProvider_MeshTriangle(), [meshes_for_cif])

    with Timing('  get bytes'):
        bcif = get_bytes_from_cif_writer(writer)
    return bcif

