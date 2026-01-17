import sqlite3

DB_NAME = "rotina.db"
BACKUP_SUFFIX = "_backup"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.cur = self.conn.cursor()
        self.create()
        self.indexes()

    def create(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS atividades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                inicio TEXT NOT NULL,
                fim TEXT NOT NULL,
                nota TEXT,
                status INTEGER DEFAULT 0,
                tags TEXT
            )
        """)
        self.conn.commit()

    def indexes(self):
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_inicio ON atividades(inicio)")
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_status ON atividades(status)")
        self.conn.commit()

    def add(self, nome, inicio, fim, tags):
        self.cur.execute(
            "INSERT INTO atividades VALUES (NULL, ?, ?, ?, '', 0, ?)",
            (nome, inicio, fim, tags)
        )
        self.conn.commit()
        self.backup()

    def update(self, id_, nome, inicio, fim, tags):
        self.cur.execute(
            "UPDATE atividades SET nome=?, inicio=?, fim=?, tags=? WHERE id=?",
            (nome, inicio, fim, tags, id_)
        )
        self.conn.commit()

    def all(self, limit, offset, status=None, busca=None):
        q = "SELECT * FROM atividades WHERE 1=1"
        p = []

        if status is not None:
            q += " AND status=?"
            p.append(status)

        if busca:
            q += " AND (nome LIKE ? OR tags LIKE ?)"
            p += [f"%{busca}%", f"%{busca}%"]

        q += " ORDER BY inicio ASC LIMIT ? OFFSET ?"
        p += [limit, offset]

        self.cur.execute(q, p)
        return self.cur.fetchall()

    def pendentes(self):
        self.cur.execute("SELECT id, nome, inicio FROM atividades WHERE status=0")
        return self.cur.fetchall()

    def toggle(self, id_, status):
        self.cur.execute("UPDATE atividades SET status=? WHERE id=?", (status, id_))
        self.conn.commit()

    def delete(self, id_):
        self.cur.execute("DELETE FROM atividades WHERE id=?", (id_,))
        self.conn.commit()

    def nota(self, id_):
        self.cur.execute("SELECT nota FROM atividades WHERE id=?", (id_,))
        r = self.cur.fetchone()
        return r[0] if r else ""

    def update_nota(self, id_, nota):
        self.cur.execute("UPDATE atividades SET nota=? WHERE id=?", (nota, id_))
        self.conn.commit()

    def backup(self):
        try:
            with open(DB_NAME, "rb") as a, open(DB_NAME + BACKUP_SUFFIX, "wb") as b:
                b.write(a.read())
        except Exception:
            pass