import pandas as pd
import os
import sqlite3
from tqdm import tqdm
import sys
from pathlib import Path

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULT_DIR = ROOT_DIR / "result"
input_db = os.path.join(RESULT_DIR, "new_orders.db")
output_file = os.path.join(RESULT_DIR, "traffic_data.csv")

# تابع بررسی وجود دیتابیس
def check_db_exists(db_path):
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} does not exist.")
        return False
    return True

# تابع بارگذاری داده‌ها از دیتابیس
def load_from_db(db_path, limit=None):
    if not check_db_exists(db_path):
        return []

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        query = "SELECT * FROM new_orders"
        if limit:
            query += f" LIMIT {limit}"
        c.execute(query)
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
                "is_congested": 1 if row[8] in ["Medium", "High"] else 0,
                "traffic_type": row[2],
                "congestion_level": row[8]
            })
            tqdm.write(f"Processed {idx + 1}/{total_rows} rows")
        print(f"Successfully loaded {len(data)} rows from database {db_path}.")
        return data
    except sqlite3.Error as e:
        print(f"Error connecting to database {db_path}: {e}")
        return []

# تابع آماده‌سازی و ذخیره داده‌ها
def prepare_and_save_data(data, output_path):
    if not data:
        print("No data available to save.")
        return 0

    try:
        result_dir = os.path.dirname(output_path)
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
            print(f"Created result directory: {result_dir}")

        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False)
        print(f"Data successfully saved to {output_path}.")
        print("First 5 rows of the data:")
        print(df.head())
        return len(df)
    except Exception as e:
        print(f"Error saving data to {output_path}: {e}")
        return 0

# تابع اصلی
def main():
    try:
        limit = 100 if os.getenv("DEMO_MODE") == "True" else None
        print("Starting data preparation process...")
        chain_data = load_from_db(input_db, limit)
        row_count = prepare_and_save_data(chain_data, output_file)
        
        summary = {
            "total_rows": row_count,
            "output_file": output_file
        }
        
        return {
            "status": "success",
            "block_count": row_count,  # تعداد ردیف‌های پردازش‌شده
            "summary": f"Processed {row_count} rows, saved to {output_file}",
            "details": summary
        }
    except Exception as e:
        print(f"Error in Step 6: Data preparation: {e}")
        return {
            "status": "error",
            "block_count": 0,
            "summary": "Failed to prepare data",
            "error": str(e)
        }

if __name__ == "__main__":
    result = main()
    print(result)