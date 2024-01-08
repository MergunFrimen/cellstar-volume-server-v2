# Instead of db store etc. there should be 
# a number of methods to store the data

# QUESTION: what is the role of db (FileSystemVolumeServerDB) then?
# What methods should be left there?
# only those that provide access to data?

from argparse import ArgumentError
from pathlib import Path
from typing import Literal
from cellstar_db.file_system.constants import GEOMETRIC_SEGMENTATION_FILENAME, GEOMETRIC_SEGMENTATIONS_ZATTRS, LATTICE_SEGMENTATION_DATA_GROUPNAME, MESH_SEGMENTATION_DATA_GROUPNAME, VOLUME_DATA_GROUPNAME
from cellstar_db.models import GeometricSegmentationData, ShapePrimitiveData
from cellstar_db.protocol import VolumeServerDB
from cellstar_preprocessor.flows.common import open_json_file, open_zarr_structure_from_path, save_dict_to_json_file
import zarr


class VolumeAndSegmentationContext:
    def __init__(self, db: VolumeServerDB, namespace: str, key: str, working_folder: Path):
        self.working_folder = working_folder
        self.intermediate_zarr_structure = (
            working_folder
            / key
        )
        self.db = db
        self.path_to_entry = self.db._path_to_object(namespace, key)
        self.key = key
        self.namespace = namespace
        self.zarr_structure_for_copying = self.intermediate_zarr_structure.parent / f'temp_{self.intermediate_zarr_structure.name}.zarr'
        self.path_to_zarr_root_data: Path = self.db.path_to_zarr_root_data(namespace, key)
        
        if self.db.store_type == "zip":
            entry_dir_path: Path = self.db._path_to_object(namespace, key)
            if not entry_dir_path.exists():
                entry_dir_path.mkdir(parents=True, exist_ok=True)
            # 0. Opening existing store
            # if exists - reading, if not - writing
            # alternatively try 'a'
            mode = 'r' if self.path_to_zarr_root_data.exists() else 'w'
            existing_store = zarr.ZipStore(
                path=str(self.path_to_zarr_root_data),
                compression=0,
                allowZip64=True,
                mode=mode,
            )
            # 1. Creating store for copying
            self.store = zarr.DirectoryStore(
                path=str(self.zarr_structure_for_copying)
            )

            # 2. Copying entire existing store to temp store
            zarr.copy_store(existing_store, self.store)
            # 3. Closing existing store
            existing_store.close()
            # 3. Deleting existing store
            self.db.path_to_zarr_root_data(namespace, key).unlink()
            
        else:
            raise ArgumentError("store type is not supported: {self.store_type}")

    def add_volume(self):
        # NOTE: only a single volume for now
        temp_store = zarr.DirectoryStore(
                str(self.intermediate_zarr_structure)
            )
        temp_zarr_structure: zarr.Group = open_zarr_structure_from_path(
            self.intermediate_zarr_structure
        )
        perm_root = zarr.group(self.store)
        zarr.copy_store(source=temp_store, dest=self.store, source_path=VOLUME_DATA_GROUPNAME, dest_path=VOLUME_DATA_GROUPNAME)
        print('Volume added')

    def add_segmentation(self, id: str, kind: Literal["lattice", "mesh", "primitive"]):
        temp_store = zarr.DirectoryStore(
                str(self.intermediate_zarr_structure)
            )
        temp_zarr_structure: zarr.Group = open_zarr_structure_from_path(
            self.intermediate_zarr_structure
        )
        perm_root = zarr.group(self.store)
        if kind == 'lattice':
            source_path = f'{LATTICE_SEGMENTATION_DATA_GROUPNAME}/{id}'
            
            if LATTICE_SEGMENTATION_DATA_GROUPNAME not in perm_root:
                perm_root.create_group(LATTICE_SEGMENTATION_DATA_GROUPNAME)
            
            zarr.copy_store(source=temp_store, dest=self.store, source_path=source_path, dest_path=source_path)    
            
        elif kind == 'mesh':
            source_path = f'{MESH_SEGMENTATION_DATA_GROUPNAME}/{id}'
            
            if MESH_SEGMENTATION_DATA_GROUPNAME not in perm_root:
                perm_root.create_group(MESH_SEGMENTATION_DATA_GROUPNAME)
            
            zarr.copy_store(source=temp_store, dest=self.store, source_path=source_path, dest_path=source_path)    
            
        elif kind == 'primitive':
            geometric_segmentation_data: list[GeometricSegmentationData] = temp_zarr_structure.attrs[GEOMETRIC_SEGMENTATIONS_ZATTRS]
            # find that segmentation by id
            filter_results = list(filter(lambda g: g["segmentation_id"] == id, geometric_segmentation_data))
            assert len(filter_results) == 1
            target_geometric_segmentation = filter_results[0]
            # open existing geometric segmentation JSON file as list
            # if exists, if not - create
            d: list[GeometricSegmentationData] = []
            shape_primitives_path: Path = self.path_to_entry / GEOMETRIC_SEGMENTATION_FILENAME
            if (shape_primitives_path).exists():
                d = open_json_file(path=shape_primitives_path)
                # add to list new segmentation
            d.append(target_geometric_segmentation)
            # save back to file
            save_dict_to_json_file(
                d,
                GEOMETRIC_SEGMENTATION_FILENAME,
                self.path_to_entry
            )

        print('Segmentation added')
            

    def remove_volume(self):
        # NOTE: all volumes for now
        # need to delete group content from store
        # TODO: how to do it - possibly recreate the store without volume data group or?
        # plan:
        # create temp store
        # move all groups from existing store to temp store
        # delete perm store
        # create it again
        # copy all groups from temp store to new perm store EXCEPT VOLUME_DATA_GROUP

        perm_root = zarr.group(self.store)
        del perm_root[VOLUME_DATA_GROUPNAME]
        print('Volumes deletes')

    def remove_segmentation(self, id: str, kind: Literal["lattice", "mesh", "primitive"]):
        # 
        pass
    
    def _before_closing(self):
        # NOTE: this part in atexit and in exit
            # 5. Re-creating existing store with mode writing
            # 6. Copying entire self.store to new existing store
            # 7. Closing new existing store
            # 8. removing self.store
        new_existing_store = zarr.ZipStore(
            path=str(self.path_to_zarr_root_data),
            compression=0,
            allowZip64=True,
            mode="w",
        )
        zarr.copy_store(self.store, new_existing_store)
        # self.store.close()
        new_existing_store.close()
        self.store.rmdir()

    def close(self):
        if hasattr(self.store, "close"):
            self.store.close()
        else:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if hasattr(self.store, "close"):
            self._before_closing()
        else:
            pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        if hasattr(self.store, "aclose"):
            raise Exception('async mode is not supported')
        if hasattr(self.store, "close"):
            self._before_closing()
        else:
            pass

    # TODO: at the end remove temp store
                # can be atexit
        # temp_store.rmdir()