from enum import Enum
import sys

import click
import yaml

from .backend import compile_pygments, compile_vscode
from .parser import parse


class OutputFormat(Enum):
    PYGMENTS = "pygments"
    VSCODE = "vscode"


@click.command()
@click.argument("input-file", type=click.File("r"))
@click.option(
    "--output-format",
    "-o",
    help="The syntax highlighting system to target.",
    required=True,
    type=click.Choice(["pygments", "vscode"]),
)
def cli(input_file, output_format: OutputFormat) -> None:
    input_data = yaml.safe_load(input_file)
    output_format = OutputFormat(output_format)

    schema = parse(input_data)
    if output_format == OutputFormat.PYGMENTS:
        sys.stdout.write(compile_pygments(schema))
    elif output_format == OutputFormat.VSCODE:
        sys.stdout.write(compile_vscode(schema))
    else:
        raise AssertionError(f"Unhandled output format {output_format}")


if __name__ == "__main__":
    cli.main()
