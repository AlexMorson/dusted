import errno
import os
import pty
import queue
import threading
from subprocess import DEVNULL, Popen

from dusted.dustforce.event import Event, parse_event

events = queue.Queue[Event]()


def process_stdout(rx_fd: int) -> None:
    buffer = b""
    while True:
        try:
            data = os.read(rx_fd, 1000)
        except OSError as error:
            if error.errno == errno.EIO:
                break
            raise

        if data == b"":
            break
        buffer += data

        *lines, buffer = buffer.split(b"\n")
        for line in lines:
            if event := parse_event(line.decode(errors="replace").strip()):
                events.put(event)

    os.close(rx_fd)


def create_proc(uri: str) -> None:
    # Pretend that we are a terminal to force Dustforce to not buffer its
    # output when writing to the console.
    rx_fd, tx_fd = pty.openpty()

    # Open the Dustforce URI in a new process, with its stdout writing to the
    # pseudo-terminal.
    Popen(["xdg-open", uri], stdout=tx_fd, stderr=DEVNULL, bufsize=0)

    # Close the write end of the pseudo-terminal. We aren't going to write to
    # it from this process.
    os.close(tx_fd)

    # Process the output from the Dustforce process in a separate thread to
    # avoid blocking the GUI when reading from the file descriptor.
    threading.Thread(target=process_stdout, args=(rx_fd,)).start()
