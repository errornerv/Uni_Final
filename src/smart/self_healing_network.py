import os
import random
import hashlib
import time
from datetime import datetime
import sqlite3
import json
import logging
import sys
from utils.db_utils import init_db, save_to_db

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# تنظیمات لاج‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# مسیر دیتابیس
current_dir = os.path.dirname(os.path.abspath(__file__))
start_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))  # به دایرکتوری start/ بروید
db_file = os.path.join(start_dir, "result", "self_healing.db")

# گراف نودها
nodes = [f"Node_{i}" for i in range(1, 11)]
graph = {node: {"neighbors": random.sample(nodes, random.randint(1, 3)), 
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]} 
         for node in nodes}

# وضعیت نودها
node_status = {node: {"max_capacity": 100, "current_traffic": 0, "active": True} for node in nodes}

# دیتابیس SQLite
def init_db():
    # اطمینان از وجود پوشه result
    result_dir = os.path.dirname(db_file)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS healing_network
                 (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                  latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT, 
                  traffic_redistribution TEXT, event_type TEXT, healing_action TEXT)''')
    conn.commit()
    conn.close()

def save_to_db(block):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("INSERT INTO healing_network VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
               block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
               block.congestion_level, block.traffic_redistribution, block.event_type, block.healing_action))
    conn.commit()
    conn.close()

# کلاس بلاک
class HealingBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_level, 
                 traffic_redistribution=None, event_type="Normal", healing_action="None"):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_layer = traffic_layer
        self.health_layer = health_layer
        self.previous_hash = previous_hash
        self.congestion_level = congestion_level
        self.traffic_redistribution = traffic_redistribution or "None"
        self.event_type = event_type
        self.healing_action = healing_action
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.timestamp, "node_id": self.node_id, "traffic_layer": self.traffic_layer,
            "health_layer": self.health_layer, "previous_hash": self.previous_hash,
            "congestion_level": self.congestion_level, "traffic_redistribution": self.traffic_redistribution,
            "event_type": self.event_type, "healing_action": self.healing_action
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# تولید داده‌های شبیه‌سازی‌شده
def generate_simulated_traffic():
    node_id = random.choice(nodes)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    traffic_types = ["Data", "Stream", "Game"]
    traffic_type = random.choice(traffic_types)
    event_type = "Normal"

    # قطعی شبکه
    if random.random() < 0.05 and node_status[node_id]["active"]:
        node_status[node_id]["active"] = False
        event_type = "Outage"
        traffic_volume = 0
        latency = 0
        network_health = "Down"
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

    if traffic_volume > 70:
        congestion_level = "High"
    elif traffic_volume > 40:
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

# اضافه کردن بلاک با ترمیم
def add_block(prev_hash):
    traffic_data = generate_simulated_traffic()
    node_id = traffic_data["node_id"]
    traffic_volume = traffic_data["traffic_layer"]["volume"]
    healing_action = "None"

    # ترمیم نود غیرفعال
    if not node_status[node_id]["active"] and random.random() < 0.10:  # 10% احتمال ترمیم
        node_status[node_id]["active"] = True
        healing_action = "Node reactivated"
        traffic_volume = random.uniform(0, 60)  # ترافیک اولیه بعد از ترمیم
        traffic_data["traffic_layer"]["volume"] = traffic_volume
        traffic_data["health_layer"]["status"] = "Normal"
        traffic_data["health_layer"]["latency"] = random.uniform(0, 10)
        traffic_data["congestion_level"] = "Low" if traffic_volume <= 40 else "Medium" if traffic_volume <= 70 else "High"

    if node_status[node_id]["active"]:
        node_status[node_id]["current_traffic"] = traffic_volume
    else:
        node_status[node_id]["current_traffic"] = 0
    
    redistribution = "None"
    if traffic_data["congestion_level"] in ["Medium", "High"] and node_status[node_id]["active"]:
        max_capacity = node_status[node_id]["max_capacity"]
        if traffic_volume > max_capacity:
            excess_traffic = traffic_volume - max_capacity
            redistribution = redistribute_traffic(node_id, excess_traffic)
            node_status[node_id]["current_traffic"] = max_capacity

    block = HealingBlock(traffic_data["timestamp"], node_id, traffic_data["traffic_layer"],
                         traffic_data["health_layer"], prev_hash, traffic_data["congestion_level"], 
                         redistribution, traffic_data["event_type"], healing_action)
    save_to_db(block)
    return block

# مانیتورینگ خود-ترمیم
def healing_monitoring():
    init_db()
    last_time = time.time()
    cache = {"prev_hash": "0"}

    for node in nodes:
        node_status[node]["current_traffic"] = 0
        node_status[node]["active"] = True

    while True:
        try:
            current_time = time.time()
            if current_time - last_time >= 1:
                block = add_block(cache["prev_hash"])
                cache["prev_hash"] = block.hash

                print(f"\nNew block added at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:")
                print(f"Node: {block.node_id}, Traffic: {block.traffic_layer['volume']:.2f} MB/s, "
                      f"Health: {block.health_layer['status']}, Congestion: {block.congestion_level}, "
                      f"Redistribution: {block.traffic_redistribution}, Event: {block.event_type}, "
                      f"Healing: {block.healing_action}")
                last_time = current_time

        except KeyboardInterrupt:
            logging.info("مانیتورینگ متوقف شد.")
            break
        except Exception as e:
            logging.error(f"خطا در مانیتورینگ: {e}")
            time.sleep(1)

if __name__ == "__main__":
    healing_monitoring()