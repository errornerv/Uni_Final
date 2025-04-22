import sqlite3
import os
import logging

def init_db(db_path, schema):
    """
    Initialize a SQLite database with the given schema.
    """
    try:
        result_dir = os.path.dirname(db_path)
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
            logging.info(f"Created result directory: {result_dir}")

        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.executescript(schema)
        conn.commit()
        conn.close()
        logging.info(f"Database initialized at {db_path}")
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")
        raise

def save_to_db(db_path, query, params):
    """
    Save data to the SQLite database.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        conn.close()
        logging.info("Data saved to database successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database save error: {e}")
        raise

def load_from_db(db_path, query):
    """
    Load data from the SQLite database.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(query)
        rows = c.fetchall()
        conn.close()
        logging.info("Data loaded from database successfully.")
        return rows
    except sqlite3.Error as e:
        logging.error(f"Database load error: {e}")
        raise