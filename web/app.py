from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO
import subprocess
import os
import sqlite3
import psutil
import random
from datetime import datetime, timedelta
import logging
import hashlib
import json

# تنظیم دایرکتوری static به صورت نسبی
# app.py توی Uni_Final/web هست، پس دایرکتوری static توی Uni_Final/web/static قرار داره
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app = Flask(__name__, static_folder=static_path)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# لاگ کردن مسیر دایرکتوری static موقع شروع
logger.info(f"Static folder set to: {app.static_folder}")

# چک کردن وجود فایل styles.css
styles_path = os.path.join(app.static_folder, 'styles.css')
if os.path.exists(styles_path):
    logger.info("styles.css found in static folder!")
else:
    logger.error("styles.css NOT found in static folder! Check the path.")

processes = {}
stop_reading_flags = {}

# گراف نودها (از code04_blockchain_with_new_orders.py)
nodes = [f"Node_{i}" for i in range(1, 11)]
graph = {node: {"neighbors": random.sample(nodes, random.randint(1, 3)), 
                "weights": [random.uniform(1, 5) for _ in range(random.randint(1, 3))]} 
         for node in nodes}

# مسیر دیتابیس (از code04_blockchain_with_new_orders.py)
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
output_db = os.path.join(base_dir, 'result', 'new_orders.db')

# کلاس NewOrderBlock (از code04_blockchain_with_new_orders.py)
class NewOrderBlock:
    def __init__(self, timestamp, node_id, traffic_layer, health_layer, previous_hash, congestion_layer=None, 
                 traffic_suggestion=None, is_congestion_order=False):
        self.timestamp = timestamp
        self.node_id = node_id
        self.traffic_layer = traffic_layer
        self.health_layer = health_layer
        self.previous_hash = previous_hash
        self.congestion_layer = congestion_layer or {"is_congested": 0, "score": 0.0, "impact": 0.0, "level": "Low"}
        self.traffic_suggestion = traffic_suggestion
        self.is_congestion_order = is_congestion_order
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
            "is_congestion_order": self.is_congestion_order
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# تابع ذخیره در دیتابیس (از code04_blockchain_with_new_orders.py)
def save_to_db(block):
    conn = sqlite3.connect(output_db)
    c = conn.cursor()
    c.execute("INSERT INTO new_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (block.timestamp, block.node_id, block.traffic_layer["type"], block.traffic_layer["volume"],
               block.health_layer["status"], block.health_layer["latency"], block.previous_hash, block.hash,
               block.congestion_layer["level"], block.congestion_layer["score"], block.congestion_layer["impact"],
               block.traffic_suggestion, 1 if block.is_congestion_order else 0))
    conn.commit()
    conn.close()


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

@app.route('/test-static')
def test_static():
    # لاگ کردن مسیر دایرکتوری static و فایل styles.css
    logger.debug(f"Static folder path: {app.static_folder}")
    styles_path = os.path.join(app.static_folder, 'styles.css')
    logger.debug(f"Looking for styles.css at: {styles_path}")
    if os.path.exists(styles_path):
        logger.debug("styles.css found!")
    else:
        logger.debug("styles.css NOT found!")
    return send_from_directory('static', 'styles.css')

@app.route('/run_script', methods=['POST'])
def run_script():
    script_id = request.form.get('script_id')
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    script_map = {
        '01': os.path.join(base_dir, 'src/blockchain/code01_blockchain_initial_data.py'),
        '02': os.path.join(base_dir, 'src/blockchain/code02_blockchain_congestion_improved.py'),
        '03': os.path.join(base_dir, 'src/blockchain/code03_blockchain_managed_traffic.py'),
        '04': os.path.join(base_dir, 'src/blockchain/code04_blockchain_with_new_orders.py'),
        '05': os.path.join(base_dir, 'src/blockchain/code05_blockchain_with_real_time_orders.py'),
        '06': os.path.join(base_dir, 'src/traffic/code06_traffic_data_preparation.py'),
        '07': os.path.join(base_dir, 'src/traffic/code07_model_training.py'),
        '08': os.path.join(base_dir, 'src/traffic/code08_advanced_traffic_report.py'),
        '09': os.path.join(base_dir, 'src/smart/code09_smart_traffic_management.py'),
        'self_healing': os.path.join(base_dir, 'src/smart/self_healing_network.py'),
        'init': os.path.join(base_dir, 'src/init__.py')
    }

    script_path = script_map.get(script_id)
    if script_path:
        if script_id in processes and processes[script_id].poll() is None:
            logger.warning(f"Script {script_id} is already running")
            return jsonify({'error': 'Script is already running'})

        try:
            def run_and_emit():
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"

                process = subprocess.Popen(
                    ['python', script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    env=env
                )
                processes[script_id] = process
                stop_reading_flags[script_id] = False

                socketio.emit('script_status', {'status': 'running', 'script_id': script_id}, namespace='/')

                while True:
                    if stop_reading_flags.get(script_id, False):
                        break
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        if "Debugger is active" in line or "Debugger PIN" in line:
                            continue
                        socketio.emit('script_output', {'script_id': script_id, 'output': line.strip()}, namespace='/')

                while True:
                    if stop_reading_flags.get(script_id, False):
                        break
                    line = process.stderr.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        if "Debugger is active" in line or "Debugger PIN" in line:
                            continue
                        socketio.emit('script_output', {'script_id': script_id, 'output': f"Error: {line.strip()}"}, namespace='/')

                if not stop_reading_flags.get(script_id, False):
                    socketio.emit('script_output', {'script_id': script_id, 'output': 'Script executed successfully.'}, namespace='/')
                    report_link = None
                    if script_id in ['01', '02', '03', '04']:
                        report_link = f"/report/{script_id}"
                    socketio.emit('report_link', {'script_id': script_id, 'report_link': report_link}, namespace='/')
                    socketio.emit('script_status', {'status': 'stopped', 'script_id': script_id}, namespace='/')

                if script_id in processes:
                    del processes[script_id]
                if script_id in stop_reading_flags:
                    del stop_reading_flags[script_id]

            socketio.start_background_task(run_and_emit)
            logger.info(f"Started script {script_id}")
            return jsonify({'output': 'Script is running...', 'report_link': None})
        except Exception as e:
            logger.error(f"Error running script {script_id}: {str(e)}")
            return jsonify({'error': str(e)})
    else:
        logger.warning(f"Invalid script ID: {script_id}")
        return jsonify({'error': 'Invalid script ID'})

@app.route('/stop_all_scripts', methods=['POST'])
def stop_all_scripts():
    logger.info("Received request to stop all scripts")
    if not processes:
        logger.info("No scripts are running")
        socketio.emit('script_status', {'status': 'stopped_all', 'message': 'No scripts are running.'}, namespace='/')
        return jsonify({'output': 'No scripts are running.'})

    stopped_scripts = []
    for script_id, process in list(processes.items()):
        try:
            logger.info(f"Attempting to stop script {script_id} with PID {process.pid}")
            stop_reading_flags[script_id] = True

            if process.poll() is None:
                parent = psutil.Process(process.pid)
                for child in parent.children(recursive=True):
                    logger.debug(f"Terminating child process {child.pid}")
                    child.kill()
                parent.kill()
                try:
                    parent.wait(timeout=1)
                    logger.info(f"Script {script_id} terminated successfully")
                except psutil.TimeoutExpired:
                    logger.warning(f"Script {script_id} did not terminate, killing it again")
                    parent.kill()
            stopped_scripts.append(script_id)
        except Exception as e:
            logger.error(f"Error stopping script {script_id}: {str(e)}")
        finally:
            if script_id in processes:
                del processes[script_id]
            if script_id in stop_reading_flags:
                del stop_reading_flags[script_id]

    logger.info(f"Stopped scripts: {stopped_scripts}")
    socketio.emit('script_status', {'status': 'stopped_all', 'stopped_scripts': stopped_scripts}, namespace='/')
    return jsonify({'output': f"Stopped scripts: {', '.join(stopped_scripts) if stopped_scripts else 'None'}"})

@app.route('/stop_script', methods=['POST'])
def stop_script():
    script_id = request.form.get('script_id')
    if script_id not in processes:
        logger.warning(f"Script {script_id} is not running")
        return jsonify({'error': 'Script is not running'})

    try:
        stop_reading_flags[script_id] = True
        process = processes[script_id]
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
        socketio.emit('script_status', {'status': 'stopped', 'script_id': script_id}, namespace='/')
        if script_id in processes:
            del processes[script_id]
        if script_id in stop_reading_flags:
            del stop_reading_flags[script_id]
        logger.info(f"Script {script_id} stopped")
        return jsonify({'output': f'Script {script_id} stopped.'})
    except Exception as e:
        logger.error(f"Error stopping script {script_id}: {str(e)}")
        return jsonify({'error': str(e)})

@app.route('/force_stop_script', methods=['POST'])
def force_stop_script():
    script_id = request.form.get('script_id')
    if script_id not in processes:
        logger.warning(f"Script {script_id} is not running")
        return jsonify({'error': 'Script is not running'})

    try:
        stop_reading_flags[script_id] = True
        process = processes[script_id]
        if process.poll() is None:
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
            try:
                parent.wait(timeout=1)
            except psutil.TimeoutExpired:
                parent.kill()
        socketio.emit('script_status', {'status': 'stopped', 'script_id': script_id}, namespace='/')
        if script_id in processes:
            del processes[script_id]
        if script_id in stop_reading_flags:
            del stop_reading_flags[script_id]
        logger.info(f"Script {script_id} force stopped")
        return jsonify({'output': f'Script {script_id} force stopped.'})
    except Exception as e:
        logger.error(f"Error force stopping script {script_id}: {str(e)}")
        return jsonify({'error': str(e)})

def fetch_data_from_db(db_name, table_name, node_id='', traffic_type='', time_range='', network_health=''):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(base_dir, 'result', db_name)
    try:
        query = f"SELECT * FROM {table_name}"
        conditions = []
        params = []

        if node_id:
            conditions.append("node_id = ?")
            params.append(node_id)

        if traffic_type:
            conditions.append("traffic_type = ?")
            params.append(traffic_type)

        if time_range:
            now = datetime.now()
            if time_range == '1h':
                time_threshold = now - timedelta(hours=1)
            elif time_range == '24h':
                time_threshold = now - timedelta(hours=24)
            elif time_range == '7d':
                time_threshold = now - timedelta(days=7)
            else:
                time_threshold = None

            if time_threshold:
                conditions.append("timestamp >= ?")
                params.append(time_threshold.strftime('%Y-%m-%d %H:%M:%S'))

        if network_health:
            conditions.append("network_health = ?")
            params.append(network_health)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC"

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        columns = [description[0] for description in c.description]
        conn.close()
        logger.debug(f"Fetched data from {db_name}, table {table_name} with filters - node_id: {node_id}, traffic_type: {traffic_type}, time_range: {time_range}, network_health: {network_health}")
        return rows, columns
    except sqlite3.Error as e:
        logger.error(f"Error fetching data from {db_name}, table {table_name}: {str(e)}")
        return [], []

@app.route('/report/<report_type>')
def report(report_type):
    report_map = {
        '01': ('traffic_data.db', 'blocks'),
        '02': ('congestion_data.db', 'congestion_blocks'),
        '03': ('managed_traffic.db', 'managed_blocks'),
        '04': ('new_orders.db', 'new_orders'),
        'initial_data': ('traffic_data.db', 'blocks'),
        'congestion': ('congestion_data.db', 'congestion_blocks'),
        'managed_traffic': ('managed_traffic.db', 'managed_blocks'),
        'new_orders': ('new_orders.db', 'new_orders'),
        'real_time_orders': ('real_time_orders.db', 'real_time_orders'),
        'self_healing': ('self_healing.db', 'healing_network'),
        'smart_traffic': ('smart_traffic.db', 'smart_traffic'),
        'traffic_report': ('traffic_report.db', 'traffic_report')
    }

    db_name, table_name = report_map.get(report_type, (None, None))
    if db_name and table_name:
        node_id = request.args.get('node_id', '')
        traffic_type = request.args.get('traffic_type', '')
        time_range = request.args.get('time_range', '')
        network_health = request.args.get('network_health', '')

        rows, columns = fetch_data_from_db(db_name, table_name, node_id, traffic_type, time_range, network_health)
        return render_template('report.html', rows=rows, columns=columns, report_type=report_type)
    else:
        logger.warning(f"Invalid report type: {report_type}")
        return "Invalid report type", 404

@app.route('/traffic_data')
def traffic_data():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(base_dir, 'result', 'real_time_orders.db')
    try:
        node_id = request.args.get('node_id', '')
        traffic_type = request.args.get('traffic_type', '')
        time_range = request.args.get('time_range', '')

        query = "SELECT timestamp, traffic_volume, network_health, latency, traffic_type FROM real_time_orders"
        conditions = []
        params = []

        if node_id:
            conditions.append("node_id = ?")
            params.append(node_id)

        if traffic_type:
            conditions.append("traffic_type = ?")
            params.append(traffic_type)

        if time_range:
            now = datetime.now()
            if time_range == '1m':
                time_threshold = now - timedelta(minutes=1)
            elif time_range == '5m':
                time_threshold = now - timedelta(minutes=5)
            else:
                time_threshold = None

            if time_threshold:
                conditions.append("timestamp >= ?")
                params.append(time_threshold.strftime('%Y-%m-%d %H:%M:%S'))

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT 10"

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()

        logger.debug("Fetched rows from DB: %s", rows)

        timestamps = [row[0] for row in rows]
        volumes = [min(100, max(0, float(row[1]) + random.uniform(-20, 20))) for row in rows]
        health_map = {'good': 0, 'moderate': 4, 'poor': 8}
        network_health_scores = [min(8, max(0, health_map.get(row[2], 0) + random.uniform(-1, 1))) for row in rows]
        latencies = [min(200, max(0, float(row[3]) + random.uniform(-30, 30))) for row in rows]
        traffic_types = [row[4] for row in rows]
        type_counts = {}
        for t in traffic_types:
            type_counts[t] = type_counts.get(t, 0) + 1

        max_count = max(type_counts.values(), default=1)
        normalized_type_counts = {t: (count / max_count) * 10 for t, count in type_counts.items()}

        logger.debug("Processed data: %s", {
            'timestamps': timestamps,
            'volumes': volumes,
            'network_health_scores': network_health_scores,
            'latencies': latencies,
            'traffic_types': list(normalized_type_counts.keys()),
            'type_counts': list(normalized_type_counts.values())
        })

        return jsonify({
            'timestamps': timestamps,
            'volumes': volumes,
            'network_health_scores': network_health_scores,
            'latencies': latencies,
            'traffic_types': list(normalized_type_counts.keys()),
            'type_counts': list(normalized_type_counts.values())
        })
    except sqlite3.Error as e:
        logger.error("Database error: %s", str(e))
        return jsonify({'error': str(e)})

@app.route('/add_new_order', methods=['POST'])
def add_new_order():
    try:
        node_id = request.form.get('node_id')
        traffic_type = request.form.get('traffic_type')
        traffic_volume = float(request.form.get('traffic_volume'))
        network_health = request.form.get('network_health')
        latency = float(request.form.get('latency'))

        if not node_id or node_id not in nodes:
            return jsonify({'error': 'Invalid Node ID'})
        if traffic_type not in ["Data", "Stream", "Game"]:
            return jsonify({'error': 'Invalid Traffic Type'})
        if traffic_volume < 0:
            return jsonify({'error': 'Traffic Volume must be positive'})
        if network_health not in ["Normal", "Delayed", "Down"]:
            return jsonify({'error': 'Invalid Network Health'})
        if latency < 0:
            return jsonify({'error': 'Latency must be positive'})

        conn = sqlite3.connect(output_db)
        c = conn.cursor()
        c.execute("SELECT * FROM new_orders ORDER BY timestamp DESC LIMIT 1")
        last_row = c.fetchone()
        conn.close()

        previous_block = None
        if last_row:
            traffic_layer = {"type": last_row[2], "volume": float(last_row[3])}
            health_layer = {"status": last_row[4], "latency": float(last_row[5])}
            congestion_layer = {
                "is_congested": 1 if last_row[8] in ["Medium", "High"] else 0, 
                "score": float(last_row[9]), 
                "impact": float(last_row[10]), 
                "level": last_row[8]
            }
            previous_block = NewOrderBlock(
                last_row[0], last_row[1], traffic_layer, health_layer, last_row[6], 
                congestion_layer, last_row[11], bool(last_row[12])
            )
            previous_block.hash = last_row[7]

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        if traffic_volume > 70:
            level = "High"
            is_congested = 1
        elif 40 <= traffic_volume <= 70:
            level = "Medium"
            is_congested = 1
        else:
            level = "Low"
            is_congested = 0

        congestion_score = random.uniform(0, 100) if is_congested else 0.0
        latency_impact = random.uniform(0, 10) if is_congested else 0.0
        traffic_layer = {"type": traffic_type, "volume": traffic_volume}
        health_layer = {"status": network_health, "latency": latency}
        congestion_layer = {
            "is_congested": is_congested, 
            "score": congestion_score, 
            "impact": latency_impact, 
            "level": level
        }

        traffic_suggestion = None
        is_congestion_order = False
        if is_congested:
            neighbors = graph[node_id]["neighbors"]
            traffic_suggestion = f"Redirect {traffic_type} to {random.choice(neighbors)}" if neighbors else "Reduce load"
            is_congestion_order = True

        previous_hash = previous_block.hash if previous_block else "0"
        new_block = NewOrderBlock(
            timestamp, node_id, traffic_layer, health_layer, previous_hash, 
            congestion_layer, traffic_suggestion, is_congestion_order
        )

        save_to_db(new_block)

        logger.info(f"New order added: Node {node_id}, Traffic Type {traffic_type}")
        return jsonify({'message': 'Order added successfully'})
    except Exception as e:
        logger.error(f"Error adding new order: {str(e)}")
        return jsonify({'error': str(e)})

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

if __name__ == '__main__':
    logger.info("Skipping Tailwind CSS execution as styles.css already exists.")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)