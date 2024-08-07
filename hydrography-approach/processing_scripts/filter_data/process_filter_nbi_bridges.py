import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

exclude_bridges = []


def exclude_duplicate_bridges(df, output_duplicate_exclude_csv):
    """
    Function to exclude duplicate bridges, remove non-posted culverts and save the result to a CSV
    """
    total_bridges=len(df)
    # Drop duplicate bridges based on coordinates
    df.drop_duplicates(
        subset=["16 - Latitude (decimal)", "17 - Longitude (decimal)"], inplace=True
    )

    # Drop duplicate bridges based on Bridge ID
    df = df[~df['8 - Structure Number'].str.contains('*', regex=False)]
    overlapping_or_duplicate_coordinates=total_bridges-len(df)
    old_len=len(df)

    # Remove culverts which are not posted
    df = df[
        ~(
            (df["43B - Main Span Design"] == "Culvert")
            & (df["41 - Structure Operational Status Code"] != "P")
        )
    ]
    non_posted_culverts=old_len-len(df)

    df.to_csv(output_duplicate_exclude_csv, index=False)

    return df,[total_bridges,overlapping_or_duplicate_coordinates,non_posted_culverts]


def convert_to_gpkg(df, output_gpkg_file):
    """
    Function to convert the DataFrame to a GeoPackage
    """

    # Create geometry from latitude and longitude
    geometry = [
        Point(xy)
        for xy in zip(df["17 - Longitude (decimal)"], df["16 - Latitude (decimal)"])
    ]
    gdf = gpd.GeoDataFrame(df, geometry=geometry)

    gdf.to_file(output_gpkg_file, driver="GPKG")

    print(f"GeoPackage saved successfully to {output_gpkg_file}")


def create_nbi_geopackage(input_csv, output_duplicate_exclude_csv, output_gpkg_file):
    """
    Funtion to perform processing of coordinates and filtering of bridges
    """

    df = pd.read_csv(input_csv)
    # Exclude duplicate bridges and save the result to a CSV
    df,list_of_bridge_stats = exclude_duplicate_bridges(df, output_duplicate_exclude_csv)

    # Convert the final DataFrame to a GeoPackage file
    convert_to_gpkg(df, output_gpkg_file)

    return list_of_bridge_stats