import subprocess
import sys


packages = [
    "numpy==1.24.3",
    "cryptography==42.0.2",
    "pandas==2.0.3",
    "tqdm==4.66.1",
    "flask==2.3.3",
    "flask-socketio==5.3.4",
    "joblib==1.3.2",
    "scikit-learn==1.3.0",
    "matplotlib==3.7.1",
    "requests==2.31.0",
    "psutil==5.9.5",
    "reportlab==4.2.2",
    "openpyxl==3.1.5",
    "gevent==24.2.1",
    "gevent-websocket==0.10.1"
    "xlsxwriter==3.1.2"
]

def install_packages():
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"Successfully installed {package}")
        except subprocess.CalledProcessError:
            print(f"Error installing {package}")

if __name__ == "__main__":
    install_packages()