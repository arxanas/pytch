import os
import sys

import afl

from .__main__ import compile_file
from .utils import FileInfo


def main() -> None:
    afl.init()
    with open(sys.argv[1]) as f:
        # afl-fuzz will often generate invalid Unicode and count that as a
        # crash. See
        # https://barro.github.io/2018/01/taking-a-look-at-python-afl/
        try:
            file_info = FileInfo(file_path="<stdin>", source_code=f.read())
        except UnicodeDecodeError:
            pass
        else:
            compile_file(file_info, fuzz=True)
    os._exit(0)


if __name__ == "__main__":
    main()
