import pandas as pd


def load_bridge_info(csv_file):
    """Load bridge information CSV into a DataFrame."""
    return pd.read_csv(csv_file)


def load_nearby_join(csv_file):
    """Load nearby join CSV into a DataFrame."""
    return pd.read_csv(csv_file)


def filter_duplicates_and_output(bridge_df, join_df, output_csv):
    """Filter duplicates based on osm_similarity score and output filtered bridge info."""

    filtered_df = join_df[
        join_df["8 - Structure Number"] != join_df["8 - Structure Number_2"]
    ]

    # Set to keep IDs that should be retained
    remove_ids = set()

    # Iterate over join_df with index to avoid modification during iteration
    for index, row in filtered_df.iterrows():
        sn1 = row["8 - Structure Number"]
        sn2 = row["8 - Structure Number_2"]

        if (sn1 not in remove_ids) and (sn2 not in remove_ids):
            try:
                # Retrieve osm_similarity scores
                osm_similarity_sn1 = bridge_df.loc[
                    bridge_df["8 - Structure Number"] == sn1, "osm_similarity"
                ].values[0]
                osm_similarity_sn2 = bridge_df.loc[
                    bridge_df["8 - Structure Number"] == sn2, "osm_similarity"
                ].values[0]

            except IndexError:
                # Handle the case where ID is not found in bridge_df
                print(f"id {sn1} or {sn2} not found in bridge_df")
                continue

            # Determine which ID to retain based on osm_similarity score
            if osm_similarity_sn1 > osm_similarity_sn2:
                remove_ids.add(sn2)
            elif osm_similarity_sn2 > osm_similarity_sn1:
                remove_ids.add(sn1)
            else:
                remove_ids.add(sn2)  # Arbitrarily keep sn1 if scores are equal
        else:
            continue

    # Print set of IDs that are retained
    print("IDs to be removed:", remove_ids)

    # Filter bridge_df based on retain_ids and output to a new CSV
    filtered_bridge_df = bridge_df[~bridge_df["8 - Structure Number"].isin(remove_ids)]
    filtered_bridge_df.to_csv(output_csv, index=False)

    print(f"Filtered bridge information saved to '{output_csv}'.")


def main():
    # File paths
    bridge_info_csv = (
        "output-data/csv-files/Association-match-check-with-percentage.csv"
    )
    nearby_join_csv = "output-data/csv-files/NBI-30-NBI-Join.csv"
    output_csv = "output-data/csv-files/Final-bridges-with-percentage-match.csv"

    # Load data
    bridge_df = load_bridge_info(bridge_info_csv)
    join_df = load_nearby_join(nearby_join_csv)

    # Filter duplicates based on osm_similarity score and output filtered bridge info
    filter_duplicates_and_output(bridge_df, join_df, output_csv)


if __name__ == "__main__":
    main()
