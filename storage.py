import sqlite3


class Storage:
  def __init__(self, db_path):
    self.conn = sqlite3.connect(db_path, check_same_thread=False)
    self.conn.execute("PRAGMA foreign_keys=ON")
    self.conn.row_factory = sqlite3.Row
    self.cursor = self.conn.cursor()
    self.create_tables()

  def create_tables(self):
    self.cursor.execute(
      '''
      CREATE TABLE IF NOT EXISTS optimizations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        script_obj TEXT NOT NULL,
        initial_balance REAL NOT NULL,
        game_results TEXT NOT NULL,
        parameter_names TEXT NOT NULL,
        space TEXT NOT NULL
        num_particles INTEGER NOT NULL,
        max_iter INTEGER NOT NULL,
        c1 REAL NOT NULL,
        c2 REAL NOT NULL,
        w REAL NOT NULL,
        damping REAL NOT NULL
        gbest_value REAL NOT NULL,
        gbest_position TEXT NOT NULL
      )
  ''')

  def save_optimization(self, optimization_data):
    self.cursor.execute(
      '''
      INSERT INTO optimizations
        (script_obj, initial_balance, game_results, parameter_names, space, num_particles, max_iter, c1, c2, w, damping, gbest_value, gbest_position)
      VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ''',
      (optimization_data['script_obj'],
       optimization_data['initial_balance'],
       optimization_data['game_results'],
       optimization_data['parameter_names'],
       optimization_data['space'],
       optimization_data['num_particles'],
       optimization_data['max_iter'],
       optimization_data['c1'],
       optimization_data['c2'],
       optimization_data['w'],
       optimization_data['damping'],
       optimization_data['gbest_value'],
       optimization_data['gbest_position'])
    )
    self.conn.commit()

  def load_optimization(self, optimization_id):
          self.cursor.execute('''
              SELECT * FROM optimizations WHERE id = ?
          ''', (optimization_id,))
          row = self.cursor.fetchone()
          if row:
              return {
                  'script_obj': row[1],
                  'initial_balance': row[2],
                  'game_results': row[3],
                  'parameter_names': row[4],
                  'space': row[5],
                  'num_particles': row[6],
                  'max_iter': row[7],
                  'c1': row[8],
                  'c2': row[9],
                  'w': row[10],
                  'damping': row[11],
                  'gbest_value': row[12],
                  'gbest_position': row[13]
              }
          else:
              return None
