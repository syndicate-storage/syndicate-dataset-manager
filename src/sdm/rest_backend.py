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

import json

DEFAULT_MOUNT_PATH = "/sdm_mounts/"
DEFAULT_SYNDICATE_DEBUG_MODE = True
DEFAULT_SYNDICATE_DEBUG_LEVEL = 3


class RestBackendConfig(object):
    """
    REST Backend Config
    """
    def __init__(self,
                 default_mount_path=DEFAULT_MOUNT_PATH):
        self.default_mount_path = default_mount_path

    @classmethod
    def from_dict(cls, d):
        return RestBackendConfig(
            d["default_mount_path"]
        )

    @classmethod
    def get_default_config(cls):
        return RestBackendConfig(
            DEFAULT_MOUNT_PATH
        )

    def to_json(self):
        return json.dumps({
            "default_mount_path": self.default_mount_path
        })

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "<RestBackendConfig %s %s>" % \
            (self.default_mount_path)


class RestBackend(object):
    def __init__(self, backend_config):
        self.backend_config = backend_config
