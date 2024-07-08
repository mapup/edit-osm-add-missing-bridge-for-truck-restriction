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
        osm_name = group["name"].iloc[0]
        stream_id = group["permanent_identifier_x"].iloc[0]
        stream_name = group["gnis_name"].iloc[0]

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
    intersection_data = intersection_data[
        ["WKT", "osm_id", "permanent_identifier", "gnis_name"]
    ]

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


def create_intermediate_association(df):
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
    df.to_csv("output-data/csv-files/Intermediate-Association.csv")
    print("\nIntermediate-Association.csv file has been created successfully!")

    return df


def create_final_associations(df):
    """
    Function to create final association among bridges and ways.
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
    df.to_csv(
        "output-data/csv-files/Associations-with-intersections.csv",
        index=False,
    )
    print(
        "\nAssociations-with-intersections.csv file has been created successfully!"
    )

    return df


def add_bridge_details(df):
    """
    Function to add bridge information to associated data.
    """
    bridge_data_df = pd.read_csv(
        "input-data/NBI-Kentucky-bridge-data.csv",
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
    result_df.to_csv(
        "output-data/csv-files/bridge-osm-association-with-lengths.csv",
        index=False,
    )
    print(
        "\nbridge-osm-association-with-lengths.csv file has been created successfully!"
    )


def main():
    df = merge_join_data_with_intersections()
    intermediate_df = create_intermediate_association(df)
    final_df = create_final_associations(intermediate_df)
    add_bridge_details(final_df)


if __name__ == "__main__":
    main()
