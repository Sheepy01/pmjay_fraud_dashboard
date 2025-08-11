import pandas as pd
import random
from datetime import datetime, timedelta

# Read the CSV file (change the filename if needed)
df = pd.read_csv("Claim_data_15uly_to_20_July copy.csv", low_memory=False)

# Function to generate random datetime between given start and end dates
def random_datetime(start, end):
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)

# Define start and end datetime
start_date = datetime(2025, 7, 15, 0, 0)
end_date = datetime(2025, 7, 20, 0, 0)  # exclusive

# Generate random datetime for each row in the desired format
# Windows-safe date format (remove leading zeros manually)
df["preauth_init_date"] = [
    f"{dt.month}/{dt.day}/{dt.year} {dt.strftime('%H:%M')}"
    for dt in (random_datetime(start_date, end_date) for _ in range(len(df)))
]

# Save to new CSV file
df.to_csv("preauth_claim_data_15july_to_20july_dummy_filled.csv", index=False)

print("preauth_init_date column overwritten with random datetime values.")
