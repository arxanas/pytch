from setuptools import find_packages, setup

from pytch import __version__

setup(
    name="pytch",
    version=__version__,
    author="Waleed Khan",
    author_email="me@waleedkhan.name",
    description="ML-like language that compiles down to Python.",
    url="https://github.com/arxanas/pytch",
    packages=find_packages(),
    entry_points="""
    [console_scripts]
    pytch=pytch.__main__:cli
    """,
    install_requires=["attrs==18.1.0", "click==6.7", "distance==0.1.3"],
)
