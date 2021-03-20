import zlib
import struct

from dustmaker.BitReader import BitReader

from . import Replay


def read_short(reader):
    return struct.unpack("<h", reader.read_bytes(2))[0]

def read_int(reader):
    return struct.unpack("<i", reader.read_bytes(4))[0]

def read_replay(data):
    reader = BitReader(data)

    version = None
    meta = {}
    while version not in (b"1", b"3", b"4"):

        if reader.read_bytes(6) != b"DF_RPL":
            return None

        version = reader.read_bytes(1)
        if version == b"2":
            username_len = read_short(reader)
            username = reader.read_bytes(username_len).decode()
            meta = {
                "username": username
            }

    version = int(version.decode())
    is_extended = version >= 3
    if is_extended:
        players = read_short(reader)
    else:
        players = 1
        read_short(reader)

    header = {
        "version": version,
        "players": players,
        "uncompressedSize": read_int(reader),
        "frames": read_int(reader),
        "characters": []
    }
    for i in range(players):
        header["characters"].append(reader.read(8))
    level_len = reader.read(8)
    header["level"] = reader.read_bytes(level_len).decode()

    replay = zlib.decompress(data[reader.pos // 8 :])
    replay_reader = BitReader(replay)

    inputs_len = read_int(replay_reader)
    inputs_all = []
    num_intents = 7
    if version >= 4:
        num_intents = 11
    elif version >= 3:
        num_intents = 8

    for player in range(players):
        inputs = []
        for i in range(num_intents):
            length = read_int(replay_reader)
            datum = replay_reader.read_bytes(length)
            datum_reader = BitReader(datum)

            state = 1 if i < 2 else 0
            states = ""
            payload_size = 4
            if i < 5:
                payload_size = 2
            elif i in (8, 9):
                payload_size = 16
            elif i == 10:
                payload_size = 8

            dpos = 0
            while dpos + 8 <= 8 * len(datum):
                res = datum_reader.read(8)
                if res == 0xFF:
                    break
                if i < 7:
                    for j in range(1 if dpos == 0 else 0, res+1):
                        states += f"{state:x}"
                if dpos + 8 + payload_size <= 8 * len(datum):
                    state = datum_reader.read(payload_size)
                dpos += 8 + payload_size

            if i < 7:
                inputs.append(states)

        inputs_all.append(inputs)

    entity_frame_containers = []
    entity_frame_containers_count = read_int(replay_reader)
    for i in range(entity_frame_containers_count):
        entity_frame_container = {
            "unk1": read_int(replay_reader),
            "unk2": read_int(replay_reader),
            "entityFrames": []
        }
        entity_frame_count = read_int(replay_reader)

        for j in range(entity_frame_count):
            entity_frame_container["entityFrames"].append({
                "time"  : read_int(replay_reader),
                "xpos"  : read_int(replay_reader),
                "ypos"  : read_int(replay_reader),
                "xspeed": read_int(replay_reader),
                "yspeed": read_int(replay_reader),
            })
        entity_frame_containers.append(entity_frame_container)

    return Replay({
        "header": header,
        "inputs": inputs_all,
        "entityFrameContainers": entity_frame_containers,
        "meta": meta
    })
