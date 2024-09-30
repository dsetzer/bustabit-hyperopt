import sqlite3
import json
import logging

class Storage:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimizations (
                id TEXT PRIMARY KEY,
                script_path TEXT,
                initial_balance INTEGER,
                num_particles INTEGER,
                max_iter INTEGER,
                c1 REAL,
                c2 REAL,
                w REAL,
                damping REAL,
                gbest_value REAL,
                gbest_position TEXT,
                status TEXT,
                current_iteration INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS iteration_states (
                optimization_id TEXT,
                iteration INTEGER,
                particles TEXT,
                gbest_position TEXT,
                gbest_value REAL,
                PRIMARY KEY (optimization_id, iteration),
                FOREIGN KEY (optimization_id) REFERENCES optimizations(id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id TEXT PRIMARY KEY,
                file_path TEXT,
                content TEXT,
                config TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def save_optimization(self, optimization_data):
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO optimizations
                (id, script_path, initial_balance, num_particles, max_iter, c1, c2, w, damping, gbest_value, gbest_position, status, current_iteration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                optimization_data["optimization_id"],
                optimization_data["script_obj"].js_file_path,
                optimization_data["initial_balance"],
                optimization_data["num_particles"],
                optimization_data["max_iter"],
                optimization_data["c1"],
                optimization_data["c2"],
                optimization_data["w"],
                optimization_data["damping"],
                optimization_data["gbest_value"],
                json.dumps(optimization_data["gbest_position"]),
                optimization_data["status"],
                optimization_data["current_iteration"],
            ))
            self.conn.commit()
            return optimization_data["optimization_id"]
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()
            return None

    def optimization_exists(self, optimization_id):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM optimizations WHERE id = ?", (optimization_id,))
            count = self.cursor.fetchone()[0]
            return count > 0
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return False

    def load_optimization(self, optimization_id):
        try:
            self.cursor.execute("SELECT * FROM optimizations WHERE id = ?", (optimization_id,))
            row = self.cursor.fetchone()
            if row:
                optimization_data = dict(row)
                optimization_data["gbest_position"] = json.loads(optimization_data["gbest_position"])
                return optimization_data
            return None
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return None

    def update_optimization(self, optimization_id, update_data):
        try:
            update_fields = ", ".join([f"{k} = ?" for k in update_data.keys()])
            query = f"UPDATE optimizations SET {update_fields} WHERE id = ?"
            values = list(update_data.values()) + [optimization_id]
            self.cursor.execute(query, values)
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()

    def save_iteration_state(self, optimization_id, iteration_data):
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO iteration_states
                (optimization_id, iteration, particles, gbest_position, gbest_value)
                VALUES (?, ?, ?, ?, ?)
            """, (
                optimization_id,
                iteration_data["iteration"],
                json.dumps(iteration_data["particles"]),
                json.dumps(iteration_data["gbest_position"]),
                iteration_data["gbest_value"],
            ))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()

    def load_iteration_state(self, optimization_id, iteration):
        try:
            self.cursor.execute("""
                SELECT * FROM iteration_states
                WHERE optimization_id = ? AND iteration = ?
            """, (optimization_id, iteration))
            row = self.cursor.fetchone()
            if row:
                iteration_data = dict(row)
                iteration_data["particles"] = json.loads(iteration_data["particles"])
                iteration_data["gbest_position"] = json.loads(iteration_data["gbest_position"])
                return iteration_data
            return None
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return None

    def get_all_optimizations(self):
        try:
            self.cursor.execute(
                "SELECT id, status, current_iteration, timestamp FROM optimizations ORDER BY timestamp DESC"
            )
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return []

    def delete_optimization(self, optimization_id):
        try:
            self.cursor.execute(
                "DELETE FROM iteration_states WHERE optimization_id = ?",
                (optimization_id,),
            )
            self.cursor.execute(
                "DELETE FROM optimizations WHERE id = ?", (optimization_id,)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()

    def save_script(self, script_obj):
        try:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO scripts
                (id, file_path, content, config)
                VALUES (?, ?, ?, ?)
            """,
                (
                    script_obj.js_file_path,
                    script_obj.js_file_path,
                    script_obj.js_code,
                    json.dumps(script_obj.config)
                ),
            )
            self.conn.commit()
            return script_obj.js_file_path
        except sqlite3.Error as e:
            logging.error(f"An error occurred while saving script: {e}")
            self.conn.rollback()
            return None

    def load_script(self, script_id):
        try:
            self.cursor.execute(
                "SELECT * FROM scripts WHERE id = ?", (script_id,)
            )
            row = self.cursor.fetchone()
            if row:
                script_data = dict(row)
                script_data['config'] = json.loads(script_data['config'])
                return script_data
            return None
        except sqlite3.Error as e:
            logging.error(f"An error occurred while loading script: {e}")
            return None

    def delete_script(self, script_id):
        try:
            self.cursor.execute(
                "DELETE FROM scripts WHERE id = ?", (script_id,)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"An error occurred while deleting script: {e}")
            self.conn.rollback()

    def get_all_scripts(self):
        try:
            self.cursor.execute("SELECT id, file_path, timestamp FROM scripts ORDER BY timestamp DESC")
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return []

    def close(self):
        self.cursor.close()
        self.conn.close()
