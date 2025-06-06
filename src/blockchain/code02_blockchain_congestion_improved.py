import hashlib
import os
import numpy as np
from tqdm import tqdm
import logging
from datetime import datetime
import sqlite3
import json
from concurrent.futures import ThreadPoolExecutor
import time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import sys
import random
from pathlib import Path

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULT_DIR = ROOT_DIR / "result"
input_db = os.path.join(RESULT_DIR, "traffic_data.db")
output_db = os.path.join(RESULT_DIR, "congestion_data.db")

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

# مقداردهی دیتابیس خروجی
def init_db():
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS congestion_blocks
                 (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                  latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT,
                  congestion_score REAL, latency_impact REAL, signature TEXT)''')
    conn.commit()
    conn.close()
    print(f"Output database initialized at {output_db}")

def save_to_db(block, retries=5, delay=1):
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(output_db)
            c = conn.cursor()
            c.execute("INSERT INTO congestion_blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
                       block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
                       block.congestion_layer["level"], block.congestion_layer["score"], block.congestion_layer["impact"],
                       block.signature.hex() if block.signature else None))
            conn.commit()
            conn.close()
            break
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e):
                logging.warning(f"Database is locked, retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logging.error(f"Database error: {e}")
                break

# کلاس بلاک با لایه‌ها
class Block:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_layer=None, signature=None):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_layer = traffic_layer
        self.health_layer = health_layer
        self.previous_hash = previous_hash
        self.congestion_layer = congestion_layer or {"is_congested": 0, "score": 0.0, "impact": 0.0, "level": "Low"}
        self.hash = self.calculate_hash()
        self.signature = signature

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "traffic_layer": self.traffic_layer,
            "health_layer": self.health_layer,
            "previous_hash": self.previous_hash,
            "congestion_layer": self.congestion_layer
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

# کلاس بلاک‌چین
class Blockchain:
    def __init__(self):
        self.chain = []
        self.cache = {}
        self.load_from_db()

    def load_from_db(self):
        conn = sqlite3.connect(input_db)
        c = conn.cursor()
        c.execute("SELECT * FROM blocks")
        rows = c.fetchall()
        for row in tqdm(rows, desc="Loading blocks from DB", file=sys.stdout):
            traffic_layer = {"volume": row[3], "type": row[2]}
            health_layer = {"status": row[4], "latency": row[5]}
            block = Block(row[0], row[1], traffic_layer, health_layer, row[6])
            block.hash = row[7]
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

    def add_block(self, block):
        if not block.verify_signature(node_public_keys[block.node_id]):
            logging.error(f"Invalid signature for block {block.node_id}, block discarded")
            return False
        self.chain.append(block)
        if block.node_id not in self.cache:
            self.cache[block.node_id] = []
        self.cache[block.node_id].append(block)
        if len(self.cache[block.node_id]) > 4:
            self.cache[block.node_id].pop(0)
        save_to_db(block)
        return True

    def detect_congestion(self, node_id):
        node_blocks = self.cache.get(node_id, [])
        if not node_blocks:
            return {"is_congested": 0, "score": 0.0, "impact": 0.0, "level": "Low"}
        traffic_values = [b.traffic_layer["volume"] for b in node_blocks]
        current_traffic = traffic_values[-1]
        mean_traffic = np.mean(traffic_values)
        dynamic_threshold = max(40, mean_traffic * 1.2)
        if current_traffic > 70:
            level = "High"
            is_congested = 1
        elif 40 <= current_traffic <= 70:
            level = "Medium"
            is_congested = 1
        else:
            level = "Low"
            is_congested = 0
        congestion_score = np.mean(traffic_values)
        latency_impact = np.mean([b.health_layer["latency"] for b in node_blocks])
        return {"is_congested": is_congested, "score": round(congestion_score, 2), "impact": round(latency_impact, 2), "level": level}

# تابع اصلی
def main():
    try:
        block_limit = 100 if os.getenv("DEMO_MODE") == "True" else None
        init_db()
        blockchain = Blockchain()
        total_blocks = len(blockchain.chain[1:]) if not block_limit else min(block_limit, len(blockchain.chain[1:]))
        processed_blocks = 0
        
        def process_block(block):
            congestion_layer = blockchain.detect_congestion(block.node_id)
            new_block = Block(block.timestamp, block.node_id, block.traffic_layer, block.health_layer, block.previous_hash, congestion_layer)
            new_block.hash = block.hash
            new_block.sign_block(node_keys[block.node_id])
            if blockchain.add_block(new_block):
                return new_block
            return None

        with ThreadPoolExecutor() as executor:
            blocks_to_process = blockchain.chain[1:total_blocks + 1] if block_limit else blockchain.chain[1:]
            new_blocks = list(tqdm(executor.map(process_block, blocks_to_process), total=total_blocks, desc="Detecting Congestion", file=sys.stdout))
            for idx, block in enumerate(new_blocks):
                if block:
                    processed_blocks += 1
                    tqdm.write(f"Processed {idx + 1}/{total_blocks} blocks - Node: {block.node_id}, Congestion: {block.congestion_layer['level']}")

        # گزارش خلاصه
        conn = sqlite3.connect(output_db)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM congestion_blocks WHERE congestion_level = 'High'")
        high_congestion = c.fetchone()[0]
        c.execute("SELECT AVG(congestion_score) FROM congestion_blocks")
        avg_score = c.fetchone()[0] or 0.0
        conn.close()
        
        summary = {
            "total_blocks": len(blockchain.chain),
            "high_congestion_points": high_congestion,
            "average_congestion_score": round(avg_score, 2)
        }
        
        return {
            "status": "success",
            "block_count": processed_blocks,
            "summary": f"Processed {processed_blocks} blocks, {high_congestion} high congestion points, avg score: {avg_score:.2f}",
            "details": summary
        }
    except Exception as e:
        logging.error(f"Error in Step 2: Congestion detection: {e}")
        return {
            "status": "error",
            "block_count": 0,
            "summary": "Failed to process blocks",
            "error": str(e)
        }

if __name__ == "__main__":
    result = main()
    print(result)