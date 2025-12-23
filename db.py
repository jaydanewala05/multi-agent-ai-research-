import sqlite3
from datetime import datetime
import json

DB_PATH = "research_history.db"

def init_db():
    """Initialize the SQLite database with both tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Research history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS research_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        sources TEXT,
        notes TEXT,
        summary TEXT,
        critique TEXT,
        final_report TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Task results table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS task_results (
        task_id TEXT PRIMARY KEY,
        filename TEXT,
        task TEXT NOT NULL,
        result TEXT,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def save_history(query, sources, notes, summary, critique, final_report):
    """Save research history to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Convert sources to string if it's a list
    if isinstance(sources, list):
        sources = json.dumps(sources)
    
    cursor.execute('''
    INSERT INTO research_history (query, sources, notes, summary, critique, final_report)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (query, sources, notes, summary, critique, final_report))
    
    conn.commit()
    conn.close()

def save_task_result(task_id, filename, task, result, status):
    """Save task execution result"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Convert result to string if it's a dict
    if isinstance(result, dict):
        result = json.dumps(result)
    
    cursor.execute('''
    INSERT OR REPLACE INTO task_results (task_id, filename, task, result, status, completed_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (task_id, filename, task, result, status, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def get_history(limit=50):
    """Get research history from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, query, sources, notes, summary, critique, final_report, created_at
    FROM research_history
    ORDER BY created_at DESC
    LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_task_history(limit=20):
    """Get task execution history"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT task_id, filename, task, status, created_at, completed_at
    FROM task_results
    ORDER BY created_at DESC
    LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return rows