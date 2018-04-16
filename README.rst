|Build Status| |Coveralls Status|

This is a port of the
`Supervisor-logging <https://github.com/infoxchange/supervisor-logging>`__
project. Along with capturing loglines, as Supervisor-logging does, it's
also intended to capture the
`PROCESS_STATE <http://supervisord.org/events.html#event-listeners-and-event-notifications>`__
events that Supervisor emits.

supervisor-logstash-notifier
============================

A `supervisor <http://supervisord.org/>`__ plugin to stream events & logs to a
Logstash instance.

Installation
------------

Python 2.7 or Python 3.4+ is required.

::

    pip install supervisor-logstash-notifier

Note that Supervisor itself does not yet work on Python 3, though it can
be installed in a separate environment (because
supervisor-logstash-notifier is a separate process).

Usage
-----

The Logstash instance to send the events to is configured with the
environment variables:

-  ``LOGSTASH_SERVER``
-  ``LOGSTASH_PORT``
-  ``LOGSTASH_PROTO``

Add the plugin as an event listener:

::

    # Capture state changes
    [eventlistener:logging]
    command = logstash_notifier
    events = PROCESS_STATE

    # Capture stdout/stderr
    [eventlistener:logging]
    command = logstash_notifier --capture-output
    events = PROCESS_LOG

    # Capture state changes and stdout/stderr
    [eventlistener:logging]
    command = logstash_notifier --capture-output
    events = PROCESS_STATE,PROCESS_LOG

If you don't wish to define the environment variables for the entire
shell, you can pass them in via Supervisor's configuration:

::

    [eventlistener:logging]
    environment=LOGSTASH_SERVER="127.0.0.1",LOGSTASH_PORT="12201",LOGSTASH_PROTO="tcp"
    command=logstash_notifier
    events=PROCESS_STATE
    
Enable the log events in your program:

::

    [program:yourprogram]
    stdout_events_enabled = true
    stderr_events_enabled = true

Advanced Usage
--------------

It is also possible to include environment variables in the event messages,
by specifying the name of the environment variables to include:

::

    [eventlistener:logging]
    command=export IPV4=`ec2metadata --local-ipv4`; logstash_notifier --include IPV4
    events=PROCESS_STATE

Or alternatively, by specifying arbitrary keyvals of data to log:

::

    [eventlistener:logging]
    command=logstash_notifier --include bears="polar,brown,black" notbears="unicorn,griffin,sphinx,otter"
    events=PROCESS_STATE

These two forms of arbitrary user data inclusion can be combined, and used together
if necessary.

Running with Logstash
---------------------

Logstash can be simply configured to receive events:

::

    input {
        tcp {
            port => 12201
            codec => json
        }
    }

    output {
        stdout {
            codec => rubydebug
        }
    }

The JSON produced by the events and log output will look like this:

::

    # State changes
    {
      "@timestamp": "2016-03-28T23:58:03.469Z",
      "@version": "1",
      "eventname": "PROCESS_STATE_STOPPED",
      "from_state": "STOPPING",
      "groupname": "myprocess",
      "host": "ip-10-93-130-24",
      "level": "INFO",
      "logger_name": "supervisor",
      "message": "PROCESS_STATE_STOPPED collectd",
      "path": "/path/to/supervisor-logstash-notifier/logstash_notifier/__init__.py",
      "pid": "1234",
      "processname": "myprocess",
      "tags": [],
      "type": "logstash"
    }

    # Log output
    {
      "@timestamp": "2016-03-28T23:58:03.741Z",
      "@version": "1",
      "channel": "stdout"
      "eventname": "PROCESS_LOG_STDOUT",
      "groupname": "myprocess",
      "host": "localhost",
      "level": "INFO",
      "logger_name": "supervisor",
      "message": "myprocess output #1\n",
      "path": "/path/to/supervisor-logstash-notifier/logstash_notifier/__init__.py",
      "pid": "1234",
      "processname": "myprocess",
      "tags": [],
      "type": "logstash",
    }

.. |Build Status| image:: https://travis-ci.org/dohop/supervisor-logstash-notifier.svg?branch=master
   :target: https://travis-ci.org/dohop/supervisor-logstash-notifier
.. |Coveralls Status| image:: https://coveralls.io/repos/github/dohop/supervisor-logstash-notifier/badge.svg?branch=master
   :target: https://coveralls.io/github/dohop/supervisor-logstash-notifier?branch=master
