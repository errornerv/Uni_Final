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
        return None, None

    if os.getenv("DEMO_MODE") == "True" and len(df) > 100:
        df = df.sample(n=100, random_state=42)
        print("DEMO mode: Sampled 100 rows for training.")

    # انکودرها رو با کلیدهای سازگار با code12 می‌سازیم
    le_node_id = LabelEncoder()
    le_traffic_type = LabelEncoder()
    le_network_health = LabelEncoder()

    df['node_id'] = le_node_id.fit_transform(df['node_id'])
    df['traffic_type'] = le_traffic_type.fit_transform(df['traffic_type'])
    df['network_health'] = le_network_health.fit_transform(df['network_health'])

    # ویژگی‌هایی که برای IsolationForest استفاده می‌کنیم
    X = df[['node_id', 'traffic_volume', 'latency', 'network_health', 'traffic_type']]

    encoders = {
        "node_id": le_node_id,
        "traffic_type": le_traffic_type,
        "network_health": le_network_health
    }
    joblib.dump(encoders, encoders_file)
    print(f"Encoders successfully saved to {encoders_file}.")

    return X, encoders

# تابع آموزش و ذخیره مدل
def train_and_save_model(X, model_path):
    if X is None:
        print("No data available for training.")
        return

    try:
        # استفاده از IsolationForest به‌جای RandomForestClassifier
        model = IsolationForest(contamination=0.1, random_state=42)
        model.fit(X)
        joblib.dump(model, model_path)
        print(f"Model successfully saved to {model_path}.")
    except Exception as e:
        print(f"Error during training or saving the model: {e}")

# تابع اصلی
def main():
    print("Starting model training process...")
    df = load_data_from_db(input_db)
    X, encoders = prepare_data(df)
    train_and_save_model(X, model_file)
    print("Model training process completed.")

if __name__ == "__main__":
    main()