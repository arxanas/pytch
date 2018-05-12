import os.path
from typing import Callable, Iterator, Optional, Sequence

from pytch import FileInfo
from pytch.lexer import lex
from pytch.parser import parse
from pytch.redcst import SyntaxTree


# Note that we can't call this `TestCaseInfo` because then it would be
# collected as a test.
class CaseInfo:
    def __init__(
        self,
        input_filename: str,
        output_filename: str,
        error_filename: Optional[str],
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
    error_extension: str = ".err"
) -> Iterator[CaseInfo]:
    current_dir = os.path.dirname(__file__)
    tests_dir = os.path.join(current_dir, dir_name)

    # Take the relative path so that the display name for the tests doesn't
    # include the path to your home directory. This makes the test names
    # consistent across systems, and also makes them much shorter and easier to
    # read.
    tests_dir = os.path.relpath(tests_dir)

    tests = set(os.path.splitext(filename)[0]
                for filename in os.listdir(tests_dir)
                if filename.endswith(input_extension))
    for test_name in tests:
        input_filename = os.path.join(tests_dir, test_name + input_extension)
        output_filename = os.path.join(tests_dir, test_name + output_extension)
        error_filename = os.path.join(
            tests_dir,
            test_name + error_extension,
        )

        yield CaseInfo(
            input_filename=input_filename,
            output_filename=output_filename,
            error_filename=error_filename,
        )


def generate(
    tests: Sequence[CaseInfo],
    make_result: Callable[[str, str], CaseResult],
) -> None:
    for test_info in tests:
        with open(test_info.input_filename) as input_file:
            input = input_file.read()
        print(f"processing {test_info.input_filename}")
        result = make_result(test_info.input_filename, input)
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
            print(f"file exists, not generating: {test_info.output_filename}")


def get_red_cst(file_info: FileInfo) -> SyntaxTree:
    lexation = lex(file_info=file_info)
    parsation = parse(file_info=file_info, tokens=lexation.tokens)
    return SyntaxTree(
        parent=None,
        origin=parsation.green_cst,
        offset=0,
    )
