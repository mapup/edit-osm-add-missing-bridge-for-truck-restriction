import os
import shutil
from typing import Dict, Optional

import dask.dataframe as dd
import pandas as pd


def process_all_join(
    nbi_30_join_csv: str,
    nbi_10_join_csv: str,
    all_join_dask: str,
    all_join_csv: str,
    logger: Optional[object] = None,
) -> None:
    """Process join of NBI 30 and NBI 10 CSVs using Dask and save the result to a single CSV file."""

    # Specify the data types for the CSV columns
    dtype: Dict[str, str] = {
        "OBJECTID_2": "float64",
        "osm_id": "float64",
        "permanent_identifier": "object",
        # Add other columns with their expected data types
    }

    try:
        # Load the CSV files into Dask DataFrames with specified dtypes
        left_ddf = dd.read_csv(nbi_30_join_csv, dtype=dtype)
        right_ddf = dd.read_csv(nbi_10_join_csv, dtype=dtype)

        # Perform a left join on the '8 - Structure Number' column
        result_ddf = left_ddf.merge(right_ddf, on="8 - Structure Number", how="left")

        # Ensure the output directory exists
        os.makedirs(all_join_dask, exist_ok=True)

        # Save the result to a directory with multiple part files
        result_ddf.to_csv(
            os.path.join(all_join_dask, "*.csv"), index=False, single_file=False
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
        combined_df.to_csv(all_join_csv, index=False)

        if logger:
            logger.info(f"Output file: {all_join_csv} has been created successfully!")

    except Exception as e:
        if logger:
            logger.error(f"An error occurred: {e}")
        else:
            print(f"An error occurred: {e}")

    finally:
        # Optional: Clean up the part files
        if os.path.exists(all_join_dask):
            shutil.rmtree(all_join_dask)
