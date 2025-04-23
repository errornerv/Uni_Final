from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO
import subprocess
import os
import sqlite3
import psutil
import random
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(level=logging.ERROR)  # فقط خطاها لاگ می‌شن
logger = logging.getLogger(__name__)

processes = {}
stop_reading_flags = {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

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

def fetch_data_from_db(db_name, table_name):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(base_dir, 'result', db_name)
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(f"SELECT * FROM {table_name}")
        rows = c.fetchall()
        columns = [description[0] for description in c.description]
        conn.close()
        logger.debug(f"Fetched data from {db_name}, table {table_name}")
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
        rows, columns = fetch_data_from_db(db_name, table_name)
        return render_template('report.html', rows=rows, columns=columns, report_type=report_type)
    else:
        logger.warning(f"Invalid report type: {report_type}")
        return "Invalid report type", 404

@app.route('/traffic_data')
def traffic_data():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(base_dir, 'result', 'real_time_orders.db')
    try:
        # Get filter parameters
        node_id = request.args.get('node_id', '')
        traffic_type = request.args.get('traffic_type', '')
        time_range = request.args.get('time_range', '')

        # Build the SQL query
        query = "SELECT timestamp, traffic_volume, network_health, latency, traffic_type FROM real_time_orders"
        conditions = []
        params = []

        # Filter by node_id
        if node_id:
            conditions.append("node_id = ?")
            params.append(node_id)

        # Filter by traffic_type
        if traffic_type:
            conditions.append("traffic_type = ?")
            params.append(traffic_type)

        # Filter by time_range
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

        # Combine conditions
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT 10"

        # Execute the query
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()

        # لاگ حذف شده
        logger.debug("Fetched rows from DB: %s", rows)

        timestamps = [row[0] for row in rows]
        volumes = [min(100, max(0, float(row[1]) + random.uniform(-20, 20))) for row in rows]
        # Updated health mapping to scale from 0 to 8
        health_map = {'good': 0, 'moderate': 4, 'poor': 8}
        network_health_scores = [min(8, max(0, health_map.get(row[2], 0) + random.uniform(-1, 1))) for row in rows]
        latencies = [min(200, max(0, float(row[3]) + random.uniform(-30, 30))) for row in rows]
        traffic_types = [row[4] for row in rows]
        type_counts = {}
        for t in traffic_types:
            type_counts[t] = type_counts.get(t, 0) + 1

        # Normalize type_counts to range 0-10
        max_count = max(type_counts.values(), default=1)
        normalized_type_counts = {t: (count / max_count) * 10 for t, count in type_counts.items()}

        # لاگ حذف شده
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

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)  # debug=False برای جلوگیری از لاگ‌های اضافی Flask