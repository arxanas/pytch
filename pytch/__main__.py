import sys

from pytch import compile_files


def main():
    files = sys.argv[1:]
    compile_files(files)


if __name__ == "__main__":
    main()
