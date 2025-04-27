import os
import sqlite3
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
import joblib
import sys
from pathlib import Path

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULT_DIR = ROOT_DIR / "result"
input_db = os.path.join(RESULT_DIR, "new_orders.db")
model_file = os.path.join(RESULT_DIR, "congestion_model.pkl")
encoders_file = os.path.join(RESULT_DIR, "encoders.pkl")

# تابع بررسی وجود دیتابیس
def check_db_exists(db_path):
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} does not exist.")
        return False
    return True

# تابع بارگذاری داده‌ها
def load_data_from_db(db_path):
    if not check_db_exists(db_path):
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM new_orders")
        rows = c.fetchall()
        conn.close()

        if not rows:
            print("Database is empty. No data to load.")
            return pd.DataFrame()

        data = []
        for row in rows:
            data.append({
                "node_id": row[1],
                "traffic_volume": row[3],
                "latency": row[5],
                "network_health": row[4],
                "traffic_type": row[2],
                "congestion_level": row[8]
            })
        print(f"Data successfully loaded from database {db_path}.")
        return pd.DataFrame(data)
    except sqlite3.Error as e:
        print(f"Error connecting to database {db_path}: {e}")
        return pd.DataFrame()

# تابع آماده‌سازی داده‌ها
def prepare_data(df):
    if df.empty:
        print("No data available for preparation.")
        return None, None, 0

    row_count = len(df)
    if os.getenv("DEMO_MODE") == "True" and len(df) > 100:
        df = df.sample(n=100, random_state=42)
        row_count = 100
        print("DEMO mode: Sampled 100 rows for training.")

    le_node_id = LabelEncoder()
    le_traffic_type = LabelEncoder()
    le_network_health = LabelEncoder()

    df['node_id'] = le_node_id.fit_transform(df['node_id'])
    df['traffic_type'] = le_traffic_type.fit_transform(df['traffic_type'])
    df['network_health'] = le_network_health.fit_transform(df['network_health'])

    X = df[['node_id', 'traffic_volume', 'latency', 'network_health', 'traffic_type']]

    encoders = {
        "node_id": le_node_id,
        "traffic_type": le_traffic_type,
        "network_health": le_network_health
    }
    joblib.dump(encoders, encoders_file)
    print(f"Encoders successfully saved to {encoders_file}.")

    return X, encoders, row_count

# تابع آموزش و ذخیره مدل
def train_and_save_model(X, model_path, row_count):
    if X is None:
        print("No data available for training.")
        return 0

    try:
        model = IsolationForest(contamination=0.1, random_state=42)
        model.fit(X)
        joblib.dump(model, model_path)
        print(f"Model successfully saved to {model_path}.")
        return row_count
    except Exception as e:
        print(f"Error during training or saving the model: {e}")
        return 0

# تابع اصلی
def main():
    try:
        print("Starting model training process...")
        df = load_data_from_db(input_db)
        X, encoders, row_count = prepare_data(df)
        trained_rows = train_and_save_model(X, model_file, row_count)
        
        summary = {
            "trained_rows": trained_rows,
            "model_file": model_file,
            "encoders_file": encoders_file
        }
        
        return {
            "status": "success",
            "block_count": trained_rows,  # تعداد ردیف‌های آموزش‌دیده
            "summary": f"Trained model on {trained_rows} rows, saved to {model_file}",
            "details": summary
        }
    except Exception as e:
        print(f"Error in Step 7: Model training: {e}")
        return {
            "status": "error",
            "block_count": 0,
            "summary": "Failed to train model",
            "error": str(e)
        }

if __name__ == "__main__":
    result = main()
    print(result)