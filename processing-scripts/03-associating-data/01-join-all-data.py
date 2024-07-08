import os
import shutil

import dask.dataframe as dd
import pandas as pd

# Specify the data types for the CSV columns
dtype_left = {
    "OBJECTID_2": "float64",
    "osm_id": "float64",
    "permanent_identifier": "object",
    # Add other columns with their expected data types
}

dtype_right = {
    "OBJECTID_2": "float64",
    "osm_id": "float64",
    "permanent_identifier": "object",
    # Add other columns with their expected data types
}

# Load the CSV files into Dask DataFrames with specified dtypes
left_ddf = dd.read_csv(
    "output-data/csv-files/NBI-30-OSM-NHD-Join.csv",
    dtype=dtype_left,
)
right_ddf = dd.read_csv(
    "output-data/csv-files/NBI-10-NHD-Join.csv",
    dtype=dtype_right,
)

# Perform a left join on the 'bridge_id' column
result_ddf = left_ddf.merge(right_ddf, on="8 - Structure Number", how="left")

# Save the result to a directory with multiple part files
result_ddf.to_csv(
    "output-data/csv-files/result_directory/*.csv",
    index=False,
)

# Ensure the Dask computations are done before combining files
dd.compute()

# List the part files
part_files = sorted(
    os.path.join("output-data/csv-files/result_directory", f)
    for f in os.listdir("output-data/csv-files/result_directory")
    if f.endswith(".csv")
)

# Combine the part files into a single DataFrame
combined_df = pd.concat(pd.read_csv(file) for file in part_files)

# Save the combined DataFrame to a single CSV file
output_path = "output-data/csv-files/All-Join-Result.csv"
combined_df.to_csv(
    output_path,
    index=False,
)
print(f"Output file: {output_path} has been created successfully!")

# Optional: Clean up the part files
shutil.rmtree("output-data/csv-files/result_directory")
