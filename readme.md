# edit-osm-add-missing-bridge-for-truck-restriction
## Introduction
This repository contains Python and JavaScript scripts using which we plan to add missing bridge data to OSM and then add truck restriction information to the bridge data included in OSM. This will be a two-phase process. In the first phase, we will add all the missing bridges. In the second phase, we will add truck restriction data to all the bridges. This repository is currently focused on Phase One.
## Setup
Install required Python packages from [requirements.txt](requirements.txt) and install
[QGIS-LTR](https://qgis.org/en/site/forusers/download.html), [Osmium tool](https://osmcode.org/osmium-tool/) with `brew install osmium-tool`, and [GDAL](https://gdal.org/index.html) library with `brew install gdal`.
## Process Overview
For a comprehensive description of the process, read this guide: [Overview-Add-missing-bridge-truck-restrictions-to-OSM](https://docs.google.com/document/d/1wzjOeGgahNM9B8nrBH0wPx1IWY3eTRSTkfMtBGokuJY/edit)
## Hydrography Approach
1. **Download Data:**
   - [OSM Ways Data](https://www.geofabrik.de/): Downloaded from Geofabrik, this project uses updated OSM data extracts for Kentucky.
      - Data link: [Kentucky-Latest.osm.pbf](https://drive.google.com/file/d/1p_Bejyj7mbCFA_8ohujI2Hy-5F-S6Op-/view?usp=sharing)
   - [NBI Bridge Dataset](https://infobridge.fhwa.dot.gov/Data/Map): Obtained from the Federal Highway Administration, containing detailed information on bridges and tunnels across the USA.
      - Data link: [Kentucky-NBI-bridge-data.csv](https://drive.google.com/file/d/1EbHY0RvZieGUjWRiAggxRcwAGA_BIu0F/view?usp=sharing)
   - [National Hydrography Dataset (NHD)](https://www.usgs.gov/national-hydrography/national-hydrography-dataset): Provides essential water feature details for accurate bridge associations.
      - Data link: [NHD-Kentucky-Streams-Flowline.gpkg](https://drive.google.com/file/d/1XEIrn9k1-eYbZCRSIacFPiXDT62Hs6SZ/view?usp=sharing)
2. **Filter & Process Data:**
Within the [filter_data](hydrography-approach/processing_scripts/filter_data) folder, we have two scripts that filter relevant OSM data and NBI bridge data.
   - **Output:** 
     - [Kentucky-filtered-highways.gpkg](https://drive.google.com/file/d/1brW3ak_0NiwqsYcO-FO-TsYI-2Gkqyqa/view?usp=sharing)
     - [Kentucky-NBI-bridges.gpkg](https://drive.google.com/file/d/1bAzaOcK1isNqyth0tEa86HAfon-NIHax/view?usp=sharing)
3. **Tag Data:**
To ensure precise associations between NBI bridges and relevant OSM ways, data tagging processes are implemented within the [tag_data](hydrography-approach/processing_scripts/tag_data) folder:
   - Filter out bridges already in OSM data, near freeway interchanges, or near tunnel=culvert OSM ways.
   - Tag OSM ways and NBI bridges with nearby NHD streams and OSM ways.
   - **Outputs:** 
      - Intersections among OSM ways and NHD streams: [OSM-NHD-Intersections.csv](https://drive.google.com/file/d/1SIQ3JWlslpvMItPInYucULJEM0uHXjVN/view?usp=sharing)
      - OSM ways data tagged with relevant NHD stream data: [OSM-NHD-Join.csv](https://drive.google.com/file/d/1VlRr6OzL1teocrYgBYujUaVdLK0qErZc/view?usp=sharing)
      - NBI bridge data tagged with nearby OSM ways: [NBI-30-OSM-NHD-Join.csv](https://drive.google.com/file/d/1dz2qvGof9BYS5ONWf9x5S38Oqv70RtDV/view?usp=sharing)
4. **Associate Data:**
Within the [associate_data](hydrography-approach/processing_scripts/associate_data) folder, we have scripts that perform the following steps:
   - Create associations among NBI-OSM and OSM-NHD data, linking NBI bridges, OSM ways, and NHD water streams.
   - Determine final OSM ways for NBI bridges based on specified conditions and bridge attributes.
   - Project final coordinates of NBI bridges onto associated OSM ways.
   - Calculate match percentages for associated OSM ways' road names.
   - Remove nearby bridges within 30m based on fuzzy match scores.
   - **Output:** [Final-bridges-with-percentage-match.csv](https://drive.google.com/file/d/1Ap97_7e0zmypqvC1wGDPJAmrxFGhvc8R/view?usp=sharing)

## Mile-point Approach
The milepoint approach automates the addition of bridges to OpenStreetMap (OSM) using detailed Linear Referencing System (LRS) data. By leveraging milepoint information from bridge and road datasets, this method accurately locates and integrates missing bridges into OSM.

1. **Integrate Data**
   - Merge bridge and road datasets including milepoint information
   - Prepare datasets by cleaning and standardizing column names.
2. **Associate bridge and road data**
   - Associate bridges with road segments based on milepoint ranges.
   - Filter and process left-right lane bridges for accurate representation.
3. **Interpolate bridges on OSM ways**
   - Calculate precise bridge positions along road geometries using milepoint data.
   - Improve accuracy through fuzzy matching of road names and bridge descriptions.
4. **Match OSM Data**
   - Match interpolated bridge locations with existing OSM road network.
   - Select closest OSM ways to each bridge location for integration.
5. **Export Data**
   - Generate files containing interpolated bridge points and associated road segments.
6. **Output**
   - [Kentucky-osm-road-points.gpkg](https://drive.google.com/file/d/1_firL0QLRn9tgK9rHEp3SVpFOpAtcPyQ/view?usp=sharing)
## Merging Association Approaches
The [merge-approaches](merge-approaches) folder contains script that merges data from both the NBI-OSM associations approaches and generates a combined output.
   - **Output:** [merged-approaches-association-output.csv](https://drive.google.com/file/d/1S1Qsp755ZCCv3omNaBCHkh9YMGLTwh5n/view?usp=sharing)

## Split OSM ways using Python and JOSM
1. **Obtain Bridge Coordinates on OSM Ways:**
Within the [obtain_bridge_split_coordinates](split-ways-using-JOSM/obtain_bridge_split_coordinates) folder, we have the script that identifies and positions bridge coordinates equidistant from the midpoint along specified OSM ways.
   - **Output:** [bridge-osm-association-with-split-coords.csv](https://drive.google.com/file/d/1_eEKMMWVWYTT9_oK8rgNEi2sFnelEmjd/view?usp=sharing)
2. **Use JOSM to Add Bridge Tags:**
Within the [split_ways_add_bridge_tag](split-ways-using-JOSM/split_ways_add_bridge_tag) folder, we have the following scripts:
   - Add Tags to Bridge Spanning over Single OSM Way:
     - Script: [01-JOSM-1-split-way-in-place.js](split-ways-using-JOSM/split_ways_add_bridge_tag/01-JOSM-1-split-way-in-place.js)
     - Utilize the JOSM Scripting Plugin to accurately position bridge locations along existing ways and split ways to incorporate new nodes. This includes adding the "bridge=yes" tag to the identified way.
   - Determine OSM ways covered by bridges which span multiple ways using [NetworkX](https://networkx.org/).
     - Script: [02-shortest-route-between-two-ways.py](split-ways-using-JOSM/split_ways_add_bridge_tag/02-shortest-route-between-two-ways.py)
   - Add Tags to Bridge Spanning over Multiple OSM Ways:
     - Script: [03-JOSM-1-handle-multi-way-bridge.js](split-ways-using-JOSM/split_ways_add_bridge_tag/03-JOSM-1-handle-multi-way-bridge.js)
     - Using Python libraries Osmium and NetworkX alongside the JOSM Scripting Plugin to update OSM data. This involves finding all OSM way IDs that the bridge spans and ensuring accurate tagging.
## Conclusion
This repository provides tools and scripts necessary to enhance OSM bridge data using publicly available datasets. By automating the identification, tagging, and association processes, it aims to improve the accuracy and completeness of bridge information within OpenStreetMap.
