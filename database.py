import sqlite3
import os
import json

def get_base_dir():
    base = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return base

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
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    return conn

def safe_int(val, default=0):
    try:
        if val is None or val == "":
            return default
        if isinstance(val, (int, float)):
            return int(val)
        if isinstance(val, str):
            digits = "".join(c for c in val if c.isdigit() or c == '-')
            return int(digits) if digits and digits != '-' else default
        return int(val)
    except Exception:
        return default

def fetch_all(table_name):
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[SQLITE_FETCH_ERR] {e}")
        return []

def insert_record(table_name, data_dict):
    try:
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
    except Exception as e:
        print(f"[SQLITE_INSERT_ERR] {e}")
        return None

def update_record(table_name, record_id, data_dict):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        set_clause = ', '.join([f"{k} = ?" for k in data_dict.keys()])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
        values = list(data_dict.values()) + [record_id]
        cursor.execute(sql, tuple(values))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SQLITE_UPDATE_ERR] {e}")

def sync_data_store_to_sqlite(data_store: dict):
    """Syncs the entire JSON data_store into local SQLite tables safely."""
    if not isinstance(data_store, dict):
        return
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM teachers")
        cursor.execute("DELETE FROM subjects")
        cursor.execute("DELETE FROM classes")
        cursor.execute("DELETE FROM rooms")
        cursor.execute("DELETE FROM lessons")
        cursor.execute("DELETE FROM grid_placements")
        cursor.execute("DELETE FROM settings")
        
        # Insert teachers
        for t in data_store.get("ogretmenler", []):
            if isinstance(t, dict):
                cursor.execute(
                    "INSERT INTO teachers (name, short_name, gender, color, max_hours_day, max_hours_week, constraints_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(t.get("ad", t.get("name", ""))),
                        str(t.get("kisa", t.get("short_name", ""))),
                        str(t.get("cinsiyet", t.get("gender", ""))),
                        str(t.get("renk", t.get("color", ""))),
                        safe_int(t.get("max_gunluk", t.get("max_hours_day", 8)), 8),
                        safe_int(t.get("max_haftalik", t.get("max_hours_week", 40)), 40),
                        json.dumps(t.get("kisitlamalar", t.get("timeoff", [])), ensure_ascii=False)
                    )
                )
                
        # Insert subjects
        for s in data_store.get("dersler", []):
            if isinstance(s, dict):
                cursor.execute(
                    "INSERT INTO subjects (name, short_name, color, difficulty) VALUES (?, ?, ?, ?)",
                    (
                        str(s.get("ad", s.get("name", ""))),
                        str(s.get("kisa", s.get("short_name", ""))),
                        str(s.get("renk", s.get("color", ""))),
                        safe_int(s.get("zorluk", s.get("difficulty", 1)), 1)
                    )
                )
                
        # Insert classes
        for c in data_store.get("siniflar", []):
            if isinstance(c, dict):
                cursor.execute(
                    "INSERT INTO classes (name, capacity, grade_level) VALUES (?, ?, ?)",
                    (
                        str(c.get("ad", c.get("name", ""))),
                        safe_int(c.get("kapasite", c.get("capacity", 30)), 30),
                        str(c.get("seviye", c.get("grade_level", "")))
                    )
                )
                
        # Insert rooms
        for r in data_store.get("derslikler", []):
            if isinstance(r, dict):
                cursor.execute(
                    "INSERT INTO rooms (name, short_name, capacity, building) VALUES (?, ?, ?, ?)",
                    (
                        str(r.get("ad", r.get("name", ""))),
                        str(r.get("kisa", r.get("short_name", ""))),
                        safe_int(r.get("kapasite", r.get("capacity", 30)), 30),
                        str(r.get("bina", r.get("building", "")))
                    )
                )
                
        # Insert lessons (atamalar)
        for a in data_store.get("atamalar", []):
            if isinstance(a, dict):
                t_list = [a.get("teacher")] if a.get("teacher") else a.get("teachers", [])
                c_list = [a.get("class")] if a.get("class") else a.get("classes", [])
                cursor.execute(
                    "INSERT INTO lessons (subject_id, duration, locked, teacher_ids_json, class_ids_json) VALUES (?, ?, ?, ?, ?)",
                    (
                        1,
                        safe_int(a.get("duration", 1), 1),
                        1 if a.get("locked") else 0,
                        json.dumps(t_list, ensure_ascii=False),
                        json.dumps(c_list, ensure_ascii=False)
                    )
                )
                
        # Insert grid placements
        for p in data_store.get("grid_placements", []):
            if isinstance(p, dict):
                cursor.execute(
                    "INSERT INTO grid_placements (lesson_id, day_index, period_index, room_id) VALUES (?, ?, ?, ?)",
                    (
                        safe_int(p.get("lesson_id", 1), 1),
                        safe_int(p.get("day", p.get("col", 0)), 0),
                        safe_int(p.get("period", p.get("row", 0)), 0),
                        1
                    )
                )
                
        # Insert settings
        settings = data_store.get("settings", {})
        if isinstance(settings, dict):
            for k, v in settings.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (str(k), json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v))
                )
                
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SQLITE_SYNC_ERR] {e}")


def trigger_save_db(widget, data_store=None):
    """Walks up the Qt parent hierarchy or top-level windows to find MainWindow/AppShell and call save_db()."""
    saved = False
    curr = widget
    while curr is not None:
        if hasattr(curr, "save_db") and callable(getattr(curr, "save_db")):
            try:
                curr.save_db(sync_from_grid=False)
                if hasattr(curr, "_refresh_tree") and callable(getattr(curr, "_refresh_tree")):
                    curr._refresh_tree()
                saved = True
                break
            except Exception as e:
                print(f"[SAVE_DB_ERR] {e}")
        if hasattr(curr, "parent") and callable(getattr(curr, "parent")):
            curr = curr.parent()
        else:
            break
            
    if not saved:
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for top in app.topLevelWidgets():
                    if hasattr(top, "save_db") and callable(getattr(top, "save_db")):
                        top.save_db(sync_from_grid=False)
                        if hasattr(top, "_refresh_tree") and callable(getattr(top, "_refresh_tree")):
                            top._refresh_tree()
                        saved = True
                        break
        except Exception:
            pass
        
    return saved
