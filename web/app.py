from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO
import subprocess
import os
import sqlite3
import psutil

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

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
            return jsonify({'output': 'Script is running...', 'report_link': None})
        except Exception as e:
            return jsonify({'error': str(e)})
    else:
        return jsonify({'error': 'Invalid script ID'})

@app.route('/stop_all_scripts', methods=['POST'])
def stop_all_scripts():
    print("Received request to stop all scripts.")
    if not processes:
        print("No scripts are running.")
        socketio.emit('script_status', {'status': 'stopped_all', 'message': 'No scripts are running.'}, namespace='/')
        return jsonify({'output': 'No scripts are running.'})

    stopped_scripts = []
    for script_id, process in list(processes.items()):
        try:
            print(f"Attempting to stop script {script_id} with PID {process.pid}")
            stop_reading_flags[script_id] = True

            if process.poll() is None:
                parent = psutil.Process(process.pid)
                for child in parent.children(recursive=True):
                    print(f"Terminating child process {child.pid}")
                    child.kill()
                parent.kill()
                try:
                    parent.wait(timeout=1)
                    print(f"Script {script_id} terminated successfully.")
                except psutil.TimeoutExpired:
                    print(f"Script {script_id} did not terminate, killing it again.")
                    parent.kill()
            stopped_scripts.append(script_id)
        except Exception as e:
            print(f"Error stopping script {script_id}: {str(e)}")
        finally:
            if script_id in processes:
                del processes[script_id]
            if script_id in stop_reading_flags:
                del stop_reading_flags[script_id]

    print(f"Stopped scripts: {stopped_scripts}")
    socketio.emit('script_status', {'status': 'stopped_all', 'stopped_scripts': stopped_scripts}, namespace='/')
    return jsonify({'output': f"Stopped scripts: {', '.join(stopped_scripts) if stopped_scripts else 'None'}"})

@app.route('/stop_script', methods=['POST'])
def stop_script():
    script_id = request.form.get('script_id')
    if script_id not in processes:
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
        return jsonify({'output': f'Script {script_id} stopped.'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/force_stop_script', methods=['POST'])
def force_stop_script():
    script_id = request.form.get('script_id')
    if script_id not in processes:
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
        return jsonify({'output': f'Script {script_id} force stopped.'})
    except Exception as e:
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
        return rows, columns
    except sqlite3.Error as e:
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
        return "Invalid report type", 404

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)