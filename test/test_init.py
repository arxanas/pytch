from pytch import FileInfo, Position


def slower_get_position_for_offset(source_code: str, offset: int) -> Position:
    line = 0
    character = 0
    current_offset = 0
    while current_offset < offset:
        if source_code[current_offset] == "\n":
            line += 1
            character = 0
        else:
            character += 1
        current_offset += 1
    return Position(line=line, character=character)


def test_fileinfo_get_position_for_offset():
    source_code = """foo
barbaz
qux"""
    file_info = FileInfo(file_path="dummy", source_code=source_code)

    for i, _c in enumerate(source_code):
        expected_position = slower_get_position_for_offset(
            source_code=source_code, offset=i
        )
        actual_position = file_info.get_position_for_offset(i)
        assert actual_position.line == expected_position.line
        assert actual_position.character == expected_position.character


def test_fileinfo_get_position_for_offset_exclusive_end():
    source_code = """foo
barbaz
qux"""
    file_info = FileInfo(file_path="dummy", source_code=source_code)

    expected_position = slower_get_position_for_offset(
        source_code=source_code, offset=len(source_code)
    )
    actual_position = file_info.get_position_for_offset(len(source_code))
    assert actual_position.line == expected_position.line
    assert actual_position.character == expected_position.character


def test_fileinfo_get_position_for_offset_exclusive_end_newline():
    source_code = """foo
barbaz
qux
"""
    file_info = FileInfo(file_path="dummy", source_code=source_code)

    expected_position = slower_get_position_for_offset(
        source_code=source_code, offset=len(source_code)
    )
    actual_position = file_info.get_position_for_offset(len(source_code))
    assert actual_position.line == expected_position.line
    assert actual_position.character == expected_position.character
