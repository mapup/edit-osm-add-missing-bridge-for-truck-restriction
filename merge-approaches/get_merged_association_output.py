import geopandas as gpd
import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz


# Function to calculate similarity
def calculate_osm_similarity(row):
    return fuzz.token_sort_ratio(row["name"], row["7 - Facility Carried By Structure"])


def read_geopackage_to_dataframe(filepath):
    """Read a GeoPackage file into a GeoDataFrame."""
    return gpd.read_file(filepath)


def extract_coordinates(geom):
    # Function to extract coordinates from geometry object
    if geom is None or pd.isnull(geom):
        return None, None
    else:
        return geom.x, geom.y


def main():
    mile_point_output = "mile-point-approach/output-data/osm_road_points.gpkg"
    hydrography_output = "hydrography-approach/output-data/Kentucky/csv-files/Final-bridges-with-percentage-match.csv"
    similarity_threshold = 75
    review_threshold = 60

    # Read GeoPackage and CSV into DataFrames
    milepoint_df = read_geopackage_to_dataframe(mile_point_output)
    milepoint_df = milepoint_df.to_crs("EPSG:4326")
    hydrography_df = pd.read_csv(hydrography_output)

    # Merge DataFrames and select desired columns
    milepoint_cols = ["bridge_id", "osm_id", "name", "geometry"]
    merge_df = pd.merge(
        hydrography_df,
        milepoint_df[milepoint_cols],
        left_on="8 - Structure Number",
        right_on="bridge_id",
        how="left",
    )
    merge_df.rename(columns={"osm_similarity": "osm_similarity_hydro"}, inplace=True)
    merge_df.rename(columns={"final_osm_id": "osm_id_hydro"}, inplace=True)
    merge_df.rename(columns={"osm_id": "osm_id_mile"}, inplace=True)

    merge_df["osm_similarity_mile"] = merge_df.apply(calculate_osm_similarity, axis=1)

    merge_df["projected_long_mile"], merge_df["projected_lat_mile"] = zip(
        *merge_df["geometry"].apply(extract_coordinates)
    )

    # Removing rows where coordinates from milepoint approach are not available
    merge_df = merge_df.dropna(
        subset=[
            "projected_long_mile",
            "projected_lat_mile",
        ]
    )

    # Condition 1
    condition1 = merge_df[
        merge_df["bridge_id"].isnull()
        & merge_df["osm_id_hydro"].notnull()
        & (merge_df["osm_similarity_hydro"] >= similarity_threshold)
    ].copy()
    condition1["final_osm_id"] = condition1["osm_id_hydro"]
    condition1["osm_match"] = condition1["osm_similarity_hydro"]
    condition1["final_long"] = condition1["projected_long"]
    condition1["final_lat"] = condition1["projected_lat"]

    # Condition 1R: Review
    condition1R = merge_df[
        merge_df["bridge_id"].isnull()
        & merge_df["osm_id_hydro"].notnull()
        & (
            (similarity_threshold > merge_df["osm_similarity_hydro"])
            & (merge_df["osm_similarity_hydro"] >= review_threshold)
        )
    ].copy()
    condition1R["final_osm_id"] = condition1R["osm_id_hydro"]
    condition1R["osm_match"] = condition1R["osm_similarity_hydro"]
    condition1R["final_long"] = condition1R["projected_long"]
    condition1R["final_lat"] = condition1R["projected_lat"]

    # Condition 2
    condition2 = merge_df[
        merge_df["bridge_id"].notnull()
        & (merge_df["osm_id_hydro"] == merge_df["osm_id_mile"])
        & (merge_df["osm_similarity_hydro"] >= similarity_threshold)
    ].copy()
    condition2["final_osm_id"] = condition2["osm_id_hydro"]
    condition2["osm_match"] = condition2["osm_similarity_hydro"]
    condition2["final_long"] = condition2["projected_long_mile"]
    condition2["final_lat"] = condition2["projected_lat_mile"]

    # Condition 2R: Review
    condition2R = merge_df[
        merge_df["bridge_id"].notnull()
        & (merge_df["osm_id_hydro"] == merge_df["osm_id_mile"])
        & (
            (similarity_threshold > merge_df["osm_similarity_hydro"])
            & (merge_df["osm_similarity_hydro"] >= review_threshold)
        )
    ].copy()
    condition2R["final_osm_id"] = condition2R["osm_id_hydro"]
    condition2R["osm_match"] = condition2R["osm_similarity_hydro"]
    condition2R["final_long"] = condition2R["projected_long_mile"]
    condition2R["final_lat"] = condition2R["projected_lat_mile"]

    # Condition 3
    condition3 = merge_df[
        (merge_df["bridge_id"].notnull())
        & (merge_df["osm_id_hydro"] != merge_df["osm_id_mile"])
        & (merge_df["osm_similarity_hydro"] > merge_df["osm_similarity_mile"])
        & (merge_df["osm_similarity_hydro"] >= similarity_threshold)
    ].copy()
    condition3["final_osm_id"] = condition3["osm_id_hydro"]
    condition3["osm_match"] = condition3["osm_similarity_hydro"]
    condition3["final_long"] = condition3["projected_long"]
    condition3["final_lat"] = condition3["projected_lat"]

    # Condition 3R: Review
    condition3R = merge_df[
        (merge_df["bridge_id"].notnull())
        & (merge_df["osm_id_hydro"] != merge_df["osm_id_mile"])
        & (merge_df["osm_similarity_hydro"] > merge_df["osm_similarity_mile"])
        & (
            (similarity_threshold > merge_df["osm_similarity_hydro"])
            & (merge_df["osm_similarity_hydro"] >= review_threshold)
        )
    ].copy()
    condition3R["final_osm_id"] = condition3R["osm_id_hydro"]
    condition3R["osm_match"] = condition3R["osm_similarity_hydro"]
    condition3R["final_long"] = condition3R["projected_long"]
    condition3R["final_lat"] = condition3R["projected_lat"]

    # Condition 4
    condition4 = merge_df[
        (merge_df["bridge_id"].notnull())
        & (merge_df["osm_id_hydro"] != merge_df["osm_id_mile"])
        & (merge_df["osm_similarity_hydro"] < merge_df["osm_similarity_mile"])
        & (merge_df["osm_similarity_mile"] >= similarity_threshold)
    ].copy()
    condition4["final_osm_id"] = condition4["osm_id_mile"]
    condition4["osm_match"] = condition4["osm_similarity_mile"]
    condition4["final_long"] = condition4["projected_long_mile"]
    condition4["final_lat"] = condition4["projected_lat_mile"]

    # Condition 4R: Review
    condition4R = merge_df[
        (merge_df["bridge_id"].notnull())
        & (merge_df["osm_id_hydro"] != merge_df["osm_id_mile"])
        & (merge_df["osm_similarity_hydro"] < merge_df["osm_similarity_mile"])
        & (
            (similarity_threshold > merge_df["osm_similarity_mile"])
            & (merge_df["osm_similarity_mile"] >= review_threshold)
        )
    ].copy()
    condition4R["final_osm_id"] = condition4R["osm_id_mile"]
    condition4R["osm_match"] = condition4R["osm_similarity_mile"]
    condition4R["final_long"] = condition4R["projected_long_mile"]
    condition4R["final_lat"] = condition4R["projected_lat_mile"]

    # Condition 5
    condition5 = merge_df[
        (merge_df["bridge_id"].notnull())
        & (merge_df["osm_id_hydro"] != merge_df["osm_id_mile"])
        & (merge_df["osm_similarity_hydro"] == merge_df["osm_similarity_mile"])
        & (merge_df["osm_similarity_mile"] >= similarity_threshold)
    ].copy()
    condition5["final_osm_id"] = condition5["osm_id_mile"]
    condition5["osm_match"] = condition5["osm_similarity_mile"]
    condition5["final_long"] = condition5["projected_long_mile"]
    condition5["final_lat"] = condition5["projected_lat_mile"]

    # Condition 5R: Review
    condition5R = merge_df[
        (merge_df["bridge_id"].notnull())
        & (merge_df["osm_id_hydro"] != merge_df["osm_id_mile"])
        & (merge_df["osm_similarity_hydro"] == merge_df["osm_similarity_mile"])
        & (
            (similarity_threshold > merge_df["osm_similarity_mile"])
            & (merge_df["osm_similarity_mile"] >= review_threshold)
        )
    ].copy()
    condition5R["final_osm_id"] = condition5R["osm_id_mile"]
    condition5R["osm_match"] = condition5R["osm_similarity_mile"]
    condition5R["final_long"] = condition5R["projected_long_mile"]
    condition5R["final_lat"] = condition5R["projected_lat_mile"]

    # Combine all subsets
    filtered_df = pd.concat(
        [condition1, condition2, condition3, condition4, condition5]
    )

    filtered_review_df = pd.concat(
        [condition1R, condition2R, condition3R, condition4R, condition5R]
    )

    # Remove duplicates
    filtered_df = filtered_df.drop_duplicates()
    filtered_review_df = filtered_review_df.drop_duplicates()

    filtered_df = filtered_df[
        [
            "8 - Structure Number",
            "final_osm_id",
            "bridge_length",
            "osm_match",
            "final_lat",
            "final_long",
        ]
    ]

    filtered_review_df = filtered_review_df[
        [
            "8 - Structure Number",
            "final_osm_id",
            "bridge_length",
            "osm_match",
            "final_lat",
            "final_long",
        ]
    ]

    # Filter out rows where projection point is not available
    filtered_df = filtered_df.dropna(
        subset=[
            "final_long",
            "final_lat",
        ]
    )

    filtered_review_df = filtered_review_df.dropna(
        subset=[
            "final_long",
            "final_lat",
        ]
    )

    # Save the filtered DataFrame to CSV
    combined_df = pd.concat([filtered_df, filtered_review_df])
    combined_df["Association"] = np.where(
        combined_df.index.isin(filtered_df.index), "Automated import", "MapRoulette"
    )
    combined_df.to_csv(
        "merge-approaches/output-data/merged-approaches-association-output.csv",
        index=False,
    )


if __name__ == "__main__":
    main()
