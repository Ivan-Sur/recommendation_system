import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
from urllib.parse import quote_plus
from sqlalchemy import create_engine

# load environment variables from .env file
load_dotenv()

# helper: construct db config for TRAIN or TEST
def _get_config(env_type="train"):
    suffix = f"_{env_type.upper()}"
    return {
        "host": os.getenv(f"DB_HOST{suffix}", "localhost"),
        "port": int(os.getenv(f"DB_PORT{suffix}", 3306)),
        "user": os.getenv(f"DB_USER{suffix}", "root"),
        "password": os.getenv(f"DB_PASSWORD{suffix}", ""),
        "database": os.getenv(f"DB_NAME{suffix}", "ban_terem"),
    }

# direct MySQL connector
def get_connection(env_type="train"):
    return mysql.connector.connect(**_get_config(env_type))

# sanity check for connection
def test_connection(env_type="train"):
    try:
        conn = get_connection(env_type)
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT DATABASE(), CURRENT_USER()")
            row = cursor.fetchone()
            cursor.close(); conn.close()
            return True, row
    except Error as e:
        return False, str(e)
    return False, "Unknown error"

# sqlalchemy engine factory
def get_engine(env_type="train"):
    cfg = _get_config(env_type)
    pwd = quote_plus(cfg.get("password") or "")
    url = f"mysql+mysqlconnector://{cfg['user']}:{pwd}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    return create_engine(url, pool_pre_ping=True)
