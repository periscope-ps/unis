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

# =============================================================================
#  periscope-ps (unis)
#
#  Copyright (c) 2012-2016, Trustees of Indiana University,
#  All rights reserved.
#
#  This software may be modified and distributed under the terms of the BSD
#  license.  See the COPYING file for details.
#
#  This software was created at the Indiana University Center for Research in
#  Extreme Scale Technologies (CREST).
# =============================================================================

from setuptools import setup
import distutils, os
from unittest import TestLoader, TextTestRunner

version = "2.3.1"

class TestingCommand(distutils.cmd.Command):
    """A testing hook for setuptools"""

    description="Run unittests on program source"
    user_options = [
        ('testpath=', None, 'path to unittest file directory'),
        ('nointegration=', None, 'disable integration testing'),
        ('nounit=', None, 'disable unit testing'),
        ('verbose=', None, 'display verbose output')
    ]

    def _get_runner(self):
        return TextTestRunner()

    def initialize_options(self):
        self.testpath = os.path.join(os.getcwd(), 'test')
        self.nointegration, self.nounit = False, False
    def finalize_options(self):
        self.testpath = os.path.abspath(self.testpath)
        assert os.path.exists(self.testpath), f"Path '{self.testpath}' does not exist"

    def run(self):
        unit_load, integration_load = TestLoader(), TestLoader()
        integration_load.testMethodPrefix = "integration_"
        unit, itg = unit_load.discover(self.testpath), integration_load.discover(self.testpath)

        runner = self._get_runner()
        if not self.nounit:
            self.announce(f"Running unit tests from '{self.testpath}'", level=distutils.log.INFO)
            runner.run(unit)
        if not self.nointegration:
            self.announce(f"Running integration tests from '{self.testpath}'", level=distutils.log.INFO)
            runner.run(itg)

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
#    data_files = [("/usr/share/periscope", ["config/unis.conf",
#                                            "config/ms.conf",
#                                            "config/RPM/wait_sv_sock",
#                                            "config/RPM/periscoped",
#                                            "config/RPM/periscoped.service",
#                                            "config/RPM/periscoped.supervisor.conf"])],
    dependency_links=[
        "https://pypi.python.org/pypi/jsonpath/"
        ],
    install_requires=[
        "six>=1.11.0",
        "tornado",
        "pymongo",
        "motor==2.3",
        "unittest2",
        "jsonschema==2.6.0",
        "jsonpath",
        "docopt",
        "jsonpointer>=0.2",
        "httplib2",
        "requests",
        "urllib3",
        "configparser"
    ],
    entry_points = {
        'console_scripts': [
            'periscoped = periscope.app:main',
        ]
    },
    cmdclass={
        'test': TestingCommand
    },
    options = {
        'bdist_rpm': {'post_install': 'config/RPM/centos_postinstall.sh',
                      'post_uninstall': 'config/RPM/centos_postuninstall.sh'}
    },
)
