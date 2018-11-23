from setuptools import find_packages, setup

version = "0.1"

setup(
    name="pytch",
    version=version,
    author="Waleed Khan",
    author_email="me@waleedkhan.name",
    description="ML-like language that compiles down to Python.",
    url="https://github.com/arxanas/pytch",
    packages=find_packages(),
    entry_points="""
    [console_scripts]
    pytch=pytch.__main__:cli
    """,
    install_requires=[
        "attrs==18.1.0",
        "click==6.7",
        "distance==0.1.3",
        "pyrsistent==0.14.2",
    ],
)
