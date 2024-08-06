import geopandas as gpd
import pandas as pd
from fuzzywuzzy import fuzz
from typing import Union, Tuple, List


# Function to calculate similarity
def calculate_osm_similarity(name: str, target: str) -> float:
    """
    Calculate the similarity between two strings using the token_sort_ratio function from the fuzz library.

    Parameters:
        name (str): The first string to compare.
        target (str): The second string to compare.

    Returns:
        int: The similarity score between the two strings, ranging from 0 to 100.
    """
    try:
        return fuzz.token_sort_ratio(name, target)
    except Exception as e:
        print(f"Error occurred while calculating OSM similarity: {e}")
        raise Exception(f"Error occurred while calculating OSM similarity: {e}")


def read_geopackage_to_dataframe(filepath: str) -> gpd.GeoDataFrame:
    """
    Read a GeoPackage file into a GeoDataFrame.

    Args:
        filepath (str): Path to the GeoPackage file.

    Returns:
        gpd.GeoDataFrame: The read GeoDataFrame.
    """
    try:
        return gpd.read_file(filepath)
    except Exception as e:
        print(f"Error occurred while reading GeoPackage file: {e}")
        raise Exception(f"Error occurred while reading GeoPackage file: {e}")


def extract_coordinates(geom: object) -> Union[Tuple[float, float] , Tuple[None, None]]:
    """
    Extract the coordinates from a geometry object.

    Args:
        geom (object): The geometry object from which to extract the coordinates.

    Returns:
        tuple[float, float] | tuple[None, None]: A tuple containing the x and y coordinates of the geometry object,
        or None if the geometry object is None or NaN.
    """
    # Function to extract coordinates from geometry object
    try:
        if geom is None or pd.isnull(geom):
            return None, None
        else:
            return geom.x, geom.y
    except Exception as e:
        print(f"Error occurred while extracting coordinates: {e}")
        raise Exception(f"Error occurred while extracting coordinates: {e}")

def calculate_similarity_for_neighbouring_roads(
    merge_df: pd.DataFrame,
    neighbouring_roads_col: str,
    fixed_cols: List[str],
    column_name_to_store_similarity: str
) -> pd.DataFrame:
    """
    Calculate the similarity between the fixed columns and the neighbouring roads for each row in the merge_df DataFrame.
    
    Parameters:
        merge_df (pandas.DataFrame): The DataFrame containing the merged data.
        neighbouring_roads_col (str): The name of the column in merge_df that contains the neighbouring roads.
        fixed_cols (List[str]): The list of fixed columns to compare with the neighbouring roads.
        neighbouring_roads_similarity_col_name (str): The name of the column to store the similarity score.
    
    Returns:
        pandas.DataFrame: The merge_df DataFrame with the added similarity columns and the dropped similarity columns.
    """
    try:
        neighbouring_roads_expanded_df=merge_df[neighbouring_roads_col].str.split(',', expand=True)
        neighbouring_roads_expanded_df=pd.concat([neighbouring_roads_expanded_df, merge_df[fixed_cols]], axis=1)
        
        merge_df[fixed_cols[0]+'_similarity']=neighbouring_roads_expanded_df.apply(lambda x: max([ calculate_osm_similarity(x[col], x[fixed_cols[0]]) for col in neighbouring_roads_expanded_df.columns if col not in fixed_cols]), axis=1)
        merge_df[fixed_cols[1]+'_similarity']=neighbouring_roads_expanded_df.apply(lambda x: max([ calculate_osm_similarity(x[col], x[fixed_cols[1]]) for col in neighbouring_roads_expanded_df.columns if col not in fixed_cols]), axis=1)
        merge_df[column_name_to_store_similarity]=merge_df[[fixed_cols[0]+'_similarity',fixed_cols[1]+'_similarity']].max(axis=1)
        merge_df.drop([fixed_cols[0]+'_similarity',fixed_cols[1]+'_similarity'], axis=1, inplace=True)
        
        return merge_df
    except Exception as e:
        print(f"Error occurred while calculating similarity for neighbouring roads: {e}")
        raise Exception(f"Error occurred while calculating similarity for neighbouring roads: {e}")


def main():
    try:
        neighbouring_roads_output = "grouped_neighbouring_roads.csv"
        mile_point_output = "osm_road_points.gpkg"
        hydrography_output = "hydrography-method/output-data/csv-files/Final-bridges-with-percentage-match.csv"
        similarity_threshold = 70

        # Read GeoPackage and CSV into DataFrames
        milepoint_df = read_geopackage_to_dataframe(mile_point_output)
        milepoint_df = milepoint_df.to_crs("EPSG:4326")
        hydrography_df = pd.read_csv(hydrography_output,dtype={"final_osm_id":object})
        neighbouring_roads_df = pd.read_csv(neighbouring_roads_output,dtype={"osm_id":object})

        # Remove the trailing '.0' from the specified column
        hydrography_df['final_osm_id'] = hydrography_df['final_osm_id'].apply(lambda x: str(x).replace('.0', '') if isinstance(x, str) and x.endswith('.0') else x)
        

        # Merge DataFrames and select desired columns
        milepoint_df.rename(columns={"osm_id": "osm_id_mile"}, inplace=True)
        milepoint_cols = ["bridge_id", "osm_id_mile", "name", "geometry"]

        merge_df = pd.merge(
            hydrography_df,
            milepoint_df[milepoint_cols],
            left_on="8 - Structure Number",
            right_on="bridge_id",
            how="left",
        )
        merge_df.rename(columns={"osm_similarity": "osm_similarity_hydro"}, inplace=True)
        merge_df.rename(columns={"final_osm_id": "osm_id_hydro"}, inplace=True)
        # merge_df.rename(columns={"osm_id": "osm_id_mile"}, inplace=True)

        # Merge on neighbouring roads
        merge_df = merge_df.merge(
            neighbouring_roads_df,
            left_on=["osm_id_mile","bridge_id"],
            right_on=["osm_id","bridge_id"],
            how="left",
        )

        #For final stats, to see blanks in point geometry
        #merge_df.to_csv("unsnapped.csv",index=False)

        # Calculate similarity for neighbouring roads
        neighbouring_roads_col='neighbouring_roads'
        fixed_cols=['7 - Facility Carried By Structure','6A - Features Intersected']
        column_name_to_store_similarity="neighbouring_roads_similarity"
        merge_df=calculate_similarity_for_neighbouring_roads(merge_df, neighbouring_roads_col, fixed_cols,column_name_to_store_similarity)

        #Get max similarity between osm road names and neighbouring roads names
        merge_df['combined_max_similarity']=merge_df[['neighbouring_roads_similarity','osm_similarity_hydro']].max(axis=1)
        merge_df['combined_max_similarity_col']=merge_df['osm_similarity_col']
        merge_df.loc[merge_df['osm_similarity_hydro'] < merge_df['neighbouring_roads_similarity'],['combined_max_similarity_col']]="neighbouring_roads"

        # Extract coordinates from geometry
        merge_df["projected_long_mile"], merge_df["projected_lat_mile"] = zip(
            *merge_df["geometry"].apply(extract_coordinates)
        )

        #Save data where hydro osm id and milepoint osm id are same
        merge_df=merge_df[merge_df['osm_id_mile']==merge_df['osm_id_hydro']]

        #removing null geometry
        merge_df=merge_df[~merge_df['geometry'].isnull()]

        #Automated and Maproulette edits 
        merge_df['osm_edits']="Automated"
        merge_df.loc[(merge_df["Unique_Bridge_OSM_Combinations"] > 1 ) & ( merge_df["combined_max_similarity"]<similarity_threshold),"osm_edits"]="Maproulette"

        # Select desired columns for output
        keep_cols = ['8 - Structure Number', 'osm_id_hydro', 'osm_name', 'final_stream_id', 'stream_name', '6A - Features Intersected', '7 - Facility Carried By Structure', 'bridge_length', 'Unique_Bridge_OSM_Combinations', 'combined_max_similarity', 'projected_long_mile', 'projected_lat_mile', 'osm_edits']
        merge_df=merge_df[keep_cols]
        merge_df.rename(columns={"osm_id_hydro": "osm_id"}, inplace=True)

        merge_df.to_csv("merged-approaches-association-output.csv", index=False)
    
    except Exception as e:
        print(f"An error occurred: {e}")
        raise Exception(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
