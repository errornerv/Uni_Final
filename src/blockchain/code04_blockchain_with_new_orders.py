
import hashlib
import os
import logging
import sqlite3
import json
import random
from tqdm import tqdm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import sys
from pathlib import Path

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULT_DIR = ROOT_DIR / "result"
input_db = os.path.join(RESULT_DIR, "managed_traffic.db")
output_db = os.path.join(RESULT_DIR, "new_orders.db")

# تنظیمات لاگینگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS new_orders
                 (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                  latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT, congestion_score REAL,
                  latency_impact REAL, traffic_suggestion TEXT, order_type TEXT, signature TEXT)''')
    conn.commit()
    conn.close()
    print(f"Output database initialized at {output_db}")

def save_to_db(block):
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute("INSERT INTO new_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            if traffic_type == "Priority":
                return f"Prioritize {traffic_type} traffic, allocate maximum bandwidth to {self.node_id}"
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
        c.execute("SELECT * FROM managed_blocks")
        rows = c.fetchall()
        for row in tqdm(rows, desc="Loading blocks from DB", file=sys.stdout):
            traffic_layer = {"volume": row[3], "type": row[2]}
            health_layer = {"status": row[4], "latency": row[5]}
            congestion_layer = {"is_congested": 1 if row[8] in ["Medium", "High"] else 0, 
                               "score": row[9], "impact": row[10], "level": row[8]}
            traffic_suggestion = row[11]
            signature = bytes.fromhex(row[12]) if len(row) > 12 and row[12] else None
            order_type = "Priority" if row[8] in ["Medium", "High"] and random.random() < 0.3 else "Standard"
            if order_type == "Priority":
                traffic_layer["type"] = "Priority"
            block = TrafficBlock(row[0], row[1], traffic_layer, health_layer, row[6], congestion_layer, 
                                traffic_suggestion, order_type, signature)
            block.hash = row[7]
            if not block.signature:
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

    def add_ordered_block(self, block):
        suggestion = block.suggest_traffic_management()
        order_type = block.order_type
        new_block = TrafficBlock(block.timestamp, block.node_id, block.traffic_layer, block.health_layer,
                                 block.previous_hash, block.congestion_layer, suggestion, order_type)
        new_block.sign_block(node_keys[block.node_id])
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
        return True

# تابع اصلی
def main():
    block_limit = 100 if os.getenv("DEMO_MODE") == "True" else None
    init_db()
    traffic_blockchain = TrafficBlockchain()
    total_blocks = len(traffic_blockchain.chain[1:]) if not block_limit else min(block_limit, len(traffic_blockchain.chain[1:]))
    for idx, block in enumerate(tqdm(traffic_blockchain.chain[1:total_blocks + 1] if block_limit else traffic_blockchain.chain[1:], desc="Processing Orders", file=sys.stdout)):
        traffic_blockchain.add_ordered_block(block)
        tqdm.write(f"Processed {idx + 1}/{total_blocks} blocks - Node: {block.node_id}, Order Type: {block.order_type}")
    # گزارش خلاصه
    priority_orders = 0
    congested_nodes = {}
    total_congested = 0
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM new_orders WHERE order_type = 'Priority'")
    priority_orders = c.fetchone()[0]
    c.execute("SELECT node_id, COUNT(*) FROM new_orders WHERE congestion_level IN ('Medium', 'High') GROUP BY node_id")
    for row in c.fetchall():
        congested_nodes[row[0]] = row[1]
        total_congested += row[1]
    conn.close()
    print("\nNew Orders Report:")
    print(f"Total Priority Orders: {priority_orders}")
    print(f"Total Congested Points: {total_congested}")
    print("Congested Nodes Distribution:")
    for node, count in congested_nodes.items():
        print(f"Node {node}: {count} congested points")
