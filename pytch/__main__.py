import sys

import click

from pytch import compile_ast, compile_files, get_ast


@click.command()
@click.argument("files", type=click.Path(exists=True), nargs=-1)
@click.option("--script", is_flag=True)
def main(files, script):
    if script:
        _run_script(files)
        return
    else:
        compile_files(files)


def _run_script(files):
    if len(files) != 1:
        click.echo("Error: Need exactly one script file", err=True)
        sys.exit(1)
    ast = get_ast(files[0])
    source_code = compile_ast(ast)
    exec(source_code)
