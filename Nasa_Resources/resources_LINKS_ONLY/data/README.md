# Downloaded-data inventory

The team reported having downloaded datasets. Those files were not attached to this task and have not been inspected. [download-manifest.json](download-manifest.json) therefore starts with an empty `records` array.

Add one record per coherent dataset subset or file group. Use IDs from [sources.json](../sources.json).

| Field | Record |
| --- | --- |
| record_id | Unique project ID |
| source_ids | Matching catalogue IDs |
| product / version | Exact product name and version from metadata |
| file_paths | Repository-relative/local project paths or a separate stable authorized data location |
| temporal_start / temporal_end | Actual observation coverage |
| area | Geometry reference, bounds and/or administrative IDs |
| variables / units | Exact layers and their units |
| crs / native_resolution | Coordinate system and genuine spatial support |
| downloaded_on / processing_timestamp | Actual dates, not the catalogue review date |
| qa_policy | Masks, flags and missing-data treatment |
| checksums | SHA-256 values for files or an associated checksum manifest |
| citation / license_notes | Provider citation, DOI and redistribution terms |
| verification_status | e.g. uninspected, metadata_checked, analysis_ready |

Use [download-manifest.example.json](download-manifest.example.json) for the shape. It contains placeholders, not observations. Replace nulls and empty arrays only with real metadata.

Suggested local subfolders are `raw/` and `processed/`; both are ignored by the included `.gitignore`. Keep small published derived examples in a separate explicitly reviewed directory if needed.
