import queue
import threading
from subprocess import PIPE, Popen

from dusted.dustforce.event import Event, parse_event

procs: list[Popen] = []
events = queue.Queue[Event]()


def process_stdout(proc: Popen) -> None:
    assert proc.stdout is not None
    while (line := proc.stdout.readline()) != b"":
        if event := parse_event(line.decode().strip()):
            events.put(event)
    procs.remove(proc)


def create_proc(uri: str) -> None:
    proc = Popen(["unbuffer", "xdg-open", uri], stdout=PIPE, stderr=PIPE)
    procs.append(proc)
    threading.Thread(target=lambda: process_stdout(proc)).start()
