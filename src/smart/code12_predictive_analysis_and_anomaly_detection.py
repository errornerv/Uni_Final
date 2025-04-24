import sqlite3
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import IsolationForest
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
output_db = os.path.join(base_dir, 'result', 'new_orders.db')
predictive_db = os.path.join(base_dir, 'result', 'predictive_analysis.db')
model_path = os.path.join(base_dir, 'result', 'congestion_model.pkl')
encoders_path = os.path.join(base_dir, 'result', 'encoders.pkl')

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
        self.traffic_suggestion = traffic_suggestion
        self.is_congestion_order = is_congestion_order
        self.signature = signature

class TrafficBlockchain:
    def __init__(self):
        self.chain = []
        self.load_from_db()

    def load_from_db(self):
        try:
            conn = sqlite3.connect(output_db)
            c = conn.cursor()
            c.execute("SELECT * FROM new_orders ORDER BY timestamp DESC")
            rows = c.fetchall()
            conn.close()

            logging.info(f"Loading {len(rows)} blocks from DB")
            for row in tqdm(rows, desc="Loading blocks from DB"):
                traffic_layer = {"type": row[2], "volume": float(row[3])}
                health_layer = {"status": row[4], "latency": float(row[5])}
                congestion_layer = {
                    "is_congested": 1 if row[8] in ["Medium", "High"] else 0,
                    "score": float(row[9]),
                    "impact": float(row[10]),
                    "level": row[8]
                }
                # مدیریت signature با کنترل خطا
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
                    traffic_suggestion=row[11],
                    is_congestion_order=bool(row[12]),
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
                # ابتدا فرمت با میکروثانیه‌ها رو امتحان کن
                block_time = datetime.strptime(block.timestamp, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                try:
                    # اگه میکروثانیه نداشت، فرمت بدون میکروثانیه رو امتحان کن
                    block_time = datetime.strptime(block.timestamp, '%Y-%m-%dT%H:%M:%S')
                except ValueError as e:
                    logging.warning(f"Invalid timestamp format for block: {block.timestamp}, error: {e}")
                    continue
            if start <= block_time <= end:
                filtered_blocks.append(block)
        return filtered_blocks

class PredictiveAnalysis:
    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.load_model_and_encoders()

    def load_model_and_encoders(self):
        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            with open(encoders_path, 'rb') as f:
                self.label_encoders = pickle.load(f)
            logging.info(f"Loaded model from {model_path} and encoders from {encoders_path}")
        except Exception as e:
            logging.error(f"Error loading model or encoders: {e}")
            self.model = IsolationForest(contamination=0.1, random_state=42)
            self.label_encoders = {
                'node_id': LabelEncoder(),
                'traffic_type': LabelEncoder(),
                'network_health': LabelEncoder()
            }

    def preprocess_data(self, blocks):
        data = []
        for block in blocks:
            data.append([
                block.node_id,
                block.traffic_layer["type"],
                block.traffic_layer["volume"],
                block.health_layer["status"],
                block.health_layer["latency"],
                block.congestion_layer["score"],
                block.congestion_layer["impact"]
            ])
        df = pd.DataFrame(data, columns=['node_id', 'traffic_type', 'traffic_volume', 'network_health', 'latency', 'congestion_score', 'congestion_impact'])

        for column in ['node_id', 'traffic_type', 'network_health']:
            if column in self.label_encoders:
                df[column] = self.label_encoders[column].fit_transform(df[column].astype(str))
            else:
                self.label_encoders[column] = LabelEncoder()
                df[column] = self.label_encoders[column].fit_transform(df[column].astype(str))

        return df

    def predict_congestion(self, data):
        if data.empty:
            return [], []

        features = data[['node_id', 'traffic_type', 'traffic_volume', 'network_health', 'latency']].values
        congestion_scores = self.model.decision_function(features)
        predictions = self.model.predict(features)

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
            return []

        features = data[['traffic_volume', 'latency', 'congestion_score', 'congestion_impact']].values
        anomalies = self.model.predict(features)
        return anomalies

def save_predictions_to_db(predictions, blocks):
    try:
        conn = sqlite3.connect(predictive_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS predictive_analysis (
                     timestamp TEXT, node_id TEXT, traffic_volume REAL, congestion_level TEXT, predicted_congestion TEXT,
                     anomaly_detected INTEGER, congestion_score REAL)''')

        for block, pred, score, anomaly in zip(blocks, predictions[0], predictions[1], predictions[2]):
            c.execute("INSERT INTO predictive_analysis VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (block.timestamp, block.node_id, block.traffic_layer["volume"], block.congestion_layer["level"],
                       pred, 1 if anomaly == -1 else 0, score))
        conn.commit()
        conn.close()
        logging.info("Predictions saved to DB")
    except sqlite3.Error as e:
        logging.error(f"Error saving predictions to DB: {e}")

def predictive_monitoring():
    traffic_blockchain = TrafficBlockchain()
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

    save_predictions_to_db((congestion_predictions, congestion_scores, anomalies), recent_blocks)

    for block, pred, score, anomaly in zip(recent_blocks, congestion_predictions, congestion_scores, anomalies):
        logging.info(f"Node: {block.node_id}, Timestamp: {block.timestamp}, Predicted Congestion: {pred}, Score: {score:.2f}, Anomaly: {'Yes' if anomaly == -1 else 'No'}")

if __name__ == "__main__":
    predictive_monitoring()