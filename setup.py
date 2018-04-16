#
# Copyright 2016 Dohop hf.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Setup script for building supervisor-logstash-notifier
"""

from setuptools import setup, find_packages

# 2 step 'with open' to be python2.6 compatible
with open('requirements.txt') as requirements:
    with open('test_requirements.txt') as test_requirements:

        setup(
            name='supervisor-logstash-notifier',
            version='0.2.5',
            packages=find_packages(exclude=['tests']),
            url='https://github.com/dohop/supervisor-logstash-notifier',
            license='Apache 2.0',
            author='aodj',
            author_email='alexander@dohop.com',
            description='Stream supervisor events to a logstash instance',
            long_description=open('README.rst').read(),
            entry_points={
                'console_scripts': [
                    'logstash_notifier = logstash_notifier:main'
                ]
            },
            install_requires=requirements.read().splitlines(),
            test_suite='tests',
            tests_require=test_requirements.read().splitlines(),
        )
