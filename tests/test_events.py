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
Tests for various event handler functions
"""

from six.moves.cStringIO import StringIO

from logstash_notifier import get_keyvals, parse_payload, process_io, supervisor_event_loop
from .compat import TestCase


class TestHeaderExtraction(TestCase):
    def test_get_headers_empty_line(self):
        line = ''
        self.assertEqual(get_keyvals(line), {})

    def test_get_headers_multiple_variables(self):
        line = 'a:1 b:2 c:3\n'
        self.assertEqual(get_keyvals(line), {'a': '1', 'b': '2', 'c': '3'})


class TestEventData(TestCase):
    def test_eventdata_parsing_empty_payload(self):
        # the payload is an empty string, so the response will be an empty
        # series of headers and data
        payload = ''
        self.assertEqual(parse_payload(payload), ({}, ''))

    def test_eventdata_parsing_headers(self):
        # the payload is an empty string, so the response will be an empty
        # series of headers and data
        payload = 'a:1 b:2 c:3'
        headers, data = parse_payload(payload)
        self.assertDictEqual(headers, {'a': '1', 'b': '2', 'c': '3'})
        self.assertEqual(data, '')

    def test_eventdata_parsing_headers_trailing_newline(self):
        # the payload is an empty string, so the response will be an empty
        # series of headers and data
        payload = 'a:1 b:2 c:3\n'
        headers, data = parse_payload(payload)
        self.assertDictEqual(headers, {'a': '1', 'b': '2', 'c': '3'})
        self.assertEqual(data, '')

    def test_eventdata_parsing_headers_and_data(self):
        # the payload is an empty string, so the response will be an empty
        # series of headers and data
        payload = 'a:1 b:2 c:3\nabcdefghijklmnopqrstuvwxyz'
        headers, data = parse_payload(payload)
        self.assertDictEqual(headers, {'a': '1', 'b': '2', 'c': '3'})
        self.assertEqual(data, 'abcdefghijklmnopqrstuvwxyz')


class TestSupervisorEventProcess(TestCase):
    def test_process_io_regular_usage(self):
        # write the necessary setup to the pipe
        stdin = StringIO('a:1 b:2 c:3 len:14\nalphabet:abcde')
        keyvals, body, data = process_io(stdin, StringIO())
        self.assertDictEqual(keyvals, {'a': '1', 'b': '2', 'c': '3', 'len': '14'})
        self.assertEqual(body, {'alphabet': 'abcde'})

    def test_process_io_missing_length(self):
        # if the 'len' field is not in the message, the handler fails, because
        # it needs that to determine how much datato read from the input
        stdin = StringIO('a:1 b:2 c:3\nabcdefghijklmnopqrstuvwxyz')
        self.assertRaises(KeyError, process_io, stdin, StringIO())


class TestEventLoop(TestCase):
    def make_line(self, event, process, **kwargs):
        payload = 'processname:{}'.format(process)
        for keyword, value in kwargs.iteritems():
            payload += ' {}:{}'.format(keyword, value)

        line = 'eventname:{event} len:{length}\n{payload}'.format(
            event=event,
            length=len(payload),
            payload=payload,
        )
        return line

    def payload_length(self, line):
        return str(len(line.split('\n', 1)[-1]))

    def test_basic_event_loop(self):
        # the events being sent need a few basics:
        # - the `eventname`, which we may, or may not be listening for
        # - the `len`, indicating how much we should read from stdin for the payload
        # the payload also needs a `processname` key, which is used to filter out events
        # from ourselves; we don't care about events we're causing, and so filter out
        # anything with a processname that is `logstash-notifier`
        line = self.make_line('RANDOM_EVENT', 'foo', key='val')
        stdin = StringIO(line)
        stdout = StringIO()
        keyvals, body, data = supervisor_event_loop(stdin, stdout, 'RANDOM_EVENT').next()
        self.assertDictEqual(keyvals, {'eventname': 'RANDOM_EVENT', 'len': self.payload_length(line)})
        self.assertDictEqual(body, {'key': 'val', 'processname': 'foo'})
        self.assertEqual(data, '')

    def test_multiple_events(self):
        line = self.make_line('RANDOM_EVENT', 'foo', key='val')
        stdin = StringIO(line * 2)
        stdout = StringIO()
        generator = supervisor_event_loop(stdin, stdout, 'RANDOM_EVENT')
        for i in xrange(2):
            # iterate through the loop twice, extracting the messages
            keyvals, body, data = generator.next()
            self.assertDictEqual(keyvals, {'eventname': 'RANDOM_EVENT', 'len': self.payload_length(line)})
            self.assertDictEqual(body, {'key': 'val', 'processname': 'foo'})
            self.assertEqual(data, '')

    def test_filtering_of_self(self):
        # make sure that we ignore events that we cause. we do this by creating two events, the first with the
        # ignored `logstash-notifier` processname, and the second with something else. when we run the test
        # we shouldn't receive the `logstash-notifier` event (since it's ignored) and instead receive the second
        # event.
        event_one = self.make_line('RANDOM_EVENT', 'logstash-notifier')
        event_two = self.make_line('RANDOM_EVENT', 'notepad')
        stdin = StringIO(event_one + event_two)
        stdout = StringIO()
        keyvals, body, data = supervisor_event_loop(stdin, stdout, 'RANDOM_EVENT').next()
        self.assertDictEqual(keyvals, {'eventname': 'RANDOM_EVENT', 'len': self.payload_length(event_two)})
        self.assertDictEqual(body, {'processname': 'notepad'})
        self.assertEqual(data, '')

    def test_filtering_of_irrelevent_events(self):
        # ensure that events we're not interested in are ignored
        event_one = self.make_line('UNKNOWN', 'winword')
        event_two = self.make_line('WHOCARES', 'notepad')
        event_three = self.make_line('WHATEVER', 'calc')
        stdin = StringIO(event_one + event_two + event_three)
        stdout = StringIO()
        generator = supervisor_event_loop(stdin, stdout, 'WHOCARES', 'WHATEVER')
        keyvals, body, _ = generator.next()
        self.assertDictEqual(keyvals, {'eventname': 'WHOCARES', 'len': self.payload_length(event_two)})
        self.assertDictEqual(body, {'processname': 'notepad'})
        keyvals, body, _ = generator.next()
        self.assertDictEqual(keyvals, {'eventname': 'WHATEVER', 'len': self.payload_length(event_three)})
        self.assertDictEqual(body, {'processname': 'calc'})
