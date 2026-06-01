import platform

if platform.system() == "Windows":
    from dusted.dustforce.windows import create_proc, events
else:
    from dusted.dustforce.linux import create_proc, events


def watch_replay(replay_id):
    create_proc(f"dustforce://replay/{replay_id}")


def watch_replay_load_state(replay_id):
    create_proc(f"dustforce://dustmod/replayLoadState/{replay_id}")


__all__ = ["events", "watch_replay", "watch_replay_load_state"]
