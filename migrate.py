import sqlite3
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Database Configuration ---
# Assuming the database file is in the same directory as the script or in a known location.
# The default database name in the project is 'app.db' located in the root.
DB_FILE = "api_server.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        # Look for the db file in the root directory
        if os.path.exists(DB_FILE):
            conn = sqlite3.connect(DB_FILE)
            logger.info(f"Successfully connected to database: {DB_FILE}")
            return conn
        else:
            logger.error(f"Database file not found at {DB_FILE}. Please ensure the path is correct.")
            return None
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        return None

def column_exists(cursor, table_name, column_name):
    """Checks if a column exists in a specific table."""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in cursor.fetchall()]
        return column_name in columns
    except sqlite3.Error as e:
        logger.error(f"Error checking column existence for {table_name}.{column_name}: {e}")
        return False

def run_migration():
    """Runs the database migration to add new columns."""
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()

    try:
        # Add 'api_key_id' to 'call_logs' table
        if not column_exists(cursor, 'call_logs', 'api_key_id'):
            logger.info("Adding 'api_key_id' column to 'call_logs' table...")
            cursor.execute("ALTER TABLE call_logs ADD COLUMN api_key_id INTEGER REFERENCES api_keys(id)")
            logger.info("'api_key_id' column added successfully.")
        else:
            logger.info("'api_key_id' column already exists in 'call_logs'. Skipping.")

        # Add 'request_body' to 'call_logs' table
        if not column_exists(cursor, 'call_logs', 'request_body'):
            logger.info("Adding 'request_body' column to 'call_logs' table...")
            cursor.execute("ALTER TABLE call_logs ADD COLUMN request_body TEXT")
            logger.info("'request_body' column added successfully.")
        else:
            logger.info("'request_body' column already exists in 'call_logs'. Skipping.")

        conn.commit()
        logger.info("Database migration completed successfully.")

    except sqlite3.Error as e:
        logger.error(f"An error occurred during migration: {e}")
        conn.rollback()
    finally:
        conn.close()
        logger.info("Database connection closed.")

if __name__ == "__main__":
    run_migration()