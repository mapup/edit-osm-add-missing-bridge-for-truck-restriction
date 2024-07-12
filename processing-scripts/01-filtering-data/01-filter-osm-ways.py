import os
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


# Path to the input OSM PBF file
input_osm_pbf = "input-data/kentucky-latest.osm.pbf"

# Make the required directories for storing outputs
os.makedirs("output-data/csv-files", exist_ok=True)
os.makedirs("output-data/gpkg-files", exist_ok=True)
os.makedirs("output-data/pbf-files", exist_ok=True)

# Path to the output filtered OSM PBF file
output_filtered_osm_pbf = "output-data/pbf-files/kentucky-filtered-highways.osm.pbf"

# Path to the output GeoPackage file
output_gpkg = "output-data/gpkg-files/kentucky-filtered-highways.gpkg"

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
filter_osm_pbf(input_osm_pbf, output_filtered_osm_pbf, filters)

# Convert the filtered OSM PBF file to a GeoPackage
convert_to_geopackage(output_filtered_osm_pbf, output_gpkg)

print(f"Output file: {output_gpkg} has been created successfully!")
