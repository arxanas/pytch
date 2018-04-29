import sys

from . import FileInfo
from .errors import get_error_lines
from .lexer import lex
from .parser import parse


def main():
    source_code = sys.stdin.read()
    file_info = FileInfo(file_path="<stdin>", source_code=source_code)
    lexation = lex(file_info=file_info)
    for error in lexation.errors:
        sys.stdout.write("\n".join(get_error_lines(error)) + "\n")
    parsation = parse(file_info=file_info, tokens=lexation.tokens)
    for error in parsation.errors:
        sys.stdout.write("\n".join(get_error_lines(error)) + "\n")


if __name__ == "__main__":
    main()
