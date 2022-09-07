import json
from collections import defaultdict

from math import ceil
from typing import Optional, Union

from db.interface.i_preprocessed_db import IReadOnlyPreprocessedDb
from db.interface.i_preprocessed_medatada import IPreprocessedMetadata
from .i_volume_server import IVolumeServer
from .preprocessed_volume_to_cif.i_volume_to_cif_converter import IVolumeToCifConverter
from volume_server.src.requests.volume_request.i_volume_request import IVolumeRequest
from .requests.cell_request.i_cell_request import ICellRequest
from .requests.entries_request.i_entries_request import IEntriesRequest
from .requests.mesh_request.i_mesh_request import IMeshRequest
from .requests.metadata_request.i_metadata_request import IMetadataRequest

__MAX_DOWN_SAMPLING_VALUE__ = 1000000


class VolumeServerV1(IVolumeServer):
    async def _filter_entries_by_keyword(self, namespace: str, entries: list[str], keyword: str):
        filtered = []
        for entry in entries:
            if keyword in entry:
                filtered.append(entry)
                continue

            annotations = await self.db.read_annotations(namespace, entry)
            if keyword.lower() in json.dumps(annotations).lower():
                filtered.append(entry)
                continue

        return filtered

    async def get_entries(self, req: IEntriesRequest) -> dict:
        limit = req.limit()
        entries = dict()
        if limit == 0:
            return entries

        sources = await self.db.list_sources()
        for source in sources:
            retrieved = await self.db.list_entries(source, limit)
            if req.keyword():
                retrieved = await self._filter_entries_by_keyword(source, retrieved, req.keyword())

            if len(retrieved) == 0:
                continue

            entries[source] = retrieved
            limit -= len(retrieved)
            if limit == 0:
                break

        return entries

    async def get_metadata(self, req: IMetadataRequest) -> Union[bytes, str]:
        grid = await self.db.read_metadata(req.source(), req.structure_id())
        try:
            annotation = await self.db.read_annotations(req.source(), req.structure_id())
        except Exception as e:
            annotation = None

        # converted = self.volume_to_cif.convert_metadata(grid_metadata)
        return {"grid": grid.json_metadata(), "annotation": annotation}

    def __init__(self, db: IReadOnlyPreprocessedDb, volume_to_cif: IVolumeToCifConverter):
        self.db = db
        self.volume_to_cif = volume_to_cif

    async def get_cell(self, req: ICellRequest) -> bytes:  # TODO: add binary cif to the project
        metadata = await self.db.read_metadata(req.source(), req.structure_id())

        with self.db.read(namespace=req.source(), key=req.structure_id()) as reader:
            db_slice = await reader.read(
                lattice_id=1,
                down_sampling_ratio=1)  # TODO: parse params from request + metadata

        cif = self.volume_to_cif.convert(db_slice, metadata, 1, [10, 10, 10])  # TODO: replace 10,10,10 with cell size
        return cif

    async def get_volume(self, req: IVolumeRequest) -> bytes:  # TODO: add binary cif to the project
        metadata = await self.db.read_metadata(req.source(), req.structure_id())

        print(metadata)

        lattice = self.decide_lattice(req, metadata)
        grid = self.decide_grid(req, metadata)
        print("Converted grid to: " + str(grid))

        down_sampling = self.decide_down_sampling(grid, req, metadata)
        print("Decided down_sampling to be: " + str(down_sampling))

        grid = self.down_sampled_grid(down_sampling, grid)

        print("Converted grid (down sampled) to: " + str(grid))

        print("Making request to read slice:\n" \
              "  source: " + str(req.source()) + "\n" +
              "  id: " + str(req.structure_id()) + "\n" +
              "  lattice: " + str(lattice) + "\n" +
              "  down_sampling: " + str(down_sampling) + "\n" +
              "  grid: " + str(grid))

        with self.db.read(namespace=req.source(), key=req.structure_id()) as reader:
            db_slice = await reader.read_slice(
                lattice_id=lattice,
                down_sampling_ratio=down_sampling,
                box=grid,
            )

        cif = self.volume_to_cif.convert(db_slice, metadata, down_sampling, self.grid_size(grid))
        return cif

    async def get_meshes(self, req: IMeshRequest) -> list[object]:
        with self.db.read(req.source(), req.id()) as context:
            try:
                return await context.read_meshes(req.segment_id(), req.detail_lvl())
            except KeyError as e:
                print("Exception in get_meshes: " + str(e))
                meta = await self.db.read_metadata(req.source(), req.id())
                segments_levels = self._extract_segments_detail_levels(meta)
                error_msg = f'Invalid segment_id={req.segment_id()} or detail_lvl={req.detail_lvl()} (available segment_ids and detail_lvls: {segments_levels})'
                raise error_msg

    def _extract_segments_detail_levels(self, meta: IPreprocessedMetadata) -> dict[int, list[int]]:
        '''Extract available segment_ids and detail_lvls for each segment_id'''
        meta_js = meta.json_metadata()
        segments_levels = meta_js.get('segmentation_meshes', {}).get('mesh_component_numbers', {}).get('segment_ids',
                                                                                                       {})
        result: dict[int, list[int]] = defaultdict(list)
        for seg, obj in segments_levels.items():
            for lvl in obj.get('detail_lvls', {}).keys():
                result[int(seg)].append(int(lvl))
        sorted_result = {seg: sorted(result[seg]) for seg in sorted(result.keys())}
        return sorted_result

    def decide_lattice(self, req: IVolumeRequest, metadata: IPreprocessedMetadata) -> Optional[int]:
        ids = metadata.segmentation_lattice_ids() or []
        if req.segmentation_id() not in ids:
            return ids[0] if len(ids) > 0 else None
        return req.segmentation_id()

    def decide_down_sampling(self, original_grid: tuple[tuple[int, int, int], tuple[int, int, int]],
                             req: IVolumeRequest, metadata: IPreprocessedMetadata) -> int:

        down_samplings = metadata.volume_downsamplings()
        print("[Downsampling] Available downsamplings: " + str(down_samplings))
        print("[Downsampling] Max points: " + str(req.max_points()))
        if not req.max_points():
            print("[Downsampling] req.max_points() is false -> returning instead downsampling = " + str(
                int(down_samplings[0])))
            return 1 if '1' in down_samplings else int(down_samplings[0])

        size = 1
        for i in self.grid_size(original_grid):
            size *= i

        print("[Downsampling] Original grid size: " + str(size))

        # TODO: improve rounding depending on conservative, strict, etc approach
        desired_down_sampling = ceil(size / req.max_points())
        print("[Downsampling] Computed desired downsampling: " + str(desired_down_sampling))

        decided = False
        decided_down_sampling = __MAX_DOWN_SAMPLING_VALUE__  # max_value
        highest_down_sampling = 0
        for ds in down_samplings:
            if int(ds) > highest_down_sampling:
                highest_down_sampling = int(ds)

            if desired_down_sampling <= int(ds) < decided_down_sampling:
                decided_down_sampling = int(ds)
                decided = True

        if decided:
            print("[Downsampling] Decided (A): " + str(decided_down_sampling))
            return decided_down_sampling

        print("[Downsampling] Decided (B): " + str(highest_down_sampling))
        return highest_down_sampling

    def grid_size(self, grid: tuple[tuple[int, int, int], tuple[int, int, int]]) -> list[int]:
        print("[Downsampling] Computing grid")
        grid_x = grid[1][0] - grid[0][0]
        grid_y = grid[1][1] - grid[0][1]
        grid_z = grid[1][2] - grid[0][2]

        print("[Downsampling] Computing grid (x,y,z): (" + str(grid_x) + "," + str(grid_y) + "," + str(grid_z) + ")")
        return [grid_x, grid_y, grid_z]

    def decide_grid(self, req: IVolumeRequest, meta: IPreprocessedMetadata) \
            -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        return (
            (self._float_to_grid(meta.origin()[0], meta.voxel_size(1)[0], meta.grid_dimensions()[0], req.x_min()),
             self._float_to_grid(meta.origin()[1], meta.voxel_size(1)[1], meta.grid_dimensions()[1], req.y_min()),
             self._float_to_grid(meta.origin()[2], meta.voxel_size(1)[2], meta.grid_dimensions()[2], req.z_min())),
            (self._float_to_grid(meta.origin()[0], meta.voxel_size(1)[0], meta.grid_dimensions()[0], req.x_max()),
             self._float_to_grid(meta.origin()[1], meta.voxel_size(1)[1], meta.grid_dimensions()[1], req.y_max()),
             self._float_to_grid(meta.origin()[2], meta.voxel_size(1)[2], meta.grid_dimensions()[2], req.z_max())))

    def down_sampled_grid(self, down_sampling: int, original_grid: tuple[tuple[int, int, int], tuple[int, int, int]]) \
            -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        if down_sampling == 1:
            return original_grid

        result: list[list] = []
        for i in range(2):
            result.append([])
            for j in range(3):
                result[i].append(round(original_grid[i][j] / down_sampling))

        return result

    def _float_to_grid(self, origin: float, step: float, grid_size: int, to_convert: float) -> int:
        if to_convert < origin:
            return 0

        if to_convert > origin + step * (grid_size - 1):
            return grid_size - 1

        return round((to_convert - origin) / step)
