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

version = "2.3.1"

setup(
    name="periscope",
    version=version,
    packages=["periscope", "periscope.handlers"], # "periscope.test", "periscope.filters",
    package_data = {
        'periscope': ['ssl/*', 'schemas/*', 'abac/*']
    },
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
        #"six>=1.11.0",
        "pymongo>=3",
        "falcon>=2",
        "falcon-jsonify==1.2",
        "gunicorn>=20",
        "pyzmq>=19",
        "APScheduler>=3.6",
        "unittest2",
        "jsonschema==2.6.0",
        "jsonpath",
        "docopt",
        "jsonpointer>=0.2",
        "httplib2",
        "requests"
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
