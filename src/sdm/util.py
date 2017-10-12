#! /usr/bin/env python
"""
   Copyright 2016 The Trustees of University of Arizona

   Licensed under the Apache License, Version 2.0 (the "License" );
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import logging
import os

from os.path import expanduser

class LogLevel(object):
    DEBUG = 9
    INFO = 7
    WARNING = 5
    ERROR = 3

    @classmethod
    def from_str(cls, name):
        if name.strip().lower() == "debug":
            return cls.DEBUG
        elif name.strip().lower() == "info":
            return cls.INFO
        elif name.strip().lower() == "warning":
            return cls.WARNING
        elif name.strip().lower() == "error":
            return cls.ERROR
        else:
            return None


def log_message(message, level=LogLevel.INFO):
    if level == LogLevel.DEBUG:
        logging.debug(message)
    elif level == LogLevel.INFO:
        logging.info(message)
    elif level == LogLevel.WARNING:
        logging.warning(message)
    elif level == LogLevel.ERROR:
        logging.error(message)


def print_message(message, dolog=False, level=LogLevel.INFO):
    if dolog:
        log_message(message, level)

    print message

def get_abs_path(path):
    if "://" in path:
        return path
    return os.path.abspath(expanduser(path).strip())

def to_bool(s):
    if s.lower() in ["yes", "true", "t", "1"]:
        return True
    return False
