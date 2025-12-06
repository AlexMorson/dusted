import platform

if platform.system() == "Windows":
    from dusted.dustforce.windows import stdout, create_proc
else:
    from dusted.dustforce.linux import stdout, create_proc


def watch_replay(replay_id):
    create_proc(f"dustforce://replay/{replay_id}")


def watch_replay_load_state(replay_id):
    create_proc(f"dustforce://dustmod/replayLoadState/{replay_id}")


__all__ = ["stdout", "watch_replay", "watch_replay_load_state"]
