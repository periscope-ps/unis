#!/usr/bin/env python
# 
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from setuptools import setup

version = "0.3.dev"

setup(
    name="periscope",
    version=version,
    packages=["periscope", "periscope.test", "periscope.filters", "periscope.handlers"],
    package_dir= {'periscope.abac': 'periscope/abac', 'periscope.ssl': 'periscope/ssl'},
    package_data={'periscope.abac': ['*'], 'periscope.ssl' : ['*']},
    author="Ahmed El-Hassany",
    author_email="ahassany@indiana.edu",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    url="https://github.com/periscope-ps/periscope",
    description="Periscope is the implementation of both Unified Network Information Service (UNIS) and Measurement Store (MS).",
    install_requires=[
        "tornado",
        "tornado-redis",
        "pymongo==2.8.0",
        "motor",
        "unittest2",
        "python-daemon>=1.5",
        "netlogger>=4.3.0",
        "jsonschema",
        "mock==0.8.0",
        "docopt",
        "jsonpointer>=0.2",
        "argparse",
        "httplib2",
        "jsonpath",
        "M2Crypto"
    ],
    entry_points = {
        'console_scripts': [
            'periscoped = periscope.app:main',
        ]
    },
)
