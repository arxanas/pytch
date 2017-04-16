import click

from pytch import compile_files


@click.command()
@click.argument("files", nargs=-1)
def main(files):
    compile_files(files)
