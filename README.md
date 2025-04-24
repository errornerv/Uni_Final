Network Traffic Problem Solve Using Blockchain: Comprehensive Documentation
1. Overview
This project, developed under the supervision of Professor Karimi at Islamic Azad University of Tabriz, provides a blockchain-based solution for managing and optimizing network traffic. By leveraging blockchain technology, machine learning, and intelligent algorithms, the system simulates, analyzes, and manages network traffic with features such as congestion detection, self-healing, resource optimization, predictive analysis, and advanced reporting. The project is authored by Ali Samadian, and all rights are reserved to him.
The system is modular, with components for blockchain management, traffic analysis, and smart optimization. This document provides a detailed guide on the project’s structure, setup, execution, and usage, focusing on running each script individually.

2. Project Components
The project is divided into three main components:

Blockchain: Stores and manages network traffic data in secure, immutable blocks using ECDSA signatures and a Proof of Stake consensus mechanism.
Traffic Analysis: Processes traffic data, trains machine learning models for congestion prediction, and generates detailed reports.
Smart Management: Implements intelligent traffic management, self-healing mechanisms, dynamic resource allocation, and predictive analysis with anomaly detection.


3. Directory Structure
The project is organized as follows:
NETWORK TRAFFIC PROBLEM SOLVE USING BLOCKCHAIN/
├── venv/                    # Python virtual environment
├── result/                  # Output databases and files
│   ├── congestion_data.db
│   ├── congestion_model.pkl
│   ├── encoders.pkl
│   ├── managed_traffic.db
│   ├── new_orders.db
│   ├── real_time_orders.db
│   ├── self_healing.db
│   ├── smart_traffic.db
│   ├── traffic_data.csv
│   ├── traffic_data.db
│   ├── traffic_report.db
│   ├── optimized_resources.db
│   ├── predictive_analysis.db
├── src/
│   ├── __init__.py
│   ├── blockchain/          # Blockchain-related scripts
│   │   ├── 01_blockchain_initial_data.py
│   │   ├── 02_blockchain_congestion_improved.py
│   │   ├── 03_blockchain_managed_traffic.py
│   │   ├── 04_blockchain_with_new_orders.py
│   │   ├── 05_blockchain_with_real_time_orders.py
│   ├── smart/               # Smart management scripts
│   │   ├── 09_smart_traffic_management.py
│   │   ├── self_healing_network.py
│   │   ├── 11_resource_optimization.py
│   │   ├── 12_predictive_analysis_and_anomaly_detection.py
│   └── traffic/             # Traffic analysis scripts
│       ├── 06_traffic_data_preparation.py
│       ├── 07_model_training.py
│       ├── 08_advanced_traffic_report.py
│       ├── __init__.py
├── web/                     # Web interface files
│   ├── app.py
│   ├── static/
│   │   └── styles.css
│   └── templates/
│       ├── index.html
│       ├── report.html
├── README.md                # Project overview
├── requirements.txt         # Required Python packages
├── road_map.docx            # Project roadmap


4. Prerequisites
To run the project, ensure the following requirements are met:

Python: Version 3.8, 3.9, or 3.10.
Operating System: Windows, Linux, or macOS.
Dependencies: Python packages listed in requirements.txt.
Hardware: Minimum 4GB RAM and 2GHz CPU (8GB RAM recommended for faster processing).


5. Installation
Follow these steps to set up the project environment:
5.1. Clone or Download the Project
Download the project files or clone the repository to your local machine. For example:
git clone <repository-url>

Alternatively, extract the project folder to a directory, e.g., C:\Users\YourUser\Desktop\project\network traffic problem solve using blockchain.
5.2. Create a Virtual Environment
Navigate to the project directory:
cd C:\Users\YourUser\Desktop\project\network traffic problem solve using blockchain

Create a virtual environment:
python -m venv venv

Activate the virtual environment:

On Windows:.\venv\Scripts\activate


On Linux/macOS:source venv/bin/activate



5.3. Install Dependencies
Install the required Python packages:
pip install -r requirements.txt

This installs packages like numpy, pandas, scikit-learn, flask, cryptography, and others listed in requirements.txt.

6. Script Execution Order
To run the project scripts individually (without using the package’s main script), execute them in the following order. Each script depends on the output of the previous one, as they process data sequentially through a pipeline of databases.
6.1. Blockchain Scripts
These scripts build and enhance the blockchain for traffic data management.

01_blockchain_initial_data.py

Purpose: Simulates initial network traffic data and creates the blockchain with a genesis block. Uses Proof of Stake and ECDSA signatures for security.
Input: None (generates simulated data).
Output: result/traffic_data.db (initial blockchain data).
Execution:python src/blockchain/01_blockchain_initial_data.py


Notes: Generates ~400 blocks for 10 nodes over 40 time steps. Ensure the result/ directory exists.


02_blockchain_congestion_improved.py

Purpose: Detects congestion levels (Low, Medium, High) based on traffic volume and latency, adding congestion metadata to blocks.
Input: result/traffic_data.db.
Output: result/congestion_data.db.
Execution:python src/blockchain/02_blockchain_congestion_improved.py


Notes: Uses a dynamic threshold for congestion detection and processes blocks in parallel with ThreadPoolExecutor.


03_blockchain_managed_traffic.py

Purpose: Provides traffic management suggestions (e.g., rerouting, bandwidth reduction) for congested blocks.
Input: result/congestion_data.db.
Output: result/managed_traffic.db.
Execution:python src/blockchain/03_blockchain_managed_traffic.py


Notes: Suggestions are based on traffic volume, network health, and node neighbors.


04_blockchain_with_new_orders.py

Purpose: Classifies blocks as Priority or Standard orders, prioritizing high-congestion blocks for faster processing.
Input: result/managed_traffic.db.
Output: result/new_orders.db.
Execution:python src/blockchain/04_blockchain_with_new_orders.py


Notes: Randomly assigns Priority status to 30% of Medium/High congestion blocks.


05_blockchain_with_real_time_orders.py

Purpose: Simulates real-time processing with reduced delays for Priority orders (0.05s vs. 0.1s for Standard).
Input: result/new_orders.db.
Output: result/real_time_orders.db.
Execution:python src/blockchain/05_blockchain_with_real_time_orders.py


Notes: Mimics real-time network behavior with artificial delays.



6.2. Traffic Analysis Scripts
These scripts process blockchain data for machine learning and reporting.

06_traffic_data_preparation.py

Purpose: Extracts and formats data from the blockchain for model training, converting it into a CSV file.
Input: result/new_orders.db.
Output: result/traffic_data.csv.
Execution:python src/traffic/06_traffic_data_preparation.py


Notes: Ensures data is clean and structured for machine learning.


07_model_training.py

Purpose: Trains a RandomForestClassifier to predict congestion levels (Low, Medium, High).
Input: result/new_orders.db.
Output: result/congestion_model.pkl, result/encoders.pkl.
Execution:python src/traffic/07_model_training.py


Notes: Saves the trained model and label encoders for later use.


08_advanced_traffic_report.py

Purpose: Generates detailed reports on traffic averages, network health impact, and high-traffic nodes.
Input: result/managed_traffic.db.
Output: result/traffic_report.db.
Execution:python src/traffic/08_advanced_traffic_report.py


Notes: Reports are stored in a database and printed to the console.



6.3. Smart Management Scripts
These scripts implement intelligent features for traffic optimization.

09_smart_traffic_management.py

Purpose: Uses the trained ML model to predict congestion and redistribute traffic to avoid bottlenecks.
Input: result/real_time_orders.db, result/congestion_model.pkl, result/encoders.pkl.
Output: result/smart_traffic.db.
Execution:python src/smart/09_smart_traffic_management.py


Notes: Dynamically adjusts congestion thresholds based on recent block history.


self_healing_network.py

Purpose: Implements self-healing by reactivating failed nodes or rerouting traffic to healthy neighbors.
Input: result/smart_traffic.db.
Output: result/self_healing.db.
Execution:python src/smart/self_healing_network.py


Notes: Uses a probabilistic approach for node reactivation based on historical performance.


11_resource_optimization.py

Purpose: Dynamically allocates bandwidth based on traffic priority, congestion, and node health.
Input: result/self_healing.db.
Output: result/optimized_resources.db.
Execution:python src/smart/11_resource_optimization.py


Notes: Prioritizes bandwidth for Priority traffic and redistributes resources from congested nodes.


12_predictive_analysis_and_anomaly_detection.py

Purpose: Performs predictive congestion analysis and detects anomalies using an Isolation Forest model.
Input: result/new_orders.db, result/congestion_model.pkl, result/encoders.pkl.
Output: result/predictive_analysis.db.
Execution:python src/smart/12_predictive_analysis_and_anomaly_detection.py


Notes: Analyzes the last hour of data for real-time insights.




7. Running the Web Interface
The project includes a Flask-based web interface for running scripts and viewing reports.

Navigate to the web directory:cd C:\Users\YourUser\Desktop\project\network traffic problem solve using blockchain\web


Run the web server:python app.py


Access the interface at http://localhost:5000.
Features:
Run Scripts: Execute scripts via http://localhost:5000/run_script/<script_id> (e.g., 1 for 01_blockchain_initial_data.py).
View Reports: Access reports at http://localhost:5000/report/<script_id>.
Stop All Scripts: Use the "Complete Stop" button to terminate all running scripts.




8. Usage Guidelines

Execution Order: Always follow the script order (1 to 12) to ensure data dependencies are met. Skipping a script may cause errors due to missing input databases.
Database Management: The result/ directory stores all output databases. Ensure write permissions for this directory.
Error Handling: Scripts include logging (logging.info, logging.error) to diagnose issues. Check console output or logs for errors.
Performance: Scripts like 07_model_training.py and 12_predictive_analysis_and_anomaly_detection.py may require significant CPU/memory for large datasets.
Web Interface: Use the web panel for interactive control, but manual script execution is recommended for debugging or specific tasks.


9. Troubleshooting

Database Locked Error: If a script reports a "database is locked" error, wait a few seconds and retry, as SQLite may be busy.
Missing Dependencies: Ensure all packages in requirements.txt are installed. Run pip install -r requirements.txt again if errors occur.
File Not Found: Verify that input databases exist in the result/ directory before running a script.
Memory Issues: For large datasets, increase available RAM or reduce the number of blocks in 01_blockchain_initial_data.py (modify time_steps).


10. Contribution
To contribute to the project:

Fork the repository (if hosted on GitHub).
Create a new branch for your changes.
Submit a pull request with detailed descriptions of your modifications.
Report issues in issues.txt or via the repository’s issue tracker.


11. License
This project is licensed under the Apache License 2.0. See the NOTICE file for copyright and attribution details. Created by Ali Samadian.

12. Additional Resources

Roadmap: Refer to road_map.docx for the project’s development plan.
Documentation: Detailed technical notes are available in documents.docx and documents.pdf in the docs/ directory.
Contact: For inquiries, contact the author via the repository or email (if provided).


This documentation ensures that users can set up, execute, and understand the project comprehensively. For further assistance, refer to the source code comments or contact the project author.
