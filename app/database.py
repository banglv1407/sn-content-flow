import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from .config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Posts queue & history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drive_file_id TEXT UNIQUE,
        file_name TEXT NOT NULL,
        file_path TEXT,
        thumbnail_url TEXT,
        caption TEXT DEFAULT '',
        platforms TEXT DEFAULT '["facebook", "instagram"]',
        status TEXT DEFAULT 'pending',
        scheduled_at DATETIME,
        published_at DATETIME,
        error_message TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT DEFAULT 'INFO',
        message TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Set default settings if not exists
    default_settings = {
        "drive_folder_id": "",
        "auto_sync_drive": "true",
        "sync_interval_minutes": "30",
        "schedule_cron": "0 9,15,20 * * *",  # 9h, 15h, 20h hằng ngày
        "default_caption": "Hình ảnh mới từ bộ sưu tập ✨ #photography #dailycontent #vietnam",
        "enable_facebook": "true",
        "enable_instagram": "true",
        "enable_tiktok": "false",
        "fb_page_id": "",
        "fb_access_token": "",
        "ig_account_id": "",
        "tiktok_access_token": ""
    }

    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def get_all_settings() -> Dict[str, str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def update_settings(settings_dict: Dict[str, str]):
    conn = get_db_connection()
    cursor = conn.cursor()
    for k, v in settings_dict.items():
        cursor.execute("""
        INSERT INTO settings (key, value, updated_at) 
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """, (k, str(v)))
    conn.commit()
    conn.close()

def log_event(message: str, level: str = "INFO"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (level, message) VALUES (?, ?)", (level, message))
    conn.commit()
    conn.close()

def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
