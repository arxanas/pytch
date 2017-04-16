import pytest


def pytest_addoption(parser):
    # Add a marker denoting that this test generates the the expected output
    # files from the actual output.
    parser.addoption("-G", "--generate", action="store_true")


def pytest_runtest_setup(item):
    should_generate = item.config.getoption("--generate")
    generate_marker = item.get_marker("generate") is not None
    if generate_marker and not should_generate:
        pytest.skip("skipping generator test because -G wasn't passed")
    elif not generate_marker and should_generate:
        pytest.skip("skipping non-generator test because -G was passed")
