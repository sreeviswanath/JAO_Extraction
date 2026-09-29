import pandas as pd
import requests
import os


JAO_URL = ("https://publicationtool.jao.eu/core/api/data/finalComputation")

def extract_final_compu_data(
    date: str,
) -> pd.DataFrame:

    # 1. Build request parameters

    from_utc = f"{date}T00:00:00Z"
    to_utc = f"{date}T23:59:59Z"

    payload={
        "skip":0,
        "fromUtc":from_utc,
        "toUtc":to_utc
    }

    # 2. Sending request

    try:
        response = requests.get(
            JAO_URL,
            params=payload,
        )

        response.raise_for_status()

    except requests.exceptions.RequestException as error:
        print("Requet failed.")
        raise

    # 3. Get JSON response

    response_json = response.json()

    # 4. Get data

    data = response_json.get("data", [])

    if not data:
        print("No BEX data returned for the requested period.")

    # 5. Convert to DataFrame

    df = pd.DataFrame(data)

    return df

# date = input(
#     "Enter date (YYYY-MM-DD): "
# ).strip()

date="2026-09-02"

# Extract BEX data
print("Extracting data.....")
df = extract_final_compu_data(date=date,)

values_to_filter = ["External Constraint DE_DK1_VH_export"]
# values_to_filter = ["220kV Divaca - Pehlin"]

df["dateTimeUtc"] = pd.to_datetime(df["dateTimeUtc"])
filtered_df = df[df["cneName"].isin(values_to_filter)]

print(filtered_df)

# output_folder = f"data_latest"
# os.makedirs(output_folder, exist_ok=True)

# output_csv_file = os.path.join(output_folder,f"Final_compu_{date}.csv")
# # output_parque_file = os.path.join(output_folder,f"final_compu_{date}.parquet")

# # filtered_df.to_parquet(output_parque_file,index=False)
# filtered_df.to_csv(output_csv_file,index=False)

# print("Data saved as csv and parquet.")