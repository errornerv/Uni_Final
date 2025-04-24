import hashlib
import os
import logging
import sqlite3
import json
import random
import time
from tqdm import tqdm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import sys

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# تنظیمات لاج‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# مسیر دیتابیس
current_dir = os.path.dirname(os.path.abspath(__file__))
start_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
input_db = os.path.join(start_dir, "result", "new_orders.db")
output_db = os.path.join(start_dir, "result", "real_time_orders.db")

# گراف نودها
nodes = [f"Node_{i}" for i in range(1, 11)] + ["Genesis"]
graph = {node: {"neighbors": random.sample(nodes, random.randint(1, 3)), 
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]} 
         for node in nodes}

# تولید کلیدهای ECDSA
node_keys = {node: ec.generate_private_key(ec.SECP256R1(), default_backend()) for node in nodes}
node_public_keys = {node: key.public_key() for node, key in node_keys.items()}

# دیتابیس خروجی
def init_db():
    result_dir = os.path.dirname(output_db)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS real_time_orders
                 (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                  latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT, congestion_score REAL,
                  latency_impact REAL, traffic_suggestion TEXT, order_type TEXT, signature TEXT)''')
    conn.commit()
    conn.close()
    print(f"Output database initialized at {output_db}")

def save_to_db(block):
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute("INSERT INTO real_time_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
               block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
               block.congestion_layer["level"], block.congestion_layer["score"], block.congestion_layer["impact"],
               block.traffic_suggestion, block.order_type, block.signature.hex() if block.signature else None))
    conn.commit()
    conn.close()

# کلاس بلاک
class TrafficBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_layer, traffic_suggestion=None, order_type=None, signature=None):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_layer = traffic_layer
        self.health_layer = health_layer
        self.previous_hash = previous_hash
        self.congestion_layer = congestion_layer
        self.traffic_suggestion = traffic_suggestion
        self.order_type = order_type
        self.hash = self.calculate_hash()
        self.signature = signature

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "traffic_layer": self.traffic_layer,
            "health_layer": self.health_layer,
            "previous_hash": self.previous_hash,
            "congestion_layer": self.congestion_layer,
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
            logging.error(f"Signing failed for {self.node_id}: {e}")
            return False

    def verify_signature(self, public_key):
        try:
            if not self.signature:
                logging.error(f"No signature found for block {self.node_id}")
                return False
            public_key.verify(self.signature, self.hash.encode(), ec.ECDSA(hashes.SHA256()))
            return True
        except Exception as e:
            logging.error(f"Signature verification failed for {self.node_id}: {e}")
            return False

    def suggest_traffic_management(self):
        if self.congestion_layer["is_congested"] == 1:
            traffic_type = self.traffic_layer["type"]
            volume = self.traffic_layer["volume"]
            health = self.health_layer["status"]
            neighbors = graph[self.node_id]["neighbors"]

            if self.order_type == "Priority":
                return f"Fast-track {traffic_type} traffic, allocate maximum resources to {self.node_id}"
            elif volume > 70:
                return f"Redirect {traffic_type} traffic to {random.choice(neighbors)} or limit bandwidth by 50%"
            elif health == "Down":
                return f"Increase monitoring for {traffic_type}, reroute to {random.choice(neighbors)}"
            elif health == "Delayed":
                return f"Optimize {traffic_type} routing, reduce load by 30%"
            else:
                return f"Reduce {traffic_type} traffic by 20% or prioritize critical nodes"
        return None

# کلاس بلاک‌چین
class TrafficBlockchain:
    def __init__(self):
        self.chain = []
        self.cache = {}
        self.load_from_db()

    def load_from_db(self):
        conn = sqlite3.connect(input_db)
        c = conn.cursor()
        c.execute("SELECT * FROM new_orders")
        rows = c.fetchall()
        # مرتب‌سازی برای اولویت دادن به بلاک‌های Priority
        priority_blocks = [row for row in rows if row[12] == "Priority"]
        standard_blocks = [row for row in rows if row[12] != "Priority"]
        sorted_rows = priority_blocks + standard_blocks
        for row in tqdm(sorted_rows, desc="Loading blocks from DB", file=sys.stdout):
            traffic_layer = {"volume": row[3], "type": row[2]}
            health_layer = {"status": row[4], "latency": row[5]}
            congestion_layer = {"is_congested": 1 if row[8] in ["Medium", "High"] else 0, 
                               "score": row[9], "impact": row[10], "level": row[8]}
            traffic_suggestion = row[11]
            order_type = row[12]
            signature = bytes.fromhex(row[13]) if len(row) > 13 and row[13] else None
            block = TrafficBlock(row[0], row[1], traffic_layer, health_layer, row[6], congestion_layer, 
                                traffic_suggestion, order_type, signature)
            block.hash = row[7]
            if not block.signature:  # برای بلاک‌های قدیمی بدون امضا
                block.sign_block(node_keys[row[1]])
            self.chain.append(block)
            if row[1] not in self.cache:
                self.cache[row[1]] = []
            self.cache[row[1]].append(block)
            if len(self.cache[row[1]]) > 4:
                self.cache[row[1]].pop(0)
            tqdm.write(f"Loaded block for Node {row[1]} at {row[0]}")
        conn.close()
        print(f"Loaded {len(rows)} blocks from {input_db}")

    def add_real_time_block(self, block):
        suggestion = block.suggest_traffic_management()
        order_type = block.order_type
        new_block = TrafficBlock(block.timestamp, block.node_id, block.traffic_layer, block.health_layer,
                                 block.previous_hash, block.congestion_layer, suggestion, order_type)
        new_block.sign_block(node_keys[block.node_id])  # امضای بلاک جدید
        if not new_block.verify_signature(node_public_keys[block.node_id]):
            logging.error(f"Invalid signature for block {new_block.node_id}, block discarded")
            return False
        self.chain.append(new_block)
        if block.node_id not in self.cache:
            self.cache[block.node_id] = []
        self.cache[block.node_id].append(new_block)
        if len(self.cache[block.node_id]) > 4:
            self.cache[block.node_id].pop(0)
        save_to_db(new_block)
        # شبیه‌سازی تأخیر بلادرنگ
        delay = 0.05 if order_type == "Priority" else 0.1
        time.sleep(delay)
        return True

    def generate_report(self):
        priority_orders = 0
        total_congested = 0
        real_time_blocks = 0

        conn = sqlite3.connect(output_db)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM real_time_orders WHERE order_type = 'Priority'")
        priority_orders = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM real_time_orders WHERE congestion_level IN ('Medium', 'High')")
        total_congested = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM real_time_orders")
        real_time_blocks = c.fetchone()[0]
        conn.close()

        print("\nReal-Time Orders Report:")
        print(f"Total Real-Time Blocks Processed: {real_time_blocks}")
        print(f"Total Priority Orders: {priority_orders}")
        print(f"Total Congested Points: {total_congested}")

# اجرا
init_db()
traffic_blockchain = TrafficBlockchain()
total_blocks = len(traffic_blockchain.chain[1:])
for idx, block in enumerate(tqdm(traffic_blockchain.chain[1:], desc="Processing Real-Time Orders", file=sys.stdout)):
    traffic_blockchain.add_real_time_block(block)
    tqdm.write(f"Processed {idx + 1}/{total_blocks} blocks - Node: {block.node_id}, Order Type: {block.order_type}, Delay: {0.05 if block.order_type == 'Priority' else 0.1}s")
traffic_blockchain.generate_report()