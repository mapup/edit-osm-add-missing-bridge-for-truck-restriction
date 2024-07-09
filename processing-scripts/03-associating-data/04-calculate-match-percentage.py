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
df["nhd_similarity"] = df.apply(calculate_nhd_similarity, axis=1)

df["similarity_type"] = pd.np.where(
    df["final_osm_id"].isnull(),
    "Not to be edited",
    pd.np.where(
        (df["osm_similarity"] > 50) | (df["nhd_similarity"] > 50),
        "Automated edit",
        "MapRoulette review required",
    ),
)

# Save the DataFrame with similarity scores
df.to_csv(
    "output-data/csv-files/Association-match-check-with-percentage.csv", index=False
)
