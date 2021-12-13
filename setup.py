from setuptools import setup
from setuptools import find_packages

with open("README.md", "r") as fh:
    long_desc = fh.read()

setup(
    name="valclient", # Replace with your own username
    version="2.23",
    author="colinh",
    description="Wrapper for VALORANT's client API",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    url="https://github.com/colinhartigan/valclient.py",
    project_urls={
        "Bug Tracker": "https://github.com/colinhartigan/valclient.py/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.0",
)