import queue
import threading
from subprocess import PIPE, Popen

procs: list[Popen] = []
stdout = queue.Queue[str]()


def process_stdout(proc: Popen) -> None:
    assert proc.stdout is not None
    while (line := proc.stdout.readline()) != b"":
        stdout.put(line.decode().strip())
    procs.remove(proc)


def create_proc(uri: str) -> None:
    proc = Popen(["unbuffer", "xdg-open", uri], stdout=PIPE, stderr=PIPE)
    procs.append(proc)
    threading.Thread(target=lambda: process_stdout(proc)).start()
