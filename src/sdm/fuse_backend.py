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

DEFAULT_MOUNT_PATH = "~/sdm_mounts/"
DEFAULT_SYNDICATE_DEBUG_MODE = True
DEFAULT_SYNDICATE_DEBUG_LEVEL = 3


class FuseBackendConfig(object):
    """
    FUSE Backend Config
    """
    def __init__(self,
                 default_mount_path=DEFAULT_MOUNT_PATH,
                 syndicate_debug_mode=DEFAULT_SYNDICATE_DEBUG_MODE,
                 syndicate_debug_level=DEFAULT_SYNDICATE_DEBUG_LEVEL):
        self.default_mount_path = default_mount_path
        self.syndicate_debug_mode = syndicate_debug_mode
        self.syndicate_debug_level = syndicate_debug_level

    @classmethod
    def from_dict(cls, d):
        return FuseBackendConfig(
            d["default_mount_path"],
            d["syndicate_debug_mode"],
            d["syndicate_debug_level"]
        )

    @classmethod
    def get_default_config(cls):
        return FuseBackendConfig(
            DEFAULT_MOUNT_PATH,
            DEFAULT_SYNDICATE_DEBUG_MODE,
            DEFAULT_SYNDICATE_DEBUG_LEVEL
        )

    def to_json(self):
        return json.dumps({
            "default_mount_path": self.default_mount_path,
            "syndicate_debug_mode": self.syndicate_debug_mode,
            "syndicate_debug_level": self.syndicate_debug_level
        })

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "<FuseBackendConfig %s %s>" % \
            (self.default_mount_path, self.syndicate_debug_mode)
