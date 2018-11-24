import sys
from typing import Sequence, TextIO

import click

from .lexer import lex
from .parser import dump_syntax_tree, parse
from .repl import compile_file, interact, print_errors, run_file
from .utils import FileInfo


@click.group()
def cli() -> None:
    pass


@cli.command("compile")
@click.argument("source_files", type=click.File(), nargs=-1)
@click.option("--dump-tree", is_flag=True)
def compile(source_files: Sequence[TextIO], dump_tree: bool) -> None:
    for source_file in source_files:
        file_info = FileInfo(file_path=source_file.name, source_code=source_file.read())
        if dump_tree:
            errors = []
            lexation = lex(file_info=file_info)
            errors.extend(lexation.errors)
            parsation = parse(file_info=file_info, tokens=lexation.tokens)
            errors.extend(parsation.errors)
            print_errors(errors)

            (offset, lines) = dump_syntax_tree(
                file_info.source_code, ast_node=parsation.green_cst
            )
            sys.stdout.write("".join(line + "\n" for line in lines))
        else:
            (compiled_output, errors) = compile_file(file_info=file_info)
            print_errors(errors)
            if compiled_output is not None and source_file is sys.stdin:
                sys.stdout.write(compiled_output)


@cli.command("run")
@click.argument("source_file", type=click.File())
def run(source_file: TextIO) -> None:
    run_file(
        file_info=FileInfo(file_path=source_file.name, source_code=source_file.read())
    )


@cli.command("repl")
def repl() -> None:
    interact()
