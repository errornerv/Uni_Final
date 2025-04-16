import os
import random
import hashlib
import time
from datetime import datetime
import sqlite3
import json
import logging
import sys

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# تنظیمات لاج‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# مسیر دیتابیس
current_dir = os.path.dirname(os.path.abspath(__file__))
start_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))  # به دایرکتوری start/ بروید
db_file = os.path.join(start_dir, "result", "smart_traffic.db")

# گراف نودها
nodes = [f"Node_{i}" for i in range(1, 11)]
graph = {node: {"neighbors": random.sample(nodes, random.randint(1, 3)), 
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]} 
         for node in nodes}

# وضعیت نودها
node_status = {node: {"max_capacity": 100, "current_traffic": 0, "active": True} for node in nodes}

# آستانه‌های پویا
thresholds = {"medium": 40, "high": 70}

# دیتابیس SQLite
def init_db():
    # اطمینان از وجود پوشه result
    result_dir = os.path.dirname(db_file)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS smart_traffic
                 (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                  latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT, 
                  traffic_redistribution TEXT, event_type TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS optimization_log
                 (timestamp TEXT, medium_threshold REAL, high_threshold REAL, high_blocks INTEGER)''')
    conn.commit()
    conn.close()

def save_to_db(block):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("INSERT INTO smart_traffic VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
               block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
               block.congestion_level, block.traffic_redistribution, block.event_type))
    conn.commit()
    conn.close()

def save_optimization_log(timestamp, medium_threshold, high_threshold, high_blocks):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("INSERT INTO optimization_log VALUES (?, ?, ?, ?)",
              (timestamp, medium_threshold, high_threshold, high_blocks))
    conn.commit()
    conn.close()

# کلاس بلاک
class SmartTrafficBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_level, 
                 traffic_redistribution=None, event_type="Normal"):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_layer = traffic_layer
        self.health_layer = health_layer
        self.previous_hash = previous_hash
        self.congestion_level = congestion_level
        self.traffic_redistribution = traffic_redistribution or "None"
        self.event_type = event_type
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.timestamp, "node_id": self.node_id, "traffic_layer": self.traffic_layer,
            "health_layer": self.health_layer, "previous_hash": self.previous_hash,
            "congestion_level": self.congestion_level, "traffic_redistribution": self.traffic_redistribution,
            "event_type": self.event_type
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# تولید داده‌های شبیه‌سازی‌شده با سناریوها
def generate_simulated_traffic():
    node_id = random.choice(nodes)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    traffic_types = ["Data", "Stream", "Game"]
    traffic_type = random.choice(traffic_types)
    event_type = "Normal"

    if random.random() < 0.05 and node_status[node_id]["active"]:
        node_status[node_id]["active"] = False
        event_type = "Outage"
        traffic_volume = 0
        latency = 0
        network_health = "Down"
    elif random.random() < 0.02 and node_status[node_id]["active"]:
        event_type = "DDoS"
        traffic_volume = random.uniform(300, 500)
        latency = random.uniform(20, 50)
        network_health = "Delayed"
    else:
        hour = datetime.now().hour + datetime.now().minute / 60
        peak_prob = 0.3 if 8 <= hour < 18 else 0.05
        if node_status[node_id]["active"]:
            if random.random() < peak_prob:
                traffic_volume = random.uniform(80, 200)
                latency = random.uniform(5, 30)
                network_health = "Delayed" if random.random() < 0.5 else "Down"
            else:
                traffic_volume = random.uniform(0, 60)
                latency = random.uniform(0, 10)
                network_health = "Normal"
        else:
            traffic_volume = 0
            latency = 0
            network_health = "Down"

    if traffic_volume > thresholds["high"]:
        congestion_level = "High"
    elif traffic_volume > thresholds["medium"]:
        congestion_level = "Medium"
    else:
        congestion_level = "Low"

    return {"timestamp": timestamp, "node_id": node_id, "traffic_layer": {"type": traffic_type, "volume": traffic_volume},
            "health_layer": {"status": network_health, "latency": latency}, "congestion_level": congestion_level,
            "event_type": event_type}

# پخش ترافیک هوشمند
def redistribute_traffic(node_id, excess_traffic):
    neighbors = graph[node_id]["neighbors"]
    available_neighbors = [n for n in neighbors if node_status[n]["active"] and 
                           node_status[n]["current_traffic"] + excess_traffic / len(neighbors) <= node_status[n]["max_capacity"]]
    
    if not available_neighbors:
        return "No available neighbors"

    split_traffic = excess_traffic / len(available_neighbors)
    redistribution = []
    for neighbor in available_neighbors:
        node_status[neighbor]["current_traffic"] += split_traffic
        redistribution.append(f"{split_traffic:.2f} MB/s to {neighbor}")
    
    return ", ".join(redistribution)

# اضافه کردن بلاک
def add_block(prev_hash):
    traffic_data = generate_simulated_traffic()
    node_id = traffic_data["node_id"]
    traffic_volume = traffic_data["traffic_layer"]["volume"]
    
    if node_status[node_id]["active"]:
        node_status[node_id]["current_traffic"] = traffic_volume
    else:
        node_status[node_id]["current_traffic"] = 0
    
    congestion_level = traffic_data["congestion_level"]
    redistribution = "None"

    if congestion_level in ["Medium", "High"] and node_status[node_id]["active"]:
        max_capacity = node_status[node_id]["max_capacity"]
        if traffic_volume > max_capacity:
            excess_traffic = traffic_volume - max_capacity
            if traffic_data["event_type"] == "DDoS":
                limited_traffic = max_capacity
                excess_traffic = traffic_volume - limited_traffic
                redistribution = f"Limited to {limited_traffic:.2f} MB/s, {excess_traffic:.2f} redistributed: {redistribute_traffic(node_id, excess_traffic)}"
                node_status[node_id]["current_traffic"] = limited_traffic
            else:
                redistribution = redistribute_traffic(node_id, excess_traffic)
                node_status[node_id]["current_traffic"] = max_capacity

    block = SmartTrafficBlock(traffic_data["timestamp"], node_id, traffic_data["traffic_layer"],
                              traffic_data["health_layer"], prev_hash, congestion_level, redistribution, 
                              traffic_data["event_type"])
    save_to_db(block)
    return block

# بهینه‌سازی آستانه‌ها
def optimize_thresholds(history):
    global thresholds
    if len(history) < 100:
        return

    threshold_pairs = [(30, 60), (40, 70), (50, 80)]
    best_high_count = float('inf')
    best_pair = (thresholds["medium"], thresholds["high"])

    for medium, high in threshold_pairs:
        high_count = sum(1 for block in history if block.traffic_layer["volume"] > high)
        if high_count < best_high_count:
            best_high_count = high_count
            best_pair = (medium, high)

    thresholds["medium"], thresholds["high"] = best_pair
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    save_optimization_log(timestamp, thresholds["medium"], thresholds["high"], best_high_count)
    print(f"Thresholds updated: Medium={thresholds['medium']}, High={thresholds['high']}, High Blocks={best_high_count}")

# مانیتورینگ هوشمند
def smart_monitoring():
    init_db()
    last_time = time.time()
    cache = {"prev_hash": "0"}
    block_history = []

    for node in nodes:
        node_status[node]["current_traffic"] = 0
        node_status[node]["active"] = True

    while True:
        try:
            current_time = time.time()
            if current_time - last_time >= 1:
                block = add_block(cache["prev_hash"])
                cache["prev_hash"] = block.hash
                block_history.append(block)

                print(f"\nNew block added at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:")
                print(f"Node: {block.node_id}, Traffic: {block.traffic_layer['volume']:.2f} MB/s, "
                      f"Health: {block.health_layer['status']}, Congestion: {block.congestion_level}, "
                      f"Redistribution: {block.traffic_redistribution}, Event: {block.event_type}")

                if len(block_history) >= 100:
                    optimize_thresholds(block_history[-100:])
                    block_history = block_history[-100:]

                last_time = current_time

        except KeyboardInterrupt:
            logging.info("مانیتورینگ متوقف شد.")
            break
        except Exception as e:
            logging.error(f"خطا در مانیتورینگ: {e}")
            time.sleep(1)

if __name__ == "__main__":
    smart_monitoring()