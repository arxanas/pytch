import sys
from typing import List, TextIO

import click

from . import FileInfo
from .binder import bind
from .errors import Error, get_error_lines
from .lexer import lex
from .parser import parse
from .redcst import SyntaxTree as RedSyntaxTree


@click.group()
def cli() -> None:
    pass


@cli.command("run")
@click.argument("source_file", type=click.File())
def run(source_file: TextIO) -> None:
    run_file(file_info=FileInfo(
        file_path=source_file.name,
        source_code=source_file.read(),
    ))


def run_file(file_info: FileInfo) -> None:
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
