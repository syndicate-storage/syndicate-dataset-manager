#!/usr/bin/env python

"""
   Copyright 2016 The Trustees of University of Arizona

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from setuptools import setup

packages = [
    'sdm'
]

# dependencies
dependencies = [
    'prettytable'
]

setup(
    name='sdm',
    version='0.1',
    description='Syndicate Dataset Manager',
    url='https://github.com/syndicate-storage/syndicate-dataset-manager',
    author='Illyoung Choi',
    author_email='syndicate@lists.cs.princeton.edu',
    license='Apache 2.0',
    packages=packages,
    package_dir={
        'sdm': 'src/sdm'
    },
    install_requires=dependencies,
    zip_safe=False
)
