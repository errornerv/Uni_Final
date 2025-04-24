import pandas as pd
import os
import sqlite3
from tqdm import tqdm
import sys

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# Database paths
current_dir = os.path.dirname(os.path.abspath(__file__))
start_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))  # Go to start/ directory
input_db = os.path.join(start_dir, "result", "new_orders.db")
output_file = os.path.join(start_dir, "result", "traffic_data.csv")

# Function to check if the database file exists
def check_db_exists(db_path):
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} does not exist.")
        return False
    return True

# Function to load data from the database
def load_from_db(db_path):
    # Check if the database exists
    if not check_db_exists(db_path):
        return []

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM new_orders")
        rows = c.fetchall()
        conn.close()

        if not rows:
            print("Database is empty. No data to load.")
            return []

        data = []
        total_rows = len(rows)
        for idx, row in enumerate(tqdm(rows, desc="Loading data from DB", file=sys.stdout)):
            data.append({
                "traffic_volume": row[3],
                "latency": row[5],
                "network_health": row[4],
                "is_congested": 1 if row[8] in ["Medium", "High"] else 0,  # Based on congestion_level
                "traffic_type": row[2],
                "congestion_level": row[8]
            })
            tqdm.write(f"Processed {idx + 1}/{total_rows} rows")
        print(f"Successfully loaded {len(data)} rows from database {db_path}.")
        return data
    except sqlite3.Error as e:
        print(f"Error connecting to database {db_path}: {e}")
        return []

# Function to prepare and save data
def prepare_and_save_data(data, output_path):
    if not data:
        print("No data available to save.")
        return

    try:
        # Ensure the result directory exists
        result_dir = os.path.dirname(output_path)
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
            print(f"Created result directory: {result_dir}")

        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False)
        print(f"Data successfully saved to {output_path}.")
        print("First 5 rows of the data:")
        print(df.head())  # Display the first 5 rows
    except Exception as e:
        print(f"Error saving data to {output_path}: {e}")

# Main execution
if __name__ == "__main__":
    print("Starting data preparation process...")
    chain_data = load_from_db(input_db)
    prepare_and_save_data(chain_data, output_file)
    print("Data preparation process completed.")