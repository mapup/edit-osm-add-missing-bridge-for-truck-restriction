import os
import shutil

import dask.dataframe as dd
import pandas as pd


def process_all_join(nbi_30_join_csv, nbi_10_join_csv, all_join_dask, all_join_csv):
    left_csv = nbi_30_join_csv
    right_csv = nbi_10_join_csv

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
        left_csv,
        dtype=dtype_left,
    )
    right_ddf = dd.read_csv(
        right_csv,
        dtype=dtype_right,
    )

    # Perform a left join on the 'bridge_id' column
    result_ddf = left_ddf.merge(right_ddf, on="8 - Structure Number", how="left")

    # Save the result to a directory with multiple part files
    result_ddf.to_csv(
        all_join_dask + "/*.csv",
        index=False,
    )

    # Ensure the Dask computations are done before combining files
    dd.compute()

    # List the part files
    part_files = sorted(
        os.path.join(all_join_dask, f)
        for f in os.listdir(all_join_dask)
        if f.endswith(".csv")
    )

    # Combine the part files into a single DataFrame
    combined_df = pd.concat(pd.read_csv(file) for file in part_files)

    # Save the combined DataFrame to a single CSV file
    combined_df.to_csv(
        all_join_csv,
        index=False,
    )
    print(f"Output file: {all_join_csv} has been created successfully!")

    # Optional: Clean up the part files
    shutil.rmtree(all_join_dask)