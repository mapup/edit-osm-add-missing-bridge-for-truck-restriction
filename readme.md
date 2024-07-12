# edit-osm-add-missing-bridge-for-truck-restriction
## Introduction
This repository contains Python and JavaScript scripts using which we plan to add missing bridge data to OSM and then add truck restriction information to the bridge data included in OSM. This will be a two-phase process. In the first phase, we will add all the missing bridges. In the second phase, we will add truck restriction data to all the bridges. This repository is currently focused on Phase One.
## Setup
- Install the necessary Python libraries using the [requirements.txt](requirements.txt) file.
- Install QGIS-LTR: [Download QGIS](https://qgis.org/en/site/forusers/download.html).
- Also, install the [Osmium tool](https://osmcode.org/osmium-tool/) using the *‘brew install osmium-tool’* command to filter OSM ways data. 
- Also, install the [GDAL](https://gdal.org/index.html) library using the command: *'brew install gdal'*
- To carry out step 3 (Tag Data) explained below, set the QGIS Python interpreter in VS Code (or any code editor of your choice) as follows:
   - Head over to ‘Applications’ on your PC.
   - Right-click on the QGIS-LTR application and select “Show Package contents”.
   - Within this folder, select ‘Contents’ and then the ‘MacOS’ folder.
   - From the ‘bin’ folder select and copy the path of the Python3 interpreter given as: “/Applications/QGIS-LTR.app/Contents/MacOS/bin/python3”
   - Enter the above interpreter path within the VS Code interpreter selector to run the scripts using QGIS with Python.
## Process Overview
For a comprehensive description of the process, read this guide: [Overview-Add-missing-bridge-truck-restrictions-to-OSM](https://docs.google.com/document/d/1wzjOeGgahNM9B8nrBH0wPx1IWY3eTRSTkfMtBGokuJY/edit)
## Steps Involved
1. **Download Data:**
   - [OSM Ways Data](https://www.geofabrik.de/): Downloaded from Geofabrik, providing updated extracts of OSM data for various regions. For this project, data for Kentucky has been chosen.
      - Data link: [Kentucky-Latest.osm.pbf](https://drive.google.com/file/d/12sFFF1nWA70qWfs-_ckUjfUcfPPpiu3L/view?usp=sharing)
   - [NBI Bridge Dataset](https://infobridge.fhwa.dot.gov/Data/Map): Obtained from the Federal Highway Administration, containing detailed information on bridges and tunnels across the USA.
      - Data link: [Kentucky-NBI-bridge-data.csv](https://drive.google.com/file/d/11dltxBUJaa6D917fZfWQtOUWaoS5R1bp/view?usp=sharing)
   - [National Hydrography Dataset (NHD)](https://www.usgs.gov/national-hydrography/national-hydrography-dataset): Provides essential water feature details for accurate bridge associations.
      - Data link: [NHD-Kentucky-Streams-Flowline.gpkg](https://drive.google.com/file/d/1i9E0QmgfjOMOu5hLIEqS4D5pRVpub6Tr/view?usp=sharing)
2. **Filter & Process Data:**
Within the [01-filtering-data](processing-scripts/01-filtering-data) folder of the [processing-scripts](processing-scripts) folder, we have the following two scripts:
   - [01-filter-osm-ways.py](processing-scripts/01-filtering-data/01-filter-osm-ways.py)
     - Select relevant OSM ways with highway types suitable for bridges and filtering based on specific criteria like "oneway=yes" and absence of a "bridge" tag.
     - **Output:** [Kentucky-filtered-highways.gpkg](https://drive.google.com/file/d/1PsGOz-1xvgbT0GsjI7_gLMhRKAJGxM34/view?usp=drive_link)
   - [02-process-filter-nbi-bridges.py](processing-scripts/01-filtering-data/02-process-filter-nbi-bridges.py)
      - Exclude culverts not marked as "posted" and removing bridges already present in OSM. 
      - Convert coordinate CSV to Geopackage for further processing.
      - **Output:** [NBI-Kentucky-Bridge-Data.gpkg](https://drive.google.com/file/d/1OpriiRxLzivBY6yn65b6g6SMQTZUQEVF/view?usp=sharing)
3. **Tag Data:**
To ensure precise associations between NBI bridges and relevant OSM ways, the following tag processes are implemented within [01-tagging-nbi-and-osm-data.py](processing-scripts/02-tagging-data/01-tagging-nbi-and-osm-data.py) script within the folder [02-tagging-data](processing-scripts/02-tagging-data):
   - Filter out bridges already existing in OSM data.
   - Filter out bridges near freeway interchanges and identify parallel bridges.
   - Filter out bridges near (within 10m) each other.
   - Tag OSM Ways with NHD Streams: Associate OSM ways with overlying NHD water streams to facilitate accurate bridge placements.
   - Calculate intersection nodes among OSM ways and NHD streams.
   - Tag NBI Bridges with NHD Streams: Associate NBI bridges with nearby water streams from NHD data using a 10-meter buffer around bridge points.
   - Tag NBI bridges with nearby OSM ways (within 30m).
   - **Outputs:** 
      - Geopackage file of NBI bridge points after all filtering steps: [Final-filtered-NBI-Bridges.gpkg](https://drive.google.com/file/d/1_UlwNASitbjKq8adaNOKIkDx9Gl2FPNF/view?usp=sharing)
      - Intersections among OSM ways and NHD streams: [OSM-NHD-Intersections.csv](https://drive.google.com/file/d/16IPQ8tpp1hZs-6wuZxhbOKFbfTPBsjlF/view?usp=sharing)
      - OSM ways data tagged with relevant NHD stream data: [OSM-NHD-Join.csv](https://drive.google.com/file/d/1yA-F4LMY3bVCNNj7Mz6ofvcNjySQH0r0/view?usp=sharing)
      - NBI bridge data tagged with relevant NHD stream data: [NBI-10-NHD-Join.csv](https://drive.google.com/file/d/1irB_8tURds27Ays9KZCos3NRAQs_fuDc/view?usp=sharing)
      - NBI bridge data tagged with nearby OSM ways: [NBI-30-OSM-NHD-Join.csv](https://drive.google.com/file/d/1zAguRYy5ctIOUgMoNxTDdBHVD4AwEp19/view?usp=sharing)
4. **Associate Data:**
Within the [03-associating-data](processing-scripts/03-associating-data) folder of the [processing-scripts](processing-scripts) folder, we have the following two scripts:
   - [01-join-all-data.py](processing-scripts/03-associating-data/01-join-all-data.py): Create Data Associations among NBI-OSM joined data and OSM-NHD joined data, resulting in association of NBI data, OSM ways and their matching NHD water streams.
      - **Output:** [All-Join-Result.csv](https://drive.google.com/file/d/18ylKZzGZj9wtCQ20FF7xWddtCf3WAu60/view?usp=sharing)
   - [02-determine-final-osm-id.py](processing-scripts/03-associating-data/02-determine-final-osm-id.py): Determining the final OSM ways to be associated with the NBI bridges based on certain conditions along with bridge length and other information.
      - **Output:** [bridge-osm-association-with-lengths.csv](https://drive.google.com/file/d/1HQ02VVRiDbm2_tZbYaRAs3n6UPD9XekV/view?usp=sharing)
   - [03-get-point-projections-on-ways.py](processing-scripts/03-associating-data/03-get-point-projections-on-ways.py): Get the final coordinates of NBI bridges projected on associated OSM ways.
      - **Output:** [bridge-osm-association-with-projected-points.csv](https://drive.google.com/file/d/19ArmfjVVawplu0SluZkh8wTzNCfYDKiy/view?usp=sharing)
   - [04-calculate-match-percentage.py](processing-scripts/03-associating-data/04-calculate-match-percentage.py): Calculate match percentage among the "6A - Features Intersected" column from NBI and Stream name from NHD. Also, calculate the metch among "7 - Facility Carried By Structure" column from NBI and OSM way road name.
     - **Output:** [Association-match-check-with-percentage.csv](https://drive.google.com/file/d/19ArmfjVVawplu0SluZkh8wTzNCfYDKiy/view?usp=sharing)
4. **Obtain Bridge Coordinates on OSM Ways:**
Within the [04-obtaining-bridge-coordinates](processing-scripts/04-obtaining-bridge-coordinates) folder of the [processing-scripts](processing-scripts) folder, we have the following script:
   - [01-obtain-bridge-split-info.py](processing-scripts/04-obtaining-bridge-coordinates/01-obtain-bridge-split-info.py): Utilizing the Python script to identify and position bridge coordinates equidistant from the midpoint along specified OSM ways.
   - **Output:** [bridge-osm-association-with-split-coords.csv](https://drive.google.com/file/d/1ahrMZpunlaZPi8TiY-rEQ8_eKzD0JIov/view?usp=sharing)
5. **Use JOSM to Add Bridge Tags:**
Within the [05-split-ways-add-bridge-tag](processing-scripts/05-split-ways-add-bridge-tag) folder of the [processing-scripts](processing-scripts) folder, we have the following three scripts:
   - Add Tags to Bridge Spanning over Single OSM Way:
     - Script: [01-JOSM-1-split-way-in-place.js](processing-scripts/05-split-ways-add-bridge-tag/01-JOSM-1-split-way-in-place.js)
     - Utilize the JOSM Scripting Plugin to accurately position bridge locations along existing ways and split ways to incorporate new nodes. This includes adding the "bridge=yes" tag to the identified way.
   - Determine OSM ways covered by bridges which span multiple ways using [NetworkX](https://networkx.org/).
     - Script: [02-shortest-route-between-two-ways.py](processing-scripts/05-split-ways-add-bridge-tag/02-shortest-route-between-two-ways.py)
   - Add Tags to Bridge Spanning over Multiple OSM Ways:
     - Script: [03-JOSM-1-handle-multi-way-bridge.js](processing-scripts/05-split-ways-add-bridge-tag/03-JOSM-1-handle-multi-way-bridge.js)
     - Using Python libraries Osmium and NetworkX alongside the JOSM Scripting Plugin to update OSM data. This involves finding all OSM way IDs that the bridge spans and ensuring accurate tagging.
## Conclusion
This repository provides tools and scripts necessary to enhance OSM bridge data using publicly available datasets. By automating the identification, tagging, and association processes, it aims to improve the accuracy and completeness of bridge information within OpenStreetMap.
