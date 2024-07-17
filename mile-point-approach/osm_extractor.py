import geopandas as gpd
import pandas as pd

# Constants for file paths
BRIDGE_LINK_LAYER = "interpolated_road.gpkg"
OSM_SHAPE_FILE_LAYER = "gis_osm_roads_free_1.shp"
BRIDGE_LOCATIONS_LAYER = "interpolated_bridge.gpkg"
OUTPUT_OSM_LINKS_GPKG = "osm_road_raw.gpkg"
OUTPUT_OSM_POINTS_GPKG = "osm_road_points.gpkg"


def load_and_prepare_data():
    """
    Loads and prepares the bridge, OSM, and bridge location data from the specified file paths.

    Returns:
        tuple: A tuple containing the prepared bridge, OSM, and bridge location GeoDataFrames.
    """
    bridge_df = gpd.read_file(
        BRIDGE_LINK_LAYER, engine="pyogrio", use_arrow=True
    ).to_crs(3857)
    osm_df = gpd.read_file(
        OSM_SHAPE_FILE_LAYER, engine="pyogrio", use_arrow=True
    ).to_crs(3857)
    bridge_location_df = gpd.read_file(
        BRIDGE_LOCATIONS_LAYER, engine="pyogrio", use_arrow=True
    ).to_crs(3857)
    bridge_df["road_length"] = bridge_df.geometry.length
    bridge_df.set_geometry(
        bridge_df["geometry"].buffer(5, cap_style="flat", single_sided=False),
        inplace=True,
    )
    return bridge_df, osm_df, bridge_location_df


def process_and_merge_osm_data(osm_df, bridge_df, bridge_location_df):
    """
    Processes and merges the OSM data with bridge data and bridge location data.

    Args:
        osm_df (GeoDataFrame): GeoDataFrame containing OSM road data.
        bridge_df (GeoDataFrame): GeoDataFrame containing bridge data.
        bridge_location_df (GeoDataFrame): GeoDataFrame containing bridge location data.

    Returns:
        tuple: A tuple containing the final merged GeoDataFrame and the point geometries.
    """
    osm_df = gpd.overlay(osm_df, bridge_df, how="intersection")
    osm_df = osm_df[osm_df["bridge_id"].notnull()]
    osm_df["osm_length"] = osm_df.geometry.length
    final_df = osm_df.merge(
        bridge_location_df, on="bridge_id", suffixes=("_osm", "_bridge")
    )
    final_df = gpd.GeoDataFrame(final_df, geometry="geometry_osm")
    final_df["distance"] = final_df.geometry.distance(final_df["geometry_bridge"])
    
    final_df["min_distance"] = final_df.groupby("geometry_bridge")["distance"].transform(
        "min"
    )
    final_df = final_df[final_df["min_distance"] == final_df["distance"]]

    point_geom = final_df.geometry_bridge.snap(final_df.geometry_osm, 10)

    final_point_geom = point_geom.where(point_geom != final_df.geometry_bridge, pd.NA)
    final_point_geom = final_point_geom[final_point_geom.notnull()]
    
    return final_df, final_point_geom


def iterative_intersection_process(bridge_df, osm_df, bridge_location_df):
    """
    Iteratively processes and merges the OSM data with bridge data and bridge location data using increasing buffer sizes.

    Args:
        bridge_df (GeoDataFrame): GeoDataFrame containing bridge data.
        osm_df (GeoDataFrame): GeoDataFrame containing OSM road data.
        bridge_location_df (GeoDataFrame): GeoDataFrame containing bridge location data.

    Returns:
        tuple: A tuple containing the final merged GeoDataFrame and a GeoSeries of point geometries.
    """
    final_df_list = []
    point_geom_list = []
    
    buffer_size = 15
    max_buffer = 30
    
    while not bridge_df.empty and buffer_size <= max_buffer:
        bridge_buffer = bridge_df.copy()
        bridge_buffer.set_geometry(
            bridge_buffer["geometry"].buffer(buffer_size, cap_style="flat", single_sided=False),
            inplace=True,
        )
        
        temp_final_df, temp_point_geom = process_and_merge_osm_data(osm_df, bridge_buffer, bridge_location_df)
        
        if not temp_final_df.empty:
            final_df_list.append(temp_final_df)
            point_geom_list.extend(temp_point_geom)
            
            processed_ids = temp_final_df["bridge_id"].unique()
            bridge_df = bridge_df[~bridge_df["bridge_id"].isin(processed_ids)]
        
        buffer_size += 5
    
    final_df = pd.concat(final_df_list, ignore_index=True)
    point_geom = gpd.GeoSeries(point_geom_list)

    return final_df, point_geom


def save_results(final_df, point_geom):
    """
    Saves the final merged results to GeoPackage files.

    Args:
        final_df (GeoDataFrame): The final merged GeoDataFrame to save.
        point_geom (GeoSeries): The point geometries to save.
    """
    final_df.drop(columns=["geometry_bridge"], inplace=True)
    osm_points = final_df.set_geometry(point_geom)
    osm_points.drop_duplicates(subset=["bridge_id"], inplace=True)
    osm_points.to_file(OUTPUT_OSM_POINTS_GPKG)
    final_df.to_file(OUTPUT_OSM_LINKS_GPKG)


def main():
    """
    Main function to execute the processing pipeline.
    """
    bridge_df, osm_df, bridge_location_df = load_and_prepare_data()
    final_df, point_geom = process_and_merge_osm_data(
        bridge_df=bridge_df, osm_df=osm_df, bridge_location_df=bridge_location_df
    )
    save_results(final_df, point_geom)


if __name__ == "__main__":
    main()
