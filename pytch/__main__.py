import sys
from typing import List, Optional, Sequence, TextIO, Tuple

import click

from . import FileInfo
from .binder import bind
from .codegen import codegen
from .errors import Error, get_error_lines, Severity
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
        (compiled_output, errors) = do_compile(file_info=FileInfo(
            file_path=source_file.name,
            source_code=source_file.read(),
        ))
        print_errors(errors)
        if compiled_output is not None and source_file is sys.stdin:
            sys.stdout.write(compiled_output)


@cli.command("run")
@click.argument("source_file", type=click.File())
def run(source_file: TextIO) -> None:
    run_file(file_info=FileInfo(
        file_path=source_file.name,
        source_code=source_file.read(),
    ))


def run_file(file_info: FileInfo) -> None:
    (compiled_output, errors) = do_compile(file_info=file_info)
    print_errors(errors)
    if compiled_output is not None:
        exec(compiled_output)


def do_compile(file_info: FileInfo) -> Tuple[Optional[str], List[Error]]:
    all_errors = []
    lexation = lex(file_info=file_info)
    all_errors.extend(lexation.errors)
    parsation = parse(file_info=file_info, tokens=lexation.tokens)
    if parsation.is_buggy:
        # Exit for fuzzing.
        sys.exit(1)

    all_errors.extend(parsation.errors)
    if has_fatal_error(all_errors):
        return (None, all_errors)

    red_cst = RedSyntaxTree(
        parent=None,
        origin=parsation.green_cst,
        offset=0,
    )

    bindation = bind(file_info=file_info, syntax_tree=red_cst)
    all_errors.extend(bindation.errors)
    if has_fatal_error(all_errors):
        return (None, all_errors)

    codegenation = codegen(syntax_tree=red_cst, bindation=bindation)
    all_errors.extend(codegenation.errors)
    if has_fatal_error(all_errors):
        return (None, all_errors)

    return (codegenation.get_compiled_output(), all_errors)


def has_fatal_error(errors: Sequence[Error]) -> bool:
    return any(
        error.severity == Severity.ERROR
        for error in errors
    )


def print_errors(errors: List[Error]) -> None:
    ascii = not sys.stdout.isatty()

    for error in errors:
        sys.stdout.write("\n".join(get_error_lines(error, ascii=ascii)) + "\n")
