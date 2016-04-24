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
Tests for getting the right log handler
"""

import logging
import logstash
import os
import six

from mock import patch
from logstash_notifier.logger import get_host_port_socket, get_log_handler, newline_formatter, get_logger
from .compat import TestCase


class TestLogger(TestCase):
    def setUp(self):
        self.mock_environ = patch.dict(os.environ)
        self.mock_environ.start()

        for key in ('LOGSTASH_SERVER', 'LOGSTASH_PORT', 'LOGSTASH_PROTO'):
            if key in os.environ:
                del os.environ[key]

    def tearDown(self):
        self.mock_environ.stop()

    def test_missing_environ_keys(self):
        # calling get_logger when one or more of the keys is missing, will raise RuntimeError
        self.assertRaises(RuntimeError, get_host_port_socket)

    def test_socket_type_invalid(self):
        # if the protocol isn't either tcp or udp, we get a RuntimeError raised
        with patch.dict(os.environ, LOGSTASH_SERVER='127.0.0.1', LOGSTASH_PORT='9001', LOGSTASH_PROTO='donkey'):
            host, port, socket_type = get_host_port_socket()
            self.assertRaises(RuntimeError, get_log_handler, socket_type)

    def test_socket_type_udp(self):
        with patch.dict(os.environ, LOGSTASH_SERVER='127.0.0.1', LOGSTASH_PORT='9001', LOGSTASH_PROTO='udp'):
            host, port, socket_type = get_host_port_socket()
            self.assertIs(get_log_handler(socket_type), logstash.UDPLogstashHandler)

    def test_socket_type_tcp(self):
        with patch.dict(os.environ, LOGSTASH_SERVER='127.0.0.1', LOGSTASH_PORT='9001', LOGSTASH_PROTO='tcp'):
            host, port, socket_type = get_host_port_socket()
            self.assertIs(get_log_handler(socket_type), logstash.TCPLogstashHandler)


def foo(input_string):
    return input_string


class TestNewlineFormatter(TestCase):
    def setUp(self):
        self.wrapped = newline_formatter(foo)

    def test_newline_formatter_with_strings(self):
        self.assertEqual(self.wrapped('bar'), 'bar\n')

    def test_newline_formatter_with_strings_with_trailing_linebreak(self):
        self.assertEqual(self.wrapped('bar\n'), 'bar\n')

    def test_newline_formatter_with_bytes(self):
        self.assertEqual(self.wrapped(b'bar'), b'bar\n')

    def test_newline_formatter_with_bytes_with_trailing_linebreak(self):
        self.assertEqual(self.wrapped(b'bar\n'), b'bar\n')

    def test_newline_formatter_with_unicode(self):
        self.assertEqual(self.wrapped(six.u('bar')), six.u('bar\n'))

    def test_newline_formatter_with_unicode_with_trailing_linebreak(self):
        self.assertEqual(self.wrapped(six.u('bar\n')), six.u('bar\n'))


class TestGetLogger(TestCase):
    def setUp(self):
        self.mock_environ = patch.dict(os.environ)
        self.mock_environ.start()

        for key in ('LOGSTASH_SERVER', 'LOGSTASH_PORT', 'LOGSTASH_PROTO'):
            if key in os.environ:
                del os.environ[key]

    def tearDown(self):
        self.mock_environ.stop()

    def test_get_logger_without_newlines(self):
        with patch.dict(os.environ, LOGSTASH_SERVER='127.0.0.1', LOGSTASH_PORT='9001', LOGSTASH_PROTO='tcp'):
            logger = get_logger(append_newline=False)
            self.assertIsInstance(logger, logging.Logger)
            self.assertIsInstance(logger.handlers[0], logstash.TCPLogstashHandler)
