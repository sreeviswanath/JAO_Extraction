import pandas as pd
import os


# =========================================================
# 1. File paths
# =========================================================

historical_file = r"2026-09_presolved_final_computation.parquet"

new_file = (r"data_latest\Final_compu_2026-09-02.csv")

output_folder = "Combined_data"
os.makedirs(output_folder, exist_ok=True)

output_csv_file = os.path.join(
    output_folder,
    "2026-09_presolved_final_computation.csv"
)

output_parquet_file = os.path.join(
    output_folder,
    "2026-09_presolved_final_computation.parquet"
)


# =========================================================
# 2. Read files
# =========================================================

historical_df = pd.read_parquet(historical_file)
historical_cols = historical_df.columns.tolist()
# print(historical_cols)
# print("Data_type of date in historical:",historical_df["dateTime"].dtype)
# print("Historical_df columns:",historical_df.dtypes)



new_df = pd.read_csv(
    new_file,
    keep_default_na=False,
    na_filter=False,
    # na_values=["NA", "N/A", "na", "n/a", ""]
)

# print("New_df columns:",new_df.dtypes)

print(f"Historical rows : {len(historical_df)}")
print(f"New CSV rows    : {len(new_df)}")


if new_df.empty:
    print("No new data to merge.")
    exit()


# =========================================================
# 3. Make copies
# =========================================================

historical_df = historical_df.copy()
new_df = new_df.copy()


# =========================================================
# 4. Create a NORMALIZED timestamp in both files
# =========================================================

# Historical file uses "dateTime"
if "dateTime" not in historical_df.columns:
    raise ValueError(
        "'dateTime' is missing from historical dataframe"
    )

# New CSV uses "dateTimeUtc"
if "dateTimeUtc" not in new_df.columns:
    raise ValueError(
        "'dateTimeUtc' is missing from new dataframe"
    )

if "cneName" not in historical_df.columns:
    raise ValueError(
        "'cneName' is missing from historical dataframe"
    )

if "cneName" not in new_df.columns:
    raise ValueError(
        "'cneName' is missing from new dataframe"
    )


historical_df["_merge_datetime"] = pd.to_datetime(
    historical_df["dateTime"],
    errors="coerce",
    utc=True
)

new_df["_merge_datetime"] = pd.to_datetime(
    new_df["dateTimeUtc"],
    errors="coerce",
    utc=True
)


# =========================================================
# 5. Clean cneName
# =========================================================

historical_df["cneName"] = (
    historical_df["cneName"]
    .astype(str)
    .str.strip()
)

new_df["cneName"] = (
    new_df["cneName"]
    .astype(str)
    .str.strip()
)


# =========================================================
# 6. Create merge key
# =========================================================

key_cols = [
    "_merge_datetime",
    "cneName"
]


# =========================================================
# 7. Remove duplicate keys inside new CSV
# =========================================================

new_df = new_df.drop_duplicates(
    subset=key_cols,
    keep="last"
)

print(f"Unique rows in new CSV: {len(new_df)}")


# =========================================================
# 8. Identify common columns
# =========================================================

# We don't want to overwrite these columns
# with temporary merge columns.
temporary_cols = {
    "_merge_datetime"
}

common_cols = [
    col
    for col in historical_df.columns
    if col in new_df.columns
    and col not in temporary_cols
]


# =========================================================
# 9. Convert blank strings to NaN
# =========================================================

for col in common_cols:

    if historical_df[col].dtype == "object":
        historical_df[col] = historical_df[col].replace(
            r"^\s*$",
            pd.NA,
            regex=True
        )

    if new_df[col].dtype == "object":
        new_df[col] = new_df[col].replace(
            r"^\s*$",
            pd.NA,
            regex=True
        )


# =========================================================
# 10. Set indexes using the merge key
# =========================================================

historical_df = historical_df.set_index(key_cols)
new_df = new_df.set_index(key_cols)


# =========================================================
# 11. Make sure new data has only columns we need
# =========================================================

new_update_cols = [
    col
    for col in new_df.columns
    if col in historical_df.columns
    and col not in temporary_cols
]


# =========================================================
# 12. UPDATE EXISTING ROWS
#
# Only fill historical missing values.
#
# Example:
#
# Historical:
#     value = NaN
#
# New:
#     value = 35010
#
# Result:
#     value = 35010
#
# But if historical already has a value, keep it.
# =========================================================

existing_keys = historical_df.index.intersection(
    new_df.index
)

print(
    f"Existing rows found in historical data: "
    f"{len(existing_keys)}"
)


# Count how many individual cells will be filled
filled_cells = 0

for col in new_update_cols:

    if col not in historical_df.columns:
        continue

    historical_values = historical_df.loc[
        existing_keys,
        col
    ]

    new_values = new_df.loc[
        existing_keys,
        col
    ]

    # Count cells where historical is missing
    # and new data has a value
    mask = (
        historical_values.isna()
        & new_values.notna()
    )

    filled_cells += mask.sum()

    # Fill ONLY missing historical values
    historical_df.loc[
        existing_keys,
        col
    ] = historical_values.where(
        historical_values.notna(),
        new_values
    )


print(
    f"Missing cells filled from new CSV: "
    f"{filled_cells}"
)


# =========================================================
# 13. FIND COMPLETELY NEW ROWS
# =========================================================

new_keys = new_df.index.difference(
    historical_df.index
)

rows_to_add = new_df.loc[
    new_keys
].copy()

print(
    f"Completely new rows to add: "
    f"{len(rows_to_add)}"
)


# =========================================================
# 14. Convert index back to columns
# =========================================================

historical_df = historical_df.reset_index()
rows_to_add = rows_to_add.reset_index()


# =========================================================
# 15. Make sure rows_to_add has the same columns
# =========================================================

# Start with historical structure
rows_to_add_aligned = pd.DataFrame(
    index=rows_to_add.index,
    columns=historical_df.columns
)


# Copy matching columns
for col in rows_to_add.columns:

    if col in rows_to_add_aligned.columns:
        rows_to_add_aligned[col] = rows_to_add[col]


# =========================================================
# 16. IMPORTANT:
#     New CSV has dateTimeUtc.
#     Historical file has dateTime.
#
#     Therefore populate historical dateTime
#     when adding new rows.
# =========================================================

# if "dateTime" in rows_to_add_aligned.columns:

#     mask = (
#         rows_to_add_aligned["dateTime"].isna()
#         & rows_to_add_aligned["_merge_datetime"].notna()
#     )

#     rows_to_add_aligned.loc[
#         mask,
#         "dateTime"
#     ] = rows_to_add_aligned.loc[
#         mask,
#         "_merge_datetime"
#     ].dt.strftime("%-d-%-m-%Y %H:%M")

# =========================================================
# 16. Populate dateTime for newly added rows
# =========================================================

if "dateTime" in rows_to_add_aligned.columns:

    mask = (
        rows_to_add_aligned["dateTime"].isna()
        & rows_to_add_aligned["_merge_datetime"].notna()
    )

    # Assign actual UTC datetime values, NOT formatted strings
    rows_to_add_aligned.loc[mask, "dateTime"] = (
        rows_to_add_aligned.loc[mask, "_merge_datetime"]
    )

    print(
        "New rows dateTime dtype:",
        rows_to_add_aligned["dateTime"].dtype
    )


# =========================================================
# 17. Combine historical + genuinely new rows
# =========================================================

combined = pd.concat(
    [
        historical_df,
        rows_to_add_aligned
    ],
    ignore_index=True
)


# =========================================================
# 18. Remove temporary merge column
# =========================================================

if "_merge_datetime" in combined.columns:
    combined = combined.drop(
        columns=["_merge_datetime"]
    )


# =========================================================
# 19. Final duplicate check
# =========================================================

combined["_check_datetime"] = pd.to_datetime(
    combined["dateTime"],
    errors="coerce",
    utc=True
)

duplicate_count = combined.duplicated(
    subset=["_check_datetime", "cneName"]
).sum()

print(
    f"Duplicate timestamp + cneName combinations: "
    f"{duplicate_count}"
)


# =========================================================
# 20. Remove check column
# =========================================================

combined = combined.drop(
    columns=["_check_datetime"]
)
# =========================================================
# 20A. ENFORCE CORRECT DATETIME TYPE
# =========================================================

combined["dateTime"] = pd.to_datetime(
    combined["dateTime"],
    errors="coerce",
    utc=True
)

print(
    "Final dateTime dtype:",
    combined["dateTime"].dtype
)

# Verify the datetime column is correct
assert str(combined["dateTime"].dtype) == (
    "datetime64[ns, UTC]"
), "dateTime is not in the expected UTC datetime format!"

# =========================================================
# 20B. NORMALIZE CONTINGENCIES
# =========================================================

import ast
import numpy as np


def parse_contingencies(value):

    # Missing value
    if value is None or value is pd.NA:
        return None

    if isinstance(value, float) and pd.isna(value):
        return None

    # Already a Python list/dict
    if isinstance(value, (list, tuple, dict)):
        return value

    # CSV values are strings
    if isinstance(value, str):

        value = value.strip()

        if value == "":
            return None

        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            # Keep original value if it cannot be parsed
            return value

    return value


if "contingencies" in combined.columns:

    combined["contingencies"] = (
        combined["contingencies"]
        .map(parse_contingencies)
    )

    print(
        "Final contingencies dtype:",
        combined["contingencies"].dtype
    )

    print(
        "First contingency Python type:",
        type(combined["contingencies"].iloc[0])
    )


# =========================================================
# 21. Sort
# =========================================================

combined["_sort_datetime"] = pd.to_datetime(
    combined["dateTime"],
    errors="coerce",
    utc=True
)

combined = (
    combined
    .sort_values(
        by=["_sort_datetime", "cneName"],
        na_position="last"
    )
    .drop(columns=["_sort_datetime"])
    .reset_index(drop=True)
)

combined = combined[historical_cols]

# =========================================================
# 22. Save
# =========================================================

combined.to_csv(
    output_csv_file,
    index=False
)

combined.to_parquet(
    output_parquet_file,
    index=False
)

# =========================================================
# 23. Final information
# =========================================================

print()
print("=" * 60)
print("MERGE COMPLETE")
print("=" * 60)

print(
    f"Original historical rows : {len(historical_df)}"
)

print(
    f"New rows added           : {len(rows_to_add_aligned)}"
)

print(
    f"Cells filled             : {filled_cells}"
)

print(
    f"Final row count          : {len(combined)}"
)

print(
    f"Duplicate keys           : {duplicate_count}"
)

print()
print(
    f"Output saved to:\n"
    f"{output_csv_file}"
)

print(
    f"Output saved to:\n"
    f"{output_parquet_file}"
)