import os

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from processing_scripts.associate_data import (
    calculate_match_percentage,
    determine_final_osm_id,
    exclude_nearby_bridges,
    get_point_projections_on_ways,
    join_all_data,
)
from processing_scripts.filter_data import filter_osm_ways, process_filter_nbi_bridges
from processing_scripts.tag_data import tag_nbi_and_osm_data


def load_config(state_name):
    """
    Load configuration
    """
    env = Environment(
        loader=FileSystemLoader("."), autoescape=select_autoescape(["yaml"])
    )

    with open("config.yml", "r") as file:
        template = env.from_string(file.read())
        rendered_yaml = template.render(state=f"{state_name}")
        config = yaml.safe_load(rendered_yaml)

    return config


def main():
    # Mention state to process
    state_name = "Kentucky"

    # Load config file
    print("\nLoading the config file.")
    config = load_config(state_name)

    # Make the required directories for storing outputs
    print("\nMake the required directories.")
    os.makedirs(
        config["output_data_folders"]["state_folder"],
        exist_ok=True,
    )
    os.makedirs(config["output_data_folders"]["csv_files"], exist_ok=True)
    os.makedirs(config["output_data_folders"]["gpkg_files"], exist_ok=True)
    os.makedirs(config["output_data_folders"]["pbf_files"], exist_ok=True)

    # --------------------------------------------Filter OSM ways data--------------------------------------------
    input_osm_pbf = config["input_data_folder"]["state_latest_osm"]
    output_osm_pbf = config["output_files"]["filtered_osm_pbf"]
    output_gpkg = config["output_files"]["filtered_highways"]

    print("\nFiltering OSM ways data.")
    filter_osm_ways.filter_ways(input_osm_pbf, output_osm_pbf, output_gpkg)

    # --------------------------------------------Filter NBI data and create geopackage--------------------------------------------
    input_csv = config["input_data_folder"]["nbi_bridge_data"]
    output_duplicate_exclude_csv = config["output_files"]["duplicate_exclude_csv"]
    output_gpkg_file = config["output_files"]["nbi_geopackage"]

    print("\nFiltering NBI bridge data.")
    process_filter_nbi_bridges.create_nbi_geopackage(
        input_csv, output_duplicate_exclude_csv, output_gpkg_file
    )

    # --------------------------------------------Tag NBI data with OSM-NHD join data--------------------------------------------
    nbi_geopackage = config["output_files"]["nbi_geopackage"]
    filtered_highways = config["output_files"]["filtered_highways"]
    state_latest_osm = config["input_data_folder"]["state_latest_osm"]
    bridge_yes_join_csv = config["output_files"]["bridge_yes_join_csv"]
    yes_filter_bridges = config["output_files"]["yes_filter_bridges"]
    manmade_join_csv = config["output_files"]["manmade_join_csv"]
    manmade_filter_bridges = config["output_files"]["manmade_filter_bridges"]
    parallel_join_csv = config["output_files"]["parallel_join_csv"]
    parallel_filter_bridges = config["output_files"]["parallel_filter_bridges"]
    nearby_join_csv = config["output_files"]["nearby_join_csv"]
    state_folder = config["output_data_folders"]["state_folder"]
    culvert_join_csv = config["output_files"]["culvert_join_csv"]
    final_bridges = config["output_files"]["final_bridges"]
    rivers_data = config["input_data_folder"]["nhd_streams_flowline"]
    intersections_csv = config["output_files"]["intersections_csv"]
    osm_nhd_join_csv = config["output_files"]["osm_nhd_join_csv"]
    nbi_10_join_csv = config["output_files"]["nbi_10_join_csv"]
    nbi_30_join_csv = config["output_files"]["nbi_30_join_csv"]

    print("\nTagging NBI and OSM data.")
    tag_nbi_and_osm_data.process_tagging(
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
        state_name,
        culvert_join_csv,
        final_bridges,
        rivers_data,
        intersections_csv,
        osm_nhd_join_csv,
        nbi_10_join_csv,
        nbi_30_join_csv,
    )

    # --------------------------------------------Associate join data--------------------------------------------
    all_join_dask = config["output_files"]["all_join_dask"]
    all_join_csv = config["output_files"]["all_join_csv"]
    intermediate_association = config["output_files"]["intermediate_association"]
    association_with_intersections = config["output_files"][
        "association_with_intersections"
    ]
    bridge_association_lengths = config["output_files"]["bridge_association_lengths"]
    bridge_with_proj_points = config["output_files"]["bridge_with_proj_points"]
    bridge_match_percentage = config["output_files"]["bridge_match_percentage"]
    final_bridges_csv = config["output_files"]["final_bridges_csv"]

    print("\nJoining association data together.")
    join_all_data.process_all_join(
        nbi_30_join_csv, nbi_10_join_csv, all_join_dask, all_join_csv
    )

    print("\nDetermining final OSM way ID for each NBI bridge.")
    determine_final_osm_id.process_final_id(
        all_join_csv,
        intersections_csv,
        intermediate_association,
        association_with_intersections,
        input_csv,
        bridge_association_lengths,
    )

    print("\nGetting NBI point projections on associated ways.")
    get_point_projections_on_ways.run(
        final_bridges,
        filtered_highways,
        bridge_association_lengths,
        bridge_with_proj_points,
    )

    print("\nCalculating fuzzy match for OSM road name.")
    calculate_match_percentage.run(bridge_with_proj_points, bridge_match_percentage)

    print("\nExcluding nearby bridges.")
    exclude_nearby_bridges.run(
        bridge_match_percentage, nearby_join_csv, final_bridges_csv
    )

    print("\nProcess completed.")

if __name__ == "__main__":
    main()
