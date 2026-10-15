# QGIS and Power BI

## QGIS

1. Start a QGIS project and add `outputs/hazard_zones.geojson`, `outputs/coverage.geojson`, `outputs/properties.geojson`, and the `cells` layer from `outputs/concentration.gpkg`.
2. Set the project CRS to EPSG:3310 for California distance and area inspection. GeoJSON inputs are WGS84; use QGIS reprojection on the fly.
3. Categorize hazard zones by `band` (V yellow, VI orange, VII+ red) with 35% opacity. Categorize properties by `band` and size by `tiv_usd`. Style cells with graduated `tiv_usd` values.
4. Inspect property IDs and source row lineage. Use the coverage polygon to distinguish below-threshold and unmapped areas.
5. Save the QGIS project with relative layer paths if sharing. Re-running the pipeline updates the same layer paths.

The delivered GIS layers are generated and verified by Python; no manually edited QGIS project is required for reproducibility.

## Power BI Desktop

1. Run `python build_powerbi.py` after the pipeline. Open `powerbi/Property_Exposure.pbip` in a recent Power BI Desktop supporting PBIP/PBIR.
2. If moving the folder to another machine, set the `OutputFolder` Power Query parameter to the absolute `outputs` folder, using forward slashes. Refresh data.
3. Inspect the three pages: historical exposure with city/occupancy slicers; 10 km concentrations; and global data-quality exceptions.
4. Check Total Insured Value against `outputs/validation.json`, and accepted row count against `properties.csv`. VI+ includes bands VI and VII+ only. Quality tables are deliberately disconnected from accepted properties so quality results describe the full source population.
5. Save as `.pbix` in Desktop if needed. Power BI Desktop rendering and refresh have not been validated by the automated Python tests. No `.pbix` binary is claimed as delivered.

The Power BI report uses local CSV imports and DAX measures. Geographic inspection is available in the standalone Leaflet map, Streamlit map and QGIS layers. No Power BI account or cloud service is required for the local Python pipeline.
