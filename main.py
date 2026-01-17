import sys
import os
import logging
from datetime import datetime, timedelta  # noqa: F401

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QDialog, QTextEdit,
    QMessageBox, QMenu, QComboBox,
    QTimeEdit, QDateEdit, QInputDialog
)
from PySide6.QtCore import Qt, QTimer, QTime, QDate
from PySide6.QtGui import QIcon

from database import Database  # NOVO: banco separado

# ================= CONFIG =================
logging.basicConfig(level=logging.INFO)

STYLES_DIR = "styles"
DARK_THEME = "dark.qss"
LIGHT_THEME = "light.qss"

NOTIFICATION_MINUTES = 5
PAGE_SIZE = 30

def resource_path(path):
    try:
        base = sys._MEIPASS
    except AttributeError:
        base = os.path.abspath(".")
    return os.path.join(base, path)

# ================= NOTA DIALOG =================
class NotaDialog(QDialog):
    def __init__(self, id_, nome, db, dark):
        super().__init__()
        self.db = db
        self.id_ = id_
        self.dark = dark

        self.setWindowTitle(f"Anotação — {nome}")
        self.resize(420, 300)

        layout = QVBoxLayout(self)

        self.text = QTextEdit()
        self.text.setText(self.db.nota(id_))
        layout.addWidget(self.text)

        save = QPushButton(QIcon.fromTheme("document-save"), "Salvar")
        save.clicked.connect(self.save)
        layout.addWidget(save)

        self.load_styles()

    def save(self):
        self.db.update_nota(self.id_, self.text.toPlainText())
        self.accept()

    def load_styles(self):
        theme = DARK_THEME if self.dark else LIGHT_THEME
        path = resource_path(f"{STYLES_DIR}/{theme}")
        if os.path.exists(path):
            self.setStyleSheet(open(path, encoding="utf-8").read())

# ================= ITEM =================
class ItemAtividade(QWidget):
    def __init__(self, nome, inicio, fim, status, tags):
        super().__init__()
        v = QVBoxLayout(self)
        v.setSpacing(8)
        v.setContentsMargins(10, 8, 10, 8)

        # ===== TÍTULO =====
        top = QHBoxLayout()

        title = QLabel(nome)
        title.setStyleSheet(
            "font-size:15px;"
            "font-weight:600;"
            + ("text-decoration:line-through;color:#888;" if status else "")
        )
        dot = QLabel("●")
        dot.setStyleSheet("color:#22c55e;" if status else "color:#ef4444;")

        top.addWidget(title)
        top.addStretch()
        top.addWidget(dot)

        v.addLayout(top)

        # ===== HORÁRIO =====
        horario = QLabel(f"{inicio[11:16]} - {fim[11:16]}")
        horario.setStyleSheet("font-size:12px;color:#aaa;")
        v.addWidget(horario, alignment=Qt.AlignLeft)

        # ===== TAG BADGE =====
        if tags:
            badge = QLabel(tags.upper())
            badge.setAlignment(Qt.AlignLeft)
            badge.setStyleSheet("""
                QLabel {
                    font-size:11px;
                    padding:3px 8px;
                    border-radius:8px;
                    background-color: rgba(120,120,120,0.15);
                    color: #bbb;
                }
            """)
            v.addWidget(badge, alignment=Qt.AlignLeft)

# ================= PLANNER =================
class Planner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rotina Ghost")
        self.setWindowIcon(QIcon(resource_path("icon.png")))
        self.resize(560, 700)

        self.db = Database()
        self.dark = True
        self.offset = 0
        self.notificados = set()

        layout = QVBoxLayout(self)

        # ===== TOPO =====
        top = QHBoxLayout()

        self.nome = QLineEdit()
        self.nome.setPlaceholderText("Atividade")

        self.data = QDateEdit(QDate.currentDate())
        self.data.setCalendarPopup(True)

        self.inicio = QTimeEdit(QTime.currentTime())
        self.fim = QTimeEdit(QTime.currentTime().addSecs(3600))

        self.tags = QLineEdit()
        self.tags.setPlaceholderText("Tags")

        add = QPushButton(QIcon.fromTheme("list-add"), "")
        add.setToolTip("Adicionar atividade")
        add.clicked.connect(self.add)

        self.theme_btn = QPushButton("🌙" if self.dark else "☀️")
        self.theme_btn.setToolTip("Alternar tema")
        self.theme_btn.clicked.connect(self.toggle_theme)

        for w in (self.nome, self.data, self.inicio, self.fim, self.tags, add, self.theme_btn):
            top.addWidget(w)

        layout.addLayout(top)

        # ===== FILTROS =====
        filtros = QHBoxLayout()

        self.status = QComboBox()
        self.status.addItems(["Todos", "Pendentes", "Concluídas"])
        self.status.currentIndexChanged.connect(self.reset)

        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar")
        self.busca.textChanged.connect(self.reset)

        filtros.addWidget(self.status)
        filtros.addWidget(self.busca)
        layout.addLayout(filtros)

        # ===== LISTA =====
        self.lista = QListWidget()
        self.lista.verticalScrollBar().valueChanged.connect(self.scroll)
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista.customContextMenuRequested.connect(self.menu)
        self.lista.itemDoubleClicked.connect(self.open_note)
        layout.addWidget(self.lista)

        # ===== AVISO VAZIO =====
        self.aviso_vazio = QLabel("Nenhuma atividade encontrada.")
        self.aviso_vazio.setAlignment(Qt.AlignCenter)
        self.aviso_vazio.setStyleSheet("color:#888;font-size:16px;")
        layout.addWidget(self.aviso_vazio)
        self.aviso_vazio.hide()

        self.load_styles()
        self.reset()
        self.start_notifications()

    # ===== THEME =====
    def load_styles(self):
        theme = DARK_THEME if self.dark else LIGHT_THEME
        path = resource_path(f"{STYLES_DIR}/{theme}")
        if os.path.exists(path):
            self.setStyleSheet(open(path, encoding="utf-8").read())

    def toggle_theme(self):
        self.dark = not self.dark
        self.theme_btn.setText("🌙" if self.dark else "☀️")
        self.load_styles()

    # ===== CRUD =====
    def add(self):
        if not self.nome.text():
            return

        d = self.data.date().toPython()
        inicio = datetime.combine(d, self.inicio.time().toPython()).isoformat(" ")
        fim = datetime.combine(d, self.fim.time().toPython()).isoformat(" ")

        self.db.add(self.nome.text(), inicio, fim, self.tags.text())
        self.nome.clear()
        self.tags.clear()
        self.reset()

    def edit(self, item):
        id_, nome, status = item.data(Qt.UserRole)
        row = self.db.cur.execute("SELECT * FROM atividades WHERE id=?", (id_,)).fetchone()
        if not row:
            return
        _, nome, inicio, fim, _, _, tags = row

        # Editar nome
        new_nome, ok = QInputDialog.getText(self, "Editar Atividade", "Nome:", text=nome)
        if not ok or not new_nome:
            return

        # Editar data/hora
        dt = QDate.fromString(inicio[:10], "yyyy-MM-dd")
        tm_ini = QTime.fromString(inicio[11:16], "HH:mm")
        tm_fim = QTime.fromString(fim[11:16], "HH:mm")

        new_data, ok = QInputDialog.getText(self, "Editar Data", "Data (YYYY-MM-DD):", text=dt.toString("yyyy-MM-dd"))
        if not ok or not new_data:
            return
        new_ini, ok = QInputDialog.getText(self, "Editar Início", "Início (HH:MM):", text=tm_ini.toString("HH:mm"))
        if not ok or not new_ini:
            return
        new_fim, ok = QInputDialog.getText(self, "Editar Fim", "Fim (HH:MM):", text=tm_fim.toString("HH:mm"))
        if not ok or not new_fim:
            return

        # Editar tags
        new_tags, ok = QInputDialog.getText(self, "Editar Tags", "Tags:", text=tags)
        if not ok:
            return

        try:
            inicio_str = f"{new_data} {new_ini}:00"
            fim_str = f"{new_data} {new_fim}:00"
            datetime.strptime(inicio_str, "%Y-%m-%d %H:%M:%S")
            datetime.strptime(fim_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            QMessageBox.warning(self, "Erro", "Data ou hora inválida.")
            return

        self.db.update(id_, new_nome, inicio_str, fim_str, new_tags)
        self.reset()

    def reset(self):
        self.lista.clear()
        self.offset = 0
        self.load()

    def load(self):
        st = None
        if self.status.currentText() == "Pendentes":
            st = 0
        elif self.status.currentText() == "Concluídas":
            st = 1

        rows = self.db.all(PAGE_SIZE, self.offset, st, self.busca.text())
        if not rows and self.offset == 0:
            self.aviso_vazio.show()
        else:
            self.aviso_vazio.hide()
        for r in rows:
            id_, nome, ini, fim, _, status, tags = r
            w = ItemAtividade(nome, ini, fim, status, tags)
            i = QListWidgetItem()
            i.setSizeHint(w.sizeHint())
            i.setData(Qt.UserRole, (id_, nome, status))
            self.lista.addItem(i)
            self.lista.setItemWidget(i, w)

        self.offset += len(rows)

    def scroll(self, v):
        if v == self.lista.verticalScrollBar().maximum():
            self.load()

    def menu(self, pos):
        item = self.lista.itemAt(pos)
        if not item:
            return

        id_, nome, status = item.data(Qt.UserRole)
        m = QMenu(self)

        note = m.addAction(QIcon.fromTheme("document-edit"), "Anotação")
        edit = m.addAction(QIcon.fromTheme("edit-rename"), "Editar")
        toggle = m.addAction(QIcon.fromTheme("emblem-ok"), "Concluir" if not status else "Reabrir")
        delete = m.addAction(QIcon.fromTheme("edit-delete"), "Excluir")

        a = m.exec(self.lista.mapToGlobal(pos))
        if a == note:
            self.open_note(item)
        elif a == edit:
            self.edit(item)
        elif a == toggle:
            self.db.toggle(id_, 0 if status else 1)
            self.reset()
        elif a == delete:
            reply = QMessageBox.question(self, "Excluir", f"Excluir '{nome}'?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.db.delete(id_)
                self.reset()

    def open_note(self, item):
        id_, nome, _ = item.data(Qt.UserRole)
        NotaDialog(id_, nome, self.db, self.dark).exec()

    # ===== NOTIFICAÇÕES =====
    def start_notifications(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.notify)
        self.timer.start(60000)

    def notify(self):
        now = datetime.now()

        for id_, nome, inicio in self.db.pendentes():
            if id_ in self.notificados:
                continue

            dt = datetime.fromisoformat(inicio)
            diff = (dt - now).total_seconds() / 60

            if 0 < diff <= NOTIFICATION_MINUTES:
                QMessageBox.information(
                    self,
                    "Lembrete",
                    f"'{nome}' começa em {int(diff)} minutos"
                )
                self.notificados.add(id_)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Planner()
    window.show()
    sys.exit(app.exec())
    