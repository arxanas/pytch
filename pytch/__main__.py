import sys

import click

from pytch import compile_ast, compile_files, get_ast, SourceCodeError


@click.command()
@click.argument("files", type=click.Path(exists=True), nargs=-1)
@click.option("--script", is_flag=True)
def main(files, script):
    try:
        if script:
            _run_script(files)
            return
        else:
            compile_files(files)
    except SourceCodeError as e:
        _print_error(e)


def _run_script(files):
    if len(files) != 1:
        click.echo("Error: Need exactly one script file", err=True)
        sys.exit(1)
    ast = get_ast(files[0])
    source_code = compile_ast(ast)
    exec(source_code)


def _print_error(error):
    message = ""
    message += click.style(
        f"{error.file_path}:{error.line_no}:{error.column_no}: ",
        bold=True,
    )
    message += click.style("error: ", fg="red", bold=True)
    message += error.message

    message += "\n"
    message += error.line_contents

    message += "\n"
    num_spaces = error.error_span[0] - 1
    message += (" " * num_spaces)
    underline_length = error.error_span[1] - error.error_span[0]
    message += click.style("^" * underline_length, fg="green", bold=True)

    click.echo(message)
