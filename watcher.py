from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from extensions import socketio
import os


class JSONHandler(FileSystemEventHandler):

    def on_modified(self, event):

        if event.is_directory:
            return

        if not event.src_path.endswith(".json"):
            return


        filename = os.path.basename(
            event.src_path
        )


        print(
            "Geändert:",
            filename
        )


        if filename == "scenes.json":

            socketio.emit(
                "scene_update",
                {
                    "file": filename
                }
            )


        elif filename == "sequences.json":

            socketio.emit(
                "sequence_update",
                {
                    "file": filename
                }
            )


        elif filename == "triggers.json":

            socketio.emit(
                "trigger_update",
                {
                    "file": filename
                }
            )



class DataWatcher:


    def __init__(self, path="data"):

        self.path = path
        self.observer = Observer()


    def start(self):

        handler = JSONHandler()


        self.observer.schedule(
            handler,
            self.path,
            recursive=False
        )


        self.observer.start()


        print(
            "Watcher aktiv:",
            self.path
        )


    def stop(self):

        self.observer.stop()
        self.observer.join()