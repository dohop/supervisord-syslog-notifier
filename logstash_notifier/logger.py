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

import os
import logging
import logstash


def newline_formatter(func):
    """
    Wrap a formatter function so a newline is appended if needed to the output
    """
    def __wrapped_func(*args, **kwargs):
        """
        Wrapper function that appends a newline to result of original function
        """
        result = func(*args, **kwargs)

        # The result may be a string, or bytes. In python 2 they are the same, but in python 3, they are not.
        # First, check for strings as that works the same in python 2 and 3, THEN check for bytes, as that
        # implementation is python 3 specific. If it's neither (future proofing), we use a regular new line
        line_ending = "\n"
        if isinstance(result, str):
            line_ending = "\n"
        elif isinstance(result, bytes):
            # We are redefining the variable type on purpose since python broke backwards compatibility between 2 & 3.
            line_ending = b"\n"

        # Avoid double line endings
        if not result.endswith(line_ending):
            result += line_ending

        return result

    # Return the wrapper
    return __wrapped_func


def get_host_port_socket():
    """
    Returns values from the environment
    """
    try:
        host = os.environ['LOGSTASH_SERVER']
        port = int(os.environ['LOGSTASH_PORT'])
        socket_type = os.environ['LOGSTASH_PROTO']
    except KeyError:
        raise RuntimeError("LOGSTASH_SERVER, LOGSTASH_PORT and LOGSTASH_PROTO are required.")

    return host, port, socket_type


def get_log_handler(socket_type):
    """
    Returns the log handler class based upon the socket type
    """
    logstash_handler = None
    if socket_type == 'udp':
        logstash_handler = logstash.UDPLogstashHandler
    elif socket_type == 'tcp':
        logstash_handler = logstash.TCPLogstashHandler
    else:
        raise RuntimeError('Unknown protocol defined: %r' % socket_type)

    return logstash_handler


def get_logger(append_newline=False):
    """
    Sets up the logger used to send the supervisor events and messages to the logstash server,
    via the socket type provided, port and host defined in the environment
    """
    host, port, socket_type = get_host_port_socket()
    logstash_handler = get_log_handler(socket_type)
    handler = logstash_handler(host, port, version=1)

    # To be able to append newlines to the logger output, we'll need to wrap the formatter.
    # As we can't predict the formatter class, it's easier to wrap the format() function,
    # which is part of the logger spec than it is to override/wrap the formatter class,
    # whose name is determined by the logstash class.
    if append_newline:
        handler.formatter.format = newline_formatter(handler.formatter.format)

    logger = logging.getLogger('supervisor')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
