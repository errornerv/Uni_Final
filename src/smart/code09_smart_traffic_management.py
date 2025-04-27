import os
import random
import hashlib
import time
from datetime import datetime
import sqlite3
import json
import logging
import sys
import pandas as pd
import numpy as np
from tqdm import tqdm
import joblib
from pathlib import Path

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# تنظیمات لاگینگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULT_DIR = ROOT_DIR / "result"
input_db = os.path.join(RESULT_DIR, "real_time_orders.db")
output_db = os.path.join(RESULT_DIR, "smart_traffic.db")
model_file = os.path.join(RESULT_DIR, "congestion_model.pkl")
encoders_file = os.path.join(RESULT_DIR, "encoders.pkl")

# گراف نودها
nodes = [f"Node_{i}" for i in range(1, 11)] + ["Genesis"]
graph = {node: {"neighbors": random.sample(nodes, random.randint(1, 3)), 
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]} 
         for node in nodes}

# وضعیت نودها
node_status = {
    node: {"max_capacity": 100, "current_traffic": 0, "active": True} if node != "Genesis" 
    else {"max_capacity": 0, "current_traffic": 0, "active": False} 
    for node in nodes
}

# آستانه‌های پویا
thresholds = {"medium": 40, "high": 70}

# کش برای کاهش کوئری‌های دیتابیس
db_cache = {}

# دیتابیس SQLite
def init_db():
    result_dir = os.path.dirname(output_db)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS smart_traffic
                 (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                  latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT, 
                  traffic_redistribution TEXT, event_type TEXT, predicted_congestion TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS optimization_log
                 (timestamp TEXT, medium_threshold REAL, high_threshold REAL, high_blocks INTEGER)''')
    conn.commit()
    conn.close()
    logging.info(f"Initialized output database at {output_db}")

def save_to_db(block):
    try:
        conn = sqlite3.connect(output_db)
        c = conn.cursor()
        c.execute("INSERT INTO smart_traffic VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
                   block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
                   block.congestion_level, block.traffic_redistribution, block.event_type, block.predicted_congestion))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Error saving block to database: {e}")

def save_optimization_log(timestamp, medium_threshold, high_threshold, high_blocks):
    try:
        conn = sqlite3.connect(output_db)
        c = conn.cursor()
        c.execute("INSERT INTO optimization_log VALUES (?, ?, ?, ?)",
                  (timestamp, medium_threshold, high_threshold, high_blocks))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Error saving optimization log: {e}")

# کلاس بلاک
class SmartTrafficBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_level, 
                 traffic_redistribution=None, event_type="Normal", predicted_congestion=None):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_layer = traffic_layer
        self.health_layer = health_layer
        self.previous_hash = previous_hash
        self.congestion_level = congestion_level
        self.traffic_redistribution = traffic_redistribution or "None"
        self.event_type = event_type
        self.predicted_congestion = predicted_congestion or "Unknown"
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.timestamp, "node_id": self.node_id, "traffic_layer": self.traffic_layer,
            "health_layer": self.health_layer, "previous_hash": self.previous_hash,
            "congestion_level": self.congestion_level, "traffic_redistribution": self.traffic_redistribution,
            "event_type": self.event_type, "predicted_congestion": self.predicted_congestion
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# بارگذاری مدل و انکودرها
def load_model_and_encoders():
    try:
        model = joblib.load(model_file)
        encoders = joblib.load(encoders_file)
        le_node_id = encoders["node_id"]
        le_traffic_type = encoders["traffic_type"]
        le_network_health = encoders["network_health"]
        logging.info(f"Loaded model from {model_file} and encoders from {encoders_file}")
        return model, le_node_id, le_traffic_type, le_network_health
    except Exception as e:
        logging.error(f"Failed to load model or encoders: {e}")
        raise

# پیش‌بینی با مدل ML
def predict_congestion(block, model, le_node_id, le_traffic_type, le_network_health):
    try:
        data = pd.DataFrame([{
            "node_id": block.node_id,
            "traffic_volume": block.traffic_layer["volume"],
            "latency": block.health_layer["latency"],
            "network_health": block.health_layer["status"],
            "traffic_type": block.traffic_layer["type"]
        }])

        # تبدیل مقادیر متنی به عددی
        for column in ["node_id", "traffic_type", "network_health"]:
            if column in ["node_id", "traffic_type", "network_health"]:
                known_values = set(eval(f"le_{column}").classes_)
                if data[column].iloc[0] not in known_values:
                    logging.warning(f"Unknown value in {column}: {data[column].iloc[0]}. Using default value.")
                    data[column] = known_values.pop()  # استفاده از اولین مقدار شناخته‌شده
                data[column] = eval(f"le_{column}").transform([data[column].iloc[0]])[0]

        features = data[["node_id", "traffic_volume", "latency", "network_health", "traffic_type"]]
        prediction = model.predict(features)[0]
        score = model.decision_function(features)[0]

        # تبدیل پیش‌بینی IsolationForest به سطح تراکم
        if prediction == -1:
            if score < -0.1:
                predicted_level = "High"
            else:
                predicted_level = "Medium"
        else:
            predicted_level = "Low"

        return predicted_level
    except Exception as e:
        logging.error(f"Prediction failed for block {block.node_id}: {e}")
        return block.congestion_level

# پخش ترافیک هوشمند
def redistribute_traffic(node_id, excess_traffic):
    try:
        neighbors = [n for n in graph[node_id]["neighbors"] if n != "Genesis" and node_status[n]["active"]]
        available_neighbors = [
            n for n in neighbors 
            if node_status[n]["current_traffic"] + excess_traffic / len(neighbors) <= node_status[n]["max_capacity"]
        ]
        
        if not available_neighbors:
            return "No available neighbors"

        split_traffic = excess_traffic / len(available_neighbors)
        redistribution = []
        for neighbor in available_neighbors:
            node_status[neighbor]["current_traffic"] += split_traffic
            redistribution.append(f"{split_traffic:.2f} MB/s to {neighbor}")
        
        return ", ".join(redistribution)
    except Exception as e:
        logging.error(f"Error in redistribute_traffic for node {node_id}: {e}")
        return "Redistribution failed"

# کلاس بلاک‌چین
class TrafficBlockchain:
    def __init__(self, limit=None):
        self.chain = []
        self.cache = {}
        self.block_history = []
        self.load_from_db(limit)

    def load_from_db(self, limit):
        global db_cache
        if input_db in db_cache:
            rows = db_cache[input_db]
            logging.info(f"Loaded {len(rows)} blocks from cache for {input_db}")
        else:
            conn = sqlite3.connect(input_db)
            c = conn.cursor()
            query = "SELECT * FROM real_time_orders"
            if limit:
                query += f" LIMIT {limit}"
            c.execute(query)
            rows = c.fetchall()
            conn.close()
            db_cache[input_db] = rows
            logging.info(f"Loaded {len(rows)} blocks from {input_db} and cached")

        for row in tqdm(rows, desc="Loading blocks from DB", file=sys.stdout):
            traffic_layer = {"volume": row[3], "type": row[2]}
            health_layer = {"status": row[4], "latency": row[5]}
            congestion_level = row[8]
            traffic_suggestion = row[11]
            event_type = "Normal"
            block = SmartTrafficBlock(row[0], row[1], traffic_layer, health_layer, row[6], congestion_level, 
                                     traffic_suggestion, event_type)
            block.hash = row[7]
            self.chain.append(block)
            if row[1] not in self.cache:
                self.cache[row[1]] = []
            self.cache[row[1]].append(block)
            if len(self.cache[row[1]]) > 4:
                self.cache[row[1]].pop(0)
            tqdm.write(f"Loaded block for Node {row[1]} at {row[0]}")
        print(f"Processed {len(rows)} blocks")

    def add_block(self, block, model, le_node_id, le_traffic_type, le_network_health):
        traffic_volume = block.traffic_layer["volume"]
        node_id = block.node_id
        predicted_congestion = predict_congestion(block, model, le_node_id, le_traffic_type, le_network_health)
        
        if node_status[node_id]["active"]:
            node_status[node_id]["current_traffic"] = traffic_volume
        else:
            node_status[node_id]["current_traffic"] = 0
        
        redistribution = "None"
        if block.congestion_level in ["Medium", "High"] and node_status[node_id]["active"]:
            max_capacity = node_status[node_id]["max_capacity"]
            if traffic_volume > max_capacity:
                excess_traffic = traffic_volume - max_capacity
                if block.event_type == "DDoS":
                    limited_traffic = max_capacity
                    excess_traffic = traffic_volume - limited_traffic
                    redistribution = f"Limited to {limited_traffic:.2f} MB/s, {excess_traffic:.2f} redistributed: {redistribute_traffic(node_id, excess_traffic)}"
                    node_status[node_id]["current_traffic"] = limited_traffic
                else:
                    redistribution = redistribute_traffic(node_id, excess_traffic)
                    node_status[node_id]["current_traffic"] = max_capacity

        new_block = SmartTrafficBlock(block.timestamp, node_id, block.traffic_layer, block.health_layer,
                                     block.previous_hash, block.congestion_level, redistribution, 
                                     block.event_type, predicted_congestion)
        self.chain.append(new_block)
        self.block_history.append(new_block)
        if node_id not in self.cache:
            self.cache[node_id] = []
        self.cache[node_id].append(new_block)
        if len(self.cache[node_id]) > 4:
            self.cache[node_id].pop(0)
        save_to_db(new_block)
        return new_block

    def optimize_thresholds(self):
        global thresholds
        if len(self.block_history) < 100:
            return

        threshold_pairs = [(30, 60), (40, 70), (50, 80)]
        best_high_count = float('inf')
        best_pair = (thresholds["medium"], thresholds["high"])

        for medium, high in threshold_pairs:
            high_count = sum(1 for block in self.block_history[-100:] if block.traffic_layer["volume"] > high)
            if high_count < best_high_count:
                best_high_count = high_count
                best_pair = (medium, high)

        thresholds["medium"], thresholds["high"] = best_pair
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        save_optimization_log(timestamp, thresholds["medium"], thresholds["high"], best_high_count)
        print(f"Thresholds updated: Medium={thresholds['medium']}, High={thresholds['high']}, High Blocks={best_high_count}")

    def generate_report(self):
        total_blocks = len(self.chain[1:])  # بدون جنسیس
        high_congestion = sum(1 for block in self.chain[1:] if block.congestion_level == "High")
        accurate_predictions = sum(1 for block in self.chain[1:] if block.congestion_level == block.predicted_congestion)
        accuracy = (accurate_predictions / total_blocks * 100) if total_blocks > 0 else 0

        report = {
            "total_blocks": total_blocks,
            "high_congestion_blocks": high_congestion,
            "prediction_accuracy": round(accuracy, 2),
            "accurate_predictions": accurate_predictions
        }
        return report

# تابع اصلی
def main():
    try:
        limit = 100 if os.getenv("DEMO_MODE") == "True" else None
        init_db()
        model, le_node_id, le_traffic_type, le_network_health = load_model_and_encoders()
        traffic_blockchain = TrafficBlockchain(limit)
        last_time = time.time()

        for node in nodes:
            node_status[node]["current_traffic"] = 0
            node_status[node]["active"] = node != "Genesis"

        total_blocks = len(traffic_blockchain.chain[1:])
        for idx, block in enumerate(tqdm(traffic_blockchain.chain[1:], desc="Processing Smart Traffic Blocks", file=sys.stdout)):
            traffic_blockchain.add_block(block, model, le_node_id, le_traffic_type, le_network_health)
            print(f"\nProcessed block {idx + 1}/{total_blocks} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:")
            print(f"Node: {block.node_id}, Traffic: {block.traffic_layer['volume']:.2f} MB/s, "
                  f"Health: {block.health_layer['status']}, Congestion: {block.congestion_level}, "
                  f"Predicted Congestion: {block.predicted_congestion}, Redistribution: {block.traffic_redistribution}, "
                  f"Event: {block.event_type}")
            
            if len(traffic_blockchain.block_history) >= 100:
                traffic_blockchain.optimize_thresholds()
                traffic_blockchain.block_history = traffic_blockchain.block_history[-100:]
            
            last_time = time.time()

        report = traffic_blockchain.generate_report()
        logging.info(f"Smart Traffic Management Report: {report}")

        return {
            "status": "success",
            "block_count": report["total_blocks"],
            "summary": f"Processed {report['total_blocks']} blocks, {report['high_congestion_blocks']} high congestion blocks",
            "details": report
        }
    except Exception as e:
        logging.error(f"Error in Step 9: Managing smart traffic: {e}")
        return {
            "status": "error",
            "block_count": 0,
            "summary": "Failed to process smart traffic blocks",
            "error": str(e)
        }

if __name__ == "__main__":
    result = main()
    print(result)