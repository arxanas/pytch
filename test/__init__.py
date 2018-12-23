"""Tests for the compiler.

Most tests are defined as `.pytch`/`.out`/`.err` files in the various
subdirectories (such as `lexer`). These tests are picked up by the test
runner automatically by virtue of being present there. They do not need to be
registered anywhere.

To re-generate the expected output and error files, delete the respective
`.out` and `.err` files, then run:

    poetry run py.test -G

They will be populated by running the compiler on the input files and writing
its output to those files. This can be useful in some cases, such as when the
compiler messages change and the output files need to be re-generated en
masse.

However, development of new test cases in this fashion is not very
Test-Driven, and so it is not encouraged. Instead, copy and paste an existing
test's output, if necessary.
"""
