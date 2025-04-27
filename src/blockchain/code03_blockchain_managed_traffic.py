import os
import random
import hashlib
import time
import sqlite3
import json
import logging
from datetime import datetime
import sys
from tqdm import tqdm
from pathlib import Path

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# تنظیمات لاگینگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULT_DIR = ROOT_DIR / "result"
input_db = os.path.join(RESULT_DIR, "traffic_data.db")
output_db = os.path.join(RESULT_DIR, "managed_traffic.db")

# اسم جدول ورودی
INPUT_TABLE_NAME = "blocks"

# گراف نودها
nodes = [f"Node_{i}" for i in range(1, 11)] + ["Genesis"]
graph = {node: {"neighbors": random.sample([n for n in nodes if n != node], random.randint(1, 3)), 
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]} 
         for node in nodes}

# وضعیت نودها (شامل Genesis)
node_status = {
    node: {"max_capacity": 100, "current_traffic": 0, "active": True} if node != "Genesis" 
    else {"max_capacity": 0, "current_traffic": 0, "active": False} 
    for node in nodes
}

# بررسی وجود جدول
def check_table_exists(db_path, table_name):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except sqlite3.Error as e:
        logging.error(f"Error checking table {table_name}: {e}")
        return False

# دیتابیس SQLite
def init_db():
    result_dir = os.path.dirname(output_db)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS managed_blocks
                 (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                  latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT, 
                  congestion_score REAL, latency_impact REAL, traffic_suggestion TEXT)''')
    conn.commit()
    conn.close()

def save_to_db(block):
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute("INSERT INTO managed_blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
               block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
               block.congestion_layer["level"], block.congestion_layer["score"], 
               block.congestion_layer["impact"], block.traffic_suggestion))
    conn.commit()
    conn.close()

# کلاس بلاک
class ManagedTrafficBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_layer, traffic_suggestion):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_layer = traffic_layer
        self.health_layer = health_layer
        self.previous_hash = previous_hash
        self.congestion_layer = congestion_layer
        self.traffic_suggestion = traffic_suggestion
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.timestamp, "node_id": self.node_id, "traffic_layer": self.traffic_layer,
            "health_layer": self.health_layer, "previous_hash": self.previous_hash, "congestion_layer": self.congestion_layer,
            "traffic_suggestion": self.traffic_suggestion
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# پخش ترافیک
def redistribute_traffic(node_id, excess_traffic):
    try:
        neighbors = [n for n in graph[node_id]["neighbors"] if n != "Genesis" and node_status[n]["active"]]
        available_neighbors = [
            n for n in neighbors 
            if node_status[n]["current_traffic"] + excess_traffic / len(neighbors) <= node_status[n]["max_capacity"]
        ]
        
        if not available_neighbors:
            return "No available neighbors"

        split_traffic = excess_traffic / len(available_neighbors)
        redistribution = []
        for neighbor in available_neighbors:
            node_status[neighbor]["current_traffic"] += split_traffic
            redistribution.append(f"{split_traffic:.2f} MB/s to {neighbor}")
        
        return ", ".join(redistribution)
    except Exception as e:
        logging.error(f"Error in redistribute_traffic for node {node_id}: {e}")
        return "Redistribution failed"

# محاسبه سطح تراکم
def calculate_congestion_level(traffic_volume, latency, max_capacity):
    try:
        congestion_score = (traffic_volume / max_capacity) * 0.7 + (latency / 10) * 0.3
        congestion_score = min(max(congestion_score, 0.0), 1.0)
        latency_impact = (latency / 10) * (traffic_volume / max_capacity)
        latency_impact = min(max(latency_impact, 0.0), 1.0)
        
        if congestion_score > 0.8:
            level = "High"
        elif congestion_score > 0.5:
            level = "Medium"
        else:
            level = "Low"

        return {"level": level, "score": congestion_score, "impact": latency_impact}
    except Exception as e:
        logging.error(f"Error in calculate_congestion_level: {e}")
        return {"level": "Low", "score": 0.0, "impact": 0.0}

# پیشنهاد مدیریت ترافیک
def suggest_traffic_management(block):
    try:
        if block.node_id == "Genesis":
            return "None"

        traffic_volume = block.traffic_layer["volume"]
        congestion_level = block.congestion_layer["level"]
        max_capacity = node_status.get(block.node_id, {"max_capacity": 100})["max_capacity"]

        if congestion_level in ["Medium", "High"] and traffic_volume > max_capacity:
            excess_traffic = traffic_volume - max_capacity
            redistributed = redistribute_traffic(block.node_id, excess_traffic)
            node_status[block.node_id]["current_traffic"] = max_capacity
            return f"Redistribute {excess_traffic:.2f} MB/s: {redistributed}"
        elif congestion_level == "High":
            return "Reduce Data traffic by 20% or prioritize critical nodes"
        elif block.health_layer["status"] == "Down":
            return "Reroute traffic to backup node"
        return "None"
    except Exception as e:
        logging.error(f"Error in suggest_traffic_management for node {block.node_id}: {e}")
        return "Error in traffic suggestion"

# کلاس بلاک‌چین
class TrafficBlockchain:
    def __init__(self, limit=None):
        self.chain = []
        self.processed_blocks = []
        self.cache = {}
        self.load_from_db(limit)

    def load_from_db(self, limit):
        try:
            if not check_table_exists(input_db, INPUT_TABLE_NAME):
                logging.error(f"Table '{INPUT_TABLE_NAME}' does not exist in the database")
                self.chain = []
                return

            conn = sqlite3.connect(input_db)
            c = conn.cursor()
            query = f"SELECT * FROM {INPUT_TABLE_NAME}"
            if limit:
                query += f" LIMIT {limit}"
            c.execute(query)
            rows = c.fetchall()
            for row in tqdm(rows, desc="Loading blocks from DB", file=sys.stdout):
                traffic_layer = {"volume": float(row[3] or 0.0), "type": row[2] or "Data"}
                health_layer = {"status": row[4] or "Normal", "latency": float(row[5] or 0.0)}
                max_capacity = node_status.get(row[1], {"max_capacity": 100})["max_capacity"]
                congestion_layer = calculate_congestion_level(traffic_layer["volume"], health_layer["latency"], max_capacity)
                try:
                    traffic_suggestion = row[11] if len(row) > 11 else "None"
                except IndexError:
                    traffic_suggestion = "None"
                block = ManagedTrafficBlock(row[0], row[1], traffic_layer, health_layer, row[6], congestion_layer, traffic_suggestion)
                block.hash = row[7]
                self.chain.append(block)
                if row[1] not in self.cache:
                    self.cache[row[1]] = []
                self.cache[row[1]].append(block)
                if len(self.cache[row[1]]) > 4:
                    self.cache[row[1]].pop(0)
                tqdm.write(f"Loaded block for Node {row[1]} at {row[0]}")
            conn.close()
        except sqlite3.Error as e:
            logging.error(f"Database load error: {e}")
            self.chain = []

    def add_block(self, block):
        traffic_suggestion = suggest_traffic_management(block)
        new_block = ManagedTrafficBlock(
            block.timestamp, block.node_id, block.traffic_layer, block.health_layer, 
            block.previous_hash, block.congestion_layer, traffic_suggestion
        )
        self.processed_blocks.append(new_block)
        if block.node_id not in self.cache:
            self.cache[block.node_id] = []
        self.cache[block.node_id].append(new_block)
        if len(self.cache[block.node_id]) > 4:
            self.cache[block.node_id].pop(0)
        save_to_db(new_block)

# تابع اصلی
def main():
    try:
        limit = 100 if os.getenv("DEMO_MODE") == "True" else None
        init_db()
        traffic_blockchain = TrafficBlockchain(limit)
        processed_blocks = 0
        high_congestion_count = 0

        for block in tqdm(traffic_blockchain.chain, desc="Managing Traffic", file=sys.stdout):
            traffic_blockchain.add_block(block)
            processed_blocks += 1
            if block.congestion_layer["level"] == "High":
                high_congestion_count += 1
            print(f"Processed block - Node: {block.node_id}, Congestion: {block.congestion_layer['level']}")

        summary = {
            "total_blocks": processed_blocks,
            "high_congestion_count": high_congestion_count
        }

        return {
            "status": "success",
            "block_count": processed_blocks,
            "summary": f"Processed {processed_blocks} blocks, {high_congestion_count} high congestion points",
            "details": summary
        }
    except Exception as e:
        logging.error(f"Error in Step 3: Managed traffic: {e}")
        return {
            "status": "error",
            "block_count": 0,
            "summary": "Failed to process blocks",
            "error": str(e)
        }

if __name__ == "__main__":
    result = main()
    print(result)