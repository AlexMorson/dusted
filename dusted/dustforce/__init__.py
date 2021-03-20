import platform

if platform.system() == "Windows":
    from .windows import stdout, create_proc
else:
    from .linux import stdout, create_proc


def watch_replay_load_state(replay_id):
    create_proc(f"dustforce://dustmod/replayLoadState/{replay_id}")

def watch_replay(replay_id):
    create_proc(f"dustforce://replay/{replay_id}")
