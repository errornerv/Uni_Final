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
input_db = os.path.join(RESULT_DIR, "smart_traffic.db")
output_db = os.path.join(RESULT_DIR, "self_healing.db")

# گراف نودها
nodes = [f"Node_{i}" for i in range(1, 11)] + ["Genesis"]
graph = {node: {"neighbors": random.sample(nodes, random.randint(1, 3)), 
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]} 
         for node in nodes}

# وضعیت نودها
node_status = {node: {"max_capacity": 100, "current_traffic": 0, "active": True} for node in nodes}

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
    c.execute('''CREATE TABLE IF NOT EXISTS healing_network
                 (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                  latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT, 
                  traffic_redistribution TEXT, event_type TEXT, healing_action TEXT, predicted_congestion TEXT,
                  signature TEXT)''')
    conn.commit()
    conn.close()
    logging.info(f"Initialized output database at {output_db}")

def save_to_db(block):
    try:
        conn = sqlite3.connect(output_db)
        c = conn.cursor()
        c.execute("INSERT INTO healing_network VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
                   block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
                   block.congestion_level, block.traffic_redistribution, block.event_type, block.healing_action,
                   block.predicted_congestion, block.signature.hex() if block.signature else None))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Error saving block to database: {e}")

# کلاس بلاک
class HealingBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_level, 
                 traffic_redistribution=None, event_type="Normal", healing_action="None", predicted_congestion=None, signature=None):
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
        self.signature = signature
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.timestamp, "node_id": self.node_id, "traffic_layer": self.traffic_layer,
            "health_layer": self.health_layer, "previous_hash": self.previous_hash,
            "congestion_level": self.congestion_level, "traffic_redistribution": self.traffic_redistribution,
            "event_type": self.event_type, "healing_action": self.healing_action,
            "predicted_congestion": self.predicted_congestion
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

# محاسبه احتمال فعال‌سازی مجدد نود
def calculate_reactivation_probability(node_id, chain):
    node_blocks = [b for b in chain if b.node_id == node_id][-10:]
    if not node_blocks:
        return 0.1
    
    up_blocks = sum(1 for b in node_blocks if b.health_layer["status"] == "Up")
    up_ratio = up_blocks / len(node_blocks)
    
    neighbors = graph[node_id]["neighbors"]
    healthy_neighbors = sum(1 for n in neighbors if any(b.health_layer["status"] == "Up" for b in chain if b.node_id == n))
    neighbor_health_ratio = healthy_neighbors / len(neighbors) if neighbors else 0
    
    probability = 0.1 + (up_ratio * 0.4) + (neighbor_health_ratio * 0.3)
    return min(probability, 0.8)

# مکانیزم خود-ترمیمی
def self_heal(block, chain):
    health = block.health_layer["status"]
    congestion = block.predicted_congestion
    node_id = block.node_id
    neighbors = graph[node_id]["neighbors"]
    
    healthy_neighbors = []
    for neighbor in neighbors:
        neighbor_blocks = [b for b in chain if b.node_id == neighbor]
        if neighbor_blocks and neighbor_blocks[-1].health_layer["status"] == "Up":
            healthy_neighbors.append(neighbor)
    
    healing_action = "None"
    if not node_status[node_id]["active"]:
        reactivation_prob = calculate_reactivation_probability(node_id, chain)
        if random.random() < reactivation_prob:
            node_status[node_id]["active"] = True
            block.health_layer["status"] = "Up"
            block.health_layer["latency"] = random.uniform(0, 5)
            healing_action = f"Node reactivated with probability {reactivation_prob:.2f}"
    
    if congestion in ["High", "Medium"] and healthy_neighbors:
        return f"Reroute traffic to healthy neighbor {random.choice(healthy_neighbors)} due to predicted {congestion} congestion", healing_action
    elif health == "Down" and healthy_neighbors:
        return f"Reroute traffic to healthy neighbor {random.choice(healthy_neighbors)} due to node failure", healing_action
    elif congestion == "High":
        return "Reduce traffic load by 40% to prevent congestion", healing_action
    return "None", healing_action

# کلاس بلاک‌چین
class TrafficBlockchain:
    def __init__(self, limit=None):
        self.chain = []
        self.cache = {}
        self.load_from_db(limit)

    def load_from_db(self, limit):
        try:
            conn = sqlite3.connect(input_db)
            c = conn.cursor()
            query = "SELECT * FROM smart_traffic"
            if limit:
                query += f" LIMIT {limit}"
            c.execute(query)
            rows = c.fetchall()
            for row in tqdm(rows, desc="Loading blocks from DB", file=sys.stdout):
                traffic_layer = {"volume": row[3], "type": row[2]}
                health_layer = {"status": row[4], "latency": row[5]}
                block = HealingBlock(row[0], row[1], traffic_layer, health_layer, row[6], row[8], 
                                    row[9], row[10], "None", row[11])
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
        except sqlite3.Error as e:
            logging.error(f"Error loading blocks from DB: {e}")
            self.chain = []

    def add_block(self, block):
        traffic_volume = block.traffic_layer["volume"]
        node_id = block.node_id
        predicted_congestion = block.predicted_congestion
        
        if node_status[node_id]["active"]:
            node_status[node_id]["current_traffic"] = traffic_volume
        else:
            node_status[node_id]["current_traffic"] = 0
        
        redistribution = "None"
        if block.congestion_level in ["Medium", "High"] and node_status[node_id]["active"]:
            max_capacity = node_status[node_id]["max_capacity"]
            if traffic_volume > max_capacity:
                excess_traffic = traffic_volume - max_capacity
                if block.event_type == "DDoS":
                    limited_traffic = max_capacity
                    excess_traffic = traffic_volume - limited_traffic
                    redistribution = f"Limited to {limited_traffic:.2f} MB/s, {excess_traffic:.2f} redistributed: {redistribute_traffic(node_id, excess_traffic)}"
                    node_status[node_id]["current_traffic"] = limited_traffic
                else:
                    redistribution = redistribute_traffic(node_id, excess_traffic)
                    node_status[node_id]["current_traffic"] = max_capacity

        reroute_action, healing_action = self_heal(block, self.chain)
        new_block = HealingBlock(block.timestamp, node_id, block.traffic_layer, block.health_layer,
                                block.previous_hash, block.congestion_level, redistribution, 
                                block.event_type, healing_action, predicted_congestion)
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
        total_blocks = len(self.chain[1:])  # بدون جنسیس
        high_congestion = sum(1 for block in self.chain[1:] if block.congestion_level == "High")
        self_heal_actions = sum(1 for block in self.chain[1:] if block.healing_action != "None")

        report = {
            "total_blocks": total_blocks,
            "high_congestion_blocks": high_congestion,
            "self_heal_actions": self_heal_actions
        }
        return report

# تابع اصلی
def main():
    try:
        limit = 100 if os.getenv("DEMO_MODE") == "True" else None
        init_db()
        traffic_blockchain = TrafficBlockchain(limit)
        last_time = time.time()

        for node in nodes:
            node_status[node]["current_traffic"] = 0
            node_status[node]["active"] = True

        total_blocks = len(traffic_blockchain.chain[1:])
        for idx, block in enumerate(tqdm(traffic_blockchain.chain[1:], desc="Processing Self-Heal Blocks", file=sys.stdout)):
            traffic_blockchain.add_block(block)
            print(f"\nProcessed block {idx + 1}/{total_blocks} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:")
            print(f"Node: {block.node_id}, Traffic: {block.traffic_layer['volume']:.2f} MB/s, "
                  f"Health: {block.health_layer['status']}, Congestion: {block.congestion_level}, "
                  f"Predicted Congestion: {block.predicted_congestion}, Redistribution: {block.traffic_redistribution}, "
                  f"Event: {block.event_type}, Healing: {block.healing_action}")
            last_time = time.time()

        report = traffic_blockchain.generate_report()
        logging.info(f"Self-Healing Network Report: {report}")

        return {
            "status": "success",
            "block_count": report["total_blocks"],
            "summary": f"Processed {report['total_blocks']} blocks, {report['self_heal_actions']} self-heal actions",
            "details": report
        }
    except Exception as e:
        logging.error(f"Error in Step 10: Self-healing network: {e}")
        return {
            "status": "error",
            "block_count": 0,
            "summary": "Failed to process self-healing blocks",
            "error": str(e)
        }

if __name__ == "__main__":
    result = main()
    print(result)