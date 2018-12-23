import os
import sys

import afl

from pytch.lexer import lex
from pytch.parser import parse
from pytch.utils import FileInfo


def check_for_buggy_parse(file_info: FileInfo) -> None:
    lexation = lex(file_info=file_info)
    parsation = parse(file_info=file_info, tokens=lexation.tokens)
    if parsation.is_buggy:
        raise ValueError("found buggy parse")


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
            check_for_buggy_parse(file_info)
    os._exit(0)


if __name__ == "__main__":
    main()
