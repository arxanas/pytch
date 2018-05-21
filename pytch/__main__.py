import sys
from typing import Sequence, TextIO

import click

from . import FileInfo
from .repl import compile_file, interact, print_errors, run_file


@click.group()
def cli() -> None:
    pass


@cli.command("compile")
@click.argument("source_files", type=click.File(), nargs=-1)
def compile(source_files: Sequence[TextIO]) -> None:
    for source_file in source_files:
        (compiled_output, errors) = compile_file(file_info=FileInfo(
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


@cli.command("repl")
def repl() -> None:
    interact()
