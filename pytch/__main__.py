import sys
from typing import List

from . import FileInfo
from .binder import bind
from .errors import Error, get_error_lines
from .lexer import lex
from .parser import parse
from .redcst import SyntaxTree as RedSyntaxTree


def main():
    process_source_code(source_code=sys.stdin.read())


def process_source_code(source_code: str) -> None:
    file_info = FileInfo(file_path="<stdin>", source_code=source_code)

    lexation = lex(file_info=file_info)
    print_errors(lexation.errors)

    parsation = parse(file_info=file_info, tokens=lexation.tokens)
    print_errors(parsation.errors)
    if parsation.is_buggy:
        sys.exit(1)

    red_cst = RedSyntaxTree(
        parent=None,
        origin=parsation.green_cst,
        offset=0,
    )

    bindation = bind(file_info=file_info, syntax_tree=red_cst)
    print_errors(bindation.errors)


def print_errors(errors: List[Error]) -> None:
    for error in errors:
        sys.stdout.write("\n".join(get_error_lines(error)) + "\n")


if __name__ == "__main__":
    main()
