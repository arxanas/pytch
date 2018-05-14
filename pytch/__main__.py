import sys
from typing import List, Sequence, TextIO

import click

from . import FileInfo
from .binder import bind
from .codegen import codegen
from .errors import Error, get_error_lines
from .lexer import lex
from .parser import parse
from .redcst import SyntaxTree as RedSyntaxTree


@click.group()
def cli() -> None:
    pass


@cli.command("compile")
@click.argument("source_files", type=click.File(), nargs=-1)
def compile(source_files: Sequence[TextIO]) -> None:
    for source_file in source_files:
        compiled_output = do_compile(file_info=FileInfo(
            file_path=source_file.name,
            source_code=source_file.read(),
        ))
        if source_file is sys.stdin:
            sys.stdout.write(compiled_output)


@cli.command("run")
@click.argument("source_file", type=click.File())
def run(source_file: TextIO) -> None:
    run_file(file_info=FileInfo(
        file_path=source_file.name,
        source_code=source_file.read(),
    ))


def run_file(file_info: FileInfo) -> None:
    compiled_output = do_compile(file_info=file_info)
    exec(compiled_output)


def do_compile(file_info: FileInfo) -> str:
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

    codegenation = codegen(syntax_tree=red_cst, bindation=bindation)
    return codegenation.get_compiled_output()


def print_errors(errors: List[Error]) -> None:
    for error in errors:
        sys.stdout.write("\n".join(get_error_lines(error)) + "\n")
