import os
import sqlite3

class RegrasDB:
    def __init__(self, db_path="botdata.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        # Tabela de regras
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS regras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                canal_id INTEGER,
                regex TEXT,
                cargo_id INTEGER
            )
        """)
        # Tabela de links
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS fatos_checks_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                link TEXT,
                tipo TEXT
            )
        """)
        # Tabela de configs
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                tag TEXT,
                value TEXT
            )
        """)
        # Tabela de canais
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS osaka_channel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_channel INTEGER,
                id_guild INTEGER,
                allow INTEGER
            )
        """)
        # Tabela de usuários
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS fatos_checks_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                nome TEXT,
                taxa REAL,
                checking REAL,
                deny INTEGER
            )
        """)
        # Tabela de canais
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS fatos_checks_channel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_channel INTEGER,
                id_guild INTEGER,
                allow INTEGER
            )
        """)
        # Tabela de configs
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS fatos_checks_configs (
                guild_id INTEGER PRIMARY KEY,
                enable_fatos INTEGER,
                random_user_enable INTEGER,
                random_taxa REAL,
                all_channel_enable INTEGER,
                enable_security INTEGER
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

    def get_config_by_guild(self, guild_id):
        self.cursor.execute(
            "SELECT * FROM fatos_checks_configs WHERE guild_id = ?", (guild_id,)
        )
        return self.cursor.fetchone()

    def add_config(self, guild_id, enable_fatos, random_user_enable, random_taxa, all_channel_enable, enable_security):
        self.cursor.execute(
            "INSERT INTO fatos_checks_configs (guild_id, enable_fatos, random_user_enable, random_taxa, all_channel_enable, enable_security) VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, int(enable_fatos), int(random_user_enable), float(random_taxa), int(all_channel_enable), int(enable_security))
        )
        self.conn.commit()
        
    def update_config(self, guild_id, enable_fatos, random_user_enable, random_taxa, all_channel_enable, enable_security):
        # Atualiza se já existe, senão insere
        self.cursor.execute("""
            SELECT guild_id FROM fatos_checks_configs WHERE guild_id = ?
        """, (guild_id, ))
        if self.cursor.fetchone():
            self.cursor.execute("""
                UPDATE fatos_checks_configs
                SET enable_fatos = ?, random_user_enable = ?, random_taxa = ?, all_channel_enable = ?, enable_security = ?
                WHERE guild_id = ?
            """, (int(enable_fatos), int(random_user_enable), float(random_taxa), int(all_channel_enable), int(enable_security), guild_id))
        else:
            self.cursor.execute("""
                INSERT INTO fatos_checks_configs (guild_id, enable_fatos, random_user_enable, random_taxa, all_channel_enable, enable_security)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (guild_id, int(enable_fatos), int(random_user_enable), float(random_taxa), int(all_channel_enable), int(enable_security)))
        self.conn.commit()

    def set_user_config(self, user_id, guild_id, nome, taxa, checking, deny):
        # Atualiza se já existe, senão insere
        self.cursor.execute("""
            SELECT id FROM fatos_checks_users WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))
        if self.cursor.fetchone():
            self.cursor.execute("""
                UPDATE fatos_checks_users
                SET nome = ?, taxa = ?, checking = ?, deny = ?
                WHERE user_id = ? AND guild_id = ?
            """, (nome, taxa, checking, deny, user_id, guild_id))
        else:
            self.cursor.execute("""
                INSERT INTO fatos_checks_users (user_id, guild_id, nome, taxa, checking, deny)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, guild_id, nome, taxa, checking, deny))
        self.conn.commit()

    def get_users_by_guild(self, guild_id):
        self.cursor.execute("""
            SELECT * FROM fatos_checks_users WHERE guild_id = ?
        """, (guild_id,))
        return self.cursor.fetchall()

    def remove_user_config(self, user_id, guild_id):
        self.cursor.execute("""
            DELETE FROM fatos_checks_users WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))
        self.conn.commit()
    
    def set_channel_config(self, id_channel, id_guild, allow):
        self.cursor.execute("""
            SELECT id FROM fatos_checks_channel WHERE id_channel = ? AND id_guild = ?
        """, (id_channel, id_guild))
        if self.cursor.fetchone():
            self.cursor.execute("""
                UPDATE fatos_checks_channel
                SET allow = ?
                WHERE id_channel = ? AND id_guild = ?
            """, (int(allow), id_channel, id_guild))
        else:
            self.cursor.execute("""
                INSERT INTO fatos_checks_channel (id_channel, id_guild, allow)
                VALUES (?, ?, ?)
            """, (id_channel, id_guild, int(allow)))
        self.conn.commit()

    def get_channels_by_guild(self, id_guild):
        self.cursor.execute("""
            SELECT id_channel, allow FROM fatos_checks_channel WHERE id_guild = ?
        """, (id_guild,))
        return self.cursor.fetchall()

    def remove_channel_config(self, id_channel, id_guild):
        self.cursor.execute("""
            DELETE FROM fatos_checks_channel WHERE id_channel = ? AND id_guild = ?
        """, (id_channel, id_guild))
        self.conn.commit()
    
    def set_url_config(self, id_guild, url, tipo):
        self.cursor.execute("""
            INSERT INTO fatos_checks_links (guild_id, link, tipo)
            VALUES (?, ?, ?)
        """, (id_guild, url, tipo,))
        self.conn.commit()
 
    def get_url_by_guild(self, guild_id):
        self.cursor.execute("""
            SELECT * FROM fatos_checks_links WHERE guild_id = ?
        """, (guild_id,))
        return self.cursor.fetchall()
    
    def remove_url_config(self, id_guild, id):
        self.cursor.execute("""
            DELETE FROM fatos_checks_links WHERE guild_id = ? AND id = ?
        """, (id_guild, id))
        self.conn.commit()
        
    def check_url_exists(self, guild_id, url, tipo):
        self.cursor.execute("""
            SELECT * FROM fatos_checks_links WHERE guild_id = ? AND link = ? AND tipo = ?
        """, (guild_id, url, tipo, ))
        return self.cursor.fetchone() is not None
 
    def get_configs_by_tag(self, guild_id, tag):
        self.cursor.execute("""
            SELECT value FROM configs WHERE guild_id = ? AND tag = ?
        """, (guild_id, tag, ))
        res = self.cursor.fetchone()
        return res[0] if res else None
    
    def set_config_by_tag(self, guild_id, tag, value):
        existing = self.get_configs_by_tag(guild_id, tag)
        if existing:
            self.cursor.execute("""
                UPDATE configs SET value = ? WHERE guild_id = ? AND tag = ?
            """, (value, guild_id, tag))
        else:
            self.cursor.execute("""
                INSERT INTO configs (guild_id, tag, value) VALUES (?, ?, ?)
            """, (guild_id, tag, value))
        self.conn.commit()
 
    def set_osaka_channel_config(self, id_channel, id_guild, allow):
        self.cursor.execute("""
            SELECT id FROM osaka_channel WHERE id_channel = ? AND id_guild = ?
        """, (id_channel, id_guild))
        if self.cursor.fetchone():
            self.cursor.execute("""
                UPDATE osaka_channel
                SET allow = ?
                WHERE id_channel = ? AND id_guild = ?
            """, (int(allow), id_channel, id_guild))
        else:
            self.cursor.execute("""
                INSERT INTO osaka_channel (id_channel, id_guild, allow)
                VALUES (?, ?, ?)
            """, (id_channel, id_guild, int(allow)))
        self.conn.commit()

    def get_osaka_channels_by_guild(self, id_guild):
        self.cursor.execute("""
            SELECT id_channel, allow FROM osaka_channel WHERE id_guild = ?
        """, (id_guild,))
        return self.cursor.fetchall()
 
    def remove_osaka_channels_by_guild(self, id_channel, id_guild):
        self.cursor.execute("""
            DELETE FROM osaka_channel WHERE id_channel = ? AND id_guild = ?
        """, (id_channel, id_guild))
        self.conn.commit()
        
    def close(self):
        self.conn.close()
        
class MessagesDB:
    def _start_db(self, guild_id):
        os.makedirs("osaka_db", exist_ok=True)
        db_path = f"osaka_db/{guild_id}.db"
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file {db_path} does not exist.")
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
    def get_all_messages(self, guild_id, message):
        try:
            self._start_db(guild_id)
            self.cursor.execute("INSERT OR IGNORE INTO mensagens (id, conteudo) VALUES (?, ?)", (message.id, message.content))
            self.conn.commit()
            self.cursor.execute("SELECT conteudo FROM mensagens")
            messages = self.cursor.fetchall()
            self.cursor.close()
            self.conn.close()
            return messages
        except Exception as e:
            print(f"Error fetching messages: {e}")
            return []