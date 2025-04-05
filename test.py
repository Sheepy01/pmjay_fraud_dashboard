import pandas as pd

def calculate_geographic_anomalies():
    # 1. Read the "Dump" sheet from the Last 24 Hours Excel file
    df = pd.read_excel("data/Last 24 Hours Bihar Reports 05-02-2025.xlsx", sheet_name="Dump")

    # 2. Clean up column names (remove extra whitespace)
    df.columns = df.columns.str.strip()

    # 3. Convert columns to a consistent format for comparison
    df["Hospital Type"] = df["Hospital Type"].astype(str).str.strip().str.upper()
    df["State Name"] = df["State Name"].astype(str).str.strip().str.upper()
    df["Hospital State Name"] = df["Hospital State Name"].astype(str).str.strip().str.upper()

    # 4. Filter for:
    #    - Hospital Type = "P"
    #    - State Name != Hospital State Name
    anomalies_df = df[
        (df["Hospital Type"] == "P") &
        (df["State Name"] != df["Hospital State Name"])
    ]

    # 5. Count the number of anomalies
    geographic_anomalies_count = len(anomalies_df)

    return geographic_anomalies_count

if __name__ == "__main__":
    count = calculate_geographic_anomalies()
    print("Number of Geographic Anomalies:", count)
