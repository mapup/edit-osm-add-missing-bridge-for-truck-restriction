import logging
import math
from typing import Optional, Tuple

import pandas as pd


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Function to calculate Haversine distance between two points.

    :param lon1: Longitude of the first point.
    :param lat1: Latitude of the first point.
    :param lon2: Longitude of the second point.
    :param lat2: Latitude of the second point.
    :return: Haversine distance in kilometers.
    """
    # Radius of the Earth in kilometers
    R = 6371.0

    try:
        # Convert latitude and longitude from degrees to radians
        lon1 = math.radians(lon1)
        lat1 = math.radians(lat1)
        lon2 = math.radians(lon2)
        lat2 = math.radians(lat2)

        # Compute differences between the coordinates
        dlon = lon2 - lon1
        dlat = lat2 - lat1

        # Haversine formula
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        # Distance in kilometers
        distance = R * c

        return distance

    except TypeError as e:
        raise ValueError("Invalid input type. All inputs must be numeric.") from e


def extract_coordinates(wkt: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """
    Function to extract latitude and longitude from WKT (Well-Known Text) format.

    :param wkt: WKT string containing the coordinates.
    :return: Tuple containing latitude and longitude.
    """
    if pd.isna(wkt):
        return None, None

    try:
        # Remove 'POINT (' and ')'
        coords = wkt.replace("POINT (", "").replace(")", "")
        # Split the coordinates
        lon, lat = coords.split()
        return float(lat), float(lon)

    except (AttributeError, ValueError) as e:
        raise ValueError("Invalid WKT format. Could not extract coordinates.") from e


def determine_final_osm_id(group: pd.DataFrame) -> pd.Series:
    """
    Function to determine the final_osm_id, final_long, and final_lat for each group.

    :param group: DataFrame containing group data.
    :return: Series with final_osm_id, osm_name, final_stream_id, stream_name, final_long, final_lat.
    """
    try:
        true_stream = group[group["Is_Stream_Identical"]]
        min_dist = group[group["Is_Min_Dist"]]

        if group["combo-count"].iloc[0] == 1:
            # If there is only one unique OSM id
            osm_id = group["osm_id"].iloc[0]
            osm_name = group["name"].iloc[0]

            if len(min_dist) == 0:
                stream_id = pd.NA
                stream_name = pd.NA
            else:
                stream_id = min_dist["permanent_identifier_x"].iloc[0]
                stream_name = min_dist["gnis_name"].iloc[0]

            if len(true_stream) == 1:
                long, lat = true_stream[["Long_intersection", "Lat_intersection"]].iloc[
                    0
                ]
            elif len(true_stream) > 1:
                min_dist_match = true_stream[true_stream["Is_Min_Dist"]]
                if not min_dist_match.empty:
                    long, lat = min_dist_match[
                        ["Long_intersection", "Lat_intersection"]
                    ].iloc[0]
                else:
                    long, lat = true_stream[
                        ["Long_intersection", "Lat_intersection"]
                    ].iloc[0]
            else:
                # If there are no rows with stream_check as TRUE, use MIN-DIST
                if not min_dist.empty:
                    long, lat = min_dist[
                        ["Long_intersection", "Lat_intersection"]
                    ].iloc[0]
                else:
                    long, lat = group[["Long_intersection", "Lat_intersection"]].iloc[0]
        else:
            if len(true_stream) == 1:
                # If there is exactly one OSM id with stream_check as TRUE
                osm_id, osm_name, stream_id, stream_name, long, lat = true_stream[
                    [
                        "osm_id",
                        "name",
                        "permanent_identifier_x",
                        "gnis_name",
                        "Long_intersection",
                        "Lat_intersection",
                    ]
                ].iloc[0]
            else:
                # If there are multiple OSM ids with stream_check as TRUE, use 'MIN-DIST'
                if not min_dist.empty:
                    osm_id, osm_name, stream_id, stream_name, long, lat = min_dist[
                        [
                            "osm_id",
                            "name",
                            "permanent_identifier_x",
                            "gnis_name",
                            "Long_intersection",
                            "Lat_intersection",
                        ]
                    ].iloc[0]
                else:
                    osm_id, osm_name, stream_id, stream_name, long, lat = [
                        pd.NA,
                        pd.NA,
                        pd.NA,
                        pd.NA,
                        pd.NA,
                        pd.NA,
                    ]

        return pd.Series(
            [osm_id, osm_name, stream_id, stream_name, long, lat],
            index=[
                "final_osm_id",
                "osm_name",
                "final_stream_id",
                "stream_name",
                "final_long",
                "final_lat",
            ],
        )

    except (IndexError, KeyError) as e:
        raise ValueError(
            "Error processing group data for final OSM ID determination."
        ) from e


def merge_join_data_with_intersections(
    all_join_csv: str, intersections_csv: str
) -> pd.DataFrame:
    """
    Function to tag all data join result with intersections information.

    :param all_join_csv: Path to the CSV file with the final join data.
    :param intersections_csv: Path to the CSV file with intersection data.
    :return: DataFrame with merged data containing intersections information.
    """
    try:
        # Load the final join data
        final_join_data = pd.read_csv(all_join_csv)

        # Load the intersection data
        intersection_data = pd.read_csv(intersections_csv, low_memory=False)
        intersection_data = intersection_data[
            ["WKT", "osm_id", "permanent_identifier", "gnis_name"]
        ]

        # Ensure 'osm_id' and 'permanent_identifier_x' in df are of the same type as df2 columns
        final_join_data["osm_id"] = final_join_data["osm_id"].astype(str)
        final_join_data["permanent_identifier_x"] = final_join_data[
            "permanent_identifier_x"
        ].astype(str)

        intersection_data["osm_id"] = intersection_data["osm_id"].astype(str)
        intersection_data["permanent_identifier"] = intersection_data[
            "permanent_identifier"
        ].astype(str)

        # Perform the left merge
        merged_df = pd.merge(
            final_join_data,
            intersection_data,
            how="left",
            left_on=["osm_id", "permanent_identifier_x"],
            right_on=["osm_id", "permanent_identifier"],
        )

        return merged_df

    except FileNotFoundError as e:
        raise FileNotFoundError("One of the CSV files could not be found.") from e
    except pd.errors.EmptyDataError as e:
        raise ValueError("One of the CSV files is empty.") from e
    except KeyError as e:
        raise KeyError("A required column is missing from the CSV files.") from e
    except Exception as e:
        raise RuntimeError("An unexpected error occurred while merging data.") from e


def create_intermediate_association(
    df: pd.DataFrame, intermediate_association: str, logger: logging.Logger
) -> pd.DataFrame:
    """
    Function to create intermediate association among bridges and ways.

    :param df: DataFrame containing bridge and way data.
    :param intermediate_association: Path to the output CSV file.
    :param logger: Logger object for logging information and errors.
    :return: DataFrame with additional columns and calculations.
    """
    # Apply the function to the WKT column to create new columns
    df[["Lat_intersection", "Long_intersection"]] = df["WKT"].apply(
        lambda x: pd.Series(extract_coordinates(x))
    )

    # Calculate Haversine distance
    df["Haversine_dist"] = df.apply(
        lambda row: haversine(
            row["17 - Longitude (decimal)"],
            row["16 - Latitude (decimal)"],
            row["Long_intersection"],
            row["Lat_intersection"],
        ),
        axis=1,
    )

    # Calculate minimum Haversine distance for each bridge
    df["Min_Haversine_dist"] = df.groupby("8 - Structure Number")[
        "Haversine_dist"
    ].transform("min")

    # Flag rows with minimum distance
    df["Is_Min_Dist"] = df["Min_Haversine_dist"] == df["Haversine_dist"]

    # Check if stream identifiers match
    df["Is_Stream_Identical"] = (
        df["permanent_identifier_x"] == df["permanent_identifier_y"]
    )

    # Count unique OSM-Bridge combinations
    df["Unique_Bridge_OSM_Combinations"] = df.groupby("8 - Structure Number")[
        "osm_id"
    ].transform("nunique")

    # Save intermediate results
    try:
        df.to_csv(intermediate_association)
        logger.info(f"{intermediate_association} file has been created successfully!")
    except IOError as e:
        logger.error(f"Failed to write {intermediate_association}: {str(e)}")

    return df


def create_final_associations(
    df: pd.DataFrame, association_with_intersections: str, logger: logging.Logger
) -> pd.DataFrame:
    """
    Function to create final association among bridges and ways.

    :param df: DataFrame containing bridge and way data.
    :param association_with_intersections: Path to the output CSV file.
    :param logger: Logger object for logging information and errors.
    :return: DataFrame with final associations.
    """
    # Group by 'BRIDGE_ID' and calculate the number of unique 'osm_id's for each group
    unique_osm_count = (
        df.groupby("8 - Structure Number")["osm_id"].nunique().reset_index()
    )

    # Rename the column to 'combo-count'
    unique_osm_count.rename(columns={"osm_id": "combo-count"}, inplace=True)

    # Merge the unique counts back to the original dataframe
    df = df.merge(unique_osm_count, on="8 - Structure Number", how="left")

    # Apply the function to each group and create a new DataFrame with final_osm_id, final_long, and final_lat for each BRIDGE_ID
    final_values_df = (
        df.groupby("8 - Structure Number").apply(determine_final_osm_id).reset_index()
    )

    # Merge the final values back to the original dataframe
    df = df.merge(final_values_df, on="8 - Structure Number", how="left")

    # Save the updated dataframe to a new CSV file
    try:
        df.to_csv(
            association_with_intersections,
            index=False,
        )
        logger.info(
            f"{association_with_intersections} file has been created successfully!"
        )
    except IOError as e:
        logger.error(f"Failed to write {association_with_intersections}: {str(e)}")

    return df


def add_bridge_details(
    df: pd.DataFrame,
    nbi_bridge_data: str,
    bridge_association_lengths: str,
    logger: logging.Logger,
) -> None:
    """
    Function to add bridge information to associated data.

    :param df: DataFrame containing bridge and associated data.
    :param nbi_bridge_data: Path to the NBI bridge data CSV file.
    :param bridge_association_lengths: Path to the output CSV file with bridge details.
    :param logger: Logger object for logging information and errors.
    """
    bridge_data_df = pd.read_csv(
        nbi_bridge_data,
        low_memory=False,
    )

    # Merge the data on '8 - Structure Number'
    merged_df = pd.merge(
        df,
        bridge_data_df[
            [
                "8 - Structure Number",
                "49 - Structure Length (ft.)",
                "6A - Features Intersected",
                "7 - Facility Carried By Structure",
                "49 - Structure Length (ft.)",
            ]
        ],
        on="8 - Structure Number",
        how="left",
    )

    # Select the required columns and ensure the uniqueness
    result_df = merged_df[
        [
            "8 - Structure Number",
            "final_osm_id",
            "osm_name",
            "final_stream_id",
            "stream_name",
            "final_long",
            "final_lat",
            "6A - Features Intersected",
            "7 - Facility Carried By Structure",
            "49 - Structure Length (ft.)",
        ]
    ].drop_duplicates()

    # Rename '49 - Structure Length (ft.)' to 'bridge_length'
    result_df.rename(
        columns={"49 - Structure Length (ft.)": "bridge_length"}, inplace=True
    )

    # Save the resulting DataFrame to a new CSV file
    try:
        result_df.to_csv(
            bridge_association_lengths,
            index=False,
        )
        logger.info(f"{bridge_association_lengths} file has been created successfully!")
    except IOError as e:
        logger.error(f"Failed to write {bridge_association_lengths}: {str(e)}")


def process_final_id(
    all_join_csv: str,
    intersections_csv: str,
    intermediate_association: str,
    association_with_intersections: str,
    nbi_bridge_data: str,
    bridge_association_lengths: str,
    logger: logging.Logger,
) -> None:
    """
    Function to process and merge data, creating final bridge associations and details.

    :param all_join_csv: Path to the CSV file with all join data.
    :param intersections_csv: Path to the CSV file with intersection data.
    :param intermediate_association: Path to save intermediate association results.
    :param association_with_intersections: Path to save final association results with intersections.
    :param nbi_bridge_data: Path to the NBI bridge data CSV file.
    :param bridge_association_lengths: Path to save bridge details.
    :param logger: Logger object for logging information and errors.
    """
    # Merge join data with intersections
    df = merge_join_data_with_intersections(all_join_csv, intersections_csv)

    # Create intermediate association
    intermediate_df = create_intermediate_association(
        df, intermediate_association, logger
    )

    # Create final associations
    final_df = create_final_associations(
        intermediate_df, association_with_intersections, logger
    )

    # Add bridge details
    add_bridge_details(final_df, nbi_bridge_data, bridge_association_lengths, logger)
