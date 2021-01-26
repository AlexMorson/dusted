import zlib

from dustmaker.BitReader import BitReader


def read_expect(reader, data):
    for x in data:
        if x != reader.read(8):
            raise ValueError(f"Expected {data}")

def read_intents(reader, intent_size, initial):
    intents = []
    current = initial
    run = 0
    while (token := reader.read(8)) != 0xFF:
        run += token
        intents.extend(run * [current])
        current = hex(reader.read(intent_size))[2:]
        run = 1
    return intents

def read_replay(data):
    reader = BitReader(data)

    read_expect(reader, b"DF_RPL2")

    username_len = reader.read(16)
    username = reader.read_bytes(username_len).decode()

    read_expect(reader, b"DF_RPL1")

    players = reader.read(8)

    reader.skip(8) # Often seems to be 0

    uncompressed_size = reader.read(4 * 8)
    frames = reader.read(4 * 8)

    characters = [reader.read(8) for _ in range(players)]

    levelname_len = reader.read(8)
    levelname = reader.read_bytes(levelname_len).decode()

    # Just read the rest of the data
    r2 = BitReader(zlib.decompress(reader.data[reader.pos // 8 : ]))

    r2.skip(4 * 8) # No idea what this number is

    inputs = []
    inputs.append(read_intents(BitReader(r2.read_bytes(r2.read(4 * 8))), 2, "1")) # X
    inputs.append(read_intents(BitReader(r2.read_bytes(r2.read(4 * 8))), 2, "1")) # Y
    inputs.append(read_intents(BitReader(r2.read_bytes(r2.read(4 * 8))), 2, "0")) # Jump
    inputs.append(read_intents(BitReader(r2.read_bytes(r2.read(4 * 8))), 2, "0")) # Dash
    inputs.append(read_intents(BitReader(r2.read_bytes(r2.read(4 * 8))), 2, "0")) # Fall
    inputs.append(read_intents(BitReader(r2.read_bytes(r2.read(4 * 8))), 4, "0")) # Light
    inputs.append(read_intents(BitReader(r2.read_bytes(r2.read(4 * 8))), 4, "0")) # Heavy

    return {
        "username": username,
        "header": {
            "players": players,
            "characters": characters,
            "levelname": levelname
        },
        "inputs": [
            inputs
        ]
    }
