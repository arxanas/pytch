import os.path

from pytch import PYTCH_EXTENSION


def find_tests(dir_name):
    current_dir = os.path.dirname(__file__)
    tests_dir = os.path.join(current_dir, dir_name)
    tests = set(os.path.splitext(filename)[0]
                for filename in os.listdir(tests_dir)
                if filename.endswith(PYTCH_EXTENSION))
    for test in tests:
        input_filename = os.path.join(tests_dir, f"{test}{PYTCH_EXTENSION}")
        output_filename = os.path.join(tests_dir, f"{test}.out")
        yield (input_filename, output_filename)


def generate(tests, make_output):
    for input_filename, output_filename in tests:
        with open(input_filename) as input_file:
            input = input_file.read()
        print(f"processing {input_filename}")
        output = make_output(input)
        if not os.path.exists(output_filename):
            with open(output_filename, "w") as output_file:
                output_file.write(output)
        else:
            print(f"file exists, not generating: {output_filename}")
