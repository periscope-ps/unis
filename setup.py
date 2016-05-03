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

version = "2.0.dev"

setup(
    name="periscope",
    version=version,
    packages=["periscope", "periscope.test", "periscope.filters", "periscope.handlers"],
    package_data = {
        'periscope': ['ssl/*', 'schemas/*', 'abac/*']
    },
    author="Ahmed El-Hassany",
    author_email="ahassany@indiana.edu",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    url="https://github.com/periscope-ps/unis",
    description="Periscope is the implementation of both Unified Network Information Service (UNIS) and Measurement Store (MS).",
    data_files = [("/usr/share/periscope", ["config/unis.conf",
                                            "config/ms.conf",
                                            "config/RPM/wait_sv_sock",
                                            "config/RPM/periscoped",
                                            "config/RPM/periscoped.service",
                                            "config/RPM/periscoped.supervisor.conf"])],
    dependency_links=[
        "https://pypi.python.org/pypi/jsonpath/"
        ],
    install_requires=[
        "tornado==4.2",
        "tornado-redis",
        "pymongo==2.8.0",
        "motor",
        "unittest2",
        "netlogger>=4.3.0",
        "jsonschema",
        "jsonpath",
        "docopt",
        "jsonpointer>=0.2",
        "argparse",
        "httplib2",
        "M2Crypto",
    ],
    entry_points = {
        'console_scripts': [
            'periscoped = periscope.app:main',
        ]
    },
    options = {
        'bdist_rpm': {'post_install': 'config/RPM/centos_postinstall.sh',
                      'post_uninstall': 'config/RPM/centos_postuninstall.sh'}
    },
)
