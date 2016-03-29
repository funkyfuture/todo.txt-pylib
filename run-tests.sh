#!/bin/bash

set -e

LWD=$(pwd)

cd $(dirname $0)
flake8 todotxt
flake8 --doctests --ignore=F821 todotxt
flake8 --ignore=F999 tests
py.test
sphinx-build -b doctest docs/source docs/build docs/source/examples.rst

cd $LWD
