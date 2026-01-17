import time
import os
import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Caminho do seu projeto
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

# Extensões consideradas "grandes mudanças"
WATCHED_EXTENSIONS = (".py", ".qss", ".ui")

# Flag para saber se houve mudança relevante
changed = False

class ChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        global changed
        if event.is_directory:
            return
        if event.src_path.endswith(WATCHED_EXTENSIONS):
            changed = True

if __name__ == "__main__":
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, PROJECT_PATH, recursive=True)
    observer.start()
    print("Monitorando alterações...", flush=True)

    try:
        while True:
            for _ in range(60):  # 1 minuto em segundos
                time.sleep(1)
            if changed:
                status = os.popen("git status --porcelain").read().strip()
                if status:
                    msg = f"Auto commit {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    os.system("git add .")
                    os.system(f'git commit -m "{msg}"')
                    os.system("git push")
                    print("Alterações enviadas para o GitHub.", flush=True)
                else:
                    print("Mudança detectada, mas nada para commitar.", flush=True)
                changed = False
            else:
                print("Nenhuma alteração relevante detectada.", flush=True)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    