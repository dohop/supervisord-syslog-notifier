#!/usr/bin/env python
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
A module for dispatching Supervisor PROCESS_STATE events to a Syslog instance
"""

import argparse
import os
import signal
import sys
import warnings

from .logger import get_logger


def get_keyvals(line):
    """
    Parse Supervisor message headers.
    """
    return dict([x.split(':') for x in line.split()])


def parse_payload(payload):
    """
    Parse a Supervisor event.
    """
    if '\n' in payload:
        headerinfo, data = payload.split('\n', 1)
    else:
        headerinfo = payload
        data = ''
    headers = get_keyvals(headerinfo)
    return headers, data


def send_ready(stdout):
    """
    Sends the READY signal to supervisor
    """
    stdout.write('READY\n')
    stdout.flush()


def send_ok(stdout):
    """
    Sends an ack to supervisor
    """
    stdout.write('RESULT 2\nOK')
    stdout.flush()


def process_io(stdin, stdout):
    """
    Handle communication with Supervisor to receive events and their payloads
    """
    send_ready(stdout)

    line = stdin.readline()
    # line = 'ver:3.0 server:supervisor serial:0 pool:logstash-notifier
    #         poolserial:0 eventname:PROCESS_STATE_STARTING len:84\n'
    keyvals = get_keyvals(line)
    # keyvals = {'ver': '3.0', 'poolserial': '0', 'len': '84', 'server': 'supervisor',
    #            'eventname': 'PROCESS_STATE_STARTING', 'serial': '0', 'pool': 'logstash-notifier'}
    payload = stdin.read(int(keyvals['len']))
    # payload = 'processname:logstash-notifier groupname:logstash-notifier from_state:STOPPED tries:0'

    body, data = parse_payload(payload)

    return keyvals, body, data


def supervisor_event_loop(stdin, stdout, *events):
    """
    Runs forever to receive supervisor events
    """
    while True:
        keyvals, body, data = process_io(stdin, stdout)

        # if we're not listening to the event that we've received, ignore it
        if keyvals['eventname'] not in events:
            send_ok(stdout)
            continue

        # if it's an event we caused, ignore it
        if body['processname'] == 'logstash-notifier':
            send_ok(stdout)
            continue

        yield keyvals, body, data

        send_ok(stdout)


def get_value_from_input(text):
    """
    Parses the input from the command line to work out if we've been given the name of an environment
    variable to include or a keyval of arbitrary data to include instead
    """
    values = {}
    if '=' in text:
        key, val = text.split('=', 1)
        values[key] = val
    else:
        if text in os.environ:
            values[text] = os.getenv(text)
    return values


def __newline_formatter(func):
    """
    Wrap a formatter function so a newline is appended if needed to the output
    """
    def __wrapped_func(*args, **kwargs):
        """
        Wrapper function that appends a newline to result of original fucntion
        """
        result = func(*args, **kwargs)

        # The result may be a string, or bytes. In python 2 they are the
        # same, but in python 3, they are not. First, check for strings
        # as that works the same in python 2 and 3, THEN check for bytes,
        # as that implementation is python 3 specific. If it's neither
        # (future proofing), we use a regular new line
        line_ending = "\n"
        if isinstance(result, str):
            line_ending = "\n"
        elif isinstance(result, bytes):
            # We are redefining the variable type on purpose since python
            # broke backwards compatibility between 2 & 3. Pylint will
            # throw an error on this, so we have to disable the check.
            line_ending = b"\n"

        # Avoid double line endings
        if not result.endswith(line_ending):
            result = result + line_ending

        return result

    # Return the wrapper
    return __wrapped_func


def application(include=None, capture_output=False, append_newline=False):
    """
    Main application loop.
    """
    log_instance = get_logger(append_newline=append_newline)

    events = ['BACKOFF', 'FATAL', 'EXITED', 'STOPPED', 'STARTING', 'RUNNING']
    events = ['PROCESS_STATE_' + state for state in events]

    if capture_output:
        events += ['PROCESS_LOG_STDOUT', 'PROCESS_LOG_STDERR']

    for keyvals, body, data in supervisor_event_loop(sys.stdin, sys.stdout, *events):
        extra = body.copy()
        extra['eventname'] = keyvals['eventname']

        if include is not None:
            user_data = {}
            for variable in include:
                user_data.update(get_value_from_input(variable))

            if user_data:
                extra['user_data'] = user_data

        # Events, like starting/stopping don't have a message body and the data is set to '' in data().
        # Stdout/Stderr events do have a message body, so use that if it's present, or fallback to
        # eventname/processname if it's not.
        if not len(data) > 0:
            data = '%s %s' % (keyvals['eventname'], body['processname'])

        log_instance.info(data, extra=extra)


def run_with_coverage():  # pragma: no cover
    """
    Invoked when `-c|--coverage` is used on the command line
    """
    try:
        import coverage
    except ImportError:
        warnings.warn('Coverage data will not be generated because coverage is not installed. '
                      'Please run `pip install coverage` and try again.')
        return

    coverage.process_startup()
    # need to register a shutdown handler for SIGTERM since it won't run the
    # atexit functions required by coverage
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))


def main():  # pragma: no cover
    """
    Main entry point
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i', '--include',
        nargs='*', default=list(),
        help='include named environment variables and/or arbitrary metadata keyvals in messages'
    )
    parser.add_argument(
        '-c', '--coverage',
        action='store_true', default=False,
        help='enables coverage when running tests'
    )
    parser.add_argument(
        '-o', '--capture-output',
        action='store_true', default=False,
        help='capture stdout/stderr output from supervisor processes in addition to events'
    )
    parser.add_argument(
        '-n', '--append-newline',
        action='store_true', default=False,
        help='ensure all messages sent end with a newline character'
    )
    args = parser.parse_args()
    if args.coverage:
        run_with_coverage()

    application(
        include=args.include,
        capture_output=args.capture_output,
        append_newline=args.append_newline,
    )


if __name__ == '__main__':  # pragma: no cover
    main()
