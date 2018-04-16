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
Tests for the inclusion logic
"""

import os

from logstash_notifier import get_value_from_input
from .compat import TestCase


class TestIncludeParser(TestCase):
    """
    Tests the parsing of the include options
    """
    def test_key_val_parsing(self):
        # Test parsing of keyval strings
        self.assertEqual(
            get_value_from_input('fruits="pear,kiwi,banana"'),
            {'fruits': '"pear,kiwi,banana"'}
        )
        self.assertEqual(
            get_value_from_input('berries='),
            {'berries': ''}
        )
        self.assertEqual(
            get_value_from_input('pythagoras=a2+b2=c2'),
            {'pythagoras': 'a2+b2=c2'}
        )

    def test_environ_extraction(self):
        # Test inclusion of variables from the environ
        os.environ['vegetables'] = '"carrot,peas,green beans"'
        os.environ['smellythings'] = ''
        self.assertEqual(
            get_value_from_input('vegetables'),
            {'vegetables': '"carrot,peas,green beans"'}
        )
        self.assertEqual(
            get_value_from_input('smellythings'),
            {'smellythings': ''}
        )

    def test_combination(self):
        # Test having both environment vars and arbitrary keyvals
        os.environ['bears'] = 'polar,brown,black'
        os.environ['notbears'] = 'unicorn,griffin,sphinx,otter'
        command_line = ['bears', 'notbears', 'e=mc2', 'v=iR', 'qwertyuiop']
        expected = {
            'bears': 'polar,brown,black',
            'notbears': 'unicorn,griffin,sphinx,otter',
            'e': 'mc2',
            'v': 'iR',
        }
        result = {}
        for variable in command_line:
            result.update(get_value_from_input(variable))

        self.assertDictEqual(result, expected)
