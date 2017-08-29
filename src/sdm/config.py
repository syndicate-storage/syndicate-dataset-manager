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

import os
import os.path
import json

from os.path import expanduser

CONFIG_PATH = "~/.sdm/sdm.conf"

DEFAULT_REPO_URL = "https://butler.opencloud.cs.arizona.edu/sdm/catalogue"
DEFAULT_MOUNT_PATH = "~/sdm_mounts/"
DEFAULT_SYNDICATE_DEBUG_MODE = True
DEFAULT_SYNDICATE_DEBUG_LEVEL = 3


class Config(object):
    """
    Manage SDM config
    """
    def __init__(self, path=CONFIG_PATH):
        self.repo_url = DEFAULT_REPO_URL
        self.default_mount_path = DEFAULT_MOUNT_PATH
        self.syndicate_debug_mode = DEFAULT_SYNDICATE_DEBUG_MODE
        self.syndicate_debug_level = DEFAULT_SYNDICATE_DEBUG_LEVEL
        try:
            self.load_config(path)
        except IOError:
            self.save_config(path)

    def _save(self):
        return {
            "REPO_URL": self.repo_url,
            "DEFAULT_MOUNT_PATH": self.default_mount_path,
            "SYNDICATE_DEBUG_MODE": self.syndicate_debug_mode,
            "SYNDICATE_DEBUG_LEVEL": self.syndicate_debug_level,
            "SYNDICATE_DEBUG_MODE": self.syndicate_debug_mode
        }

    def _load(self, conf):
        for k in conf.keys():
            kl = k.strip().lower()
            if kl == "repo_url":
                self.repo_url = conf[k].strip()
            elif kl == "default_mount_path":
                self.default_mount_path = conf[k].strip()
            elif kl == "syndicate_debug_mode":
                self.syndicate_debug_mode = bool(conf[k])
            elif kl == "syndicate_debug_level":
                self.syndicate_debug_level = int(conf[k])
            elif kl == "syndicate_debug_mode":
                self.syndicate_debug_mode = bool(conf[k])

    def load_config(self, path=CONFIG_PATH):
        abs_path = os.path.abspath(expanduser(path).strip())
        conf = {}
        with open(abs_path, 'r') as f:
            conf = json.load(f)

        self._load(conf)

    def save_config(self, path=CONFIG_PATH):
        abs_path = os.path.abspath(expanduser(path).strip())
        parent = os.path.dirname(abs_path)
        if not os.path.exists(parent):
            os.makedirs(parent, 0755)

        with open(abs_path, 'w') as f:
            conf = self._save()
            json.dump(conf, f)

    def get_repo_url(self):
        return self.repo_url

    def set_repo_rul(self, repo_url):
        self.repo_url = repo_url

    def get_default_mount_path(self):
        return self.default_mount_path

    def set_default_mount_path(self, default_mount_path):
        self.default_mount_path = default_mount_path

    def get_syndicate_debug_mode(self):
        return self.syndicate_debug_mode

    def set_syndicate_debug_mode(self, syndicate_debug_mode):
        self.syndicate_debug_mode = syndicate_debug_mode

    def get_syndicate_debug_level(self):
        return self.syndicate_debug_level

    def set_syndicate_debug_level(self, syndicate_debug_level):
        self.syndicate_debug_level = syndicate_debug_level
