import sqlite3
import json
import os
import sys

def get_base_dir():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
        if sys.platform == "darwin" and base_dir.endswith("Contents/MacOS"):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(base_dir)))
        return base_dir
    return os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(get_base_dir(), "bgz_local_database.sqlite")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Kapsamlı Öğretmenler Tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_name TEXT,
            gender TEXT,
            color TEXT,
            max_hours_day INTEGER DEFAULT 8,
            max_hours_week INTEGER DEFAULT 40,
            constraints_json TEXT
        )
    """)
    
    # Dersler Tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_name TEXT,
            color TEXT,
            difficulty INTEGER DEFAULT 1
        )
    """)
    
    # Sınıflar Tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER DEFAULT 30,
            grade_level TEXT
        )
    """)
    
    # Derslikler Tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_name TEXT,
            capacity INTEGER,
            building TEXT
        )
    """)
    
    # Çoklu Öğretmen/Sınıf desteki Atamalar (Lessons)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            duration INTEGER DEFAULT 1,
            locked BOOLEAN DEFAULT 0,
            teacher_ids_json TEXT, -- ["T1", "T2"]
            class_ids_json TEXT,   -- ["C1", "C2"]
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
    """)
    
    # Grid Hücreleri (Placements)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grid_placements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER,
            day_index INTEGER,
            period_index INTEGER,
            room_id INTEGER,
            FOREIGN KEY(lesson_id) REFERENCES lessons(id)
        )
    """)
    
    # Global Ayarlar (Ziller, Günler)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def fetch_all(table_name):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def insert_record(table_name, data_dict):
    conn = get_connection()
    cursor = conn.cursor()
    columns = ', '.join(data_dict.keys())
    placeholders = ', '.join(['?' for _ in data_dict])
    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    cursor.execute(sql, tuple(data_dict.values()))
    last_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return last_id

def update_record(table_name, record_id, data_dict):
    conn = get_connection()
    cursor = conn.cursor()
    set_clause = ', '.join([f"{k} = ?" for k in data_dict.keys()])
    sql = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
    values = list(data_dict.values()) + [record_id]
    cursor.execute(sql, tuple(values))
    conn.commit()
    conn.close()

