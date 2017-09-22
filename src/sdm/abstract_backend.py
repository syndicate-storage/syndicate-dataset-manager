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

from abc import ABCMeta, abstractmethod


class AbstractBackendException(Exception):
    pass


class AbstractBackendConfig(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def from_dict(cls, d):
        pass

    @abstractmethod
    def get_default_config(cls):
        pass

    @abstractmethod
    def to_json(self):
        pass


class AbstractBackend(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_name(cls):
        pass

    @abstractmethod
    def make_default_mount_path(self, dataset, default_mount_path):
        pass

    @abstractmethod
    def is_legal_mount_path(self, mount_path):
        pass

    @abstractmethod
    def mount(self, mount_id, ms_host, dataset, username, user_pkey, gateway_name, mount_path):
        pass

    @abstractmethod
    def check_mount(self, mount_id, dataset, mount_path):
        pass

    @abstractmethod
    def unmount(self, mount_id, dataset, mount_path, cleanup=False):
        pass
