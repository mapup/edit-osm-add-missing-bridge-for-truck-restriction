import logging
from typing import Dict, List

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point


def project_point_on_line(point: Point, line: LineString) -> Point:
    """Project a point onto a line and return the projected point."""
    return line.interpolate(line.project(point))


def run(
    final_bridges: str,
    filtered_highways: str,
    bridge_association_lengths: str,
    bridge_with_proj_points: str,
    logger: logging.Logger,
) -> None:
    """Project bridge points onto OSM ways and save the results to a CSV file."""

    # Load geopackage files
    bridge_points_gdf = gpd.read_file(final_bridges)
    osm_ways_gdf = gpd.read_file(filtered_highways, layer="lines")

    # Load CSV file
    associations_df = pd.read_csv(bridge_association_lengths)

    # Ensure CRS is consistent
    if bridge_points_gdf.crs != osm_ways_gdf.crs:
        bridge_points_gdf = bridge_points_gdf.to_crs(epsg=4326)
        osm_ways_gdf = osm_ways_gdf.to_crs(epsg=4326)

    # Trim whitespace from structure numbers
    associations_df["8 - Structure Number"] = associations_df[
        "8 - Structure Number"
    ].str.strip()
    bridge_points_gdf["8 - Structure Number"] = bridge_points_gdf[
        "8 - Structure Number"
    ].str.strip()

    projected_data: List[Dict] = []

    for _, row in associations_df.iterrows():
        structure_number = row["8 - Structure Number"]

        try:
            final_osm_id = str(
                int(row["final_osm_id"])
            )  # Convert to integer and then to string

            # Find the corresponding bridge point
            bridge_point = bridge_points_gdf.loc[
                bridge_points_gdf["8 - Structure Number"] == structure_number
            ].geometry.values[0]

            # Find the corresponding OSM way
            osm_way = osm_ways_gdf.loc[
                osm_ways_gdf["osm_id"] == final_osm_id
            ].geometry.values[0]

            # Project the bridge point onto the OSM way
            projected_point = project_point_on_line(bridge_point, osm_way)

            projected_data.append(
                {
                    "8 - Structure Number": structure_number,
                    "final_osm_id": row["final_osm_id"],
                    "osm_name": row["osm_name"],
                    "final_stream_id": row["final_stream_id"],
                    "stream_name": row["stream_name"],
                    "6A - Features Intersected": row["6A - Features Intersected"],
                    "7 - Facility Carried By Structure": row[
                        "7 - Facility Carried By Structure"
                    ],
                    "bridge_length": round(row["bridge_length"] / 3.281, 2),
                    "projected_long": projected_point.x,
                    "projected_lat": projected_point.y,
                }
            )

        except (ValueError, KeyError, IndexError) as e:
            # Handle cases where final_osm_id is NaN or OSM way is not found
            projected_data.append(
                {
                    "8 - Structure Number": structure_number,
                    "final_osm_id": row["final_osm_id"],
                    "osm_name": row["osm_name"],
                    "final_stream_id": row["final_stream_id"],
                    "stream_name": row["stream_name"],
                    "6A - Features Intersected": row["6A - Features Intersected"],
                    "7 - Facility Carried By Structure": row[
                        "7 - Facility Carried By Structure"
                    ],
                    "bridge_length": round(row["bridge_length"] / 3.281, 2),
                    "projected_long": "",
                    "projected_lat": "",
                }
            )
            logger.error(f"Error processing structure number {structure_number}: {e}")

    # Create output DataFrame
    output_df = pd.DataFrame(projected_data)

    # Save to CSV
    output_df.to_csv(bridge_with_proj_points, index=False)
