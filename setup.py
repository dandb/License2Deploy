#!/usr/bin/python

import os
import sys
from CustomInstall import CustomInstall
from setuptools import setup, Command

install_requires = [
    "boto",
    "PyYaml"
  ]

tests_require = [
    "mock",
    "boto",
    "moto",
    "PyYaml"
  ]

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "License2Deploy",
    version = "0.0.1",
    author = "Dun and Bradstreet",
    author_email = "license2deploy@dandb.com",
    description = ("Rolling deploys by changing desired amount of instances AWS EC2 Autoscale Group"),
    license = "GPLv3",
    keywords = "AWS EC2 AutoScale Group AMI desired capacity",
    url = "https://github.com/dandb/License2Deploy",
    packages=['License2Deploy'],
    include_package_data=True,
    install_requires = install_requires,
    tests_require = tests_require,
    extras_require={'test': tests_require},
    long_description=read('README.md') + '\n\n' + read('CHANGES'),
    test_suite = 'tests'
)
