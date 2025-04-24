import sqlite3
import joblib  # تغییر از pickle به joblib برای سازگاری
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import IsolationForest
from tqdm import tqdm
from pathlib import Path

# تنظیمات لاگینگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULT_DIR = ROOT_DIR / "result"
output_db = os.path.join(RESULT_DIR, "new_orders.db")
predictive_db = os.path.join(RESULT_DIR, "predictive_analysis.db")
model_path = os.path.join(RESULT_DIR, "congestion_model.pkl")
encoders_path = os.path.join(RESULT_DIR, "encoders.pkl")

# کلاس بلاک
class TrafficBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, hash_value, 
                 congestion_layer=None, traffic_suggestion=None, is_congestion_order=False, signature=None):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_layer = traffic_layer or {"type": "Data", "volume": 0.0}
        self.health_layer = health_layer or {"status": "Normal", "latency": 0.0}
        self.previous_hash = previous_hash
        self.hash = hash_value
        self.congestion_layer = congestion_layer or {"is_congested": 0, "score": 0.0, "impact": 0.0, "level": "Low"}
        self.traffic_suggestion = traffic_suggestion or "None"
        self.is_congestion_order = is_congestion_order
        self.signature = signature

# کلاس بلاک‌چین
class TrafficBlockchain:
    def __init__(self, limit=None):
        self.chain = []
        self.load_from_db(limit)

    def load_from_db(self, limit):
        try:
            conn = sqlite3.connect(output_db)
            c = conn.cursor()
            query = "SELECT * FROM new_orders ORDER BY timestamp DESC"
            if limit:
                query += f" LIMIT {limit}"
            c.execute(query)
            rows = c.fetchall()
            conn.close()

            logging.info(f"Loading {len(rows)} blocks from DB")
            for row in tqdm(rows, desc="Loading blocks from DB"):
                traffic_layer = {"type": row[2] or "Data", "volume": float(row[3] or 0.0)}
                health_layer = {"status": row[4] or "Normal", "latency": float(row[5] or 0.0)}
                congestion_layer = {
                    "is_congested": 1 if (row[8] or "Low") in ["Medium", "High"] else 0,
                    "score": float(row[9] or 0.0),
                    "impact": float(row[10] or 0.0),
                    "level": row[8] or "Low"
                }
                try:
                    signature = bytes.fromhex(row[13]) if row[13] and row[13] != '0' else None
                except (ValueError, IndexError) as e:
                    logging.warning(f"Invalid signature format for block at timestamp {row[0]}: {e}")
                    signature = None

                block = TrafficBlock(
                    timestamp=row[0],
                    node_id=row[1],
                    traffic_layer=traffic_layer,
                    health_layer=health_layer,
                    previous_hash=row[6],
                    hash_value=row[7],
                    congestion_layer=congestion_layer,
                    traffic_suggestion=row[11] or "None",
                    is_congestion_order=bool(row[12] or 0),
                    signature=signature
                )
                self.chain.append(block)

        except sqlite3.Error as e:
            logging.error(f"Error loading blockchain from DB: {e}")
            self.chain = []

    def get_last_block(self):
        return self.chain[-1] if self.chain else None

    def get_blocks_in_time_range(self, start_time, end_time):
        start = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        filtered_blocks = []
        for block in self.chain:
            try:
                block_time = datetime.strptime(block.timestamp, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                try:
                    block_time = datetime.strptime(block.timestamp, '%Y-%m-%dT%H:%M:%S')
                except ValueError as e:
                    logging.warning(f"Invalid timestamp format for block: {block.timestamp}, error: {e}")
                    continue
            if start <= block_time <= end:
                filtered_blocks.append(block)
        return filtered_blocks

# کلاس تحلیل پیش‌بینی
class PredictiveAnalysis:
    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.load_model_and_encoders()

    def load_model_and_encoders(self):
        try:
            self.model = joblib.load(model_path)
            self.label_encoders = joblib.load(encoders_path)  # تغییر به joblib برای سازگاری
            logging.info(f"Loaded model from {model_path} and encoders from {encoders_path}")
            # لاگ مقادیر classes_ برای بررسی
            for column in ['node_id', 'traffic_type', 'network_health']:
                if column in self.label_encoders:
                    logging.info(f"Classes for {column}: {self.label_encoders[column].classes_}")
                else:
                    logging.warning(f"No encoder found for {column}")
        except Exception as e:
            logging.warning(f"Failed to load model or encoders: {e}. Using default IsolationForest model.")
            self.model = IsolationForest(contamination=0.1, random_state=42)
            self.label_encoders = {
                'node_id': LabelEncoder(),
                'traffic_type': LabelEncoder(),
                'network_health': LabelEncoder()
            }

    def preprocess_data(self, blocks):
        data = []
        for block in blocks:
            traffic_layer = block.traffic_layer or {"type": "Data", "volume": 0.0}
            health_layer = block.health_layer or {"status": "Normal", "latency": 0.0}
            congestion_layer = block.congestion_layer or {"score": 0.0, "impact": 0.0, "level": "Low"}
            
            data.append([
                block.node_id or "Unknown",
                traffic_layer.get("type", "Data"),
                float(traffic_layer.get("volume", 0.0)),
                health_layer.get("status", "Normal"),
                float(health_layer.get("latency", 0.0)),
                float(congestion_layer.get("score", 0.0)),
                float(congestion_layer.get("impact", 0.0))
            ])
        df = pd.DataFrame(data, columns=['node_id', 'traffic_type', 'traffic_volume', 'network_health', 'latency', 'congestion_score', 'congestion_impact'])

        # پر کردن مقادیر NaN
        df.fillna({
            'traffic_volume': 0.0,
            'latency': 0.0,
            'congestion_score': 0.0,
            'congestion_impact': 0.0
        }, inplace=True)

        # لاگ مقادیر اولیه
        logging.info(f"Initial data types:\n{df.dtypes}")
        logging.info(f"Sample data before encoding:\n{df.head().to_string()}")

        # بررسی تنوع داده‌ها
        if df['congestion_score'].nunique() == 1 and df['congestion_impact'].nunique() == 1:
            logging.warning("No variation in congestion_score and congestion_impact. Adding synthetic variation.")
            df['congestion_score'] = df['traffic_volume'] * 0.01 + np.random.uniform(-0.1, 0.1, len(df))
            df['congestion_impact'] = df['latency'] * 0.01 + np.random.uniform(-0.1, 0.1, len(df))

        # تبدیل مقادیر متنی به عددی با مدیریت مقادیر ناشناخته
        for column in ['node_id', 'traffic_type', 'network_health']:
            if column in self.label_encoders:
                encoder = self.label_encoders[column]
                try:
                    # بررسی مقادیر شناخته‌شده
                    known_values = set(encoder.classes_)
                    logging.info(f"Known values for {column}: {known_values}")
                    current_values = set(df[column].astype(str))
                    unknown_values = current_values - known_values
                    if unknown_values:
                        logging.warning(f"Unknown values in {column}: {unknown_values}. Replacing with first known value.")
                        # انتخاب اولین مقدار شناخته‌شده به‌عنوان پیش‌فرض
                        default_value = list(known_values)[0] if known_values else "Unknown"
                        df[column] = df[column].astype(str).apply(
                            lambda x: x if x in known_values else default_value
                        )
                    df[column] = encoder.transform(df[column].astype(str))
                except Exception as e:
                    logging.error(f"Error encoding {column}: {e}")
                    # در صورت خطا، از یه انکودر جدید استفاده کن
                    self.label_encoders[column] = LabelEncoder()
                    df[column] = self.label_encoders[column].fit_transform(df[column].astype(str))
            else:
                logging.warning(f"No encoder for {column}. Fitting a new one.")
                self.label_encoders[column] = LabelEncoder()
                df[column] = self.label_encoders[column].fit_transform(df[column].astype(str))

        # لاگ مقادیر بعد از انکودینگ
        logging.info(f"Data types after encoding:\n{df.dtypes}")
        logging.info(f"Sample data after encoding:\n{df.head().to_string()}")

        return df

    def predict_congestion(self, data):
        if data.empty:
            logging.warning("No data to predict.")
            return [], []

        features = data[['node_id', 'traffic_type', 'traffic_volume', 'network_health', 'latency']].values
        logging.info(f"Features shape: {features.shape}")
        logging.info(f"Features sample:\n{features[:5]}")

        if np.any(np.isnan(features)):
            logging.warning("NaN values found in features for prediction. Replacing with 0.")
            features = np.nan_to_num(features, 0.0)

        try:
            congestion_scores = self.model.decision_function(features)
            predictions = self.model.predict(features)
            logging.info(f"Predictions sample: {predictions[:5]}")
            logging.info(f"Congestion scores sample: {congestion_scores[:5]}")
        except Exception as e:
            logging.error(f"Error in model prediction: {e}")
            return [], []

        congestion_levels = []
        for score, pred in zip(congestion_scores, predictions):
            if pred == -1:
                if score < -0.1:
                    congestion_levels.append("High")
                else:
                    congestion_levels.append("Medium")
            else:
                congestion_levels.append("Low")

        return congestion_levels, congestion_scores

    def detect_anomalies(self, data):
        if data.empty:
            logging.warning("No data for anomaly detection.")
            return []

        features = data[['traffic_volume', 'latency', 'congestion_score', 'congestion_impact']].values
        logging.info(f"Anomaly features shape: {features.shape}")
        logging.info(f"Anomaly features sample:\n{features[:5]}")

        if np.any(np.isnan(features)):
            logging.warning("NaN values found in features for anomaly detection. Replacing with 0.")
            features = np.nan_to_num(features, 0.0)

        try:
            anomalies = self.model.predict(features)
            logging.info(f"Anomalies sample: {anomalies[:5]}")
        except Exception as e:
            logging.error(f"Error in anomaly detection: {e}")
            return np.zeros(len(data), dtype=int)

        return anomalies

def save_predictions_to_db(congestion_predictions, congestion_scores, anomalies, blocks):
    try:
        conn = sqlite3.connect(predictive_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS predictive_analysis (
                     timestamp TEXT, node_id TEXT, traffic_volume REAL, congestion_level TEXT, predicted_congestion TEXT,
                     anomaly_detected INTEGER, congestion_score REAL)''')

        for block, pred, score, anomaly in zip(blocks, congestion_predictions, congestion_scores, anomalies):
            c.execute("INSERT INTO predictive_analysis VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (block.timestamp, block.node_id, block.traffic_layer["volume"], block.congestion_layer["level"],
                       pred, 1 if anomaly == -1 else 0, score))
        conn.commit()
        conn.close()
        logging.info("Predictions saved to DB")
    except sqlite3.Error as e:
        logging.error(f"Error saving predictions to DB: {e}")

# تابع اصلی
def main():
    limit = 100 if os.getenv("DEMO_MODE") == "True" else None
    traffic_blockchain = TrafficBlockchain(limit)
    if not traffic_blockchain.chain:
        logging.warning("No blocks found in the blockchain")
        return

    analysis = PredictiveAnalysis()
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    recent_blocks = traffic_blockchain.get_blocks_in_time_range(
        start_time.strftime('%Y-%m-%d %H:%M:%S'),
        end_time.strftime('%Y-%m-%d %H:%M:%S')
    )

    if not recent_blocks:
        logging.warning("No recent blocks found for analysis")
        return

    data = analysis.preprocess_data(recent_blocks)
    congestion_predictions, congestion_scores = analysis.predict_congestion(data)
    anomalies = analysis.detect_anomalies(data)

    save_predictions_to_db(congestion_predictions, congestion_scores, anomalies, recent_blocks)

    for block, pred, score, anomaly in zip(recent_blocks, congestion_predictions, congestion_scores, anomalies):
        logging.info(f"Node: {block.node_id}, Timestamp: {block.timestamp}, Predicted Congestion: {pred}, Score: {score:.2f}, Anomaly: {'Yes' if anomaly == -1 else 'No'}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Error in Step 12: Predictive analysis and anomaly detection...: {e}")
        raise