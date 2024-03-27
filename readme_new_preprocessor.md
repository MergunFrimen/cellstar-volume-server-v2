## Using preprocessor to add entry to database or extend data of existing entry

The `preprocess` command of `preprocessor/cellstar_preprocessor/preprocess.py` script is used for adding entries to the database with the following arguments:

  | Argument | Description |
  | -------- | ---------- |
  |`--mode` | Either `add` (adding entry to the database) or `extend` (extend data of existing entry) |
  |`--quantize-dtype-str` | Optional data quantization (options are - `u1` or `u2`), less precision, but also requires less storage. Not used by default |
  |`--quantize-downsampling-levels` | Specify which downsampling level should be quantized as a sequence of numbers, e.g. `1 2`. Not used by default |
  |`--force-volume-dtype` | optional data type of volume data to be used instead of the one used volume file. Not used by default |
  |`--max-size-per-downsampling-lvl-mb` | Maximum size of data per downsampling level in MB. Used to deterimine the number of downsampling steps data from which will be stored |
  |`--min-size-per-channel-mb` | Minimum size of data per downsampling level in MB. Used to deterimine the number of downsampling steps data from which will be stored. Default is `5` |
  |`--min-downsampling-level` | Minimum downsampling level |
  |`--max-downsampling-level` | Maximum downsampling level |
  |`--remove-original-resolution` | Optional flag for removing original resolution data |
  |`--entry-id` | entry id (e.g. `emd-1832`) to be used as database folder name for that entry |
  |`--source-db` | source database name (e.g. `emdb`) to be used as DB folder name |
  |`--source-db-id` | actual source database ID of that entry (will be used to compute metadata) |
  |`--source-db-name` | actual source database name (will be used to compute metadata) |
  |`--working-folder` | path to directory where temporary files will be stored during the build process |
  |`--db-path` | path to folder with database |
  |`--input-path` | Path to input file. Should be provided for each input file separately (see examples) |
  |`--input-kind` | Kind of input file. One of the following: <code>[map\|sff\|omezarr\|mask\|application_specific_segmentation\|custom_annotations\|nii_volume\|nii_segmentation\|geometric_segmentation\|star_file_geometric_segmentation\|ometiff_image\|ometiff_segmentation\|extra_data]</code>. See examples for more details. |
  <!-- TODO: table with input kinds? -->
  <!-- TODO: remove nii things? -->


### Example of adding a single entry to the database

<!-- - Create a folder `inputs/emd-1832`
- Download [MAP](https://ftp.ebi.ac.uk/pub/databases/emdb/structures/EMD-1832/map/emd_1832.map.gz) and extract it to `inputs/emd-1832/emd_1832.map`
- Download [Segmentation](https://www.ebi.ac.uk/em_static/emdb_sff/18/1832/emd_1832.hff.gz) and extract it to `inputs/emd-1832/emd_1832.hff` -->

- To add a single entry to the db, run:

```
python preprocessor/cellstar_preprocessor/preprocess.py preprocess --mode add --input-path test-data/preprocessor/sample_volumes/emdb_sff/EMD-1832.map --input-kind map --input-path test-data/preprocessor/sample_segmentations/emdb_sff/emd_1832.hff --input-kind sff --entry-id emd-1832 --source-db emdb --source-db-id emd-1832 --source-db-name emdb --working-folder preprocessor/temp/temp_zarr_hierarchy_storage --db-path preprocessor/temp/test_db --quantize-dtype-str u1
```

It will add entry `emd-1832` to the database and during preprocessing volume data will be quantized with `u1` option