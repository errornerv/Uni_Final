import hashlib
import json
import os
import time
from datetime import datetime, timedelta
import numpy as np
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import sqlite3
import random
from tqdm import tqdm
import sys

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# تنظیمات اولیه
np.random.seed(42)
num_nodes = 10
time_steps = 40  # برای حدود 400 بلاک
start_time = datetime(2025, 2, 27, 7, 0, 0)
congestion_prob = 0.15

# تعریف کلاس نود
class Node:
    def __init__(self, node_id, capacity):
        self.node_id = node_id
        self.capacity = capacity  # ظرفیت نود (مثلاً پهنای باند یا توان پردازش)
        self.history = 0  # تعداد بلاک‌های موفق اعتبارسنجی‌شده

    def update_history(self):
        """افزایش تاریخچه بعد از اعتبارسنجی موفق"""
        self.history += 1

# گراف نودها
nodes = [Node(f"Node_{i}", random.uniform(100, 1000)) for i in range(1, num_nodes + 1)]
graph = {}
for node in nodes:
    neighbors = random.sample([n.node_id for n in nodes], random.randint(1, 3))
    weights = [random.uniform(1, 5) for _ in neighbors]
    graph[node.node_id] = {"neighbors": neighbors, "weights": weights}

# تولید کلیدهای ECDSA
node_keys = {node.node_id: ec.generate_private_key(ec.SECP256R1(), default_backend()) for node in nodes}
node_public_keys = {node_id: key.public_key() for node_id, key in node_keys.items()}

# دیتابیس SQLite
current_dir = os.path.dirname(os.path.abspath(__file__))
start_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
db_file = os.path.join(start_dir, "result", "traffic_data.db")

def init_db():
    result_dir = os.path.dirname(db_file)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS blocks
                 (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL,
                  network_health TEXT, latency REAL, previous_hash TEXT, block_hash TEXT)''')
    conn.commit()
    conn.close()
    print(f"Database initialized at {db_file}")

def save_to_db(block):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (block.get_timestamp_str(), block.node_id, block.traffic_type, block.traffic_volume,
               block.network_health, block.latency, block.previous_hash, block.hash))
    conn.commit()
    conn.close()

# کلاس بلاک
class Block:
    def __init__(self, timestamp, node_id, traffic_type, traffic_volume, network_health, latency, previous_hash, nonce=0):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_type = traffic_type
        self.traffic_volume = traffic_volume
        self.network_health = network_health
        self.latency = latency
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()
        self.signature = None

    def get_timestamp_str(self):
        return self.timestamp.isoformat()

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.get_timestamp_str(),
            "node_id": self.node_id,
            "traffic_type": self.traffic_type,
            "traffic_volume": self.traffic_volume,
            "network_health": self.network_health,
            "latency": self.latency,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def sign_block(self, private_key):
        try:
            message = self.hash.encode()
            self.signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception as e:
            print(f"Signing failed for {self.node_id}: {e}")
            return False

# کلاس بلاک‌چین
class Blockchain:
    def __init__(self):
        self.chain = []
        self.cache = {"latest_hash": "0"}
        self.nodes = nodes  # اضافه کردن لیست نودها به بلاکچین
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(datetime(2025, 2, 27, 7, 0, 0), "Genesis", "Data", 0, "Normal", 0, "0")
        if genesis.sign_block(node_keys["Node_1"]):
            self.chain.append(genesis)
            save_to_db(genesis)
            self.cache["latest_hash"] = genesis.hash
            print("Genesis block created")

    def get_latest_block(self):
        return self.chain[-1]

    def proof_of_stake(self, node_id):
        """انتخاب اعتبارسنج با وزن‌دهی بر اساس ظرفیت و تاریخچه"""
        weights = [node.capacity + node.history * 10 for node in self.nodes]  # وزن = ظرفیت + 10 * تاریخچه
        total_weight = sum(weights)
        if total_weight == 0:
            return False
        selected_node = random.choices(self.nodes, weights=weights, k=1)[0]
        if selected_node.node_id == node_id:
            selected_node.update_history()  # به‌روزرسانی تاریخچه نود انتخاب‌شده
            return True
        return False

    def add_block(self, block, node_id):
        start_time = time.time()
        nonce = 0
        while not self.proof_of_stake(node_id):
            nonce += 1
            block.nonce = nonce
            block.hash = block.calculate_hash()  # اصلاح: استفاده از متد calculate_hash بلاک
            if time.time() - start_time > 5:
                print(f"Timeout for block at {block.timestamp} for {node_id}")
                return False
        if block.sign_block(node_keys[node_id]):
            if block.previous_hash == self.cache["latest_hash"]:
                self.chain.append(block)
                save_to_db(block)
                self.cache["latest_hash"] = block.hash
                return True
        return False

# توابع شبیه‌سازی و تولید بلاک
def simulate_traffic(node_id, timestamp):
    hour = timestamp.hour + timestamp.minute / 60
    peak_prob = 0.3 if 8 <= hour < 18 else 0.05
    traffic_types = ["Data", "Stream", "Game"]
    traffic_type = random.choice(traffic_types)

    if np.random.random() < (congestion_prob * peak_prob):
        traffic = np.random.uniform(80, 150)
        health = "Delayed" if np.random.random() < 0.5 else "Down"
    else:
        traffic = np.random.uniform(1, 60)
        health = "Normal"
    latency = np.random.uniform(0.1, 10)

    return {"type": traffic_type, "volume": traffic, "health": health, "latency": latency}

def create_block(traffic_data, previous_hash, node_id):
    return Block(
        datetime.now(), node_id, traffic_data["type"], traffic_data["volume"],
        traffic_data["health"], traffic_data["latency"], previous_hash
    )

# تولید داده‌ها
init_db()
blockchain = Blockchain()

tasks = [(t, node.node_id) for t in range(time_steps) for node in nodes]
random.shuffle(tasks)

total_tasks = len(tasks)
for idx, (t, node_id) in enumerate(tqdm(tasks, desc="Processing blocks", file=sys.stdout)):
    timestamp = start_time + timedelta(seconds=t * 5)
    traffic_data = simulate_traffic(node_id, timestamp)
    previous_hash = blockchain.cache["latest_hash"]
    block = create_block(traffic_data, previous_hash, node_id)
    if blockchain.add_block(block, node_id):
        tqdm.write(f"Processed {idx + 1}/{total_tasks} blocks - Node: {node_id}, Traffic: {traffic_data['volume']:.2f} MB/s")

# نمایش خلاصه
conn = sqlite3.connect(db_file)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM blocks WHERE traffic_volume > 70")
congested = c.fetchone()[0]
c.execute("SELECT AVG(traffic_volume) FROM blocks")
avg_traffic = c.fetchone()[0]
conn.close()

print("\nData Summary:")
print(f"Total Blocks: {len(blockchain.chain)}")
print(f"Congested Points (>70 MB/s): {congested}")
print(f"Average Traffic: {avg_traffic:.2f} MB/s")