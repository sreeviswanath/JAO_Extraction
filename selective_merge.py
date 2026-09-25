import pandas as pd
import os


# ---------------------------------------------------------
# 1. File paths
# ---------------------------------------------------------

historical_file = "2026-09_presolved_final_computation 1.parquet"

new_file = "data\_2026-09-02\Final_compu_2026-09-02.csv"

output_folder = "Combined_data"
os.makedirs(output_folder, exist_ok=True)

output_csv_file = os.path.join(
    output_folder,
    "Filled_complete_data.csv"
)


# ---------------------------------------------------------
# 2. Read files
# ---------------------------------------------------------

historical_df = pd.read_parquet(historical_file)
new_df = pd.read_csv(new_file)

print(f"Historical rows : {len(historical_df)}")
print(f"New CSV rows    : {len(new_df)}")


if new_df.empty:
    print("No new data to merge.")
else:

    # -----------------------------------------------------
    # 3. Make copies
    # -----------------------------------------------------

    historical_df = historical_df.copy()
    new_df = new_df.copy()


    # -----------------------------------------------------
    # 4. Create a common timestamp column
    # -----------------------------------------------------

    # Historical file
    historical_df["dateTimeUtc"] = pd.to_datetime(
        historical_df["dateTime"],
        utc=True
    )

    # New CSV
    new_df["dateTimeUtc"] = pd.to_datetime(
        new_df["dateTimeUtc"],
        utc=True
    )


    # -----------------------------------------------------
    # 5. Check required columns
    # -----------------------------------------------------

    key_cols = [
        "dateTimeUtc",
        "cneName"
    ]

    for col in key_cols:

        if col not in historical_df.columns:
            raise ValueError(
                f"'{col}' is missing from historical dataframe"
            )

        if col not in new_df.columns:
            raise ValueError(
                f"'{col}' is missing from new dataframe"
            )


    # -----------------------------------------------------
    # 6. Align columns
    # -----------------------------------------------------

    extra_cols = set(new_df.columns) - set(historical_df.columns)

    if extra_cols:
        print(
            f"Note: new data has columns not present in "
            f"historical file: {extra_cols}"
        )

    # Only columns that historical_df contains
    new_df = new_df[
        [c for c in historical_df.columns if c in new_df.columns]
    ]


    # -----------------------------------------------------
    # 7. Remove duplicate rows inside new_df itself
    # -----------------------------------------------------

    new_df = new_df.drop_duplicates(
        subset=key_cols
    )

    print(f"Unique rows in new CSV: {len(new_df)}")


    # -----------------------------------------------------
    # 8. Create historical keys
    # -----------------------------------------------------

    historical_keys = historical_df[
        key_cols
    ].drop_duplicates()


    # -----------------------------------------------------
    # 9. Find rows that are genuinely missing
    # -----------------------------------------------------

    new_df_marked = new_df.merge(
        historical_keys,
        on=key_cols,
        how="left",
        indicator=True
    )

    rows_to_add = (
        new_df_marked[
            new_df_marked["_merge"] == "left_only"
        ]
        .drop(columns=["_merge"])
    )


    # -----------------------------------------------------
    # 10. Print information about rows being added
    # -----------------------------------------------------

    print(
        f"Found {len(rows_to_add)} genuinely missing rows "
        f"to fill."
    )


    # -----------------------------------------------------
    # 11. Append only missing rows
    # -----------------------------------------------------

    combined = pd.concat(
        [
            historical_df,
            rows_to_add
        ],
        ignore_index=True
    )


    # -----------------------------------------------------
    # 12. Final safety check
    # -----------------------------------------------------

    duplicate_count = combined.duplicated(
        subset=key_cols
    ).sum()

    print(
        f"Duplicate timestamp + cneName combinations "
        f"after merge: {duplicate_count}"
    )


    # -----------------------------------------------------
    # 13. Sort
    # -----------------------------------------------------

    combined = combined.sort_values(
        by=key_cols
    ).reset_index(drop=True)


    # -----------------------------------------------------
    # 14. Save
    # -----------------------------------------------------

    combined.to_csv(
        output_csv_file,
        index=False
    )

    print(
        f"Combined file saved successfully:\n"
        f"{output_csv_file}"
    )

    print(f"Final row count: {len(combined)}")