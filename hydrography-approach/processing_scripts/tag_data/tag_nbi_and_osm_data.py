import csv
import os
import subprocess
import sys
from typing import Optional, Tuple
from qgis.analysis import QgsNativeAlgorithms
from qgis.core import (
    QgsApplication,
    QgsProcessingFeedback,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
)

# Initialize QGIS application
QgsApplication.setPrefixPath("/Applications/QGIS-LTR.app/Contents/MacOS", True)
qgs = QgsApplication([], False)
qgs.initQgis()

# Add QGIS plugin path
sys.path.append("/Applications/QGIS-LTR.app/Contents/Resources/python/plugins")

import processing
from processing.core.Processing import Processing

# Initialize QGIS processing
Processing.initialize()
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
feedback = QgsProcessingFeedback()


def create_buffer(vector_layer, radius):
    """
    Create a buffer around a vector layer
    """
    buffered = processing.run(
        "native:buffer",
        {
            "DISSOLVE": False,
            "DISTANCE": radius,
            "END_CAP_STYLE": 0,
            "INPUT": vector_layer,
            "JOIN_STYLE": 0,
            "MITER_LIMIT": 2,
            "OUTPUT": "memory:",
            "SEGMENTS": 5,
        },
    )["OUTPUT"]
    return buffered


def filter_osm_data(vector_layer, filter_expression):
    """
    Apply a filter expression to a vector layer
    """
    vector_layer.setSubsetString(filter_expression)
    return vector_layer


def explode_osm_data(vector_layer):
    """
    Explode the 'other_tags' field in OSM data
    """
    exploded = processing.run(
        "native:explodehstorefield",
        {
            "EXPECTED_FIELDS": "",
            "FIELD": "other_tags",
            "INPUT": vector_layer,
            "OUTPUT": "memory:",
        },
    )["OUTPUT"]
    return exploded


def join_by_location(input_layer, join_layer, join_fields, geometric_predicates):
    """
    Join attributes by location
    """
    joined_layer = processing.run(
        "native:joinattributesbylocation",
        {
            "DISCARD_NONMATCHING": False,
            "INPUT": input_layer,
            "JOIN": join_layer,
            "JOIN_FIELDS": join_fields,
            "METHOD": 0,
            "OUTPUT": "memory:",
            "PREDICATE": geometric_predicates,
            # Predicates - [0, 1, 2, 3, 4, 5, 6] = [‘intersects’, ‘contains’, ‘equals’, ‘touches’, ‘overlaps’, ‘within’, ‘crosses’]
            "PREFIX": "",
        },
    )["OUTPUT"]
    return joined_layer


def vl_to_csv_filter(vector_layer, csv_path, keep_fields):
    """
    Export vector layer to CSV with selected columns
    """
    fields = vector_layer.fields()
    with open(csv_path, mode="w", newline="", encoding="utf-8") as file:
        csv_writer = csv.writer(file)
        header = [field.name() for field in fields if field.name() in keep_fields]
        csv_writer.writerow(header)
        for feature in vector_layer.getFeatures():
            row = [
                feature[field.name()] for field in fields if field.name() in keep_fields
            ]
            csv_writer.writerow(row)


def vl_to_csv(vector_layer, csv_path):
    """
    Export vector layer to CSV with WKT geometry column
    """
    QgsVectorFileWriter.writeAsVectorFormat(
        vector_layer,
        csv_path,
        "utf-8",
        vector_layer.crs(),
        "CSV",
        layerOptions=["GEOMETRY=AS_WKT"],
    )


def get_nearby_bridge_ids_from_csv(csv_file_path):
    """
    Extract nearby bridge IDs from CSV file
    """
    nearby_bridge_ids = []

    with open(csv_file_path, mode="r") as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            if row["8 - Structure Number"] != row["8 - Structure Number_2"]:
                nearby_bridge_ids.append(row["8 - Structure Number"])
                nearby_bridge_ids.append(row["8 - Structure Number_2"])
    nearby_bridge_ids = list(set(nearby_bridge_ids))

    return nearby_bridge_ids


def get_bridge_ids_from_csv(csv_file_path):
    """
    Extract bridge IDs from CSV file
    """
    bridge_ids = []
    with open(csv_file_path, mode="r") as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            bridge_id = row["8 - Structure Number"]
            if bridge_id:
                bridge_ids.append(bridge_id)
    return bridge_ids


def filter_nbi_layer(vector_layer, exclusion_ids):
    """
    Filter NBI layer by excluding certain IDs
    """
    # Create a memory layer to store filtered features
    filtered_layer = QgsVectorLayer("Point?crs=EPSG:4326", "filtered_layer", "memory")
    provider = filtered_layer.dataProvider()

    # Add fields from the original layer to the filtered layer
    provider.addAttributes(vector_layer.fields())
    filtered_layer.updateFields()

    # Iterate through the features and filter them
    for feature in vector_layer.getFeatures():
        if feature["8 - Structure Number"] not in exclusion_ids:
            provider.addFeature(feature)

    return filtered_layer


def get_line_intersections(filtered_osm_gl, rivers_gl):
    """
    Get intersections between OSM lines and rivers
    """
    intersections = processing.run(
        "native:lineintersections",
        {
            "INPUT": filtered_osm_gl,
            "INPUT_FIELDS": [],
            "INTERSECT": rivers_gl,
            "INTERSECT_FIELDS": [
                "OBJECTID",
                "permanent_identifier",
                "gnis_id",
                "gnis_name",
                "fcode_description",
            ],
            "INTERSECT_FIELDS_PREFIX": "",
            "OUTPUT": "memory:",
        },
    )["OUTPUT"]
    return intersections


def load_layers(nbi_points_fp: str, osm_fp: str, logger) -> Tuple[Optional[QgsVectorLayer], Optional[QgsVectorLayer]]:
    """
    Load required layers with improved error handling.

    Args:
        nbi_points_fp (str): File path to the NBI points layer.
        osm_fp (str): File path to the OSM ways layer.
        logger: Logger instance for logging errors.

    Returns:
        Tuple[Optional[QgsVectorLayer], Optional[QgsVectorLayer]]:
            A tuple containing the NBI points layer and the OSM ways layer.
    """
    def load_layer(fp: str, layer_name: str) -> Optional[QgsVectorLayer]:
        """
        Load a layer and log errors if the loading fails.

        Args:
            fp (str): File path to the layer.
            layer_name (str): Name of the layer for logging purposes.

        Returns:
            Optional[QgsVectorLayer]: Loaded layer or None if failed.
        """
        layer = QgsVectorLayer(fp, layer_name, "ogr")
        if not layer.isValid():
            logger.error(f"{layer_name} layer failed to load. Check the file path and ensure the file exists.")
            return None
        return layer

    nbi_points_gl = load_layer(nbi_points_fp, "nbi-points")
    osm_gl = load_layer(osm_fp, "filtered")

    if nbi_points_gl is None:
        logger.error("NBI points layer is critical and could not be loaded. Exiting.")
        sys.exit(1)

    if osm_gl is None:
        logger.error("OSM ways layer could not be loaded. Exiting.")
        sys.exit(1)

    return nbi_points_gl, osm_gl


'''
def load_layers(nbi_points_fp, osm_fp):
    """
    Load required layers and create spatial indexes
    """
    nbi_points_gl = QgsVectorLayer(nbi_points_fp, "nbi-points", "ogr")
    if not nbi_points_gl.isValid():
        print("NBI points layer failed to load!")
        sys.exit(1)

    osm_gl = QgsVectorLayer(osm_fp, "filtered", "ogr")
    if not osm_gl.isValid():
        print("OSM ways layer failed to load!")
        sys.exit(1)

    # Create spatial index for NBI points
    nbi_index = QgsSpatialIndex(nbi_points_gl.getFeatures())

    # Create spatial index for OSM ways
    osm_index = QgsSpatialIndex(osm_gl.getFeatures())

    return nbi_points_gl, osm_gl
'''


def process_bridge(
    nbi_points_gl, exploded_osm_gl, bridge_yes_join_csv, yes_filter_bridges, logger
):
    """
    Process bridges: filter and join NBI data with OSM data
    """
    filter_expression = "bridge is not null or man_made='bridge'"

    filtered_osm_gl = filter_osm_data(exploded_osm_gl, filter_expression)

    buffer_80 = create_buffer(filtered_osm_gl, 0.0008)

    osm_bridge_yes_nbi_join = join_by_location(
        buffer_80,
        nbi_points_gl,
        [
            "8 - Structure Number",
        ],
        geometric_predicates=[0, 1],
    )

    vl_to_csv(osm_bridge_yes_nbi_join, bridge_yes_join_csv)

    exclusion_ids = get_bridge_ids_from_csv(bridge_yes_join_csv)

    filtered_layer = filter_nbi_layer(nbi_points_gl, exclusion_ids)

    QgsVectorFileWriter.writeAsVectorFormat(
        filtered_layer, yes_filter_bridges, "utf-8", filtered_layer.crs(), "GPKG"
    )

    logger.info(f"Output file: {yes_filter_bridges} has been created successfully!")

    QgsProject.instance().removeMapLayer(filtered_osm_gl.id())
    QgsProject.instance().removeMapLayer(buffer_80.id())
    QgsProject.instance().removeMapLayer(osm_bridge_yes_nbi_join.id())

    return filtered_layer


def process_layer_tag(
    nbi_points_gl, exploded_osm_gl, manmade_join_csv, manmade_filter_bridges, logger
):
    """
    Process layer tags: filter and join NBI data with OSM data based on layer tag
    """
    filter_expression = "layer>0"

    filtered_osm_gl = filter_osm_data(exploded_osm_gl, filter_expression)

    buffer_30 = create_buffer(filtered_osm_gl, 0.0003)

    osm_bridge_yes_nbi_join = join_by_location(
        buffer_30,
        nbi_points_gl,
        [
            "8 - Structure Number",
        ],
        geometric_predicates=[0, 1],
    )

    vl_to_csv(osm_bridge_yes_nbi_join, manmade_join_csv)

    exclusion_ids = get_bridge_ids_from_csv(manmade_join_csv)

    filtered_layer = filter_nbi_layer(nbi_points_gl, exclusion_ids)

    QgsVectorFileWriter.writeAsVectorFormat(
        filtered_layer, manmade_filter_bridges, "utf-8", filtered_layer.crs(), "GPKG"
    )

    logger.info(f"Output file: {manmade_filter_bridges} has been created successfully!")

    QgsProject.instance().removeMapLayer(filtered_osm_gl.id())
    QgsProject.instance().removeMapLayer(buffer_30.id())
    QgsProject.instance().removeMapLayer(osm_bridge_yes_nbi_join.id())

    return filtered_layer


def process_parallel_bridges(
    nbi_points_gl, exploded_osm_gl, parallel_join_csv, parallel_filter_bridges, logger
):
    """
    Process parallel bridges: identify and filter parallel bridges
    """
    filter_expression = "highway IN ('motorway_link', 'primary', 'primary_link', 'trunk', 'motorway', 'trunk_link') AND oneway = 'yes' AND bridge is null"

    filtered_osm_gl = filter_osm_data(exploded_osm_gl, filter_expression)

    buffer_30 = create_buffer(filtered_osm_gl, 0.0003)

    osm_oneway_yes_osm_join = join_by_location(
        buffer_30,
        filtered_osm_gl,
        [
            "osm_id",
        ],
        geometric_predicates=[0],
    )

    osm_oneway_yes_osm_bridge_join = join_by_location(
        osm_oneway_yes_osm_join,
        nbi_points_gl,
        ["8 - Structure Number"],
        geometric_predicates=[0, 1],
    )

    keep_fields = ["osm_id", "osm_id_2", "8 - Structure Number"]
    vl_to_csv_filter(osm_oneway_yes_osm_bridge_join, parallel_join_csv, keep_fields)

    parallel_bridge_ids = get_bridge_ids_from_csv(parallel_join_csv)
    filtered_layer = filter_nbi_layer(
        vector_layer=nbi_points_gl, exclusion_ids=parallel_bridge_ids
    )

    QgsVectorFileWriter.writeAsVectorFormat(
        filtered_layer, parallel_filter_bridges, "utf-8", filtered_layer.crs(), "GPKG"
    )

    logger.info(
        f"Output file: {parallel_filter_bridges} has been created successfully!"
    )

    QgsProject.instance().removeMapLayer(filtered_osm_gl.id())
    QgsProject.instance().removeMapLayer(buffer_30.id())
    QgsProject.instance().removeMapLayer(osm_oneway_yes_osm_join.id())
    QgsProject.instance().removeMapLayer(osm_oneway_yes_osm_bridge_join.id())

    return filtered_layer


def process_nearby_bridges(nbi_points_gl, nearby_join_csv):
    """
    Process nearby bridges: identify and filter nearby bridges
    """
    buffer_30 = create_buffer(nbi_points_gl, 0.0003)

    nbi_30_nbi_join = join_by_location(
        buffer_30,
        nbi_points_gl,
        [
            "8 - Structure Number",
        ],
        geometric_predicates=[0, 1],
    )

    keep_fields = ["8 - Structure Number", "8 - Structure Number_2"]
    vl_to_csv_filter(nbi_30_nbi_join, nearby_join_csv, keep_fields)

    QgsProject.instance().removeMapLayer(buffer_30.id())
    QgsProject.instance().removeMapLayer(nbi_30_nbi_join.id())


def process_culverts_from_pbf(
    nbi_points_gl,
    osm_pbf_path,
    state_folder,
    state_name,
    culvert_join_csv,
    final_bridges,
    logger,
):
    """
    Process and filter out tunnels marked as culverts from a local OSM PBF file.
    Return a layer with filtered out items.
    """
    # Define file paths
    base_name = os.path.splitext(os.path.basename(osm_pbf_path))[0].replace(".osm", "")

    culverts_pbf_path = state_folder + f"/pbf-files/{base_name}-culverts.osm.pbf"
    culverts_geojson_path = state_folder + f"/gpkg-files/{base_name}-culverts.geojson"
    culverts_gpkg_path = state_folder + f"/gpkg-files/{base_name}-culverts.gpkg"

    # Step 1: Filter OSM data for tunnels marked as culverts
    filter_command = [
        "osmium",
        "tags-filter",
        osm_pbf_path,
        "w/tunnel=culvert",
        "-o",
        culverts_pbf_path,
    ]
    subprocess.run(filter_command, check=True)

    # Step 2: Convert the filtered data to GeoJSON
    export_command = [
        "osmium",
        "export",
        "-f",
        "geojson",
        "-o",
        culverts_geojson_path,
        culverts_pbf_path,
    ]
    subprocess.run(export_command, check=True)

    # Step 3: Convert the GeoJSON to GeoPackage
    convert_command = [
        "ogr2ogr",
        "-f",
        "GPKG",
        culverts_gpkg_path,
        culverts_geojson_path,
    ]
    subprocess.run(convert_command, check=True)

    # Remove intermediate files
    os.remove(culverts_pbf_path)
    os.remove(culverts_geojson_path)

    # Load the GeoPackage layer
    osm_fp = (
        culverts_gpkg_path
        + f"|layername={state_name}-latest-culverts|geometrytype=LineString"
    )

    osm_layer = QgsVectorLayer(osm_fp, "osm-culverts", "ogr")
    if not osm_layer.isValid():
        raise Exception(f"Failed to load layer from {culverts_gpkg_path}")

    # Create a 30m buffer (0.0003 degrees)
    buffer_30 = create_buffer(osm_layer, 0.0003)

    # Join filtered OSM data with NBI points based on location
    osm_culvert_nbi_join = join_by_location(
        buffer_30,
        nbi_points_gl,
        [
            "8 - Structure Number",
        ],
        geometric_predicates=[0],
    )

    # Save the joined layer to a CSV file
    vl_to_csv(osm_culvert_nbi_join, culvert_join_csv)

    # Get exclusion IDs from the CSV file
    exclusion_ids = get_bridge_ids_from_csv(culvert_join_csv)

    # Filter the NBI layer using the exclusion IDs
    filtered_layer = filter_nbi_layer(nbi_points_gl, exclusion_ids)

    QgsVectorFileWriter.writeAsVectorFormat(
        filtered_layer, final_bridges, "utf-8", filtered_layer.crs(), "GPKG"
    )

    logger.info(f"Output file: {final_bridges} has been created successfully!")

    # Remove temporary layers from the project
    QgsProject.instance().removeMapLayer(osm_layer.id())
    QgsProject.instance().removeMapLayer(buffer_30.id())
    QgsProject.instance().removeMapLayer(osm_culvert_nbi_join.id())

    return filtered_layer


def process_buffer_join(
    nbi_points_gl,
    osm_gl,
    exploded_osm_gl,
    rivers_data,
    state_name,
    intersections_csv,
    osm_nhd_join_csv,
    nbi_10_join_csv,
    nbi_30_join_csv,
    logger,
):
    """
    Process buffer join: join NBI data with OSM and river data
    """
    base_filename = os.path.splitext(os.path.basename(rivers_data))[0]
    rivers_fp = rivers_data + f"|layername=NHD-{state_name}-Flowline"
    # rivers_fp = rivers_data + "|layername=NHDFlowline"

    rivers_gl = QgsVectorLayer(rivers_fp, "rivers", "ogr")
    if not rivers_gl.isValid():
        logger.error("Rivers layer failed to load!")
        sys.exit(1)

    filter_expression = "highway not in ('abandoned','bridleway','construction','corridor','crossing','cycleway','elevator','escape','footway','living_street','path','pedestrian','planned','proposed','raceway','rest_area','steps') AND bridge IS NULL AND layer IS NULL"
    exploded_osm_gl = filter_osm_data(exploded_osm_gl, filter_expression)

    intersections = get_line_intersections(exploded_osm_gl, rivers_gl)

    vl_to_csv(
        intersections,
        intersections_csv,
    )
    logger.info(f"Output file: {intersections_csv} has been created successfully!")

    osm_river_join = join_by_location(
        osm_gl,
        rivers_gl,
        [
            "OBJECTID",
            "permanent_identifier",
            "gnis_id",
            "gnis_name",
            "fcode_description",
        ],
        geometric_predicates=[0],
    )

    vl_to_csv(
        osm_river_join,
        osm_nhd_join_csv,
    )
    logger.info(f"Output file: {osm_nhd_join_csv} has been created successfully!")

    buffer_10 = create_buffer(nbi_points_gl, 0.0001)
    buffer_30 = create_buffer(nbi_points_gl, 0.0003)

    nbi_10_river_join = join_by_location(
        buffer_10,
        rivers_gl,
        [
            "OBJECTID",
            "permanent_identifier",
            "gnis_id",
            "gnis_name",
            "fcode_description",
        ],
        geometric_predicates=[0],
    )

    keep_fields = [
        "8 - Structure Number",
        "permanent_identifier",
    ]

    vl_to_csv_filter(
        nbi_10_river_join,
        nbi_10_join_csv,
        keep_fields,
    )
    logger.info(f"Output file: {nbi_10_join_csv} has been created successfully!")

    nbi_30_osm_river_join = join_by_location(
        buffer_30, osm_river_join, [], geometric_predicates=[0]
    )

    keep_fields = [
        "1 - State Code",
        "8 - Structure Number",
        "16 - Latitude (decimal)",
        "17 - Longitude (decimal)",
        "osm_id",
        "name",
        "highway",
        "OBJECTID_2",
        "permanent_identifier",
    ]

    vl_to_csv_filter(
        nbi_30_osm_river_join,
        nbi_30_join_csv,
        keep_fields,
    )
    logger.info(f"Output file: {nbi_30_join_csv} has been created successfully!")


def process_tagging(
    nbi_geopackage,
    filtered_highways,
    state_latest_osm,
    bridge_yes_join_csv,
    yes_filter_bridges,
    manmade_join_csv,
    manmade_filter_bridges,
    parallel_join_csv,
    parallel_filter_bridges,
    nearby_join_csv,
    state_folder,
    culvert_join_csv,
    final_bridges,
    rivers_data,
    intersections_csv,
    osm_nhd_join_csv,
    nbi_10_join_csv,
    nbi_30_join_csv,
    logger,
    state_name,
):
    # Get QGIS pathname for NBI points vector layer
    base_filename = os.path.splitext(os.path.basename(nbi_geopackage))[0]
    nbi_points_fp = nbi_geopackage + "|layername=" + base_filename

    osm_fp = filtered_highways + "|layername=lines"
    osm_pbf_path = state_latest_osm

    nbi_points_gl, osm_gl = load_layers(nbi_points_fp, osm_fp, logger)
    exploded_osm_gl = explode_osm_data(osm_gl)

    output_layer1 = process_bridge(
        nbi_points_gl, exploded_osm_gl, bridge_yes_join_csv, yes_filter_bridges, logger
    )
    output_layer2 = process_layer_tag(
        output_layer1, exploded_osm_gl, manmade_join_csv, manmade_filter_bridges, logger
    )
    output_layer3 = process_parallel_bridges(
        output_layer2,
        exploded_osm_gl,
        parallel_join_csv,
        parallel_filter_bridges,
        logger,
    )
    process_nearby_bridges(output_layer3, nearby_join_csv)
    output_layer4 = process_culverts_from_pbf(
        output_layer3,
        osm_pbf_path,
        state_folder,
        state_name,
        culvert_join_csv,
        final_bridges,
        logger,
    )
    process_buffer_join(
        output_layer4,
        osm_gl,
        exploded_osm_gl,
        rivers_data,
        state_name,
        intersections_csv,
        osm_nhd_join_csv,
        nbi_10_join_csv,
        nbi_30_join_csv,
        logger,
    )
