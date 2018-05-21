from code import InteractiveConsole
import re
import readline
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import __version__, FileInfo
from .binder import bind
from .codegen import codegen
from .errors import Error, get_error_lines, Severity
from .lexer import lex
from .parser import parse
from .redcst import SyntaxTree as RedSyntaxTree


NO_MORE_INPUT_REQUIRED = False
MORE_INPUT_REQUIRED = True
LEADING_WHITESPACE_RE = re.compile("^\s*")


class PytchRepl(InteractiveConsole):
    def __init__(self) -> None:
        super().__init__()
        self.buffer: List[str] = []
        self.locals: Dict[str, Any] = {}
        self.all_source_code = ""
        readline.set_completer(lambda text, state: text + "foo")

    def push(self, line: str) -> bool:
        readline.insert_text("foo")
        if line:
            self.buffer.append(line)
            match = LEADING_WHITESPACE_RE.match(line)
            if match is not None:
                readline.insert_text(match.group())
            return MORE_INPUT_REQUIRED

        source_code = "\n".join(self.buffer)
        self.resetbuffer()

        run_file(FileInfo(
            file_path="<repl>",
            source_code=self.all_source_code + source_code,
        ))
        return NO_MORE_INPUT_REQUIRED


def interact() -> None:
    PytchRepl().interact(
        banner=f"Pytch version {__version__} REPL",
        exitmsg="",
    )


def run_file(file_info: FileInfo) -> None:
    (compiled_output, errors) = compile_file(file_info=file_info)
    print_errors(errors)
    if compiled_output is not None:
        exec(compiled_output)


def compile_file(
    file_info: FileInfo,
    fuzz: bool = False,
) -> Tuple[Optional[str], List[Error]]:
    all_errors = []
    lexation = lex(file_info=file_info)
    all_errors.extend(lexation.errors)
    parsation = parse(file_info=file_info, tokens=lexation.tokens)
    all_errors.extend(parsation.errors)

    if fuzz and parsation.is_buggy:
        sys.exit(1)

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
    ascii = (not sys.stderr.isatty())
    for error in errors:
        sys.stderr.write("\n".join(get_error_lines(error, ascii=ascii)) + "\n")


__all__ = [
    "compile_file",
    "interact",
    "print_errors",
    "run_file",
]
