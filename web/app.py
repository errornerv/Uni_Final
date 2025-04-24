import gevent
from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import subprocess
import sqlite3
from pathlib import Path
import threading
import logging
import os
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# تنظیمات لاگینگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# مسیر ریشه پروژه
ROOT_DIR = Path(__file__).resolve().parent.parent  # به C:\Programming\Git-Hub\Uni_Final اشاره می‌کنه
RESULT_DIR = ROOT_DIR / "result"

# ایجاد دایرکتوری result اگر وجود ندارد
if not RESULT_DIR.exists():
    RESULT_DIR.mkdir()

# لیست اسکریپت‌ها با مسیرهای اصلاح‌شده
SCRIPTS = {
    'code01': str(Path("src/blockchain/code01_blockchain_initial_data.py")),
    'code02': str(Path("src/blockchain/code02_blockchain_congestion_improved.py")),
    'code03': str(Path("src/blockchain/code03_blockchain_managed_traffic.py")),
    'code04': str(Path("src/blockchain/code04_blockchain_with_new_orders.py")),
    'code05': str(Path("src/blockchain/code05_blockchain_with_real_time_orders.py")),
    'code06': str(Path("src/traffic/code06_traffic_data_preparation.py")),
    'code07': str(Path("src/traffic/code07_model_training.py")),
    'code08': str(Path("src/traffic/code08_advanced_traffic_report.py")),
    'code09': str(Path("src/smart/code09_smart_traffic_management.py")),
    'code10': str(Path("src/smart/code10_self_healing_network.py")),
    'code11': str(Path("src/smart/code11_resource_optimization.py")),
    'code12': str(Path("src/smart/code12_predictive_analysis_and_anomaly_detection.py"))
}

# تابع برای اجرای اسکریپت و ارسال خروجی لایو
def run_script(script_name, socketio):
    script_path = ROOT_DIR / script_name
    logging.info(f"Attempting to run script: {script_path}")
    
    if not script_path.exists():
        logging.error(f"Script not found: {script_path}")
        socketio.emit('output', f"Error: Script {script_name} not found")
        return
    
    try:
        process = subprocess.Popen(
            ['python', str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        while True:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()
            
            if stdout_line:
                logging.info(f"Script output: {stdout_line.strip()}")
                socketio.emit('output', stdout_line.strip())
            if stderr_line:
                logging.error(f"Script error: {stderr_line.strip()}")
                socketio.emit('output', f"ERROR: {stderr_line.strip()}")
            
            if process.poll() is not None:
                break
        
        socketio.emit('output', f"Script {script_name} execution completed")
        logging.info(f"Script {script_name} execution completed")
    except Exception as e:
        logging.error(f"Error running script {script_name}: {e}")
        socketio.emit('output', f"Error running {script_name}: {str(e)}")

# تابع برای گرفتن گزارش‌ها از دیتابیس‌ها
def get_reports(node_id='', traffic_type='', time_range='', network_health=''):
    reports = {}
    
    # فیلترهای SQL
    where_clauses = []
    params = []
    if node_id:
        where_clauses.append("node_id = ?")
        params.append(node_id)
    if traffic_type:
        where_clauses.append("traffic_type = ?")
        params.append(traffic_type)
    if network_health:
        where_clauses.append("network_health = ?")
        params.append(network_health)
    if time_range:
        if time_range == '24h':
            where_clauses.append("timestamp >= datetime('now', '-1 day')")
        elif time_range == '7d':
            where_clauses.append("timestamp >= datetime('now', '-7 days')")
        elif time_range == '30d':
            where_clauses.append("timestamp >= datetime('now', '-30 days')")
    
    where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # گزارش برای code01
    try:
        db_path = RESULT_DIR / "traffic_data.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM blocks {where_clause} AND traffic_volume > 70", params)
            congested = c.fetchone()[0]
            c.execute(f"SELECT AVG(traffic_volume) FROM blocks {where_clause}", params)
            avg_traffic = c.fetchone()[0] or 0.0
            c.execute(f"SELECT COUNT(*) FROM blocks {where_clause}", params)
            total_blocks = c.fetchone()[0]
            reports['code01'] = {
                'total_blocks': total_blocks,
                'congested_points': congested,
                'avg_traffic': round(avg_traffic, 2)
            }
            conn.close()
        else:
            reports['code01'] = {'error': 'traffic_data.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading traffic_data.db: {e}")
        reports['code01'] = {'error': str(e)}
    
    # گزارش برای code02
    try:
        db_path = RESULT_DIR / "congestion_data.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM congestion_blocks {where_clause} AND congestion_level = 'High'", params)
            high_congestion = c.fetchone()[0]
            c.execute(f"SELECT AVG(congestion_score) FROM congestion_blocks {where_clause}", params)
            avg_score = c.fetchone()[0] or 0.0
            reports['code02'] = {
                'high_congestion': high_congestion,
                'avg_congestion_score': round(avg_score, 2)
            }
            conn.close()
        else:
            reports['code02'] = {'error': 'congestion_data.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading congestion_data.db: {e}")
        reports['code02'] = {'error': str(e)}
    
    # گزارش برای code03
    try:
        db_path = RESULT_DIR / "managed_traffic.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM managed_blocks {where_clause} AND congestion_level IN ('Medium', 'High')", params)
            congested_blocks = c.fetchone()[0]
            reports['code03'] = {'congested_blocks': congested_blocks}
            conn.close()
        else:
            reports['code03'] = {'error': 'managed_traffic.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading managed_traffic.db: {e}")
        reports['code03'] = {'error': str(e)}
    
    # گزارش برای code04
    try:
        db_path = RESULT_DIR / "new_orders.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM new_orders {where_clause} AND order_type = 'Priority'", params)
            priority_orders = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM new_orders {where_clause} AND congestion_level IN ('Medium', 'High')", params)
            total_congested = c.fetchone()[0]
            reports['code04'] = {
                'priority_orders': priority_orders,
                'total_congested': total_congested
            }
            conn.close()
        else:
            reports['code04'] = {'error': 'new_orders.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading new_orders.db: {e}")
        reports['code04'] = {'error': str(e)}
    
    # گزارش برای code05
    try:
        db_path = RESULT_DIR / "real_time_orders.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM real_time_orders {where_clause} AND order_type = 'Priority'", params)
            priority_orders = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM real_time_orders {where_clause} AND congestion_level IN ('Medium', 'High')", params)
            total_congested = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM real_time_orders {where_clause}", params)
            total_blocks = c.fetchone()[0]
            reports['code05'] = {
                'total_blocks': total_blocks,
                'priority_orders': priority_orders,
                'total_congested': total_congested
            }
            conn.close()
        else:
            reports['code05'] = {'error': 'real_time_orders.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading real_time_orders.db: {e}")
        reports['code05'] = {'error': str(e)}
    
    # گزارش برای code06
    try:
        csv_path = RESULT_DIR / "traffic_data.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            if node_id:
                df = df[df['node_id'] == node_id]
            if traffic_type:
                df = df[df['traffic_type'] == traffic_type]
            if time_range:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                if time_range == '24h':
                    df = df[df['timestamp'] >= pd.Timestamp.now() - pd.Timedelta(days=1)]
                elif time_range == '7d':
                    df = df[df['timestamp'] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
                elif time_range == '30d':
                    df = df[df['timestamp'] >= pd.Timestamp.now() - pd.Timedelta(days=30)]
            reports['code06'] = {
                'total_rows': len(df),
                'avg_traffic_volume': round(df['traffic_volume'].mean(), 2) if 'traffic_volume' in df else 0.0
            }
        else:
            reports['code06'] = {'error': 'traffic_data.csv not found'}
    except Exception as e:
        logging.error(f"Error reading traffic_data.csv: {e}")
        reports['code06'] = {'error': str(e)}
    
    # گزارش برای code07
    try:
        model_path = RESULT_DIR / "congestion_model.pkl"
        if model_path.exists():
            reports['code07'] = {'status': 'Model trained successfully'}
        else:
            reports['code07'] = {'error': 'congestion_model.pkl not found'}
    except Exception as e:
        logging.error(f"Error checking congestion_model.pkl: {e}")
        reports['code07'] = {'error': str(e)}
    
    # گزارش برای code08
    try:
        db_path = RESULT_DIR / "traffic_report.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(f"SELECT report_type, node_id, value, details FROM traffic_report {where_clause}", params)
            traffic_reports = c.fetchall()
            reports['code08'] = {
                'daily_averages': [],
                'health_impacts': [],
                'high_traffic_nodes': []
            }
            for report_type, node_id, value, details in traffic_reports:
                if report_type == 'daily_average':
                    reports['code08']['daily_averages'].append({'node': node_id, 'value': round(value, 2)})
                elif report_type == 'health_impact':
                    reports['code08']['health_impacts'].append({'health': node_id, 'value': round(value, 2), 'details': details})
                elif report_type == 'high_traffic':
                    reports['code08']['high_traffic_nodes'].append(details)
            conn.close()
        else:
            reports['code08'] = {'error': 'traffic_report.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading traffic_report.db: {e}")
        reports['code08'] = {'error': str(e)}
    
    # گزارش برای code09
    try:
        db_path = RESULT_DIR / "smart_traffic.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM smart_traffic {where_clause}", params)
            total_blocks = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM smart_traffic {where_clause} AND congestion_level = 'High'", params)
            high_congestion = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM smart_traffic {where_clause} AND congestion_level = predicted_congestion", params)
            accurate_predictions = c.fetchone()[0]
            accuracy = (accurate_predictions / total_blocks * 100) if total_blocks > 0 else 0
            reports['code09'] = {
                'total_blocks': total_blocks,
                'high_congestion': high_congestion,
                'prediction_accuracy': round(accuracy, 2)
            }
            conn.close()
        else:
            reports['code09'] = {'error': 'smart_traffic.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading smart_traffic.db: {e}")
        reports['code09'] = {'error': str(e)}
    
    # گزارش برای code10
    try:
        db_path = RESULT_DIR / "self_healing.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM healing_network {where_clause}", params)
            total_blocks = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM healing_network {where_clause} AND congestion_level = 'High'", params)
            high_congestion = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM healing_network {where_clause} AND healing_action != 'None'", params)
            self_heal_actions = c.fetchone()[0]
            reports['code10'] = {
                'total_blocks': total_blocks,
                'high_congestion': high_congestion,
                'self_heal_actions': self_heal_actions
            }
            conn.close()
        else:
            reports['code10'] = {'error': 'self_healing.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading self_healing.db: {e}")
        reports['code10'] = {'error': str(e)}
    
    # گزارش برای code11
    try:
        db_path = RESULT_DIR / "optimized_resources.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM optimized_resources {where_clause}", params)
            total_blocks = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM optimized_resources {where_clause} AND congestion_level = 'High'", params)
            high_congestion = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM optimized_resources {where_clause} AND resource_allocation != 'No resource optimization needed'", params)
            resource_allocations = c.fetchone()[0]
            c.execute(f"SELECT DISTINCT node_id FROM optimized_resources {where_clause} AND traffic_volume > 50", params)
            high_traffic_nodes = [row[0] for row in c.fetchall()]
            reports['code11'] = {
                'total_blocks': total_blocks,
                'high_congestion': high_congestion,
                'resource_allocations': resource_allocations,
                'high_traffic_nodes': high_traffic_nodes
            }
            conn.close()
        else:
            reports['code11'] = {'error': 'optimized_resources.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading optimized_resources.db: {e}")
        reports['code11'] = {'error': str(e)}
    
    # گزارش برای code12
    try:
        db_path = RESULT_DIR / "predictive_analysis.db"
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute(f"SELECT COUNT(*) FROM predictive_analysis {where_clause}", params)
            total_predictions = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM predictive_analysis {where_clause} AND anomaly_detected = 1", params)
            anomalies_detected = c.fetchone()[0]
            reports['code12'] = {
                'total_predictions': total_predictions,
                'anomalies_detected': anomalies_detected
            }
            conn.close()
        else:
            reports['code12'] = {'error': 'predictive_analysis.db not found'}
    except sqlite3.Error as e:
        logging.error(f"Error reading predictive_analysis.db: {e}")
        reports['code12'] = {'error': str(e)}
    
    return reports

# مسیرهای Flask
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report/<report_type>', methods=['GET'])
@app.route('/report', methods=['GET'])
def report(report_type='traffic_report'):
    node_id = request.args.get('node_id', '')
    traffic_type = request.args.get('traffic_type', '')
    time_range = request.args.get('time_range', '')
    network_health = request.args.get('network_health', '')
    
    reports = get_reports(node_id, traffic_type, time_range, network_health)
    
    # تبدیل گزارش‌ها به فرمت جدول
    columns = ['Code', 'Metric', 'Value']
    rows = []
    for code, report in reports.items():
        if 'error' in report:
            rows.append([code, 'Error', report['error']])
        else:
            for key, value in report.items():
                rows.append([code, key.replace('_', ' ').title(), str(value)])
    
    return render_template('report.html', 
                         reports=reports, 
                         report_type=report_type,
                         columns=columns,
                         rows=rows,
                         node_id=node_id,
                         traffic_type=traffic_type,
                         time_range=time_range,
                         network_health=network_health)

@app.route('/traffic_data', methods=['GET'])
def traffic_data():
    node_id = request.args.get('node_id', '')
    traffic_type = request.args.get('traffic_type', '')
    time_range = request.args.get('time_range', '')
    
    try:
        db_path = RESULT_DIR / "traffic_data.db"
        if not db_path.exists():
            return jsonify({'error': 'traffic_data.db not found'})
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        where_clauses = []
        params = []
        if node_id:
            where_clauses.append("node_id = ?")
            params.append(node_id)
        if traffic_type:
            where_clauses.append("traffic_type = ?")
            params.append(traffic_type)
        if time_range:
            if time_range == '24h':
                where_clauses.append("timestamp >= datetime('now', '-1 day')")
            elif time_range == '7d':
                where_clauses.append("timestamp >= datetime('now', '-7 days')")
            elif time_range == '30d':
                where_clauses.append("timestamp >= datetime('now', '-30 days')")
        
        where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # گرفتن داده‌ها
        c.execute(f"SELECT timestamp, traffic_volume, network_health, latency FROM blocks {where_clause} ORDER BY timestamp DESC LIMIT 100", params)
        rows = c.fetchall()
        
        timestamps = [row[0] for row in rows]
        volumes = [row[1] for row in rows]
        health_scores = {'Good': 0, 'Fair': 0, 'Moderate': 0, 'Poor': 0, 'Bad': 0}
        for row in rows:
            health = row[2]
            if health in health_scores:
                health_scores[health] += 1
        latencies = [row[3] for row in rows]
        
        # گرفتن انواع ترافیک
        c.execute(f"SELECT traffic_type, COUNT(*) FROM blocks {where_clause} GROUP BY traffic_type", params)
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
    node_id = request.args.get('node_id', '')
    time_range = request.args.get('time_range', '')
    
    try:
        db_path = RESULT_DIR / "predictive_analysis.db"
        if not db_path.exists():
            return jsonify({'error': 'predictive_analysis.db not found'})
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        where_clauses = []
        params = []
        if node_id:
            where_clauses.append("node_id = ?")
            params.append(node_id)
        if time_range:
            if time_range == '24h':
                where_clauses.append("timestamp >= datetime('now', '-1 day')")
            elif time_range == '7d':
                where_clauses.append("timestamp >= datetime('now', '-7 days')")
            elif time_range == '30d':
                where_clauses.append("timestamp >= datetime('now', '-30 days')")
        
        where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        c.execute(f"SELECT node_id, actual_congestion, predicted_congestion FROM predictive_analysis {where_clause} ORDER BY timestamp DESC LIMIT 50", params)
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
        c = conn.cursor()
        
        c.execute("SELECT timestamp, value FROM traffic_report WHERE report_type = 'daily_average' ORDER BY timestamp DESC LIMIT 30")
        daily_avg = c.fetchall()
        
        c.execute("SELECT timestamp, value FROM traffic_report WHERE report_type = 'high_traffic' ORDER BY timestamp DESC LIMIT 30")
        daily_max = c.fetchall()
        
        c.execute("SELECT timestamp, value FROM traffic_report WHERE report_type = 'low_traffic' ORDER BY timestamp DESC LIMIT 30")
        daily_min = c.fetchall()
        
        c.execute("SELECT timestamp, details FROM traffic_report WHERE report_type = 'health_impact' ORDER BY timestamp DESC LIMIT 30")
        health_trend = c.fetchall()
        
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
        latency = float(data.get('traffic_volume'))
        
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
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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
    return jsonify({'status': 'error', 'message': 'PDF export not implemented yet'})

@app.route('/export/excel/<report_type>', methods=['GET'])
def export_excel(report_type):
    return jsonify({'status': 'error', 'message': 'Excel export not implemented yet'})

@app.route('/run_project', methods=['POST'])
def run_project():
    def run_all_scripts():
        for code, script_name in SCRIPTS.items():
            socketio.emit('output', f"Starting {script_name}...")
            run_script(script_name, socketio)
    
    threading.Thread(target=run_all_scripts, daemon=True).start()
    return jsonify({'status': 'started'})

@app.route('/run_module/<code>', methods=['POST'])
def run_module(code):
    if code not in SCRIPTS:
        logging.error(f"Invalid module requested: {code}")
        return jsonify({'status': 'error', 'message': f"Invalid module: {code}"})
    
    threading.Thread(target=run_script, args=(SCRIPTS[code], socketio), daemon=True).start()
    return jsonify({'status': 'started'})

# مدیریت WebSocket
@socketio.on('connect')
def handle_connect():
    logging.info('Client connected to WebSocket')
    socketio.emit('output', 'Connected to WebSocket server')

@socketio.on('disconnect')
def handle_disconnect():
    logging.info('Client disconnected from WebSocket')

if __name__ == '__main__':
    logging.info('Starting Flask-SocketIO server...')
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)