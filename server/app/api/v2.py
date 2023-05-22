from typing import Optional

from fastapi import FastAPI, Query, Response
from starlette.responses import JSONResponse

from app.api.requests import (
    EntriesRequest,
    MeshRequest,
    MetadataRequest,
    VolumeRequestBox,
    VolumeRequestDataKind,
    VolumeRequestInfo,
)
from app.core.service import VolumeServerService
from app.serialization.json_numpy_response import JSONNumpyResponse
from app.settings import settings
HTTP_CODE_UNPROCESSABLE_ENTITY = 422


def configure_endpoints(app: FastAPI, volume_server: VolumeServerService):
    @app.get("/v2/version")
    async def get_version():
        # settings = app.settings
        git_tag = settings.GIT_TAG
        git_sha = settings.GIT_SHA

        return {
            'git_tag': git_tag,
            'git_sha': git_sha
        }


    @app.get("/v2/list_entries/{limit}")
    async def get_entries(limit: int = 100):
        request = EntriesRequest(limit=limit, keyword="")
        response = await volume_server.get_entries(request)

        return response

    @app.get("/v2/list_entries/{limit}/{keyword}")
    async def get_entries_keyword(keyword: str, limit: int = 100):
        request = EntriesRequest(limit=limit, keyword=keyword)
        response = await volume_server.get_entries(request)

        return response

    @app.get("/v2/{source}/{id}/segmentation/box/{segmentation}/{time}/{channel_id}/{a1}/{a2}/{a3}/{b1}/{b2}/{b3}")
    async def get_segmentation_box(
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
        max_points: Optional[int] = Query(0)
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

        return Response(response, headers={"Content-Disposition": f'attachment;filename="{id}.bcif"'})

    @app.get("/v2/{source}/{id}/volume/box/{time}/{channel_id}/{a1}/{a2}/{a3}/{b1}/{b2}/{b3}")
    async def get_volume_box(
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
        max_points: Optional[int] = Query(0),
    ):
        response = await volume_server.get_volume_data(
            req=VolumeRequestInfo(
                source=source, structure_id=id, channel_id=channel_id,
                time=time, max_points=max_points, data_kind=VolumeRequestDataKind.volume
            ),
            req_box=VolumeRequestBox(bottom_left=(a1, a2, a3), top_right=(b1, b2, b3)),
        )

        return Response(response, headers={"Content-Disposition": f'attachment;filename="{id}.bcif"'})

    @app.get("/v2/{source}/{id}/segmentation/cell/{segmentation}/{time}/{channel_id}")
    async def get_segmentation_cell(source: str, id: str, segmentation: str, time: int, channel_id: int,  max_points: Optional[int] = Query(0)):
        response = await volume_server.get_volume_data(
            req=VolumeRequestInfo(
                source=source,
                structure_id=id,
                segmentation_id=segmentation,
                time=time,
                channel_id=channel_id,
                max_points=max_points,
                data_kind=VolumeRequestDataKind.segmentation,
            ),
        )

        return Response(response, headers={"Content-Disposition": f'attachment;filename="{id}.bcif"'})

    @app.get("/v2/{source}/{id}/volume/cell/{time}/{channel_id}")
    async def get_volume_cell(source: str, id: str, time: int, channel_id: int, max_points: Optional[int] = Query(0)):
        response = await volume_server.get_volume_data(
            req=VolumeRequestInfo(
                source=source, structure_id=id,
                time=time, channel_id=channel_id, max_points=max_points, data_kind=VolumeRequestDataKind.volume
            ),
        )

        return Response(response, headers={"Content-Disposition": f'attachment;filename="{id}.bcif"'})

    @app.get("/v2/{source}/{id}/metadata")
    async def get_metadata(
        source: str,
        id: str,
    ):
        request = MetadataRequest(source=source, structure_id=id)
        metadata = await volume_server.get_metadata(request)

        return metadata

    @app.get("/v2/{source}/{id}/mesh/{segment_id}/{detail_lvl}")
    async def get_meshes(source: str, id: str, segment_id: int, detail_lvl: int):
        request = MeshRequest(source=source, structure_id=id, segment_id=segment_id, detail_lvl=detail_lvl)
        try:
            meshes = await volume_server.get_meshes(request)
            return JSONNumpyResponse(meshes)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=HTTP_CODE_UNPROCESSABLE_ENTITY)

    @app.get("/v2/{source}/{id}/volume_info")
    async def get_volume_info(
        source: str,
        id: str,
    ):
        request = MetadataRequest(source=source, structure_id=id)
        response_bytes = await volume_server.get_volume_info(request)
        return Response(response_bytes, headers={"Content-Disposition": f'attachment;filename="{id}-volume_info.bcif"'})

    @app.get("/v2/{source}/{id}/mesh_bcif/{segment_id}/{detail_lvl}")
    async def get_meshes_bcif(source: str, id: str, segment_id: int, detail_lvl: int):
        request = MeshRequest(source=source, structure_id=id, segment_id=segment_id, detail_lvl=detail_lvl)
        try:
            response_bytes = await volume_server.get_meshes_bcif(request)
            return Response(
                response_bytes, headers={"Content-Disposition": f'attachment;filename="{id}-volume_info.bcif"'}
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=HTTP_CODE_UNPROCESSABLE_ENTITY)
        finally:
            pass
