import os
import random
import hashlib
import time
from datetime import datetime
import sqlite3
import json
import logging
import sys
from tqdm import tqdm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from pathlib import Path

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# تنظیمات لاگینگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULT_DIR = ROOT_DIR / "result"
input_db = os.path.join(RESULT_DIR, "self_healing.db")
output_db = os.path.join(RESULT_DIR, "optimized_resources.db")

# گراف نودها
nodes = [f"Node_{i}" for i in range(1, 11)] + ["Genesis"]
graph = {node: {"neighbors": random.sample(nodes, random.randint(1, 3)), 
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]} 
         for node in nodes}

# وضعیت نودها
node_status = {node: {"max_capacity": 100, "current_traffic": 0, "active": True, "allocated_bandwidth": 50} for node in nodes}

# تولید کلیدهای ECDSA
node_keys = {node: ec.generate_private_key(ec.SECP256R1(), default_backend()) for node in nodes}
node_public_keys = {node: key.public_key() for node, key in node_keys.items()}

# دیتابیس SQLite
def init_db():
    result_dir = os.path.dirname(output_db)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS optimized_resources
                 (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                  latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT, 
                  traffic_redistribution TEXT, event_type TEXT, healing_action TEXT, predicted_congestion TEXT,
                  resource_allocation TEXT, signature TEXT)''')
    conn.commit()
    conn.close()

def save_to_db(block):
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute("INSERT INTO optimized_resources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
               block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
               block.congestion_level, block.traffic_redistribution, block.event_type, block.healing_action,
               block.predicted_congestion, block.resource_allocation, block.signature.hex() if block.signature else None))
    conn.commit()
    conn.close()

# کلاس بلاک
class OptimizedBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_level, 
                 traffic_redistribution=None, event_type="Normal", healing_action="None", predicted_congestion=None, 
                 resource_allocation=None, signature=None):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_layer = traffic_layer
        self.health_layer = health_layer
        self.previous_hash = previous_hash
        self.congestion_level = congestion_level
        self.traffic_redistribution = traffic_redistribution or "None"
        self.event_type = event_type
        self.healing_action = healing_action
        self.predicted_congestion = predicted_congestion
        self.resource_allocation = resource_allocation or "None"
        self.signature = signature
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.timestamp, "node_id": self.node_id, "traffic_layer": self.traffic_layer,
            "health_layer": self.health_layer, "previous_hash": self.previous_hash,
            "congestion_level": self.congestion_level, "traffic_redistribution": self.traffic_redistribution,
            "event_type": self.event_type, "healing_action": self.healing_action,
            "predicted_congestion": self.predicted_congestion, "resource_allocation": self.resource_allocation
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

# تخصیص منابع پویا
def optimize_resources(block, chain):
    node_id = block.node_id
    traffic_volume = block.traffic_layer["volume"]
    predicted_congestion = block.predicted_congestion
    health = block.health_layer["status"]
    neighbors = graph[node_id]["neighbors"]

    traffic_by_node = {}
    for b in chain:
        if b.node_id not in traffic_by_node:
            traffic_by_node[b.node_id] = []
        traffic_by_node[b.node_id].append(b.traffic_layer["volume"])
    
    avg_traffic = {node: sum(volumes) / len(volumes) if volumes else 0 for node, volumes in traffic_by_node.items()}
    high_traffic_nodes = [node for node, avg in avg_traffic.items() if avg > 50]

    if "Priority" in block.traffic_layer["type"]:
        extra_bandwidth = 30
        node_status[node_id]["allocated_bandwidth"] += extra_bandwidth
        return f"Allocated {extra_bandwidth} MB/s extra bandwidth due to Priority traffic"
    elif predicted_congestion in ["High", "Medium"] and node_id in high_traffic_nodes:
        healthy_neighbors = [n for n in neighbors if node_status[n]["active"] and node_status[n]["current_traffic"] < node_status[n]["max_capacity"]]
        if healthy_neighbors:
            reduced_bandwidth = 20
            node_status[node_id]["allocated_bandwidth"] -= reduced_bandwidth
            split_bandwidth = reduced_bandwidth / len(healthy_neighbors)
            for neighbor in healthy_neighbors:
                node_status[neighbor]["allocated_bandwidth"] += split_bandwidth
            return f"Reduced {reduced_bandwidth} MB/s bandwidth, redistributed {split_bandwidth:.2f} MB/s to {', '.join(healthy_neighbors)}"
        else:
            return "Reduced 20 MB/s bandwidth due to high congestion, no healthy neighbors available"
    elif health == "Down":
        healthy_neighbors = [n for n in neighbors if node_status[n]["active"] and node_status[n]["current_traffic"] < node_status[n]["max_capacity"]]
        if healthy_neighbors:
            extra_bandwidth = 10
            for neighbor in healthy_neighbors:
                node_status[neighbor]["allocated_bandwidth"] += extra_bandwidth / len(healthy_neighbors)
            return f"Redistributed {extra_bandwidth / len(healthy_neighbors):.2f} MB/s to {', '.join(healthy_neighbors)} due to node failure"
    return "No resource optimization needed"

# کلاس بلاک‌چین
class TrafficBlockchain:
    def __init__(self, limit=None):
        self.chain = []
        self.cache = {}
        self.load_from_db(limit)

    def load_from_db(self, limit):
        conn = sqlite3.connect(input_db)
        c = conn.cursor()
        query = "SELECT * FROM healing_network"
        if limit:
            query += f" LIMIT {limit}"
        c.execute(query)
        rows = c.fetchall()
        for row in tqdm(rows, desc="Loading blocks from DB", file=sys.stdout):
            traffic_layer = {"volume": row[3], "type": row[2]}
            health_layer = {"status": row[4], "latency": row[5]}
            signature = bytes.fromhex(row[13]) if row[13] else None
            block = OptimizedBlock(row[0], row[1], traffic_layer, health_layer, row[6], row[8], 
                                  row[9], row[10], row[11], row[12], None, signature)
            block.hash = row[7]
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
        traffic_volume = block.traffic_layer["volume"]
        node_id = block.node_id
        predicted_congestion = block.predicted_congestion
        
        if node_status[node_id]["active"]:
            node_status[node_id]["current_traffic"] = traffic_volume
        else:
            node_status[node_id]["current_traffic"] = 0
        
        resource_allocation = optimize_resources(block, self.chain)
        new_block = OptimizedBlock(block.timestamp, node_id, block.traffic_layer, block.health_layer,
                                  block.previous_hash, block.congestion_level, block.traffic_redistribution, 
                                  block.event_type, block.healing_action, predicted_congestion, resource_allocation)
        new_block.sign_block(node_keys[node_id])
        if not new_block.verify_signature(node_public_keys[node_id]):
            logging.error(f"Invalid signature for block {new_block.node_id}, block discarded")
            return False
        self.chain.append(new_block)
        if node_id not in self.cache:
            self.cache[node_id] = []
        self.cache[node_id].append(new_block)
        if len(self.cache[node_id]) > 4:
            self.cache[node_id].pop(0)
        save_to_db(new_block)
        return new_block

    def generate_report(self):
        total_blocks = len(self.chain)
        high_congestion = sum(1 for block in self.chain if block.congestion_level == "High")
        resource_allocations = sum(1 for block in self.chain if block.resource_allocation != "No resource optimization needed")
        high_traffic_nodes = set()
        for block in self.chain:
            if block.traffic_layer["volume"] > 50:
                high_traffic_nodes.add(block.node_id)

        print("\nResource Optimization Report:")
        print(f"Total Blocks Processed: {total_blocks}")
        print(f"High Congestion Blocks: {high_congestion}")
        print(f"Total Resource Allocations: {resource_allocations}")
        print(f"High Traffic Nodes: {', '.join(high_traffic_nodes)}")

# تابع اصلی
def main():
    limit = 100 if os.getenv("DEMO_MODE") == "True" else None
    init_db()
    traffic_blockchain = TrafficBlockchain(limit)
    last_time = time.time()

    for node in nodes:
        node_status[node]["current_traffic"] = 0
        node_status[node]["active"] = True
        node_status[node]["allocated_bandwidth"] = 50

    total_blocks = len(traffic_blockchain.chain[1:])
    for idx, block in enumerate(tqdm(traffic_blockchain.chain[1:], desc="Processing Optimized Resource Blocks", file=sys.stdout)):
        traffic_blockchain.add_block(block)
        print(f"\nProcessed block {idx + 1}/{total_blocks} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:")
        print(f"Node: {block.node_id}, Traffic: {block.traffic_layer['volume']:.2f} MB/s, "
              f"Health: {block.health_layer['status']}, Congestion: {block.congestion_level}, "
              f"Predicted Congestion: {block.predicted_congestion}, "
              f"Resource Allocation: {block.resource_allocation}")
        last_time = time.time()

    traffic_blockchain.generate_report()