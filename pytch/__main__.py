from . import FileInfo, OffsetRange
from .errors import Error, get_error_lines, Note, Severity


def main():
    source_code = """let foo = 1
let bar = 2
let foo = 3
"""
    file_info = FileInfo(file_path="foo.pytch", source_code=source_code)
    error = Error(
        file_info=file_info,
        severity=Severity.ERROR,
        title="Naming",
        code=1234,
        message="The name 'foo' is already bound.",
        offset_range=OffsetRange(start=28, end=31),
        notes=[Note(
            file_info=file_info,
            message="In Pytch, you cannot rebind names at the top-level.",
        ), Note(
            file_info=file_info,
            message="Here is the original binding of the name 'foo'.",
            offset_range=OffsetRange(start=4, end=7),
        )],
    )
    lines = "\n".join(get_error_lines(error))
    print(lines)


if __name__ == "__main__":
    main()
