
from server.app.api.requests import VolumeRequestBox, VolumeRequestDataKind, VolumeRequestInfo
from server.app.core.service import VolumeServerService


async def get_segmentation_box_query(
        volume_server: VolumeServerService,
        source: str,
        id: str,
        segmentation: str,
        time: int,
        channel_id: int,
        a1: float,
        a2: float,
        a3: float,
        b1: float,
        b2: float,
        b3: float,
        max_points: int
):
    response = await volume_server.get_volume_data(
        req=VolumeRequestInfo(
            source=source,
            structure_id=id,
            segmentation_id=segmentation,
            channel_id=channel_id,
            time=time,
            max_points=max_points,
            data_kind=VolumeRequestDataKind.segmentation,
        ),
        req_box=VolumeRequestBox(bottom_left=(a1, a2, a3), top_right=(b1, b2, b3)),
    )
    return response

async def get_volume_box_query(
        volume_server: VolumeServerService,
        source: str,
        id: str,
        time: int,
        channel_id: int,
        a1: float,
        a2: float,
        a3: float,
        b1: float,
        b2: float,
        b3: float,
        max_points: int
):
    response = await volume_server.get_volume_data(
        req=VolumeRequestInfo(
            source=source,
            structure_id=id,
            channel_id=channel_id,
            time=time,
            max_points=max_points,
            data_kind=VolumeRequestDataKind.volume,
        ),
        req_box=VolumeRequestBox(bottom_left=(a1, a2, a3), top_right=(b1, b2, b3)),
    )
    return response