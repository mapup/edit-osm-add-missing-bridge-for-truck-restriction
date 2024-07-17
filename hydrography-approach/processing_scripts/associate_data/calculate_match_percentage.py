import pandas as pd
from fuzzywuzzy import fuzz


# Function to calculate similarity
def calculate_osm_similarity(row):
    return fuzz.token_sort_ratio(
        row["osm_name"], row["7 - Facility Carried By Structure"]
    )


def calculate_nhd_similarity(row):
    return fuzz.token_sort_ratio(row["stream_name"], row["6A - Features Intersected"])


def calculate_cross_similarity_1(row):
    return fuzz.token_sort_ratio(row["osm_name"], row["6A - Features Intersected"])


def calculate_cross_similarity_2(row):
    return fuzz.token_sort_ratio(
        row["stream_name"], row["7 - Facility Carried By Structure"]
    )


def run(bridge_with_proj_points, bridge_match_percentage):
    df = pd.read_csv(bridge_with_proj_points)

    # Apply the function row-wise
    df["osm_similarity"] = df.apply(calculate_osm_similarity, axis=1)
    df["nhd_similarity"] = df.apply(calculate_nhd_similarity, axis=1)

    # Save the DataFrame with similarity scores
    df.to_csv(bridge_match_percentage, index=False)
