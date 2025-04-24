import logging
import os
import sys
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import sqlite3
import pandas as pd

# تنظیمات لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent
RESULT_DIR = ROOT_DIR / "result"
sys.path.append(str(ROOT_DIR))

# وارد کردن ماژول‌های پروژه
from src.blockchain.code01_blockchain_initial_data import main as run_initial_data
from src.blockchain.code02_blockchain_congestion_improved import main as run_congestion
from src.blockchain.code03_blockchain_managed_traffic import main as run_managed_traffic
from src.blockchain.code04_blockchain_with_new_orders import main as run_new_orders
from src.blockchain.code05_blockchain_with_real_time_orders import main as run_real_time_orders
from src.traffic.code06_traffic_data_preparation import main as run_data_preparation
from src.traffic.code07_model_training import main as run_model_training
from src.traffic.code08_advanced_traffic_report import main as run_advanced_report
from src.smart.code09_smart_traffic_management import main as run_smart_traffic
from src.smart.code10_self_healing_network import main as run_self_healing
from src.smart.code11_resource_optimization import main as run_resource_optimization
from src.smart.code12_predictive_analysis_and_anomaly_detection import main as run_predictive_analysis

# اطمینان از وجود دایرکتوری result
def ensure_result_dir():
    if not RESULT_DIR.exists():
        RESULT_DIR.mkdir()
        logger.info("Created result directory")

# بررسی وجود فایل‌های موردنیاز
def check_file_exists(file_path, step_name):
    if not os.path.exists(file_path):
        logger.error(f"Required file {file_path} for {step_name} does not exist. Skipping step.")
        return False
    return True

# تولید نمودار برای دمو
def plot_summary():
    try:
        conn = sqlite3.connect(RESULT_DIR / "predictive_analysis.db")
        df = pd.read_sql_query("SELECT congestion_level, predicted_congestion, anomaly_detected FROM predictive_analysis", conn)
        conn.close()
        if not df.empty:
            plt.figure(figsize=(8, 6))
            levels = df['congestion_level'].value_counts()
            plt.subplot(1, 2, 1)
            plt.bar(levels.index, levels.values, color=['green', 'orange', 'red'])
            plt.title("Congestion Level Distribution")
            plt.xlabel("Congestion Level")
            plt.ylabel("Count")
            
            anomalies = df['anomaly_detected'].value_counts()
            plt.subplot(1, 2, 2)
            plt.bar(['Normal', 'Anomaly'], anomalies.values, color=['blue', 'red'])
            plt.title("Anomaly Detection")
            plt.ylabel("Count")
            
            plt.tight_layout()
            plt.savefig(RESULT_DIR / "traffic_summary.png")
            plt.show()
    except Exception as e:
        logger.warning(f"Failed to generate summary plot: {e}")

# اجرای کل پروژه
def run_pipeline(demo=False):
    logger.info("Starting Network Traffic Congestion Management with AI and Blockchain...")
    start_time = datetime.now()

    ensure_result_dir()
    if demo:
        logger.info("Running in DEMO mode with reduced data")
        os.environ["DEMO_MODE"] = "True"

    steps = [
        ("Step 1: Initializing blockchain data...", run_initial_data, None),
        ("Step 2: Detecting congestion...", run_congestion, None),
        ("Step 3: Managing traffic...", run_managed_traffic, RESULT_DIR / "traffic_data.db"),
        ("Step 4: Processing new orders...", run_new_orders, RESULT_DIR / "managed_traffic.db"),
        ("Step 5: Processing real-time orders...", run_real_time_orders, RESULT_DIR / "new_orders.db"),
        ("Step 6: Preparing traffic data...", run_data_preparation, RESULT_DIR / "new_orders.db"),
        ("Step 7: Training machine learning model...", run_model_training, RESULT_DIR / "new_orders.db"),
        ("Step 8: Generating advanced traffic report...", run_advanced_report, RESULT_DIR / "managed_traffic.db"),
        ("Step 9: Managing smart traffic...", run_smart_traffic, RESULT_DIR / "congestion_model.pkl"),
        ("Step 10: Self-healing network...", run_self_healing, RESULT_DIR / "smart_traffic.db"),
        ("Step 11: Optimizing resources...", run_resource_optimization, RESULT_DIR / "self_healing.db"),
        ("Step 12: Predictive analysis and anomaly detection...", run_predictive_analysis, RESULT_DIR / "congestion_model.pkl"),
    ]

    for step_message, step_function, required_file in steps:
        try:
            if required_file and not check_file_exists(required_file, step_message):
                continue
            logger.info(step_message)
            step_function()
        except Exception as e:
            logger.error(f"Error in {step_message}: {e}")
            if demo:
                logger.info("Continuing in DEMO mode despite error...")
                continue
            else:
                sys.exit(1)

    end_time = datetime.now()
    logger.info(f"Pipeline completed in {end_time - start_time}")

    if demo:
        logger.info("Generating demo summary plot...")
        plot_summary()

# تابع اصلی
def main():
    demo = "--demo" in sys.argv
    run_pipeline(demo=demo)

if __name__ == "__main__":
    main()