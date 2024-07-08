import pandas as pd
from fuzzywuzzy import fuzz

# Assuming your CSV data is loaded into a DataFrame `df`
# df = pd.read_csv('your_file.csv')


df = pd.read_csv(
    "output-data/csv-files/bridge-osm-association-with-projected-points.csv"
)


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


# Apply the function row-wise
df["osm_similarity"] = df.apply(calculate_osm_similarity, axis=1)
df["nhd_similrity"] = df.apply(calculate_nhd_similarity, axis=1)
df["osm_with_features_intersected"] = df.apply(calculate_cross_similarity_1, axis=1)
df["nhd_with_facility_carried"] = df.apply(calculate_cross_similarity_2, axis=1)

# Save the DataFrame with similarity scores
df.to_csv(
    "output-data/csv-files/Association-match-check-with-percentage.csv", index=False
)
