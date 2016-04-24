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
Test logstash_notifier
"""

from .utilities import BaseSupervisorTestCase, record, get_config


class SupervisorLoggingTestCase(BaseSupervisorTestCase):
    """
    Test logging.
    """
    def test_logging(self):
        """
        Test logging.
        """
        logstash = self.run_logstash()
        try:
            environment = {
                'LOGSTASH_SERVER': logstash.server_address[0],
                'LOGSTASH_PORT': str(logstash.server_address[1]),
                'LOGSTASH_PROTO': 'udp',
                'COVERAGE_PROCESS_START': '.coveragerc'
            }

            config = get_config()
            self.run_supervisor(environment, config)
            self.messages(clear_buffer=True, wait_for=2)

            try:
                self.run_supervisorctl(['stop', 'messages'])
                expected = [
                    record('PROCESS_STATE_STOPPED', 'STOPPING'),
                ]
                received = self.messages(clear_buffer=True, wait_for=1)
                self.assertEqual(received, expected)

                self.run_supervisorctl(['start', 'messages'])
                expected = [
                    record('PROCESS_STATE_STARTING', 'STOPPED'),
                    record('PROCESS_STATE_RUNNING', 'STARTING'),
                ]

                received = self.messages(clear_buffer=True, wait_for=2)
                self.assertEqual(received, expected)

                self.run_supervisorctl(['restart', 'messages'])
                expected = [
                    record('PROCESS_STATE_STOPPED', 'STOPPING'),
                    record('PROCESS_STATE_STARTING', 'STOPPED'),
                    record('PROCESS_STATE_RUNNING', 'STARTING'),
                ]
                received = self.messages(clear_buffer=True, wait_for=3)
                self.assertEqual(received, expected)
            finally:
                self.shutdown_supervisor()
        finally:
            self.shutdown_logstash()


class SupervisorEnvironmentLoggingTestCase(BaseSupervisorTestCase):
    """
    Test case for logging extra environment variables
    """

    def _test_environment_logging(self, include=None):
        """
        test logging of env variables
        """
        logstash = self.run_logstash()
        try:
            environment = {
                'LOGSTASH_SERVER': logstash.server_address[0],
                'LOGSTASH_PORT': str(logstash.server_address[1]),
                'LOGSTASH_PROTO': 'udp',
                'COVERAGE_PROCESS_START': '.coveragerc'
            }
            if include is not None:
                environment.update(include)

            config = get_config(arguments='--include FRUITS VEGETABLES')
            self.run_supervisor(environment, config)
            self.messages(clear_buffer=True, wait_for=2)

            try:
                self.run_supervisorctl(['stop', 'messages'])
                received = self.messages(clear_buffer=True, wait_for=1)
                # should only have the 'stopping' message
                self.assertTrue(len(received) == 1)
                message = received[0]

                yield message
            finally:
                self.shutdown_supervisor()
        finally:
            self.shutdown_logstash()

    def test_not_present(self):
        """
        If the logger is configured to add two environment variables, FRUITS
        and VEGETABLES, but neither is set, we shouldn't get anything extra
        """
        for message in self._test_environment_logging({}):
            # should have no additional added values since we asked for an
            # empty dict to be added
            self.assertTrue('user_data' not in message)

    def test_only_one_value_set(self):
        """
        If only one of them is set, we should only see that one in the logged
        message
        """
        env = {
            'FRUITS': 'pineapple,raspberry,kiwi'
        }
        for message in self._test_environment_logging(env):
            self.assertTrue('user_data' in message)
            self.assertDictEqual(env, message['user_data'])

    def test_both_values_set(self):
        """
        If both of them is set, we should get both returned in the logged
        message
        """
        env = {
            'FRUITS': 'pineapple,raspberry,kiwi',
            'VEGETABLES': 'sweet potato,leek,mushroom'
        }
        for message in self._test_environment_logging(env):
            self.assertTrue('user_data' in message)
            self.assertDictEqual(env, message['user_data'])


class SupervisorKeyvalsLoggingTestCase(BaseSupervisorTestCase):
    """
    Test case for logging user data keyvals
    """

    def _test_environment_logging(self):
        """
        test logging of user data keyvals
        """
        logstash = self.run_logstash()
        try:
            environment = {
                'LOGSTASH_SERVER': logstash.server_address[0],
                'LOGSTASH_PORT': str(logstash.server_address[1]),
                'LOGSTASH_PROTO': 'udp',
                'COVERAGE_PROCESS_START': '.coveragerc'
            }

            config = get_config(
                arguments='--include '
                          'bears="polar,brown,black" '
                          'notbears="unicorn,griffin,sphinx,otter"'
            )
            self.run_supervisor(environment, config)
            self.messages(clear_buffer=True, wait_for=2)

            try:
                self.run_supervisorctl(['stop', 'messages'])
                received = self.messages(clear_buffer=True, wait_for=1)
                # should only have the 'stopping' message
                self.assertTrue(len(received) == 1)
                message = received[0]

                yield message
            finally:
                self.shutdown_supervisor()
        finally:
            self.shutdown_logstash()

    def test_get_user_data(self):
        """
        Get the user data passed to logstash_notifier
        """
        for message in self._test_environment_logging():
            self.assertTrue('user_data' in message)
            user_data = {
                'bears': "polar,brown,black",
                'notbears': "unicorn,griffin,sphinx,otter"
            }
            self.assertDictEqual(
                user_data,
                message['user_data']
            )


class SupervisorOutPutLoggingTestCase(BaseSupervisorTestCase):
    """
    Test capturing stdout/stderr logs.
    """

    def test_output_logging(self):
        """
        Test stdout is captured in logs when capture-output argument is set.
        """
        logstash = self.run_logstash()
        try:
            environment = {
                'LOGSTASH_SERVER': logstash.server_address[0],
                'LOGSTASH_PORT': str(logstash.server_address[1]),
                'LOGSTASH_PROTO': 'udp',
                'COVERAGE_PROCESS_START': '.coveragerc'
            }
            config = get_config(
                arguments='--capture-output',
                events='PROCESS_LOG'
            )
            self.run_supervisor(environment, config)

            try:
                expected = [{
                    '@version': '1',
                    'channel': 'stdout',
                    'eventname': 'PROCESS_LOG_STDOUT',
                    'groupname': 'messages',
                    'level': 'INFO',
                    'logger_name': 'supervisor',
                    'message': 'Test 0\n',
                    'path': './logstash_notifier/__init__.py',
                    'processname': 'messages',
                    'tags': [],
                    'type': 'logstash',
                }]

                received = self.messages(clear_buffer=True, wait_for=1)
                self.assertEqual(received, expected)

            finally:
                self.shutdown_supervisor()
        finally:
            self.shutdown_logstash()


class SupervisorAppendNewLineTestCase(BaseSupervisorTestCase):
    """
    Test appending newlines to log messages.
    """

    def test_newline_logging(self):
        """
        Test a newline is appended when relevant config option is set.
        """
        logstash = self.run_logstash()
        try:
            environment = {
                'LOGSTASH_SERVER': logstash.server_address[0],
                'LOGSTASH_PORT': str(logstash.server_address[1]),
                'LOGSTASH_PROTO': 'udp',
                'COVERAGE_PROCESS_START': '.coveragerc'
            }
            config = get_config(
                arguments='--append-newline',
            )

            self.run_supervisor(environment, config)
            self.messages(clear_buffer=True, wait_for=2)

            try:
                self.run_supervisorctl(['stop', 'messages'])

                # Base test case - note added newline
                expected = [
                    record('PROCESS_STATE_STOPPED', 'STOPPING'),
                ]
                # Keep the buffer, needed in next test.
                received = self.messages(clear_buffer=False, wait_for=1)
                self.assertEqual(received, expected)

                # Raw message test case
                for message in self.get_message_buffer():
                    self.assertTrue(message.endswith("\n"))

            finally:
                self.shutdown_supervisor()
        finally:
            self.shutdown_logstash()
