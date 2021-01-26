import zlib

from dustmaker.BitWriter import BitWriter


def write_intents(writer, intents, size, initial):
    w = BitWriter()
    current = initial
    run = 0
    for intent in intents:
        if intent != current:
            while run >= 0xFF:
                run -= 0xFE
                w.write(8, 0xFE)
                w.write(size, current)
            w.write(8, run)
            w.write(size, current)

            current = int(intent, 16)
            run = 0
        else:
            run += 1
    w.write(8, 0xFF)

    bs = w.bytes()
    writer.write(4 * 8, len(bs))
    writer.write_bytes(bs)


def write_replay(replay):

    intents_writer = BitWriter()
    intents_writer.write(4 * 8, 0)
    inputs = replay["inputs"][0]
    write_intents(intents_writer, inputs[0], 2, 1)
    write_intents(intents_writer, inputs[1], 2, 1)
    write_intents(intents_writer, inputs[2], 2, 0)
    write_intents(intents_writer, inputs[3], 2, 0)
    write_intents(intents_writer, inputs[4], 2, 0)
    write_intents(intents_writer, inputs[5], 4, 0)
    write_intents(intents_writer, inputs[6], 4, 0)
    intents_writer.write(4 * 8, 0)

    writer = BitWriter()

    writer.write_bytes(b"DF_RPL2")

    username = replay["username"].encode()
    writer.write(16, len(username))
    writer.write_bytes(username)

    writer.write_bytes(b"DF_RPL1")

    header = replay["header"]
    writer.write(8, header["players"])
    writer.write(8, 0)
    writer.write(4 * 8, len(intents_writer.bytes()))
    writer.write(4 * 8, max(len(i) for i in inputs))
    for character in header["characters"]:
        writer.write(8, character)
    levelname = header["levelname"].encode()
    writer.write(8, len(levelname))
    writer.write_bytes(levelname)
    writer.write_bytes(zlib.compress(intents_writer.bytes()))

    return writer.bytes()
