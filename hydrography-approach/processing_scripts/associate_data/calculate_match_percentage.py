import pandas as pd
from typing import List, Tuple, Optional
from fuzzywuzzy import fuzz

# Function to calculate similarity
def calculate_similarity(row: pd.Series, cols: List[str], fixed_column: str) -> Tuple[int, Optional[str]]:
    """
    Calculate the maximum similarity score between a row and a list of columns with respect to a fixed column.

    Parameters:
        row (pandas.Series): A row from a DataFrame.
        cols (list): A list of column names to compare.
        fixed_column (str): The column name to compare against.

    Returns:
        tuple: A tuple containing the maximum similarity score and the column name with the maximum similarity score.
    """
    try:
        max_score = 0
        max_col = None
        for col in cols:
            if col in row and pd.notna(row[col]) and pd.notna(row[fixed_column]):
                score = fuzz.token_sort_ratio(str(row[col]), str(row[fixed_column]))
                if score > max_score:
                    max_score = score
                    max_col = col
        return max_score, max_col
    except Exception as e:
        print(f"Error occurred while calculating similarity: {e}")
        raise Exception(f"Error occurred while calculating similarity: {e}")

def read_exploded_osm_data_csv(exploded_osm_data_csv: str, osm_cols_for_road_names: List[str]) -> Tuple[pd.DataFrame, List[str]]:
    """
    Reads the 'exploded_osm_data' CSV file and returns a DataFrame with the required columns.

    Parameters:
        exploded_osm_data_csv (str): The path to the CSV file.
        osm_cols_for_road_names (list): The list of column names to read from the CSV file.

    Returns:
        pandas.DataFrame: The DataFrame containing the required columns.
    """
    series_list=[]
    available_osm_road_names=[]
    for col in osm_cols_for_road_names:
        try:
            series=pd.read_csv(exploded_osm_data_csv,usecols=[col])
            series_list.append(series)
            available_osm_road_names.append(col)
        except Exception as e:
            print(e)
            continue
    
    try:
        exploded_osm_data_df=pd.concat(series_list,axis=1)
        return exploded_osm_data_df, available_osm_road_names
    except Exception as e:
        print(f"Error occurred while concatenating the series: {e}")
        raise Exception(f"Error occurred while concatenating the series: {e}")
    

def run(bridge_with_proj_points, bridge_match_percentage,exploded_osm_data_csv):

    df = pd.read_csv(bridge_with_proj_points)

    # Read the 'exploded_osm_data' CSV file and select the required columns
    osm_cols_for_road_names=["osm_id",  "name",  "ref",    "name_1",    "name_2",    "name_3",    "name_5",    "name_4",
                        "name1",    "tiger:name_base_1",    "tiger:name_base_2",    "tiger:name_base_3",
                        "tiger:name_base",    "alt_name",    "name:en",    "official_name",    "bridge:name"]

    # Read only required columns one at a time because the CSV file is too large to read all at once
    exploded_osm_data_df,available_osm_road_names = read_exploded_osm_data_csv(exploded_osm_data_csv, osm_cols_for_road_names)

    df['final_osm_id'] = df['final_osm_id'].astype('object')
    exploded_osm_data_df['osm_id'] = exploded_osm_data_df['osm_id'].astype('object')

    #Merge the data on 'final_osm_id' and 'osm_id'
    df = pd.merge(df, exploded_osm_data_df, left_on='final_osm_id', right_on='osm_id', how='left')

    available_osm_road_names.remove('osm_id')

    #get osm_similarity
    fixed_column_1="7 - Facility Carried By Structure"
    fixed_column_2="6A - Features Intersected"
    df["osm_similarity"], df["osm_similarity_col"] = zip(*df.apply(lambda x: max([calculate_similarity(x, available_osm_road_names, fixed_column_1), calculate_similarity(x, available_osm_road_names, fixed_column_2)], key=lambda item: item[0]), axis=1))

    #get nhd_similarity
    nhd_cols_for_stream_name=["stream_name"]
    fixed_column="6A - Features Intersected"
    df["nhd_similarity"], df["nhd_similarity_col"] = zip(*df.apply(lambda x: calculate_similarity(x, nhd_cols_for_stream_name, fixed_column), axis=1))

    # Save the DataFrame with similarity scores
    df.to_csv(bridge_match_percentage, index=False)
