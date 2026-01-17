import sqlite3
from datetime import datetime


class Database:
    def __init__(self, path="rotina.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._create()

    def _create(self):
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            inicio TEXT NOT NULL,
            fim TEXT NOT NULL,
            nota TEXT DEFAULT "",
            status INTEGER DEFAULT 0,
            tags TEXT DEFAULT ""
        )
        """)
        self.conn.commit()

    # ===== CRUD =====
    def add(self, nome, inicio, fim, tags=""):
        self.cur.execute(
            "INSERT INTO atividades (nome, inicio, fim, tags) VALUES (?, ?, ?, ?)",
            (nome, inicio, fim, tags)
        )
        self.conn.commit()

    def update(self, id_, nome, inicio, fim, tags):
        self.cur.execute("""
            UPDATE atividades
            SET nome=?, inicio=?, fim=?, tags=?
            WHERE id=?
        """, (nome, inicio, fim, tags, id_))
        self.conn.commit()

    def delete(self, id_):
        self.cur.execute("DELETE FROM atividades WHERE id=?", (id_,))
        self.conn.commit()

    def toggle(self, id_, status):
        self.cur.execute("UPDATE atividades SET status=? WHERE id=?", (status, id_))
        self.conn.commit()

    # ===== QUERIES =====
    def all(self, limit, offset, status=None, search=""):
        q = "SELECT * FROM atividades WHERE 1=1"
        params = []

        if status is not None:
            q += " AND status=?"
            params.append(status)

        if search:
            q += " AND nome LIKE ?"
            params.append(f"%{search}%")

        q += " ORDER BY inicio LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        return self.cur.execute(q, params).fetchall()

    def pendentes(self):
        return self.cur.execute(
            "SELECT id, nome, inicio FROM atividades WHERE status=0"
        ).fetchall()

    # ===== NOTAS =====
    def nota(self, id_):
        r = self.cur.execute(
            "SELECT nota FROM atividades WHERE id=?", (id_,)
        ).fetchone()
        return r["nota"] if r else ""

    def update_nota(self, id_, nota):
        self.cur.execute(
            "UPDATE atividades SET nota=? WHERE id=?", (nota, id_)
        )
        self.conn.commit()

