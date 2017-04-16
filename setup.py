from setuptools import find_packages, setup


setup(
    name="pytch",
    version="0.1",
    author="Waleed Khan",
    author_email="me@waleedkhan.name",
    description="ML-like language that compiles down to Python.",
    url="https://github.com/arxanas/pytch",

    packages=find_packages(),
    entry_points="""
    [console_scripts]
    pytch=pytch.__main__:main
    """,
    install_requires=[
        "click==6.7",
        "pyparsing==2.1.10",
    ],
)
