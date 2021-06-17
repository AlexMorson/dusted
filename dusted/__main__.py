import logging
from pathlib import Path

import appdirs

from .gui import App


def main():
    log_file = Path(appdirs.user_log_dir(opinion=False)) / "dusted.log"
    logging.basicConfig(
        filename=str(log_file),
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    App().mainloop()


if __name__ == "__main__":
    main()
