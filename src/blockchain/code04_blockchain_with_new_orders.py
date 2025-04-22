import os
import random
import hashlib
from datetime import datetime, timedelta
import logging
import sqlite3
import json
from tqdm import tqdm
import sys
from utils.db_utils import init_db, save_to_db

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# تنظیمات لاج‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# مسیر دیتابیس
current_dir = os.path.dirname(os.path.abspath(__file__))
start_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))  # به دایرکتوری start/ بروید
input_db = os.path.join(start_dir, "result", "managed_traffic.db")
output_db = os.path.join(start_dir, "result", "new_orders.db")

# گراف نودها
nodes = [f"Node_{i}" for i in range(1, 11)]
graph = {node: {"neighbors": random.sample(nodes, random.randint(1, 3)), 
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]} 
         for node in nodes}

# دیتابیس خروجی
def init_db():
    # اطمینان از وجود پوشه result
    result_dir = os.path.dirname(output_db)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS new_orders
                 (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                  latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT, congestion_score REAL,
                  latency_impact REAL, traffic_suggestion TEXT, is_congestion_order INTEGER)''')
    conn.commit()
    conn.close()
    print(f"Output database initialized at {output_db}")

def save_to_db(block):
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute("INSERT INTO new_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
               block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
               block.congestion_layer["level"], block.congestion_layer["score"], block.congestion_layer["impact"],
               block.traffic_suggestion, 1 if block.is_congestion_order else 0))
    conn.commit()
    conn.close()

# کلاس بلاک
class NewOrderBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_layer=None, 
                 traffic_suggestion=None, is_congestion_order=False):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_layer = traffic_layer
        self.health_layer = health_layer
        self.previous_hash = previous_hash
        self.congestion_layer = congestion_layer or {"is_congested": 0, "score": 0.0, "impact": 0.0, "level": "Low"}
        self.traffic_suggestion = traffic_suggestion
        self.is_congestion_order = is_congestion_order
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "traffic_layer": self.traffic_layer,
            "health_layer": self.health_layer,
            "previous_hash": self.previous_hash,
            "congestion_layer": self.congestion_layer,
            "traffic_suggestion": self.traffic_suggestion,
            "is_congestion_order": self.is_congestion_order
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# تولید سفارش جدید
def generate_new_order(previous_block):
    node_id = random.choice(nodes)
    timestamp = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    traffic_types = ["Data", "Stream", "Game"]
    traffic_type = random.choice(traffic_types)
    traffic_volume = random.uniform(0, 150)
    network_health = random.choice(["Normal", "Delayed", "Down"])
    latency = random.uniform(0, 10)

    # تحلیل چندمرحله‌ای
    if traffic_volume > 70:
        level = "High"
        is_congested = 1
    elif 40 <= traffic_volume <= 70:
        level = "Medium"
        is_congested = 1
    else:
        level = "Low"
        is_congested = 0

    congestion_score = random.uniform(0, 100) if is_congested else 0.0
    latency_impact = random.uniform(0, 10) if is_congested else 0.0
    traffic_layer = {"type": traffic_type, "volume": traffic_volume}
    health_layer = {"status": network_health, "latency": latency}
    congestion_layer = {"is_congested": is_congested, "score": congestion_score, "impact": latency_impact, "level": level}

    traffic_suggestion = None
    is_congestion_order = False
    if is_congested:
        neighbors = graph[node_id]["neighbors"]
        traffic_suggestion = f"Redirect {traffic_type} to {random.choice(neighbors)}" if neighbors else "Reduce load"
        is_congestion_order = True

    previous_hash = previous_block.hash if previous_block else "0"
    return NewOrderBlock(timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_layer, 
                         traffic_suggestion, is_congestion_order)

# اضافه کردن بلاک‌ها
def add_new_orders(num_orders=4000):
    conn = sqlite3.connect(input_db)
    c = conn.cursor()
    c.execute("SELECT * FROM managed_blocks ORDER BY timestamp DESC LIMIT 1")
    last_row = c.fetchone()
    conn.close()

    chain = []
    if last_row:
        traffic_layer = {"type": last_row[2], "volume": last_row[3]}
        health_layer = {"status": last_row[4], "latency": last_row[5]}
        congestion_layer = {"is_congested": 1 if last_row[8] in ["Medium", "High"] else 0, 
                           "score": last_row[9], "impact": last_row[10], "level": last_row[8]}
        previous_block = NewOrderBlock(last_row[0], last_row[1], traffic_layer, health_layer, last_row[6], 
                                       congestion_layer, last_row[11], last_row[8] in ["Medium", "High"])
        previous_block.hash = last_row[7]
    else:
        previous_block = None
        chain.append({"node_id": "Genesis", "hash": "0", "previous_hash": "0"})

    for idx in tqdm(range(num_orders), desc="Adding New Orders", file=sys.stdout):
        new_block = generate_new_order(previous_block)
        chain.append(new_block)
        save_to_db(new_block)
        previous_block = new_block
        tqdm.write(f"Added order {idx + 1}/{num_orders} - Node: {new_block.node_id}, Congestion: {new_block.congestion_layer['level']}")

    return chain

# اجرا
init_db()
updated_chain = add_new_orders(4000)

# نمایش نمونه
conn = sqlite3.connect(output_db)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM new_orders")
total_blocks = c.fetchone()[0]
conn.close()

print(f"\nTotal number of new orders: {total_blocks}")