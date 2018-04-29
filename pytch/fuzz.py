import os
import sys

import afl

from pytch.__main__ import process_source_code


def main() -> None:
    afl.init()
    with open(sys.argv[1]) as f:
        # afl-fuzz will often generate invalid Unicode and count that as a
        # crash. See
        # https://barro.github.io/2018/01/taking-a-look-at-python-afl/
        try:
            contents = f.read()
        except UnicodeDecodeError:
            pass
        else:
            process_source_code(contents)
    os._exit(0)


if __name__ == "__main__":
    main()
