import geopandas as gpd

# Constants for file paths
BRIDGE_LINK_LAYER = "interpolated_road.gpkg"
OSM_SHAPE_FILE_LAYER = "gis_osm_roads_free_1.shp"
BRIDGE_LOCATIONS_LAYER = "interpolated_bridge.gpkg"
OUTPUT_OSM_LINKS_GPKG = "osm_road_raw.gpkg"
OUTPUT_OSM_POINTS_GPKG = "osm_road_points.gpkg"


def load_and_prepare_data():
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
    osm_df = gpd.overlay(osm_df, bridge_df, how="intersection")
    osm_df = osm_df[osm_df["bridge_id"].notnull()]
    osm_df["osm_length"] = osm_df.geometry.length
    final_df = osm_df.merge(
        bridge_location_df, on="bridge_id", suffixes=("_osm", "_bridge")
    )
    final_df = gpd.GeoDataFrame(final_df, geometry="geometry_osm")
    final_df["distance"] = final_df.geometry.distance(final_df["geometry_bridge"])
    final_df["min_distance"] = final_df.groupby("lrs_id_osm")["distance"].transform(
        "min"
    )
    final_df = final_df[final_df["min_distance"] == final_df["distance"]]
    point_geom = final_df.geometry_bridge.snap(final_df.geometry, 5)
    return final_df, point_geom


def save_results(final_df, point_geom):
    final_df.drop(columns=["geometry_bridge"], inplace=True)
    osm_points = final_df.set_geometry(point_geom)
    osm_points.to_file(OUTPUT_OSM_POINTS_GPKG)
    final_df.to_file(OUTPUT_OSM_LINKS_GPKG)


def main():
    bridge_df, osm_df, bridge_location_df = load_and_prepare_data()
    final_df, point_geom = process_and_merge_osm_data(
        osm_df, bridge_df, bridge_location_df
    )
    save_results(final_df, point_geom)


if __name__ == "__main__":
    main()
