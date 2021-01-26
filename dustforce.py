import queue
import threading
from subprocess import PIPE, Popen

procs = []
stdout = queue.Queue()

def create_proc(uri):
    proc = Popen(["unbuffer", "xdg-open", uri], stdout=PIPE, stderr=PIPE)
    procs.append(proc)
    threading.Thread(target=lambda:process_stdout(proc)).start()

def process_stdout(proc):
    while (line := proc.stdout.readline()) != b'':
        stdout.put(line.decode().strip())
    procs.remove(proc)

def watch_replay_load_state(replay_id):
    create_proc(f"dustforce://dustmod/replayLoadState/{replay_id}")

def watch_replay(replay_id):
    create_proc(f"dustforce://replay/{replay_id}")
