import logging
import os
from typing import Dict
import sys
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

# Initialize global logger
logger = logging.getLogger(__name__)


def load_config(state_name: str) -> Dict:
    """
    Load and render configuration from a YAML file.
    """
    try:
        env = Environment(
            loader=FileSystemLoader("."), autoescape=select_autoescape(["yaml"])
        )

        with open("config.yml", "r") as file:
            template = env.from_string(file.read())
            rendered_yaml = template.render(state=state_name)
            config = yaml.safe_load(rendered_yaml)

        return config

    except FileNotFoundError as e:
        print(f"Error: The configuration file was not found. Details: {e}")
        raise

    except yaml.YAMLError as e:
        print(f"Error: Failed to parse the YAML configuration. Details: {e}")
        raise

    except Exception as e:
        print(f"An unexpected error occurred while loading the configuration. Details: {e}")
        raise


def create_directories(config: Dict[str, str]) -> None:
    """
    Create directories for output data as specified in the configuration.
    
    :param config: Dictionary containing paths for directories to be created.
    """
    output_folders = config.get("output_data_folders", {})

    # Define required folder keys
    required_folders = ["state_folder", "csv_files", "gpkg_files", "pbf_files"]

    for folder in required_folders:
        folder_path = output_folders.get(folder)
        if folder_path:
            if not os.path.exists(folder_path):
                try:
                    os.makedirs(folder_path)
                    logger.info(f"Directory created: {folder_path}")
                except Exception as e:
                    logger.error(f"Failed to create directory {folder_path}: {e}")
            else:
                logger.info(f"Directory already exists: {folder_path}")
        else:
            logger.warning(f"Path for {folder} not specified in configuration.")


def filter_osm_data(config: Dict) -> None:
    """
    Filter OSM ways data using the provided configuration.
    """
    input_osm_pbf = config["input_data_folder"]["state_latest_osm"]
    output_osm_pbf = config["output_files"]["filtered_osm_pbf"]
    output_gpkg = config["output_files"]["filtered_highways"]

    logger.info("Filtering OSM ways data.")
    filter_osm_ways.filter_ways(input_osm_pbf, output_osm_pbf, output_gpkg, logger)


def filter_nbi_data(config: Dict) -> None:
    """
    Filter NBI bridge data and create a GeoPackage.
    """
    input_csv = config["input_data_folder"]["nbi_bridge_data"]
    output_duplicate_exclude_csv = config["output_files"]["duplicate_exclude_csv"]
    output_gpkg_file = config["output_files"]["nbi_geopackage"]

    logger.info("Filtering NBI bridge data.")
    process_filter_nbi_bridges.create_nbi_geopackage(
        input_csv, output_duplicate_exclude_csv, output_gpkg_file, logger
    )


def tag_data(config: Dict, state_name: str) -> None:
    """
    Tag NBI data with OSM-NHD join data.
    """
    # Extract file paths from config
    file_paths = {
        "nbi_geopackage": config["output_files"]["nbi_geopackage"],
        "filtered_highways": config["output_files"]["filtered_highways"],
        "state_latest_osm": config["input_data_folder"]["state_latest_osm"],
        "bridge_yes_join_csv": config["output_files"]["bridge_yes_join_csv"],
        "yes_filter_bridges": config["output_files"]["yes_filter_bridges"],
        "manmade_join_csv": config["output_files"]["manmade_join_csv"],
        "manmade_filter_bridges": config["output_files"]["manmade_filter_bridges"],
        "parallel_join_csv": config["output_files"]["parallel_join_csv"],
        "parallel_filter_bridges": config["output_files"]["parallel_filter_bridges"],
        "nearby_join_csv": config["output_files"]["nearby_join_csv"],
        "state_folder": config["output_data_folders"]["state_folder"],
        "culvert_join_csv": config["output_files"]["culvert_join_csv"],
        "final_bridges": config["output_files"]["final_bridges"],
        "rivers_data": config["input_data_folder"]["nhd_streams_flowline"],
        "intersections_csv": config["output_files"]["intersections_csv"],
        "osm_nhd_join_csv": config["output_files"]["osm_nhd_join_csv"],
        "nbi_10_join_csv": config["output_files"]["nbi_10_join_csv"],
        "nbi_30_join_csv": config["output_files"]["nbi_30_join_csv"],
    }

    logger.info("Tagging NBI and OSM data.")
    tag_nbi_and_osm_data.process_tagging(
        **file_paths, logger=logger, state_name=state_name
    )


def associate_join_data(config: Dict) -> None:
    """
    Associate and process join data.
    """
    files = {
        "all_join_dask": config["output_files"]["all_join_dask"],
        "all_join_csv": config["output_files"]["all_join_csv"],
        "intermediate_association": config["output_files"]["intermediate_association"],
        "association_with_intersections": config["output_files"][
            "association_with_intersections"
        ],
        "bridge_association_lengths": config["output_files"][
            "bridge_association_lengths"
        ],
        "bridge_with_proj_points": config["output_files"]["bridge_with_proj_points"],
        "bridge_match_percentage": config["output_files"]["bridge_match_percentage"],
        "final_bridges_csv": config["output_files"]["final_bridges_csv"],
    }

    logger.info("Joining association data together.")
    join_all_data.process_all_join(
        config["output_files"]["nbi_30_join_csv"],
        config["output_files"]["nbi_10_join_csv"],
        files["all_join_dask"],
        files["all_join_csv"],
        logger,
    )

    logger.info("Determining final OSM way ID for each NBI bridge.")
    determine_final_osm_id.process_final_id(
        files["all_join_csv"],
        config["output_files"]["intersections_csv"],
        files["intermediate_association"],
        files["association_with_intersections"],
        config["input_data_folder"]["nbi_bridge_data"],
        files["bridge_association_lengths"],
        logger,
    )

    logger.info("Getting NBI point projections on associated ways.")
    get_point_projections_on_ways.run(
        config["output_files"]["final_bridges"],
        config["output_files"]["filtered_highways"],
        files["bridge_association_lengths"],
        files["bridge_with_proj_points"],
    )

    logger.info("Calculating fuzzy match for OSM road name.")
    calculate_match_percentage.run(
        files["bridge_with_proj_points"], files["bridge_match_percentage"]
    )

    logger.info("Excluding nearby bridges.")
    exclude_nearby_bridges.run(
        files["bridge_match_percentage"],
        config["output_files"]["nearby_join_csv"],
        files["final_bridges_csv"],
        logger,
    )


def main() -> None:
    """
    Main function to orchestrate the data processing pipeline.
    """
    state_name = "Kentucky"

    try:
        # Load configuration
        config = load_config(state_name)

    except (FileNotFoundError, yaml.YAMLError, Exception) as e:
        print(f"Configuration loading failed: {e}")
        sys.exit(1)  # Exit with a non-zero status to indicate an error

    try:
        # Configure logging after loading config
        log_file_path = config["logging"].get(
            "log_file_path", "hydrography-pipeline.log"
        )
        logging.basicConfig(
            filename=log_file_path,  # Use the path from the configuration
            level=logging.INFO,
            format="%(asctime)s - [%(levelname)s] - (%(filename)s).%(funcName)s - %(message)s",
        )

        # Create directories
        logger.info("Creating directories.")
        create_directories(config)

        # Filter OSM & NBI data
        filter_osm_data(config)
        filter_nbi_data(config)

        # Tag NBI and OSM data
        tag_data(config, state_name)

        # Associate and process join data
        associate_join_data(config)
        logger.info("Association process completed.")

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}", exc_info=True)
    except yaml.YAMLError as e:
        logger.error(f"YAML configuration error: {e}", exc_info=True)
    except KeyError as e:
        logger.error(f"Missing key in configuration or data: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise  # Re-raise the exception to ensure the program terminates with an error status


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise
