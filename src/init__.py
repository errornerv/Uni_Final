import logging
import os
import sys
import time
import random
import hashlib
import json
from datetime import datetime, timedelta
import sqlite3
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
import asyncio
import threading
from tqdm import tqdm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import matplotlib.pyplot as plt

# تنظیمات لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent
RESULT_DIR = ROOT_DIR / "result"
sys.path.append(str(ROOT_DIR))

# وارد کردن ماژول‌های پروژه
from src.blockchain.code01_blockchain_initial_data import main as run_initial_data
from src.blockchain.code02_blockchain_congestion_improved import main as run_congestion
from src.blockchain.code03_blockchain_managed_traffic import main as run_managed_traffic
from src.blockchain.code04_blockchain_with_new_orders import main as run_new_orders
from src.blockchain.code05_blockchain_with_real_time_orders import main as run_real_time_orders
from src.traffic.code06_traffic_data_preparation import main as run_data_preparation
from src.traffic.code07_model_training import main as run_model_training
from src.traffic.code08_advanced_traffic_report import main as run_advanced_report
from src.smart.code09_smart_traffic_management import main as run_smart_traffic
from src.smart.code10_self_healing_network import main as run_self_healing
from src.smart.code11_resource_optimization import main as run_resource_optimization
from src.smart.code12_predictive_analysis_and_anomaly_detection import main as run_predictive_analysis

# تنظیمات اولیه
np.random.seed(42)
num_nodes = 10
start_time = datetime(2025, 2, 27, 7, 0, 0)
congestion_prob = 0.15

# گراف نودها و کلیدهای ECDSA
nodes = [f"Node_{i}" for i in range(1, num_nodes + 1)] + ["Genesis"]
graph = {node: {"neighbors": random.sample(nodes, random.randint(1, 3)),
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]}
         for node in nodes}
node_keys = {node: ec.generate_private_key(ec.SECP256R1(), default_backend()) for node in nodes}
node_public_keys = {node: key.public_key() for node, key in node_keys.items()}
node_status = {node: {"max_capacity": 100, "current_traffic": 0, "active": True, "allocated_bandwidth": 50}
               for node in nodes}

# اطمینان از وجود دایرکتوری result
def ensure_result_dir():
    if not RESULT_DIR.exists():
        RESULT_DIR.mkdir()
        logger.info("Created result directory")

# بررسی وجود فایل‌های موردنیاز
def check_file_exists(file_path, step_name):
    if not os.path.exists(file_path):
        logger.error(f"Required file {file_path} for {step_name} does not exist. Skipping step.")
        return False
    return True

# تولید نمودار برای دمو
def plot_summary():
    try:
        conn = sqlite3.connect(RESULT_DIR / "predictive_analysis.db")
        df = pd.read_sql_query("SELECT congestion_level, predicted_congestion, anomaly_detected FROM predictive_analysis", conn)
        conn.close()
        if not df.empty:
            plt.figure(figsize=(8, 6))
            levels = df['congestion_level'].value_counts()
            plt.subplot(1, 2, 1)
            plt.bar(levels.index, levels.values, color=['green', 'orange', 'red'])
            plt.title("Congestion Level Distribution")
            plt.xlabel("Congestion Level")
            plt.ylabel("Count")
            
            anomalies = df['anomaly_detected'].value_counts()
            plt.subplot(1, 2, 2)
            plt.bar(['Normal', 'Anomaly'], anomalies.values, color=['blue', 'red'])
            plt.title("Anomaly Detection")
            plt.ylabel("Count")
            
            plt.tight_layout()
            plt.savefig(RESULT_DIR / "traffic_summary.png")
            plt.close()
            logger.info("Summary plot generated")
    except Exception as e:
        logger.warning(f"Failed to generate summary plot: {e}")

# شبیه‌سازی داده‌های ترافیک جدید
def simulate_traffic(node_id, timestamp):
    hour = timestamp.hour + timestamp.minute / 60
    peak_prob = 0.3 if 8 <= hour < 18 else 0.05
    traffic_types = ["Data", "Stream", "Game", "Priority"]
    traffic_type = random.choice(traffic_types)
    if np.random.random() < (congestion_prob * peak_prob):
        traffic = np.random.uniform(80, 150)
        health = "Delayed" if np.random.random() < 0.5 else "Down"
    else:
        traffic = np.random.uniform(1, 60)
        health = "Normal"
    latency = np.random.uniform(0.1, 10)
    return {"type": traffic_type, "volume": traffic, "health": health, "latency": latency}

# کلاس بلاک برای ریل‌تایم
class RealTimeBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_level="Low"):
        self.timestamp = timestamp.isoformat()
        self.node_id = node_id
        self.traffic_layer = traffic_layer
        self.health_layer = health_layer
        self.previous_hash = previous_hash
        self.congestion_level = congestion_level
        self.congestion_score = 0.0
        self.congestion_impact = 0.0
        self.traffic_suggestion = "None"
        self.order_type = "Standard"
        self.signature = None
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "traffic_layer": self.traffic_layer,
            "health_layer": self.health_layer,
            "previous_hash": self.previous_hash,
            "congestion_level": self.congestion_level,
            "congestion_score": self.congestion_score,
            "congestion_impact": self.congestion_impact,
            "traffic_suggestion": self.traffic_suggestion,
            "order_type": self.order_type
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def sign_block(self, private_key):
        try:
            message = self.hash.encode()
            self.signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception as e:
            logger.error(f"Signing failed for {self.node_id}: {e}")
            return False

# تولید پیشنهادات ترافیک
def generate_traffic_suggestion(traffic_type, congestion_level):
    if traffic_type == "Priority":
        return "Fast-track Priority traffic, allocate maximum resources to critical nodes"
    elif congestion_level in ["Medium", "High"]:
        if traffic_type == "Stream":
            return "Reduce Stream traffic by 20% or prioritize critical nodes"
        elif traffic_type == "Game":
            return "Reduce Game traffic by 20% or prioritize critical nodes"
    return "NULL"

# ذخیره بلاک ریل‌تایم در دیتابیس
def save_real_time_block(block, output_db):
    try:
        conn = sqlite3.connect(output_db)
        c = conn.cursor()
        c.execute("INSERT INTO real_time_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
                   block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
                   block.congestion_level, block.congestion_score, block.congestion_impact,
                   block.traffic_suggestion, block.order_type, block.signature.hex() if block.signature else None))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error saving real-time block: {e}")

# پیش‌بینی تراکم با مدل ML
async def predict_congestion(block, model, le_node_id, le_traffic_type, le_network_health):
    try:
        data = pd.DataFrame([{
            "node_id": block.node_id,
            "traffic_volume": block.traffic_layer["volume"],
            "latency": block.health_layer["latency"],
            "network_health": block.health_layer["status"],
            "traffic_type": block.traffic_layer["type"]
        }])
        for column in ["node_id", "traffic_type", "network_health"]:
            known_values = set(eval(f"le_{column}").classes_)
            if data[column].iloc[0] not in known_values:
                logger.warning(f"Unknown value for {column}: {data[column].iloc[0]}. Using default value.")
                data[column] = list(known_values)[0]
            data[column] = eval(f"le_{column}").transform([data[column].iloc[0]])[0]
        features = data[["node_id", "traffic_volume", "latency", "network_health", "traffic_type"]]
        prediction = model.predict(features)[0]
        score = model.decision_function(features)[0]
        
        # تبدیل پیش‌بینی به سطح تراکم
        if prediction == -1:
            if score < -0.1:
                predicted_level = "High"
            else:
                predicted_level = "Medium"
        else:
            predicted_level = "Low"
        
        # تنظیم مقادیر congestion_score و congestion_impact
        block.congestion_score = abs(score)
        block.congestion_impact = abs(score) * random.uniform(0.8, 1.2)  # شبیه‌سازی تأثیر
        return predicted_level
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return block.congestion_level

# تابع ریل‌تایم برای پردازش بلاک‌های جدید
async def real_time_processing():
    logger.info("Starting real-time traffic processing...")
    try:
        model = joblib.load(RESULT_DIR / "congestion_model.pkl")
        encoders = joblib.load(RESULT_DIR / "encoders.pkl")
        le_node_id = encoders["node_id"]
        le_traffic_type = encoders["traffic_type"]
        le_network_health = encoders["network_health"]
    except FileNotFoundError as e:
        logger.error(f"Failed to load model or encoders: {e}")
        return

    output_db = RESULT_DIR / "real_time_orders.db"
    
    # اطمینان از وجود جدول
    try:
        conn = sqlite3.connect(output_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS real_time_orders
                     (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, 
                      network_health TEXT, latency REAL, previous_hash TEXT, block_hash TEXT, 
                      congestion_level TEXT, congestion_score REAL, congestion_impact REAL, 
                      traffic_suggestion TEXT, order_type TEXT, signature TEXT)''')
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error initializing real_time_orders table: {e}")
        conn.close()
        return
    finally:
        conn.close()

    # گرفتن previous_hash
    try:
        conn = sqlite3.connect(output_db)
        c = conn.cursor()
        c.execute("SELECT block_hash FROM real_time_orders ORDER BY timestamp DESC LIMIT 1")
        result = c.fetchone()
        previous_hash = result[0] if result else "0"
        conn.close()
        logger.info(f"Starting real-time processing with previous_hash: {previous_hash}")
    except sqlite3.Error as e:
        logger.error(f"Error fetching previous hash: {e}")
        previous_hash = "0"

    while True:
        try:
            timestamp = datetime.now()
            for node_id in nodes:
                if node_id == "Genesis":
                    continue
                traffic_data = simulate_traffic(node_id, timestamp)
                block = RealTimeBlock(timestamp, node_id, traffic_data, 
                                    {"status": traffic_data["health"], "latency": traffic_data["latency"]}, 
                                    previous_hash)
                block.sign_block(node_keys[node_id])
                congestion_level = await predict_congestion(block, model, le_node_id, le_traffic_type, le_network_health)
                block.congestion_level = congestion_level
                block.order_type = "Priority" if traffic_data["type"] == "Priority" else "Standard"
                block.traffic_suggestion = generate_traffic_suggestion(traffic_data["type"], congestion_level)
                save_real_time_block(block, output_db)
                previous_hash = block.hash
                logger.info(f"Processed real-time block for {node_id}: {traffic_data['volume']:.2f} MB/s, Congestion: {congestion_level}, Suggestion: {block.traffic_suggestion}")
            await asyncio.sleep(1)  # هر ثانیه بلاک جدید
        except Exception as e:
            logger.error(f"Error in real-time processing: {e}")
            await asyncio.sleep(5)

# اجرای پایپ‌لاین اولیه
def run_pipeline(demo=False):
    logger.info("Starting Network Traffic Congestion Management with AI and Blockchain...")
    start_time = datetime.now()
    ensure_result_dir()
    
    if demo:
        logger.info("Running in DEMO mode with reduced data")
        os.environ["DEMO_MODE"] = "True"

    steps = [
        ("Step 1: Initializing blockchain data...", run_initial_data, None),
        ("Step 2: Detecting congestion...", run_congestion, None),
        ("Step 3: Managing traffic...", run_managed_traffic, RESULT_DIR / "traffic_data.db"),
        ("Step 4: Processing new orders...", run_new_orders, RESULT_DIR / "managed_traffic.db"),
        ("Step 5: Processing real-time orders...", run_real_time_orders, RESULT_DIR / "new_orders.db"),
        ("Step 6: Preparing traffic data...", run_data_preparation, RESULT_DIR / "new_orders.db"),
        ("Step 7: Training machine learning model...", run_model_training, RESULT_DIR / "new_orders.db"),
        ("Step 8: Generating advanced traffic report...", run_advanced_report, RESULT_DIR / "managed_traffic.db"),
        ("Step 9: Managing smart traffic...", run_smart_traffic, RESULT_DIR / "congestion_model.pkl"),
        ("Step 10: Self-healing network...", run_self_healing, RESULT_DIR / "smart_traffic.db"),
        ("Step 11: Optimizing resources...", run_resource_optimization, RESULT_DIR / "self_healing.db"),
        ("Step 12: Predictive analysis and anomaly detection...", run_predictive_analysis, RESULT_DIR / "congestion_model.pkl"),
    ]

    for step_message, step_function, required_file in steps:
        try:
            if required_file and not check_file_exists(required_file, step_message):
                continue
            logger.info(step_message)
            result = step_function()
            logger.info(f"Result: {result['summary']}")
        except Exception as e:
            logger.error(f"Error in {step_message}: {e}")
            if demo:
                logger.info("Continuing in DEMO mode despite error...")
                continue
            else:
                sys.exit(1)

    end_time = datetime.now()
    logger.info(f"Initial pipeline completed in {end_time - start_time}")
    
    if demo:
        logger.info("Generating demo summary plot...")
        plot_summary()

# تابع اصلی
def main():
    demo = "--demo" in sys.argv
    run_pipeline(demo=demo)
    
    # شروع پردازش ریل‌تایم
    loop = asyncio.get_event_loop()
    loop.run_until_complete(real_time_processing())

if __name__ == "__main__":
    main()