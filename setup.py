#!/usr/bin/env python3

from setuptools import setup
from todotxt import SOURCE_URL, __version__

with open('LICENSE', 'rt') as f:
    license = f.read()


setup(
    name='todo.txt-pylib',
    version=__version__,
    author='Frank Sachsenheim',
    author_email="funkyfuture@riseup.net",
    license=license,
    url=SOURCE_URL,
    description="A pythonic interface to Gina Trapani's todo.txt-format for Python 3.",
    long_description=open('README.rst', 'rt').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: ISC License (ISCL)'
    ],
    packages=['todotxt'],
)
