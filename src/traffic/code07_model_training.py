import os
import sqlite3
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib
import sys
from utils.db_utils import init_db, save_to_db

# غیرفعال کردن بافرینگ خروجی
sys.stdout.reconfigure(line_buffering=True)

# Paths for database and model
current_dir = os.path.dirname(os.path.abspath(__file__))
start_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))  # Go to start/ directory
input_db = os.path.join(start_dir, "result", "new_orders.db")
model_file = os.path.join(start_dir, "result", "congestion_model.pkl")
encoders_file = os.path.join(start_dir, "result", "encoders.pkl")  # File to save encoders

# Function to check if the database file exists
def check_db_exists(db_path):
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} does not exist.")
        return False
    return True

# Function to load data from the database
def load_data_from_db(db_path):
    # Check if the database exists
    if not check_db_exists(db_path):
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM new_orders")
        rows = c.fetchall()
        conn.close()

        if not rows:
            print("Database is empty. No data to load.")
            return pd.DataFrame()

        # Convert data to DataFrame
        data = []
        for row in rows:
            data.append({
                "traffic_volume": row[3],
                "latency": row[5],
                "network_health": row[4],
                "traffic_type": row[2],
                "congestion_level": row[8]  # Multi-class target
            })
        print(f"Data successfully loaded from database {db_path}.")
        return pd.DataFrame(data)

    except sqlite3.Error as e:
        print(f"Error connecting to database {db_path}: {e}")
        return pd.DataFrame()

# Function to prepare data
def prepare_data(df):
    if df.empty:
        print("No data available for preparation.")
        return None, None, None

    # Encode categorical variables
    le_health = LabelEncoder()
    le_type = LabelEncoder()
    le_level = LabelEncoder()

    df['network_health'] = le_health.fit_transform(df['network_health'])
    df['traffic_type'] = le_type.fit_transform(df['traffic_type'])
    df['congestion_level'] = le_level.fit_transform(df['congestion_level'])

    # Separate features and target
    X = df[['traffic_volume', 'latency', 'network_health', 'traffic_type']]
    y = df['congestion_level']

    # Save encoders for future use
    encoders = {
        "health": le_health,
        "type": le_type,
        "level": le_level
    }
    joblib.dump(encoders, encoders_file)
    print(f"Encoders successfully saved to {encoders_file}.")

    return X, y, encoders

# Function to train and save the model
def train_and_save_model(X, y, model_path):
    if X is None or y is None:
        print("No data available for training.")
        return

    try:
        # Split data into training and test sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train the model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Evaluate the model
        accuracy = model.score(X_test, y_test)
        print(f"Model accuracy on test data: {accuracy:.2f}")

        # Save the model
        joblib.dump(model, model_path)
        print(f"Model successfully saved to {model_path}.")

    except Exception as e:
        print(f"Error during training or saving the model: {e}")

# Main execution
if __name__ == "__main__":
    print("Starting model training process...")
    df = load_data_from_db(input_db)
    X, y, encoders = prepare_data(df)
    train_and_save_model(X, y, model_file)
    print("Model training process completed.")