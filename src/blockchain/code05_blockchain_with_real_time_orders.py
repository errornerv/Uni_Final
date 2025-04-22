import os
import random
import hashlib
from datetime import datetime
import logging
import sqlite3
import json
import time
import threading
import sys
from utils.db_utils import init_db, save_to_db

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])

# Database paths
current_dir = os.path.dirname(os.path.abspath(__file__))
start_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))  # Go to start/ directory
input_db = os.path.join(start_dir, "result", "managed_traffic.db")
output_db = os.path.join(start_dir, "result", "real_time_orders.db")

# Graph of nodes
nodes = [f"Node_{i}" for i in range(1, 11)]  # You can reduce the number for testing (e.g., 3)
graph = {node: {"neighbors": random.sample(nodes, random.randint(1, 3)), 
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]} 
         for node in nodes}

# Initialize output database
def init_db():
    try:
        # Ensure the result directory exists
        result_dir = os.path.dirname(output_db)
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
            logging.info(f"Created result directory: {result_dir}")
        
        conn = sqlite3.connect(output_db, timeout=10)  # Add timeout to prevent locking
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS real_time_orders
                     (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                      latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT, congestion_score REAL,
                      latency_impact REAL, traffic_suggestion TEXT, is_real_time_order INTEGER)''')
        conn.commit()
        conn.close()
        logging.info(f"Initialized database: {output_db}")
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")
        raise

def save_to_db(block):
    try:
        conn = sqlite3.connect(output_db, timeout=10)  # Add timeout
        c = conn.cursor()
        c.execute("INSERT INTO real_time_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
                   block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
                   block.congestion_layer["level"], block.congestion_layer["score"], block.congestion_layer["impact"],
                   block.traffic_suggestion, 1 if block.is_real_time_order else 0))
        conn.commit()
        conn.close()
        logging.info(f"Saved real-time block for {block.node_id} at {block.timestamp}")
    except sqlite3.Error as e:
        logging.error(f"Database save error for block {block.node_id}: {e}")
        raise

# Block class
class RealTimeBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_layer=None, 
                 traffic_suggestion=None, is_real_time_order=False):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_layer = traffic_layer
        self.health_layer = health_layer
        self.previous_hash = previous_hash
        self.congestion_layer = congestion_layer or {"is_congested": 0, "score": 0.0, "impact": 0.0, "level": "Low"}
        self.traffic_suggestion = traffic_suggestion
        self.is_real_time_order = is_real_time_order
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "traffic_layer": self.traffic_layer,
            "health_layer": self.health_layer,
            "previous_hash": self.previous_hash,
            "congestion_layer": self.congestion_layer,
            "traffic_suggestion": self.traffic_suggestion,
            "is_real_time_order": self.is_real_time_order
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# Real-time blockchain class
class RealTimeBlockchain:
    def __init__(self):
        self.chain = []
        self.cache = {}
        self.load_from_db()
        self.running = True  # Flag to control the simulation loop

    def load_from_db(self):
        try:
            conn = sqlite3.connect(input_db, timeout=10)
            c = conn.cursor()
            c.execute("SELECT * FROM managed_blocks")
            rows = c.fetchall()
            for row in rows:
                traffic_layer = {"type": row[2], "volume": row[3]}
                health_layer = {"status": row[4], "latency": row[5]}
                congestion_layer = {"is_congested": 1 if row[8] in ["Medium", "High"] else 0, 
                                   "score": row[9], "impact": row[10], "level": row[8]}
                block = RealTimeBlock(row[0], row[1], traffic_layer, health_layer, row[6], congestion_layer, row[11], True)
                block.hash = row[7]
                self.chain.append(block)
                if row[1] not in self.cache:
                    self.cache[row[1]] = []
                self.cache[row[1]].append(block)
                if len(self.cache[row[1]]) > 5:  # Keep the last 5 blocks
                    self.cache[row[1]].pop(0)
            conn.close()
            logging.info(f"Loaded {len(rows)} blocks from managed_traffic.db")
        except sqlite3.Error as e:
            logging.error(f"Database load error: {e}")
            raise

    def add_real_time_block(self, block):
        try:
            self.chain.append(block)
            if block.node_id not in self.cache:
                self.cache[block.node_id] = []
            self.cache[block.node_id].append(block)
            if len(self.cache[block.node_id]) > 5:
                self.cache[block.node_id].pop(0)
            save_to_db(block)
            # Print to stdout for app.py to capture
            print(f"Real-time block added: Node {block.node_id}, Traffic: {block.traffic_layer['volume']} MB/s, "
                  f"Congestion: {block.congestion_layer['level']}, Time: {block.timestamp}")
        except Exception as e:
            logging.error(f"Error adding real-time block for {block.node_id}: {e}")
            raise

    def stop(self):
        self.running = False  # Stop the simulation loop

# Generate simulated traffic
def generate_simulated_traffic(node_id):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    traffic_layer = {
        "type": random.choice(["video", "audio", "data"]),
        "volume": random.uniform(10, 100)  # Traffic volume between 10 and 100 MB
    }
    health_layer = {
        "status": random.choice(["good", "moderate", "poor"]),
        "latency": random.uniform(10, 100)  # Latency between 10 and 100 ms
    }
    previous_hash = "0"  # For initial blocks
    return RealTimeBlock(timestamp, node_id, traffic_layer, health_layer, previous_hash)

# Simulate real-time
def simulate_real_time(blockchain):
    try:
        while blockchain.running:  # Run until stopped
            previous_block = blockchain.chain[-1] if blockchain.chain else None
            for node in nodes:
                if not blockchain.running:  # Check if we should stop
                    break
                block = generate_simulated_traffic(node)
                blockchain.add_real_time_block(block)
                print(f"Simulated real-time block for {node} at {block.timestamp} with traffic: {block.traffic_layer['volume']} MB/s")
                time.sleep(2)  # 2-second delay to reduce system load
            previous_block = blockchain.chain[-1]  # Update previous block
    except Exception as e:
        logging.error(f"Error in simulate_real_time: {e}")

# Main execution
if __name__ == "__main__":
    try:
        init_db()
        real_time_blockchain = RealTimeBlockchain()
        simulation_thread = threading.Thread(target=simulate_real_time, args=(real_time_blockchain,), daemon=True)
        simulation_thread.start()
        logging.info("Simulation thread started")
        
        # Keep the script running until interrupted
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        logging.info("Simulation stopped by user")
        real_time_blockchain.stop()
        simulation_thread.join(timeout=5)  # Wait for the thread to finish
    except Exception as e:
        logging.error(f"Critical error in main execution: {e}")
        real_time_blockchain.stop()
        if simulation_thread.is_alive():
            simulation_thread.join(timeout=5)