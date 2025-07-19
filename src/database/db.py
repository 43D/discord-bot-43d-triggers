import sqlite3

class RegrasDB:
    def __init__(self, db_path="botdata.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS regras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                canal_id INTEGER,
                regex TEXT,
                cargo_id INTEGER
            )
        """)
        self.conn.commit()

    def add_regra(self, guild_id, canal_id, regex, cargo_id):
        self.cursor.execute(
            "INSERT INTO regras (guild_id, canal_id, regex, cargo_id) VALUES (?, ?, ?, ?)",
            (guild_id, canal_id, regex, cargo_id)
        )
        self.conn.commit()

    def get_regras_by_guild(self, guild_id):
        self.cursor.execute(
            "SELECT id, canal_id, regex, cargo_id FROM regras WHERE guild_id = ?",
            (guild_id,)
        )
        return self.cursor.fetchall()

    def remove_regra(self, guild_id, regra_id):
        self.cursor.execute(
            "DELETE FROM regras WHERE guild_id = ? AND id = ?",
            (guild_id, regra_id)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()