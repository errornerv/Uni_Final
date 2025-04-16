import os
import threading
import logging
import time
import sqlite3
from tqdm import tqdm  # اضافه کردن tqdm

# تنظیمات لاج‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# وارد کردن ماژول‌های بلاک‌چین
from blockchain.code01_blockchain_initial_data import init_db as init_blockchain_db
from blockchain.code02_blockchain_congestion_improved import Blockchain as CongestionBlockchain
from blockchain.code03_blockchain_managed_traffic import TrafficBlockchain
from blockchain.code04_blockchain_with_new_orders import NewOrderBlock, generate_new_order, add_new_orders
from blockchain.code05_blockchain_with_real_time_orders import RealTimeBlock, generate_simulated_traffic, predict_congestion, generate_traffic_suggestion

# وارد کردن ماژول‌های هوش مصنوعی و آموزش داده‌ها
from traffic.code07_model_training import load_data_from_db, prepare_data, train_and_save_model
from traffic.code08_advanced_traffic_report import AdvancedTrafficAnalyzer

# وارد کردن ماژول‌های مدیریت هوشمند
from smart.code09_smart_traffic_management import smart_monitoring
from smart.self_healing_network import healing_monitoring

# مسیر دیتابیس‌ها
current_dir = os.path.dirname(os.path.abspath(__file__))
input_db = os.path.join(current_dir, "result", "traffic_data.db")
new_orders_db = os.path.join(current_dir, "result", "new_orders.db")
model_file = os.path.join(current_dir, "result", "congestion_model.pkl")

# مقداردهی اولیه دیتابیس‌ها
def initialize_databases():
    try:
        init_blockchain_db()  # مقداردهی دیتابیس اولیه بلاک‌چین
        conn = sqlite3.connect(new_orders_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS new_orders
                     (timestamp TEXT, node_id TEXT, traffic_type TEXT, traffic_volume REAL, network_health TEXT,
                      latency REAL, previous_hash TEXT, block_hash TEXT, congestion_level TEXT, congestion_score REAL,
                      latency_impact REAL, traffic_suggestion TEXT, is_congestion_order INTEGER)''')
        conn.commit()
        conn.close()
        logging.info("دیتابیس‌ها با موفقیت مقداردهی اولیه شدند.")
    except sqlite3.Error as e:
        logging.error(f"خطا در مقداردهی دیتابیس: {e}")

# آموزش مدل
def train_model():
    try:
        df = load_data_from_db(new_orders_db)
        if df.empty:
            logging.warning("داده‌ای برای آموزش مدل وجود ندارد. ابتدا داده‌ها را تولید کنید.")
            return
        X, y, encoders = prepare_data(df)
        for _ in tqdm(range(1), desc="Training model"):  # اضافه کردن tqdm
            train_and_save_model(X, y, model_file)
        logging.info("مدل با موفقیت آموزش داده شد و ذخیره شد.")
    except Exception as e:
        logging.error(f"خطا در آموزش مدل: {e}")

# تولید گزارش‌های پیشرفته
def generate_reports():
    try:
        analyzer = AdvancedTrafficAnalyzer()
        for _ in tqdm(range(1), desc="Generating reports"):  # اضافه کردن tqdm
            analyzer.generate_advanced_report()
        logging.info("گزارش‌های پیشرفته با موفقیت تولید شدند.")
    except Exception as e:
        logging.error(f"خطا در تولید گزارش: {e}")

# اجرای مانیتورینگ هوشمند
def start_smart_monitoring():
    try:
        smart_monitoring()
        logging.info("مانیتورینگ هوشمند شروع شد.")
    except Exception as e:
        logging.error(f"خطا در مانیتورینگ هوشمند: {e}")

# اجرای مانیتورینگ خود-ترمیم
def start_healing_monitoring():
    try:
        healing_monitoring()
        logging.info("مانیتورینگ خود-ترمیم شروع شد.")
    except Exception as e:
        logging.error(f"خطا در مانیتورینگ خود-ترمیم: {e}")

# مثال استفاده از بلاک‌چین
def example_blockchain_usage():
    try:
        blockchain = CongestionBlockchain()
        blockchain.load_from_db()
        for block in tqdm(blockchain.chain, desc="Loading blockchain data"):  # اضافه کردن tqdm
            print(f"بلاک: {block.timestamp}, نود: {block.node_id}, ازدحام: {block.congestion_layer['level']}")
        logging.info("داده‌های بلاک‌چین با موفقیت بارگذاری و نمایش داده شدند.")
    except Exception as e:
        logging.error(f"خطا در استفاده از بلاک‌چین: {e}")

# اجرای اصلی
if __name__ == "__main__":
    logging.info("شروع اجرای پروژه...")
    
    # مقداردهی اولیه دیتابیس‌ها
    initialize_databases()
    
    # مثال استفاده از بلاک‌چین
    example_blockchain_usage()
    
    # آموزش مدل (فقط اگه داده وجود داشته باشه)
    train_model()
    
    # تولید گزارش‌ها
    generate_reports()
    
    # اجرای مانیتورینگ‌ها در نخ‌های جداگانه
    smart_monitor_thread = threading.Thread(target=start_smart_monitoring, daemon=True)
    healing_monitor_thread = threading.Thread(target=start_healing_monitoring, daemon=True)
    
    smart_monitor_thread.start()
    healing_monitor_thread.start()
    
    # منتظر بمون تا برنامه با Ctrl+C متوقف بشه
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("برنامه با موفقیت متوقف شد.")