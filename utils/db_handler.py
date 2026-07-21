import sqlite3
import uuid
from datetime import datetime
from utils.path_tool import get_abs_path

DB_PATH = get_abs_path("data/chat_history.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 创建会话表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            session_name TEXT,
            created_at DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def get_all_sessions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT session_id, session_name FROM sessions ORDER BY created_at DESC')
    sessions = cursor.fetchall()
    conn.close()
    return sessions

def create_session(name=None):
    session_id = str(uuid.uuid4())
    if not name:
        name = f"新会话_{datetime.now().strftime('%m%d_%H%M')}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sessions (session_id, session_name, created_at) VALUES (?, ?, ?)',
                   (session_id, name, datetime.now()))
    conn.commit()
    conn.close()
    return session_id

def delete_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
    # 注意：这里可能还需要删除 checkpoints 表中对应的数据，
    # 但 SqliteSaver 的表名通常是 checkpoints，我们稍后处理。
    conn.commit()
    conn.close()

def update_session_name(session_id, new_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE sessions SET session_name = ? WHERE session_id = ?', (new_name, session_id))
    conn.commit()
    conn.close()

init_db()
