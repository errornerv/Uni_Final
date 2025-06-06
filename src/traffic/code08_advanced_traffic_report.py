import os
import logging
from collections import defaultdict
import sqlite3
import random
from tqdm import tqdm
import sys
from pathlib import Path

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# تنظیمات لاگینگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RESULT_DIR = ROOT_DIR / "result"
input_db = os.path.join(RESULT_DIR, "managed_traffic.db")
output_db = os.path.join(RESULT_DIR, "traffic_report.db")

# گراف نودها
nodes = [f"Node_{i}" for i in range(1, 11)]
graph = {node: {"neighbors": random.sample(nodes, random.randint(1, 3)), 
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]} 
         for node in nodes}

# دیتابیس گزارش
def init_db():
    result_dir = os.path.dirname(output_db)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS traffic_report
                 (report_type TEXT, node_id TEXT, value REAL, details TEXT)''')
    conn.commit()
    conn.close()
    print(f"Output database initialized at {output_db}")

def save_report_to_db(report_type, node_id, value, details):
    try:
        conn = sqlite3.connect(output_db)
        c = conn.cursor()
        c.execute("INSERT INTO traffic_report VALUES (?, ?, ?, ?)", (report_type, node_id, value, details))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Error saving report to database: {e}")

# کلاس تحلیل
class AdvancedTrafficAnalyzer:
    def __init__(self, limit=None):
        self.chain = []
        self.cache = {}
        self.load_from_db(limit)

    def load_from_db(self, limit):
        try:
            conn = sqlite3.connect(input_db)
            c = conn.cursor()
            query = "SELECT * FROM managed_blocks"
            if limit:
                query += f" LIMIT {limit}"
            c.execute(query)
            rows = c.fetchall()
            total_rows = len(rows)
            for idx, row in enumerate(tqdm(rows, desc="Loading blocks from DB", file=sys.stdout)):
                block = {
                    "timestamp": row[0], 
                    "node_id": row[1], 
                    "traffic_type": row[2], 
                    "traffic_volume": row[3],
                    "network_health": row[4], 
                    "latency": row[5], 
                    "previous_hash": row[6], 
                    "block_hash": row[7],
                    "congestion_level": row[8], 
                    "congestion_score": row[9], 
                    "latency_impact": row[10],
                    "traffic_suggestion": row[11]
                }
                self.chain.append(block)
                if block["node_id"] not in self.cache:
                    self.cache[block["node_id"]] = []
                self.cache[block["node_id"]].append(block)
                if len(self.cache[block["node_id"]]) > 10:
                    self.cache[block["node_id"]].pop(0)
                tqdm.write(f"Processed {idx + 1}/{total_rows} blocks - Loaded block for Node {block['node_id']} at {block['timestamp']}")
            conn.close()
            logging.info(f"Loaded {len(rows)} blocks from managed_traffic.db")
        except sqlite3.Error as e:
            logging.error(f"Database load error: {e}")
            self.chain = []

    def calculate_daily_traffic_average(self):
        if not self.chain:
            logging.warning("No data available for analysis.")
            return {}

        traffic_by_node = defaultdict(list)
        total_blocks = len(self.chain[1:])  # بدون بلاک جنسیس
        for idx, block in enumerate(tqdm(self.chain[1:], desc="Calculating daily traffic averages", file=sys.stdout)):
            traffic_by_node[block["node_id"]].append(float(block["traffic_volume"]))
            tqdm.write(f"Processed {idx + 1}/{total_blocks} blocks for daily average - Node: {block['node_id']}, Traffic: {block['traffic_volume']:.2f} MB/s")

        daily_averages = {}
        for node, volumes in traffic_by_node.items():
            avg = round(sum(volumes) / len(volumes), 2)
            daily_averages[node] = avg
            save_report_to_db("daily_average", node, avg, f"Average traffic for {node}")
        return daily_averages

    def analyze_network_health_impact(self):
        if not self.chain:
            logging.warning("No data available for analysis.")
            return {}

        health_impact = defaultdict(lambda: {"congested": 0, "total": 0})
        total_blocks = len(self.chain[1:])
        for idx, block in enumerate(tqdm(self.chain[1:], desc="Analyzing network health impact", file=sys.stdout)):
            health = block["network_health"]
            health_impact[health]["total"] += 1
            if block["congestion_level"] in ["Medium", "High"]:
                health_impact[health]["congested"] += 1
            tqdm.write(f"Processed {idx + 1}/{total_blocks} blocks for health impact - Health: {health}, Congestion: {block['congestion_level']}")

        impact_report = {}
        for health, stats in health_impact.items():
            if stats["total"] > 0:
                percentage = round((stats["congested"] / stats["total"]) * 100, 2)
                impact_report[health] = {"congestion_percentage": percentage, "total_blocks": stats["total"]}
                save_report_to_db("health_impact", "all", percentage, f"{health}: {stats['congested']}/{stats['total']} congested")
        return impact_report

    def identify_high_traffic_nodes(self, threshold=50):
        if not self.chain:
            logging.warning("No data available for analysis.")
            return []

        high_traffic_nodes = []
        total_blocks = len(self.chain[1:])
        for idx, block in enumerate(tqdm(self.chain[1:], desc="Identifying high traffic nodes", file=sys.stdout)):
            if block["traffic_volume"] > threshold:
                neighbors = ",".join(graph[block["node_id"]]["neighbors"])
                details = f"Node {block['node_id']} at {block['timestamp']}: {block['traffic_volume']} MB/s, Health: {block['network_health']}, Neighbors: {neighbors}"
                high_traffic_nodes.append(details)
                save_report_to_db("high_traffic", block["node_id"], block["traffic_volume"], details)
            tqdm.write(f"Processed {idx + 1}/{total_blocks} blocks for high traffic - Node: {block['node_id']}, Traffic: {block['traffic_volume']:.2f} MB/s")
        return high_traffic_nodes

    def generate_advanced_report(self):
        if not self.chain:
            logging.error("No data to process.")
            return {}

        daily_averages = self.calculate_daily_traffic_average()
        health_impact = self.analyze_network_health_impact()
        high_traffic_nodes = self.identify_high_traffic_nodes()

        report = {
            "daily_averages": daily_averages,
            "health_impact": health_impact,
            "high_traffic_nodes_count": len(high_traffic_nodes)
        }

        print("\nAdvanced Traffic Report:")
        print("Daily Average Traffic by Node (MB/s):")
        for node, avg in daily_averages.items():
            print(f"Node {node}: {avg} MB/s")

        print("\nNetwork Health Impact on Congestion (%):")
        for health, stats in health_impact.items():
            print(f"{health}: {stats['congestion_percentage']}% congested ({stats['total_blocks']} blocks)")

        print("\nHigh Traffic Nodes (Traffic > 50 MB/s):")
        for node in high_traffic_nodes[:10]:  # محدود به 10 مورد برای نمایش
            print(node)

        logging.info(f"Advanced traffic report saved to: {output_db}")
        return report

# تابع اصلی
def main():
    try:
        limit = 100 if os.getenv("DEMO_MODE") == "True" else None
        init_db()
        analyzer = AdvancedTrafficAnalyzer(limit)
        report = analyzer.generate_advanced_report()
        
        block_count = len(analyzer.chain[1:])  # تعداد بلاک‌های پردازش‌شده (بدون جنسیس)
        high_traffic_count = report.get("high_traffic_nodes_count", 0)
        
        summary = {
            "total_blocks": block_count,
            "high_traffic_nodes": high_traffic_count,
            "output_db": output_db
        }
        
        return {
            "status": "success",
            "block_count": block_count,
            "summary": f"Processed {block_count} blocks, {high_traffic_count} high traffic nodes, report saved to {output_db}",
            "details": summary
        }
    except Exception as e:
        logging.error(f"Error in Step 8: Advanced traffic report: {e}")
        return {
            "status": "error",
            "block_count": 0,
            "summary": "Failed to generate report",
            "error": str(e)
        }

if __name__ == "__main__":
    result = main()
    print(result)