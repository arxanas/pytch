import os.path
from typing import Any, Callable, Iterator, List, Optional, Tuple

import pytest

from pytch.errors import Error
from pytch.lexer import lex
from pytch.parser import parse
from pytch.redcst import SyntaxTree
from pytch.utils import FileInfo


# Note that we can't call this `TestCaseInfo` because then it would be
# collected as a test.
class CaseInfo:
    def __init__(
        self, input_filename: str, output_filename: str, error_filename: Optional[str]
    ) -> None:
        self._input_filename = input_filename
        self._output_filename = output_filename
        self._error_filename = error_filename

    @property
    def name(self) -> str:
        return os.path.splitext(self.input_filename)[0]

    @property
    def input_filename(self) -> str:
        return self._input_filename

    @property
    def input(self) -> str:
        with open(self._input_filename) as f:
            return f.read()

    @property
    def output_filename(self) -> str:
        return self._output_filename

    @property
    def output(self) -> str:
        if not os.path.exists(self._output_filename):
            raise RuntimeError(
                f"Expected test case {self.name} to "
                f"have an output file at {self._output_filename}. "
                f"Do you need to regenerate it?"
            )
        with open(self._output_filename) as f:
            return f.read()

    @property
    def error_filename(self) -> Optional[str]:
        return self._error_filename

    @property
    def error(self) -> Optional[str]:
        if self.error_filename is None:
            return None
        try:
            with open(self.error_filename) as f:
                return f.read()
        except FileNotFoundError:
            return None

    @property
    def xfail(self) -> bool:
        return "xfail" in self.input_filename


class CaseResult:
    def __init__(self, output: str, error: Optional[str]) -> None:
        self._output = output
        self._error = error

    @property
    def output(self) -> str:
        return self._output

    @property
    def error(self) -> Optional[str]:
        return self._error


def find_tests(
    dir_name: str,
    input_extension: str,
    output_extension: str = ".out",
    error_extension: str = ".err",
) -> Iterator["pytest.mark.structures.ParameterSet[CaseInfo]"]:
    current_dir = os.path.dirname(__file__)
    tests_dir = os.path.join(current_dir, dir_name)

    # Take the relative path so that the display name for the tests doesn't
    # include the path to your home directory. This makes the test names
    # consistent across systems, and also makes them much shorter and easier to
    # read.
    tests_dir = os.path.relpath(tests_dir)

    tests = set(
        os.path.splitext(filename)[0]
        for filename in os.listdir(tests_dir)
        if filename.endswith(input_extension)
    )
    for test_name in tests:
        input_filename = os.path.join(tests_dir, test_name + input_extension)
        output_filename = os.path.join(tests_dir, test_name + output_extension)
        error_filename = os.path.join(tests_dir, test_name + error_extension)

        case_info = CaseInfo(
            input_filename=input_filename,
            output_filename=output_filename,
            error_filename=error_filename,
        )
        if case_info.xfail:
            yield pytest.param(
                case_info, id=case_info.name, marks=pytest.mark.xfail(strict=True)
            )
        else:
            yield pytest.param(case_info, id=case_info.name)


def generate(
    tests: Iterator["pytest.mark.structures.ParameterSet[CaseInfo]"],
    make_result: Callable[[str, str, Any], CaseResult],
    capsys: Any,
) -> None:
    def log(message: str) -> None:
        if capsys is not None:
            with capsys.disabled():
                print(message)
        else:
            print(message)

    for paramset in tests:
        test_info = paramset.values[0]
        with open(test_info.input_filename) as input_file:
            input = input_file.read()
        log(f"processing {test_info.input_filename}")
        result = make_result(test_info.input_filename, input, capsys)
        output = result.output
        error = result.error
        if not os.path.exists(test_info.output_filename):
            with open(test_info.output_filename, "w") as output_file:
                output_file.write(output)
            if error is not None:
                assert test_info.error_filename is not None, (
                    f"Test case result for test {test_info.name} generated "
                    "error output, but no error filename is defined for this "
                    "test case"
                )
                with open(test_info.error_filename, "w") as error_file:
                    error_file.write(error)
        else:
            log(f"file exists, not generating: {test_info.output_filename}")


def get_syntax_tree(file_info: FileInfo) -> Tuple[SyntaxTree, List[Error]]:
    lexation = lex(file_info=file_info)
    parsation = parse(file_info=file_info, tokens=lexation.tokens)
    syntax_tree = SyntaxTree(parent=None, origin=parsation.green_cst, offset=0)
    errors = lexation.errors + parsation.errors
    return (syntax_tree, errors)
