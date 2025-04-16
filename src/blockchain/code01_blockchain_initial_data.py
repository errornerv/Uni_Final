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
time_steps = 400
start_time = datetime(2025, 2, 27, 7, 0, 0)
congestion_prob = 0.15

# گراف نودها
nodes = [f"Node_{i}" for i in range(1, num_nodes + 1)]
graph = {}
for node in nodes:
    neighbors = random.sample(nodes, random.randint(1, 3))  # 1 تا 3 همسایه تصادفی
    weights = [random.uniform(1, 5) for _ in neighbors]  # وزن تصادفی (تأخیر)
    graph[node] = {"neighbors": neighbors, "weights": weights}

# تولید کلیدهای ECDSA
node_keys = {node: ec.generate_private_key(ec.SECP256R1(), default_backend()) for node in nodes}
node_public_keys = {node: key.public_key() for node, key in node_keys.items()}

# دیتابیس SQLite
current_dir = os.path.dirname(os.path.abspath(__file__))
start_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))  # به دایرکتوری start/ بروید
db_file = os.path.join(start_dir, "result", "traffic_data.db")

def init_db():
    # اطمینان از وجود پوشه result
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

# کلاس بلاک با انواع ترافیک
class Block:
    def __init__(self, timestamp, node_id, traffic_type, traffic_volume, network_health, latency, previous_hash, nonce=0):
        self.timestamp = timestamp  # datetime
        self.node_id = node_id
        self.traffic_type = traffic_type  # نوع ترافیک اضافه شده
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

# کلاس بلاک‌چین با کش
class Blockchain:
    def __init__(self):
        self.chain = []
        self.cache = {"latest_hash": "0"}  # کش برای previous_hash
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
        hash_value = int(hashlib.sha256(f"{node_id}{self.cache['latest_hash']}{time.time()}".encode()).hexdigest(), 16)
        return hash_value % 1 == 0

    def add_block(self, block, node_id):
        start_time = time.time()
        nonce = 0
        while not self.proof_of_stake(node_id):
            nonce += 1
            block.nonce = nonce
            block.hash = block.calculate_hash()
            if time.time() - start_time > 5:
                print(f"Timeout for block at {block.timestamp} for {node_id}")
                return False
        if block.sign_block(node_keys[node_id]):
            if block.previous_hash == self.cache["latest_hash"]:
                self.chain.append(block)
                save_to_db(block)
                self.cache["latest_hash"] = block.hash  # به‌روزرسانی کش
                return True
        return False

# توابع تقسیم‌شده برای شبیه‌سازی و تولید بلاک
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
init_db()  # مقداردهی اولیه دیتابیس
blockchain = Blockchain()

# ایجاد لیست از تمام زمان‌ها و نودها به صورت تصادفی
tasks = [(t, node) for t in range(time_steps) for node in nodes]
random.shuffle(tasks)

# اضافه کردن نوار پیشرفت به حلقه
total_tasks = len(tasks)
for idx, (t, node) in enumerate(tqdm(tasks, desc="Processing blocks", file=sys.stdout)):
    timestamp = start_time + timedelta(seconds=t * 5)
    traffic_data = simulate_traffic(node, timestamp)
    previous_hash = blockchain.cache["latest_hash"]
    block = create_block(traffic_data, previous_hash, node)
    if blockchain.add_block(block, node):
        # چاپ پیشرفت به صورت خط جدید
        tqdm.write(f"Processed {idx + 1}/{total_tasks} blocks - Node: {node}, Traffic: {traffic_data['volume']:.2f} MB/s")

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