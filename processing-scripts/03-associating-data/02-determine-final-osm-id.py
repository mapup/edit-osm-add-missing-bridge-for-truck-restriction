import math

import pandas as pd


def haversine(lon1, lat1, lon2, lat2):
    """
    Function to calculate Haversine distance among two points
    """
    # Radius of the Earth in kilometers
    R = 6371.0

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


def extract_coordinates(wkt):
    """
    Function to extract latitude and longitude from WKT (Well-Known Text) format
    """
    if pd.isna(wkt):
        return None, None
    # Remove 'POINT (' and ')'
    coords = wkt.replace("POINT (", "").replace(")", "")
    # Split the coordinates
    lon, lat = coords.split()
    return float(lat), float(lon)


def determine_final_osm_id(group):
    """
    Function to determine the final_osm_id, final_long, and final_lat for each group
    """
    true_stream = group[group["Is_Stream_Identical"]]
    min_dist = group[group["Is_Min_Dist"]]
    if group["combo-count"].iloc[0] == 1:
        # If there is only one unique OSM id
        osm_id = group["osm_id"].iloc[0]
        if len(true_stream) == 1:
            long, lat = true_stream[["Long_intersection", "Lat_intersection"]].iloc[0]
        elif len(true_stream) > 1:
            min_dist_match = true_stream[true_stream["Is_Min_Dist"]]
            if not min_dist_match.empty:
                long, lat = min_dist_match[
                    ["Long_intersection", "Lat_intersection"]
                ].iloc[0]
            else:
                long, lat = true_stream[["Long_intersection", "Lat_intersection"]].iloc[
                    0
                ]
        else:
            # If there are no rows with stream_check as TRUE, use MIN-DIST
            if not min_dist.empty:
                long, lat = min_dist[["Long_intersection", "Lat_intersection"]].iloc[0]
            else:
                long, lat = group[["Long_intersection", "Lat_intersection"]].iloc[0]
    else:
        if len(true_stream) == 1:
            # If there is exactly one OSM id with stream_check as TRUE
            osm_id, long, lat = true_stream[
                ["osm_id", "Long_intersection", "Lat_intersection"]
            ].iloc[0]
        else:
            # If there are multiple OSM ids with stream_check as TRUE, use 'MIN-DIST'
            if not min_dist.empty:
                osm_id, long, lat = min_dist[
                    ["osm_id", "Long_intersection", "Lat_intersection"]
                ].iloc[0]
            else:
                osm_id, long, lat = [pd.NA, pd.NA, pd.NA]
    return pd.Series(
        [osm_id, long, lat], index=["final_osm_id", "final_long", "final_lat"]
    )


def merge_join_data_with_intersections():
    """
    Function to tag all data join result with intersections information.
    """
    # Load the final join data
    final_join_data = pd.read_csv("output-data/csv-files/All-Join-Result.csv")

    # Load the intersection data
    intersection_data = pd.read_csv(
        "output-data/csv-files/OSM-NHD-Intersections.csv", low_memory=False
    )
    intersection_data = intersection_data[["WKT", "osm_id", "permanent_identifier"]]

    # Ensure 'osm_id' and 'permanent_identifier_x' in df are of the same type as df2 columns
    final_join_data["osm_id"] = final_join_data["osm_id"]
    final_join_data["permanent_identifier_x"] = final_join_data[
        "permanent_identifier_x"
    ]

    # Perform the left merge
    df = pd.merge(
        final_join_data,
        intersection_data,
        how="left",
        left_on=["osm_id", "permanent_identifier_x"],
        right_on=["osm_id", "permanent_identifier"],
    )

    return df


def create_intermediate_association(df, intermediate_association, logger):
    """
    Function to create intermediate association among bridges and ways.
    """
    # Apply the function to the WKT column to create new columns
    df[["Lat_intersection", "Long_intersection"]] = df["WKT"].apply(
        lambda x: pd.Series(extract_coordinates(x))
    )

    # Calculate Haversine distance
    df["Haversine_dist"] = df.apply(
        lambda row: haversine(
            row["LONGDD"],
            row["LATDD"],
            row["Long_intersection"],
            row["Lat_intersection"],
        ),
        axis=1,
    )

    # Calculate minimum Haversine distance for each bridge
    df["Min_Haversine_dist"] = df.groupby("STRUCTURE_NUMBER_008")[
        "Haversine_dist"
    ].transform("min")

    # Flag rows with minimum distance
    df["Is_Min_Dist"] = df["Min_Haversine_dist"] == df["Haversine_dist"]

    # Check if stream identifiers match
    df["Is_Stream_Identical"] = (
        df["permanent_identifier_x"] == df["permanent_identifier_y"]
    )

    # Count unique OSM-Bridge combinations
    df["Unique_Bridge_OSM_Combinations"] = df.groupby("STRUCTURE_NUMBER_008")[
        "osm_id"
    ].transform("nunique")

    # Save intermediate results
    df.to_csv(intermediate_association)
    logger.info(f"{intermediate_association} file has been created successfully!")

    return df


def create_final_associations(df, association_with_intersections, logger):
    """
    Function to create final association among bridges and ways.
    """
    # Group by 'BRIDGE_ID' and calculate the number of unique 'osm_id's for each group
    unique_osm_count = (
        df.groupby("STRUCTURE_NUMBER_008")["osm_id"].nunique().reset_index()
    )

    # Rename the column to 'combo-count'
    unique_osm_count.rename(columns={"osm_id": "combo-count"}, inplace=True)

    # Merge the unique counts back to the original dataframe
    df = df.merge(unique_osm_count, on="STRUCTURE_NUMBER_008", how="left")

    # Apply the function to each group and create a new DataFrame with final_osm_id, final_long, and final_lat for each BRIDGE_ID
    final_values_df = (
        df.groupby("STRUCTURE_NUMBER_008").apply(determine_final_osm_id).reset_index()
    )

    # Merge the final values back to the original dataframe
    df = df.merge(final_values_df, on="STRUCTURE_NUMBER_008", how="left")

    # Save the updated dataframe to a new CSV file
    df.to_csv(
        "output-data/csv-files/Final-associations-with-intersections.csv",
        index=False,
    )
    logger.info(f"{association_with_intersections} file has been created successfully!")

    return df


def add_bridge_details(df, nbi_bridge_data, bridge_association_lengths, logger):
    """
    Function to add bridge information to associated data.
    """
    bridge_data_df = pd.read_csv(
        "input-data/NTAD-National-Bridge-Inventory-Dataset.csv",
        low_memory=False,
    )

    # Merge the data on 'STRUCTURE_NUMBER_008'
    merged_df = pd.merge(
        df,
        bridge_data_df[["STRUCTURE_NUMBER_008", "STRUCTURE_LEN_MT_049"]],
        on="STRUCTURE_NUMBER_008",
        how="left",
    )

    # Select the required columns and ensure the uniqueness
    result_df = merged_df[
        [
            "STRUCTURE_NUMBER_008",
            "final_osm_id",
            "final_long",
            "final_lat",
            "STRUCTURE_LEN_MT_049",
        ]
    ].drop_duplicates()

    # Rename 'STRUCTURE_LEN_MT_049' to 'bridge_length'
    result_df.rename(columns={"STRUCTURE_LEN_MT_049": "bridge_length"}, inplace=True)

    # Save the resulting DataFrame to a new CSV file
    result_df.to_csv(
        "output-data/csv-files/bridge-osm-association-with-lengths.csv",
        index=False,
    )
    logger.info(
        f"{bridge_association_lengths} file has been created successfully!"
    )


def process_final_id(
    all_join_csv,
    intersections_csv,
    intermediate_association,
    association_with_intersections,
    nbi_bridge_data,
    bridge_association_lengths,
    logger
):
    df = merge_join_data_with_intersections(all_join_csv, intersections_csv)
    intermediate_df = create_intermediate_association(df, intermediate_association, logger)
    final_df = create_final_associations(
        intermediate_df, association_with_intersections, logger
    )
    add_bridge_details(final_df, nbi_bridge_data, bridge_association_lengths, logger)
