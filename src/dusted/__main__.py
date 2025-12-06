import logging
from pathlib import Path

import platformdirs

from dusted.gui import App


def main():
    log_file = Path(platformdirs.user_log_dir(opinion=False)) / "dusted.log"
    file_handler = logging.FileHandler(log_file, "w")
    stream_handler = logging.StreamHandler()
    logging.basicConfig(
        handlers=[file_handler, stream_handler],
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    App().mainloop()


if __name__ == "__main__":
    main()
