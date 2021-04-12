from setuptools import setup
from setuptools import find_packages

with open("README.md", "r") as fh:
    long_desc = fh.read()

setup(
    name='valclient',
    version='0.1.0',
    description='API wrapper for VALORANT\'s client APIs',
    #long_description=long_desc,
    long_description_content_type="text/markdown",
    url='https://github.com/colinhartigan/valclient.py',
    license='MIT',
    packages=[find_packages()],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'requests',
        'os',
        'base64',
        'urllib3',
        'json'
    ]
)
