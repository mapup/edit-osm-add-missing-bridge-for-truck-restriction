from typing import Callable

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


def exclude_duplicate_bridges(
    df: pd.DataFrame, output_duplicate_exclude_csv: str
) -> pd.DataFrame:
    """
    Exclude duplicate bridges, remove non-posted culverts and save the result to a CSV.
    """
    try:
        # Drop duplicate bridges based on coordinates
        df.drop_duplicates(
            subset=["16 - Latitude (decimal)", "17 - Longitude (decimal)"], inplace=True
        )

        # Drop duplicate bridges based on Bridge ID
        df = df[~df["8 - Structure Number"].str.contains("*", regex=False)]

        # Remove culverts which are not posted
        df = df[
            ~(
                (df["43B - Main Span Design"] == "Culvert")
                & (df["41 - Structure Operational Status Code"] != "P")
            )
        ]

        df.to_csv(output_duplicate_exclude_csv, index=False)

    except Exception as e:
        print(f"Error processing duplicates and culverts: {e}")
        raise

    return df


def convert_to_gpkg(
    df: pd.DataFrame, output_gpkg_file: str, logger: Callable[[str], None]
) -> None:
    """
    Convert the DataFrame to a GeoPackage.
    """
    try:
        # Create geometry from latitude and longitude
        geometry = [
            Point(xy)
            for xy in zip(df["17 - Longitude (decimal)"], df["16 - Latitude (decimal)"])
        ]
        gdf = gpd.GeoDataFrame(df, geometry=geometry)

        gdf.to_file(output_gpkg_file, driver="GPKG")

        logger(f"GeoPackage saved successfully to {output_gpkg_file}")

    except Exception as e:
        print(f"Error saving GeoPackage: {e}")
        raise


def create_nbi_geopackage(
    input_csv: str,
    output_duplicate_exclude_csv: str,
    output_gpkg_file: str,
    logger: Callable[[str], None],
) -> None:
    """
    Perform processing of coordinates and filtering of bridges.
    """
    try:
        df = pd.read_csv(input_csv)

        # Exclude duplicate bridges and save the result to a CSV
        df = exclude_duplicate_bridges(df, output_duplicate_exclude_csv)

        # Convert the final DataFrame to a GeoPackage file
        convert_to_gpkg(df, output_gpkg_file, logger)

    except Exception as e:
        print(f"Error creating NBI GeoPackage: {e}")
        raise
