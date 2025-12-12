import os
import queue
import threading
import time

from dusted.config import config

watcher = None
stdout = queue.Queue[str]()


class LogfileWatcher:
    def __init__(self, path):
        self.path = path
        self.size = 0
        self.file = None

    def start(self):
        while 1:
            try:
                new_size = os.path.getsize(self.path)
                if self.file is None or new_size < self.size:
                    if self.file is not None:
                        self.file.close()
                    self.file = open(self.path)
                    self.file.seek(max(0, new_size - 4096))
                self.size = new_size

                while line := self.file.readline():
                    stdout.put(line.strip())

                time.sleep(1 / 60)

            except FileNotFoundError:
                self.file = None
                time.sleep(1)


def create_proc(uri):
    global watcher
    if watcher is None:
        path = os.path.join(config.dustforce_path, "output.log")
        watcher = LogfileWatcher(path)
        logfile_thread = threading.Thread(target=watcher.start, daemon=True)
        logfile_thread.start()

    os.startfile(uri)
