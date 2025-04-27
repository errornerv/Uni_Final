import gevent
from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for
from flask_socketio import SocketIO
import sqlite3
from pathlib import Path
import threading
import logging
import importlib.util
import sys
import pandas as pd
import socket
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import xlsxwriter

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# تنظیمات لاگینگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent
RESULT_DIR = ROOT_DIR / "result"

# ایجاد دایرکتوری result اگر وجود ندارد
if not RESULT_DIR.exists():
    RESULT_DIR.mkdir()

# لیست اسکریپت‌ها با نام ماژول‌ها
SCRIPTS = {
    'code01': 'src.blockchain.code01_blockchain_initial_data',
    'code02': 'src.blockchain.code02_blockchain_congestion_improved',
    'code03': 'src.blockchain.code03_blockchain_managed_traffic',
    'code04': 'src.blockchain.code04_blockchain_with_new_orders',
    'code05': 'src.blockchain.code05_blockchain_with_real_time_orders',
    'code06': 'src.traffic.code06_traffic_data_preparation',
    'code07': 'src.traffic.code07_model_training',
    'code08': 'src.traffic.code08_advanced_traffic_report',
    'code09': 'src.smart.code09_smart_traffic_management',
    'code10': 'src.smart.code10_self_healing_network',
    'code11': 'src.smart.code11_resource_optimization',
    'code12': 'src.smart.code12_predictive_analysis_and_anomaly_detection'
}

# قفل برای کنترل اجرای اسکریپت‌ها
script_locks = {code: threading.Lock() for code in SCRIPTS}

# متغیر برای ردیابی اسکریپت‌های در حال اجرا
running_scripts = set()

# تابع برای دریافت آدرس IP محلی
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logging.error(f"Error getting local IP: {e}")
        return "Unknown"

# تابع برای وارد کردن و اجرای ماژول
def run_script(script_name, socketio):
    logging.info(f"Attempting to run script: {script_name}")
    def timeout_handler():
        socketio.emit('output', f"Script {script_name} timed out after 60 seconds")
        logging.error(f"Script {script_name} timed out")
        running_scripts.discard(script_name)
        if script_locks[script_name].locked():
            script_locks[script_name].release()
            logging.info(f"Lock for {script_name} released due to timeout")

    timer = threading.Timer(60.0, timeout_handler)
    timer.start()
    try:
        sys.path.append(str(ROOT_DIR))
        module_name = SCRIPTS[script_name]
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            error_msg = f"Module {module_name} not found. Please check if the script exists."
            logging.error(error_msg)
            socketio.emit('output', error_msg)
            return
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        if hasattr(module, 'main'):
            logging.info(f"Running main function of {module_name}")
            socketio.emit('output', f"Starting {module_name}...")
            result = module.main()
            socketio.emit('output', f"Module {module_name} execution completed: {result}")
            logging.info(f"Module {module_name} execution completed: {result}")
        else:
            error_msg = f"No main function found in {module_name}. Please define a main function."
            logging.error(error_msg)
            socketio.emit('output', error_msg)
    except ZeroDivisionError as e:
        error_msg = f"Math error in {module_name}: Division by zero. Check calculations (e.g., in calculate_congestion_level)."
        logging.error(f"ZeroDivisionError in {module_name}: {e}")
        socketio.emit('output', error_msg)
    except FileNotFoundError as e:
        error_msg = f"File not found in {module_name}: {e}. Ensure required files (e.g., congestion_model.pkl) are generated."
        logging.error(f"FileNotFoundError in {module_name}: {e}")
        socketio.emit('output', error_msg)
    except sqlite3.OperationalError as e:
        error_msg = f"Database error in {module_name}: {e}. Required database or table may not exist yet."
        logging.error(f"sqlite3.OperationalError in {module_name}: {e}")
        socketio.emit('output', error_msg)
    except Exception as e:
        error_msg = f"Unexpected error in {module_name}: {str(e)}"
        logging.error(f"Unexpected error in {module_name}: {e}")
        socketio.emit('output', error_msg)
    finally:
        timer.cancel()
        if str(ROOT_DIR) in sys.path:
            sys.path.remove(str(ROOT_DIR))
        if script_locks[script_name].locked():
            script_locks[script_name].release()
            logging.info(f"Lock for {script_name} released in finally block")
        logging.info(f"Module {script_name} execution finished")

# تابع برای بررسی وجود جدول
def table_exists(conn, table_name):
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return c.fetchone() is not None

# تابع برای گرفتن گزارش‌ها و داده‌های دقیق
def get_reports():
    reports = {}
    detailed_data = {}
    detailed_columns = {}

    # Code01: traffic_data.db
    try:
        db_path = RESULT_DIR / "traffic_data.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            if table_exists(conn, 'blocks'):
                c = conn.cursor()
                # داده‌های دقیق
                c.execute("SELECT node_id, traffic_volume, network_health, latency, timestamp FROM blocks ORDER BY timestamp DESC LIMIT 50")
                rows = c.fetchall()
                detailed_data['code01'] = rows
                detailed_columns['code01'] = ['Node ID', 'Traffic Volume', 'Network Health', 'Latency', 'Timestamp']
                reports['code01'] = {'status': 'Data retrieved successfully'}
            else:
                reports['code01'] = {'error': 'Table "blocks" not found in traffic_data.db'}
            conn.close()
        else:
            reports['code01'] = {'error': 'traffic_data.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading traffic_data.db: {e}")
        reports['code01'] = {'error': str(e)}

    # Code02: congestion_data.db
    try:
        db_path = RESULT_DIR / "congestion_data.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            if table_exists(conn, 'congestion_blocks'):
                c = conn.cursor()
                # داده‌های دقیق
                c.execute("SELECT node_id, congestion_level, congestion_score, timestamp FROM congestion_blocks ORDER BY timestamp DESC LIMIT 50")
                rows = c.fetchall()
                detailed_data['code02'] = rows
                detailed_columns['code02'] = ['Node ID', 'Congestion Level', 'Congestion Score', 'Timestamp']
                reports['code02'] = {'status': 'Data retrieved successfully'}
            else:
                reports['code02'] = {'error': 'Table "congestion_blocks" not found in congestion_data.db'}
            conn.close()
        else:
            reports['code02'] = {'error': 'congestion_data.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading congestion_data.db: {e}")
        reports['code02'] = {'error': str(e)}

    # Code03: managed_traffic.db
    try:
        db_path = RESULT_DIR / "managed_traffic.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            if table_exists(conn, 'managed_blocks'):
                c = conn.cursor()
                # داده‌های دقیق
                c.execute("SELECT node_id, congestion_level, traffic_volume, timestamp FROM managed_blocks ORDER BY timestamp DESC LIMIT 50")
                rows = c.fetchall()
                detailed_data['code03'] = rows 
                detailed_columns['code03'] = ['Node ID', 'Congestion Level', 'Traffic Volume', 'Timestamp']
                reports['code03'] = {'status': 'Data retrieved successfully'}
            else:
                reports['code03'] = {'error': 'Table "managed_blocks" not found in managed_traffic.db'}
            conn.close()
        else:
            reports['code03'] = {'error': 'managed_traffic.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading managed_traffic.db: {e}")
        reports['code03'] = {'error': str(e)}

    # Code04: new_orders.db
    try:
        db_path = RESULT_DIR / "new_orders.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            if table_exists(conn, 'new_orders'):
                c = conn.cursor()
                # داده‌های دقیق
                c.execute("SELECT node_id, traffic_type, traffic_volume, network_health, latency, timestamp FROM new_orders ORDER BY timestamp DESC LIMIT 50")
                rows = c.fetchall()
                detailed_data['code04'] = rows
                detailed_columns['code04'] = ['Node ID', 'Traffic Type', 'Traffic Volume', 'Network Health', 'Latency', 'Timestamp']
                reports['code04'] = {'status': 'Data retrieved successfully'}
            else:
                reports['code04'] = {'error': 'Table "new_orders" not found in new_orders.db'}
            conn.close()
        else:
            reports['code04'] = {'error': 'new_orders.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading new_orders.db: {e}")
        reports['code04'] = {'error': str(e)}

    # Code05: real_time_orders.db
    try:
        db_path = RESULT_DIR / "real_time_orders.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            if table_exists(conn, 'real_time_orders'):
                c = conn.cursor()
                # داده‌های دقیق
                c.execute("SELECT node_id, traffic_type, traffic_volume, network_health, latency, timestamp FROM real_time_orders ORDER BY timestamp DESC LIMIT 50")
                rows = c.fetchall()
                detailed_data['code05'] = rows
                detailed_columns['code05'] = ['Node ID', 'Traffic Type', 'Traffic Volume', 'Network Health', 'Latency', 'Timestamp']
                reports['code05'] = {'status': 'Data retrieved successfully'}
            else:
                reports['code05'] = {'error': 'Table "real_time_orders" not found in real_time_orders.db'}
            conn.close()
        else:
            reports['code05'] = {'error': 'real_time_orders.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading real_time_orders.db: {e}")
        reports['code05'] = {'error': str(e)}

    # Code06: traffic_data.csv
    try:
        csv_path = RESULT_DIR / "traffic_data.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            # داده‌های دقیق (50 ردیف آخر)
            df = df.tail(50)
            rows = df[['node_id', 'traffic_type', 'traffic_volume', 'network_health', 'latency', 'timestamp']].values.tolist()
            detailed_data['code06'] = rows
            detailed_columns['code06'] = ['Node ID', 'Traffic Type', 'Traffic Volume', 'Network Health', 'Latency', 'Timestamp']
            reports['code06'] = {'status': 'Data retrieved successfully'}
        else:
            reports['code06'] = {'error': 'traffic_data.csv not found'}
    except Exception as e:
        logging.error(f"Error reading traffic_data.csv: {e}")
        reports['code06'] = {'error': str(e)}

    # Code07: congestion_model.pkl و encoders.pkl
    try:
        model_path = RESULT_DIR / "congestion_model.pkl"
        encoders_path = RESULT_DIR / "encoders.pkl"
        if model_path.exists() and encoders_path.exists():
            reports['code07'] = {'status': 'Model and encoders trained successfully'}
            detailed_data['code07'] = [['congestion_model.pkl', 'exists'], ['encoders.pkl', 'exists']]
            detailed_columns['code07'] = ['File', 'Status']
        else:
            errors = []
            if not model_path.exists():
                errors.append('congestion_model.pkl not found')
            if not encoders_path.exists():
                errors.append('encoders.pkl not found')
            reports['code07'] = {'error': '; '.join(errors)}
    except Exception as e:
        logging.error(f"Error checking congestion_model.pkl and encoders.pkl: {e}")
        reports['code07'] = {'error': str(e)}

    # Code08: traffic_report.db
    try:
        db_path = RESULT_DIR / "traffic_report.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            if table_exists(conn, 'traffic_report'):
                c = conn.cursor()
                # داده‌های دقیق
                c.execute("SELECT report_type, node_id, value, details, timestamp FROM traffic_report ORDER BY timestamp DESC LIMIT 50")
                rows = c.fetchall()
                detailed_data['code08'] = rows
                detailed_columns['code08'] = ['Report Type', 'Node ID', 'Value', 'Details', 'Timestamp']
                reports['code08'] = {'status': 'Data retrieved successfully'}
            else:
                reports['code08'] = {'error': 'Table "traffic_report" not found in traffic_report.db'}
            conn.close()
        else:
            reports['code08'] = {'error': 'traffic_report.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading traffic_report.db: {e}")
        reports['code08'] = {'error': str(e)}

    # Code09: smart_traffic.db
    try:
        db_path = RESULT_DIR / "smart_traffic.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            if table_exists(conn, 'smart_traffic'):
                c = conn.cursor()
                # داده‌های دقیق
                c.execute("SELECT node_id, congestion_level, predicted_congestion, timestamp FROM smart_traffic ORDER BY timestamp DESC LIMIT 50")
                rows = c.fetchall()
                detailed_data['code09'] = rows
                detailed_columns['code09'] = ['Node ID', 'Congestion Level', 'Predicted Congestion', 'Timestamp']
                reports['code09'] = {'status': 'Data retrieved successfully'}
            else:
                reports['code09'] = {'error': 'Table "smart_traffic" not found in smart_traffic.db'}
            conn.close()
        else:
            reports['code09'] = {'error': 'smart_traffic.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading smart_traffic.db: {e}")
        reports['code09'] = {'error': str(e)}

    # Code10: self_healing.db
    try:
        db_path = RESULT_DIR / "self_healing.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            if table_exists(conn, 'healing_network'):
                c = conn.cursor()
                # داده‌های دقیق
                c.execute("SELECT node_id, congestion_level, healing_action, timestamp FROM healing_network ORDER BY timestamp DESC LIMIT 50")
                rows = c.fetchall()
                detailed_data['code10'] = rows
                detailed_columns['code10'] = ['Node ID', 'Congestion Level', 'Healing Action', 'Timestamp']
                reports['code10'] = {'status': 'Data retrieved successfully'}
            else:
                reports['code10'] = {'error': 'Table "healing_network" not found in self_healing.db'}
            conn.close()
        else:
            reports['code10'] = {'error': 'self_healing.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading self_healing.db: {e}")
        reports['code10'] = {'error': str(e)}

    # Code11: optimized_resources.db
    try:
        db_path = RESULT_DIR / "optimized_resources.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            if table_exists(conn, 'optimized_resources'):
                c = conn.cursor()
                # داده‌های دقیق
                c.execute("SELECT node_id, congestion_level, resource_allocation, traffic_volume, timestamp FROM optimized_resources ORDER BY timestamp DESC LIMIT 50")
                rows = c.fetchall()
                detailed_data['code11'] = rows
                detailed_columns['code11'] = ['Node ID', 'Congestion Level', 'Resource Allocation', 'Traffic Volume', 'Timestamp']
                reports['code11'] = {'status': 'Data retrieved successfully'}
            else:
                reports['code11'] = {'error': 'Table "optimized_resources" not found in optimized_resources.db'}
            conn.close()
        else:
            reports['code11'] = {'error': 'optimized_resources.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading optimized_resources.db: {e}")
        reports['code11'] = {'error': str(e)}

    # Code12: predictive_analysis.db
    try:
        db_path = RESULT_DIR / "predictive_analysis.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            if table_exists(conn, 'predictive_analysis'):
                c = conn.cursor()
                # داده‌های دقیق
                c.execute("SELECT node_id, actual_congestion, predicted_congestion, anomaly_detected, timestamp FROM predictive_analysis ORDER BY timestamp DESC LIMIT 50")
                rows = c.fetchall()
                detailed_data['code12'] = rows
                detailed_columns['code12'] = ['Node ID', 'Actual Congestion', 'Predicted Congestion', 'Anomaly Detected', 'Timestamp']
                reports['code12'] = {'status': 'Data retrieved successfully'}
            else:
                reports['code12'] = {'error': 'Table "predictive_analysis" not found in predictive_analysis.db'}
            conn.close()
        else:
            reports['code12'] = {'error': 'predictive_analysis.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading predictive_analysis.db: {e}")
        reports['code12'] = {'error': str(e)}

    return reports, detailed_data, detailed_columns

# مسیرهای Flask
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report/<code>', methods=['GET'])
def report_code(code):
    if code not in SCRIPTS:
        return jsonify({'error': f'Invalid code: {code}'}), 404
    
    reports, detailed_data, detailed_columns = get_reports()
    
    # فقط گزارش مربوط به کد مورد نظر را انتخاب می‌کنیم
    report = reports.get(code, {'error': f'No data available for {code}'})
    data = detailed_data.get(code, [])
    columns = detailed_columns.get(code, ['Metric', 'Value'])
    
    return render_template('report.html', 
                         report=report,
                         detailed_data=data,
                         detailed_columns=columns,
                         code=code)

@app.route('/traffic_data', methods=['GET'])
def traffic_data():
    try:
        db_path = RESULT_DIR / "traffic_data.db"
        if not db_path.exists():
            return jsonify({'error': 'traffic_data.db not found'})
        
        conn = sqlite3.connect(db_path)
        if not table_exists(conn, 'blocks'):
            conn.close()
            return jsonify({'error': 'Table "blocks" not found in traffic_data.db'})
        
        c = conn.cursor()
        
        c.execute("SELECT timestamp, traffic_volume, network_health, latency FROM blocks ORDER BY timestamp DESC LIMIT 100")
        rows = c.fetchall()
        
        timestamps = [row[0] for row in rows]
        volumes = [row[1] for row in rows]
        health_scores = {'Good': 0, 'Fair': 0, 'Moderate': 0, 'Poor': 0, 'Bad': 0}
        for row in rows:
            health = row[2]
            if health in health_scores:
                health_scores[health] += 1
        latencies = [row[3] for row in rows]
        
        c.execute("SELECT traffic_type, COUNT(*) FROM blocks GROUP BY traffic_type")
        type_data = c.fetchall()
        traffic_types = [row[0] for row in type_data]
        type_counts = [row[1] for row in type_data]
        
        conn.close()
        
        return jsonify({
            'timestamps': timestamps,
            'volumes': volumes,
            'network_health_scores': [health_scores['Good'], health_scores['Fair'], health_scores['Moderate'], health_scores['Poor'], health_scores['Bad']],
            'latencies': latencies,
            'traffic_types': traffic_types,
            'type_counts': type_counts
        })
    except sqlite3.Error as e:
        logging.error(f"Error reading traffic_data.db: {e}")
        return jsonify({'error': str(e)})

@app.route('/predictions', methods=['GET'])
def predictions():
    try:
        db_path = RESULT_DIR / "predictive_analysis.db"
        if not db_path.exists():
            return jsonify({'error': 'predictive_analysis.db not found'})
        
        conn = sqlite3.connect(db_path)
        if not table_exists(conn, 'predictive_analysis'):
            conn.close()
            return jsonify({'error': 'Table "predictive_analysis" not found in predictive_analysis.db'})
        
        c = conn.cursor()
        
        c.execute("SELECT node_id, actual_congestion, predicted_congestion FROM predictive_analysis ORDER BY timestamp DESC LIMIT 50")
        rows = c.fetchall()
        
        node_ids = [row[0] for row in rows]
        actual_congestion = [row[1] for row in rows]
        predicted_congestion = [row[2] for row in rows]
        
        conn.close()
        
        return jsonify({
            'node_ids': node_ids,
            'actual_congestion': actual_congestion,
            'predicted_congestion': predicted_congestion
        })
    except sqlite3.Error as e:
        logging.error(f"Error reading predictive_analysis.db: {e}")
        return jsonify({'error': str(e)})

@app.route('/traffic_report_data', methods=['GET'])
def traffic_report_data():
    try:
        db_path = RESULT_DIR / "traffic_report.db"
        if not db_path.exists():
            return jsonify({'error': 'traffic_report.db not found'})
        
        conn = sqlite3.connect(db_path)
        if not table_exists(conn, 'traffic_report'):
            conn.close()
            return jsonify({'error': 'Table "traffic_report" not found in traffic_report.db'})
        
        c = conn.cursor()
        
        c.execute("SELECT timestamp, value FROM traffic_report WHERE report_type = 'daily_average' ORDER BY timestamp DESC LIMIT 30")
        daily_avg = c.fetchall() or [(datetime.now().isoformat(), 0)] * 30
        
        c.execute("SELECT timestamp, value FROM traffic_report WHERE report_type = 'high_traffic' ORDER BY timestamp DESC LIMIT 30")
        daily_max = c.fetchall() or [(datetime.now().isoformat(), 0)] * 30
        
        c.execute("SELECT timestamp, value FROM traffic_report WHERE report_type = 'low_traffic' ORDER BY timestamp DESC LIMIT 30")
        daily_min = c.fetchall() or [(datetime.now().isoformat(), 0)] * 30
        
        c.execute("SELECT timestamp, details FROM traffic_report WHERE report_type = 'health_impact' ORDER BY timestamp DESC LIMIT 30")
        health_trend = c.fetchall() or [(datetime.now().isoformat(), 'good')] * 30
        
        conn.close()
        
        return jsonify({
            'timestamps': [row[0] for row in daily_avg],
            'daily_avg_traffic': [row[1] for row in daily_avg],
            'daily_max_traffic': [row[1] for row in daily_max],
            'daily_min_traffic': [row[1] for row in daily_min],
            'health_trend': [row[1] for row in health_trend]
        })
    except sqlite3.Error as e:
        logging.error(f"Error reading traffic_report.db: {e}")
        return jsonify({'error': str(e)})

@app.route('/add_new_order', methods=['POST'])
def add_new_order():
    try:
        data = request.form
        node_id = data.get('node_id')
        traffic_type = data.get('traffic_type')
        traffic_volume = float(data.get('traffic_volume'))
        network_health = data.get('network_health')
        latency = float(data.get('latency'))
        
        if not all([node_id, traffic_type, traffic_volume >= 0, network_health, latency >= 0]):
            return jsonify({'error': 'Invalid or missing data'})
        
        db_path = RESULT_DIR / "new_orders.db"
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS new_orders (
                node_id TEXT,
                traffic_type TEXT,
                traffic_volume REAL,
                network_health TEXT,
                latency REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                order_type TEXT DEFAULT 'Standard',
                congestion_level TEXT DEFAULT 'Low'
            )
        """)
        
        c.execute("""
            INSERT INTO new_orders (node_id, traffic_type, traffic_volume, network_health, latency)
            VALUES (?, ?, ?, ?, ?)
        """, (node_id, traffic_type, traffic_volume, network_health, latency))
        
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Error adding new order: {e}")
        return jsonify({'error': str(e)})

@app.route('/export/pdf/<report_type>', methods=['GET'])
def export_pdf(report_type):
    try:
        reports, detailed_data, detailed_columns = get_reports()
        report = reports.get(report_type, {'error': f'No data available for {report_type}'})
        data = detailed_data.get(report_type, [])
        columns = detailed_columns.get(report_type, ['Metric', 'Value'])
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica", 12)
        y = 750
        
        c.drawString(100, y, f"Traffic Report - {report_type}")
        y -= 30
        
        if 'error' in report:
            c.drawString(100, y, f"Error: {report['error']}")
        else:
            # نوشتن ستون‌ها
            x = 100
            for col in columns:
                c.drawString(x, y, str(col))
                x += 100
            y -= 20
            
            # نوشتن داده‌ها
            for row in data:
                x = 100
                for cell in row:
                    c.drawString(x, y, str(cell))
                    x += 100
                y -= 20
                if y < 50:
                    c.showPage()
                    y = 750
                    x = 100
                    for col in columns:
                        c.drawString(x, y, str(col))
                        x += 100
                    y -= 20
        
        c.showPage()
        c.save()
        buffer.seek(0)
        
        return send_file(buffer, as_attachment=True, download_name=f"{report_type}_report.pdf", mimetype='application/pdf')
    except Exception as e:
        logging.error(f"Error exporting PDF for {report_type}: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/export/excel/<report_type>', methods=['GET'])
def export_excel(report_type):
    try:
        reports, detailed_data, detailed_columns = get_reports()
        report = reports.get(report_type, {'error': f'No data available for {report_type}'})
        data = detailed_data.get(report_type, [])
        columns = detailed_columns.get(report_type, ['Metric', 'Value'])
        
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        worksheet = workbook.add_worksheet()
        
        worksheet.write(0, 0, f"Traffic Report - {report_type}")
        row = 2
        
        if 'error' in report:
            worksheet.write(row, 0, "Error")
            worksheet.write(row, 1, report['error'])
        else:
            # نوشتن ستون‌ها
            for col_idx, col in enumerate(columns):
                worksheet.write(row, col_idx, col)
            row += 1
            
            # نوشتن داده‌ها
            for row_idx, row_data in enumerate(data, start=row):
                for col_idx, cell in enumerate(row_data):
                    worksheet.write(row_idx, col_idx, str(cell))
        
        workbook.close()
        buffer.seek(0)
        
        return send_file(buffer, as_attachment=True, download_name=f"{report_type}_report.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logging.error(f"Error exporting Excel for {report_type}: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/run_project', methods=['POST'])
def run_project():
    if running_scripts:
        logging.warning("A project run is already in progress")
        return jsonify({'status': 'error', 'message': "A project run is already in progress"})
    
    def run_all_scripts():
        for code in sorted(SCRIPTS.keys()):
            if code in running_scripts:
                logging.warning(f"Module {code} is already running, skipping...")
                socketio.emit('output', f"Module {code} is already running, skipping...")
                continue
            if not script_locks[code].acquire(blocking=False):
                logging.warning(f"Module {code} is locked, skipping...")
                socketio.emit('output', f"Module {code} is locked, skipping...")
                continue
            running_scripts.add(code)
            try:
                socketio.emit('output', f"Starting {code}...")
                run_script(code, socketio)
            except Exception as e:
                error_msg = f"Stopped project execution at {code} due to error: {str(e)}"
                logging.error(error_msg)
                socketio.emit('output', error_msg)
            finally:
                running_scripts.discard(code)
                if script_locks[code].locked():
                    script_locks[code].release()
                    logging.info(f"Lock for {code} released in run_project")
    
    threading.Thread(target=run_all_scripts, daemon=True).start()
    return jsonify({'status': 'started'})

@app.route('/run_module/<code>', methods=['POST'])
def run_module(code):
    if code not in SCRIPTS:
        logging.warning(f"Invalid module code: {code}")
        return jsonify({'status': 'error', 'message': f"Invalid module code: {code}"})
    
    if code in running_scripts:
        logging.warning(f"Module {code} is already running")
        return jsonify({'status': 'error', 'message': f"Module {code} is already running"})
    
    if not script_locks[code].acquire(blocking=False):
        logging.warning(f"Module {code} is locked")
        return jsonify({'status': 'error', 'message': f"Module {code} is locked"})
    
    running_scripts.add(code)
    
    def run_single_script():
        try:
            run_script(code, socketio)
        except Exception as e:
            error_msg = f"Error running {code}: {str(e)}"
            logging.error(error_msg)
            socketio.emit('output', error_msg)
        finally:
            running_scripts.discard(code)
            if script_locks[code].locked():
                script_locks[code].release()
                logging.info(f"Lock for {code} released in run_module")
    
    threading.Thread(target=run_single_script, daemon=True).start()
    return jsonify({'status': 'started'})

# سوکت برای ارسال خروجی در زمان واقعی
@socketio.on('connect')
def handle_connect():
    logging.info("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    logging.info("Client disconnected")

# اجرای سرور
if __name__ == '__main__':
    local_ip = get_local_ip()
    logging.info("Starting Flask-SocketIO server...")
    logging.info(f"Server running at http://127.0.0.1:5000")
    logging.info(f"Server also available at http://{local_ip}:5000")
    socketio.run(app, host='0.0.0.0', port=5000)