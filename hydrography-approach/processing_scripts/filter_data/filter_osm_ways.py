import subprocess


def filter_osm_pbf(input_file, output_file, filters):
    """
    Filter the OSM PBF file based on the specified filters.
    """
    cmd = ["osmium", "tags-filter", input_file] + filters + ["-o", output_file]
    subprocess.run(cmd, check=True)


def convert_to_geopackage(input_file, output_file):
    """
    Convert the filtered OSM PBF file to a GeoPackage.
    """
    cmd = ["ogr2ogr", "-f", "GPKG", output_file, input_file]
    subprocess.run(cmd, check=True)


def filter_ways(input_osm_pbf, output_osm_pbf, output_gpkg):
    """
    Perform filter operation.
    """
    # List of highway types to include in the filtering process
    highway_types = [
        "motorway",
        "motorway_link",
        "trunk",
        "trunk_link",
        "primary",
        "primary_link",
        "secondary",
        "secondary_link",
        "tertiary",
        "tertiary_link",
        "unclassified",
        "residential",
        "service",
        "services",
        "track",
        "road",
    ]

    # Construct filters to include only the desired highway types
    filters = [f"w/highway={hw_type}" for hw_type in highway_types]

    # Filter the OSM PBF file
    filter_osm_pbf(input_osm_pbf, output_osm_pbf, filters)

    # Convert the filtered OSM PBF file to a GeoPackage
    convert_to_geopackage(output_osm_pbf, output_gpkg)

    print(f"Output file: {output_gpkg} has been created successfully!")
