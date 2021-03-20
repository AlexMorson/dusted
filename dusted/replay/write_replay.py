import math
import struct
import zlib

from dustmaker.BitWriter import BitWriter


def write_short(writer, n):
    writer.write_bytes(struct.pack("<h", n))

def write_int(writer, n):
    writer.write_bytes(struct.pack("<i", n))

def write_replay(replay):
    repmeta = replay.data

    is_extended = (
        repmeta["header"].get("extended", False) or
        repmeta["header"]["players"] > 1
    )
    num_inputs = 8 if is_extended else 7
    input_data = BitWriter()
    for inputs in repmeta["inputs"]:
        for i in range(num_inputs):
            if i < len(inputs):
                inp = inputs[i]
            else:
                inp = ""
            parts = []
            j = 0
            while j < len(inp):
                sz = 1
                while sz < 255 and j + sz < len(inp) and inp[j] == inp[j+sz]:
                    sz += 1
                parts.append((sz, int(inp[j], 16)))
                j += sz

            payload_size = 4 if i in (5, 6) else 2
            bits = 8 + (8 + payload_size) * len(parts)

            inp = BitWriter()
            inp.write(8, 0)
            for part in parts:
                inp.write(payload_size, part[1])
                inp.write(8, part[0] - 1)

            pad = 8 * math.ceil(bits / 8) - inp.pos + 16
            inp.write(pad, (1 << pad) - 1)

            write_int(input_data, len(inp.bytes()))
            input_data.write_bytes(inp.bytes())

    data = BitWriter()
    write_int(data, len(input_data.bytes()))
    data.write_bytes(input_data.bytes())

    write_int(data, len(repmeta["entityFrameContainers"]))
    for entityFrameContainer in repmeta["entityFrameContainers"]:
        write_int(data, entityFrameContainer["unk1"])
        write_int(data, entityFrameContainer["unk2"])
        write_int(data, len(entityFrameContainer["entityFrames"]))
        for entityFrame in entityFrameContainer["entityFrames"]:
            write_int(data, entityFrame["time"])
            write_int(data, entityFrame["xpos"])
            write_int(data, entityFrame["ypos"])
            write_int(data, entityFrame["xspeed"])
            write_int(data, entityFrame["yspeed"])

    replay = BitWriter()
    replay.write_bytes(b"DF_RPL2")

    username = repmeta["meta"]["username"].encode()
    write_short(replay, len(username))
    replay.write_bytes(username)

    replay.write_bytes(b"DF_RPL")
    if is_extended:
        replay.write_bytes(b"3")
    else:
        replay.write_bytes(b"1")
    write_short(replay, repmeta["header"]["players"])
    write_int(replay, len(data.bytes()))
    write_int(replay, repmeta["header"]["frames"])

    for char in repmeta["header"]["characters"]:
        replay.write(8, char)
    replay.write(8, len(repmeta["header"]["level"].encode()))
    replay.write_bytes(repmeta["header"]["level"].encode())
    replay.write_bytes(zlib.compress(data.bytes()))

    return replay.bytes()
