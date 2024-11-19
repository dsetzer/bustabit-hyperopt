import json
import logging
import sqlite3


class Storage:
    def __init__(self, db_path):
        # Initialize the database connection
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Create the necessary tables
        self.create_optimizations_table()
        self.create_result_sets_table()
        self.create_scripts_table()
        self.create_optimization_result_set_links_table()
        self.create_script_optimization_links_table()

    def create_optimizations_table(self):
        # Create the optimizations table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimizations (
                id TEXT PRIMARY KEY,
                script_id TEXT,
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
                current_iteration INTEGER
            );
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS parameters (
                optimization_id TEXT,
                parameter_name TEXT,
                parameter_range TEXT,
                parameter_type TEXT,
                FOREIGN KEY (optimization_id) REFERENCES optimizations(id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_sets (
                optimization_id TEXT,
                set_id INTEGER,
                final_game_hash TEXT,
                total_games INTEGER,
                summary_metrics TEXT,
                game_data TEXT,
                PRIMARY KEY (optimization_id, set_id),
                FOREIGN KEY (optimization_id) REFERENCES optimizations(id)
            )
        """)
        self.conn.commit()

    def save_game_set(self, game_set):
        pass

    def get_game_sets(self, optimization_id):
        pass

    def get_game_set(self, set_id):
        pass

    

    def save_optimization(self, optimization_data):
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO optimizations
                (id, script_id, initial_balance, num_particles, max_iter, c1, c2, w, damping, gbest_value, gbest_position, status, current_iteration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                optimization_data["optimization_id"],
                optimization_data["script_obj"].script_id,
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
            return optimization_data["id"]
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()
            return None

    def get_optimization(self, optimization_id):
        """
        Retrieve an optimization from the database.

        optimization_id: The ID of the optimization to retrieve.

        Returns the optimization as a dictionary if it exists, None otherwise.
        """
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

    def update_optimization(self, optimization_id, optimization_data):
        """
        Update the optimization with the given optimization_id using the given optimization_data.

        optimization_id: The ID of the optimization to update.
        optimization_data: A dictionary containing the fields to update in the optimization.

        Returns the optimization_id if the update was successful, None otherwise.
        """
        try:
            update_fields = ", ".join([f"{k} = ?" for k in optimization_data.keys()])
            query = f"UPDATE optimizations SET {update_fields} WHERE id = ?"
            values = list(optimization_data.values()) + [optimization_id]
            if "gbest_position" in optimization_data:
                values[values.index(optimization_data["gbest_position"])] = json.dumps(optimization_data["gbest_position"])
            self.cursor.execute(query, values)
            self.conn.commit()
            return optimization_id
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()
            return None

    def delete_optimization(self, optimization_id):
        try:
            self.cursor.execute("DELETE FROM optimizations WHERE id = ?", (optimization_id,))
            self.conn.commit()
            return optimization_id
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()
            return None

    def get_all_optimizations(self):
        try:
            self.cursor.execute("SELECT * FROM optimizations")
            rows = self.cursor.fetchall()
            optimizations = []
            for row in rows:
                optimization_data = dict(row)
                optimization_data["gbest_position"] = json.loads(optimization_data["gbest_position"])
                optimizations.append(optimization_data)
            return optimizations
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return []

    # Result set management
    def insert_result_set(self, result_set_data, game_results):
        try:
            self.cursor.execute("""
                INSERT INTO result_sets
                (id, optimization_id, hash, num_games, required_median)
                VALUES (?, ?, ?, ?, ?)
            """, (
                result_set_data["id"],
                result_set_data["optimization_id"],
                result_set_data["hash"],
                result_set_data["num_games"],
                result_set_data["required_median"],
            ))
            self.conn.commit()

            for game_result in game_results:
                self.cursor.execute("""
                    INSERT INTO result_set_game_results
                    (result_set_id, game_id, hash, busted_at, duration, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    result_set_data["id"],
                    game_result["game_id"],
                    game_result["hash"],
                    game_result["busted_at"],
                    game_result["duration"],
                    game_result["timestamp"],
                ))
            self.conn.commit()
            return result_set_data["id"]
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()
            return None

    def get_result_set(self, result_set_id):
        try:
            self.cursor.execute("SELECT * FROM result_sets WHERE id = ?", (result_set_id,))
            row = self.cursor.fetchone()
            if row:
                result_set_data = dict(row)
                self.cursor.execute("SELECT * FROM result_set_game_results WHERE result_set_id = ?", (result_set_id,))
                game_results = [dict(game_row) for game_row in self.cursor.fetchall()]
                result_set_data["game_results"] = game_results
                return result_set_data
            return None
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return None

    def update_result_set(self, result_set_id, result_set_data):
        try:
            update_fields = []
            values = []
            for key, value in result_set_data.items():
                update_fields.append(f"{key} = ?")
                values.append(value)
            update_fields = ", ".join(update_fields)
            query = f"UPDATE result_sets SET {update_fields} WHERE id = ?"
            values += [result_set_id]
            self.cursor.execute(query, values)
            self.conn.commit()
            return result_set_id
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()
            return None

    def delete_result_set(self, result_set_id):
        try:
            self.cursor.execute("DELETE FROM result_set_game_results WHERE result_set_id = ?", (result_set_id,))
            self.cursor.execute("DELETE FROM result_sets WHERE id = ?", (result_set_id,))
            self.conn.commit()
            return result_set_id
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()
            return None

    def get_all_result_sets(self, optimization_id):
        try:
            self.cursor.execute("SELECT * FROM result_sets WHERE optimization_id = ?", (optimization_id,))
            rows = self.cursor.fetchall()
            result_sets = []
            for row in rows:
                result_set_data = dict(row)
                self.cursor.execute("SELECT * FROM result_set_game_results WHERE result_set_id = ?", (result_set_data["id"],))
                game_results = [dict(game_row) for game_row in self.cursor.fetchall()]
                result_set_data["game_results"] = game_results
                result_sets.append(result_set_data)
            return result_sets
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return []

    # Script data management
    def insert_script(self, script_data):
        try:
            self.cursor.execute("""
                INSERT INTO scripts
                (id, file_name,script_config, script_obj, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (
                script_data["id"],
                script_data["file_name"],
                json.dumps(script_data["script_config"]),
                json.dumps(script_data["script_obj"]),
                script_data["last_updated"],
            ))
            self.conn.commit()
            return script_data["id"]
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()
            return None

    def get_script(self, script_id):
        """
        Retrieve a script from the database.

        script_id: The ID of the script to retrieve.

        Returns the script as a dictionary if it exists, None otherwise.
        """
        try:
            self.cursor.execute("SELECT * FROM scripts WHERE id = ?", (script_id,))
            row = self.cursor.fetchone()
            if row:
                script_data = dict(row)
                script_data["script_config"] = json.loads(script_data["script_config"])
                script_data["script_obj"] = json.loads(script_data["script_obj"])
                return script_data
            return None
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return None

    def update_script(self, script_id, script_data):
        """
        Update an existing script in the database.

        script_id: The ID of the script to update.
        script_data: A dictionary containing the id, file_name, script_config, script_obj, and last_updated to update.

        Returns the script_id if the update was successful, None otherwise.
        """
        try:
            self.cursor.execute("""
                UPDATE scripts
                SET file_name = ?, script_config = ?, script_obj = ?, last_updated = ?
                WHERE id = ?
            """, (
                script_data["file_name"],
                json.dumps(script_data["script_config"]),
                json.dumps(script_data["script_obj"]),
                script_data["last_updated"],
                script_id,
            ))
            self.conn.commit()
            return script_id
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()
            return None

    def delete_script(self, script_id):
        """
        Delete a script from the database.

        Returns the script_id if the deletion was successful, None otherwise.
        """
        try:
            self.cursor.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
            self.conn.commit()
            return script_id
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()
            return None

    def get_all_scripts(self):
        """
        Retrieve all scripts from the database.

        Returns a list of dictionaries, each containing the id file_name, last_updated date, and config parameter names of each script.
        If an error occurs, returns an empty list.
        """
        try:
            self.cursor.execute("""
                SELECT s.id, s.file_name, s.last_updated
                , (SELECT json_group_array(key) FROM json_each(s.script_config)) AS config_params
                FROM scripts s
            """)
            rows = self.cursor.fetchall()
            scripts = []
            for row in rows:
                scripts.append(dict(row))
            return scripts
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return []

    # Relationships between data
    def link_optimization_to_result_set(self, optimization_id, result_set_id):
        """
        Link an optimization to a result set.

        optimization_id: The ID of the optimization to link.
        result_set_id: The ID of the result set to link to the optimization.

        Returns None if the link was successful, otherwise an error message.
        """
        try:
            self.cursor.execute("""
                INSERT INTO optimization_result_set_links
                (optimization_id, result_set_id)
                VALUES (?, ?)
            """, (optimization_id, result_set_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()

    def save_script(self, script_obj):
        if not script_obj:
            raise ValueError("Script object is null")

        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO scripts
                (id, file_path, content, config)
                VALUES (?, ?, ?, ?)
            """, (
                    script_obj.script_id,
                    script_obj.js_file_path,
                    script_obj.js_code,
                    json.dumps(script_obj.config)
            ))
            self.conn.commit()
            return script_obj.js_file_path
        except TypeError as e:
            if "not JSON serializable" in str(e):
                raise ValueError(f"Script config is not JSON serializable: {e}")
            else:
                raise e
        except sqlite3.Error as e:
            logging.error(f"An error occurred while saving script: {e}")
            self.conn.rollback()
            return None

        script_id: The ID of the script.
        optimization_id: The ID of the optimization.

        Returns None if the link was successful, otherwise an error message.
        """
        try:
            self.cursor.execute("""
                INSERT INTO script_optimization_links
                (script_id, optimization_id)
                VALUES (?, ?)
            """, (script_id, optimization_id))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            self.conn.rollback()

    def get_optimizations_for_script(self, script_id):
        """
        Retrieve all optimizations that are linked to the given script.

        :param script_id: The ID of the script to retrieve optimizations for.
        :return: A list of optimization data, where each item is a dictionary containing the optimization's ID,
            script object, initial balance, number of particles, maximum number of iterations, c1 and c2 values,
            weight, damping, global best value, global best position, status, and current iteration.
        """
        try:
            self.cursor.execute("""
                SELECT o.id, o.script_obj, o.initial_balance, o.num_particles, o.max_iter, o.c1, o.c2, o.w, o.damping, o.gbest_value, o.gbest_position, o.status, o.current_iteration
                FROM optimizations o
                INNER JOIN script_optimization_links l ON o.id = l.optimization_id
                WHERE l.script_id = ?
            """, (script_id,))
            rows = self.cursor.fetchall()
            optimizations = []
            for row in rows:
                optimization_data = dict(row)
                optimization_data["gbest_position"] = json.loads(optimization_data["gbest_position"])
                optimizations.append(optimization_data)
            return optimizations
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return []

    def get_result_sets_for_optimization(self, optimization_id):
        """
        Retrieve all result sets for a given optimization.

        optimization_id: The ID of the optimization to retrieve result sets for.

        Returns a list of dictionaries, each containing the id, hash, num_games, and required_median
        of a result set linked to the given optimization. If no result sets are found, returns an empty
        list.
        """
        try:
            self.cursor.execute("""
                SELECT r.id, r.hash, r.num_games, r.required_median
                FROM result_sets r
                INNER JOIN optimization_result_set_links l ON r.id = l.result_set_id
                WHERE l.optimization_id = ?
            """, (optimization_id,))
            rows = self.cursor.fetchall()
            result_sets = []
            for row in rows:
                result_set_data = dict(row)
                result_sets.append(result_set_data)
            return result_sets
        except sqlite3.Error as e:
            logging.error(f"An error occurred: {e}")
            return []

    def save_parameters(self, optimization_id, parameters):
        try:
            for param in parameters:
                self.cursor.execute("""
                    INSERT OR REPLACE INTO parameters
                    (optimization_id, parameter_name, parameter_range, parameter_type)
                    VALUES (?, ?, ?, ?)
                """, (
                    optimization_id,
                    param[0],
                    json.dumps(param[1]),
                    param[2]
                ))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"An error occurred while saving parameters: {e}")
            self.conn.rollback()

    def get_parameters_by_optimization_id(self, optimization_id):
        try:
            self.cursor.execute("""
                SELECT parameter_name, parameter_range, parameter_type
                FROM parameters
                WHERE optimization_id = ?
            """, (optimization_id,))
            rows = self.cursor.fetchall()
            return [(row['parameter_name'], json.loads(row['parameter_range']), row['parameter_type']) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"An error occurred while retrieving parameters: {e}")
            return []

    def get_num_games_by_optimization_id(self, optimization_id):
        try:
            self.cursor.execute("""
                SELECT num_particles
                FROM optimizations
                WHERE id = ?
            """, (optimization_id,))
            row = self.cursor.fetchone()
            return row['num_particles'] if row else None
        except sqlite3.Error as e:
            logging.error(f"An error occurred while retrieving num_particles: {e}")
            return None

    def get_initial_balance_by_optimization_id(self, optimization_id):
        try:
            self.cursor.execute("""
                SELECT initial_balance
                FROM optimizations
                WHERE id = ?
            """, (optimization_id,))
            row = self.cursor.fetchone()
            return row['initial_balance'] if row else None
        except sqlite3.Error as e:
            logging.error(f"An error occurred while retrieving initial_balance: {e}")
            return None

    def close(self):
        # Close the database connection
        self.conn.close()
