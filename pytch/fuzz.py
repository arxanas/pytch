import os
import sys

import afl

from . import FileInfo
from .__main__ import run_file


def main() -> None:
    afl.init()
    with open(sys.argv[1]) as f:
        # afl-fuzz will often generate invalid Unicode and count that as a
        # crash. See
        # https://barro.github.io/2018/01/taking-a-look-at-python-afl/
        try:
            file_info = FileInfo(
                file_path="<stdin>",
                source_code=f.read(),
            )
        except UnicodeDecodeError:
            pass
        else:
            run_file(file_info)
    os._exit(0)


if __name__ == "__main__":
    main()
