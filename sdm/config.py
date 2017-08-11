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

CONFIG_PATH = "~/.sdm/sdm.conf"

DEFAULT_REPO_URL = "https://butler.opencloud.cs.arizona.edu/sdm/"
DEFAULT_MOUNT_PATH = "~/sdm_mounts/"

class Config(object):
    """
    Manage SDM config
    """
    def __init__(self, path=CONFIG_PATH):
        self.repo_url = DEFAULT_REPO_URL
        self.default_mount_path = DEFAULT_MOUNT_PATH
        self.load_config(path)

    def _save_conf(self):
        return {
            "REPO_URL": self.repo_url,
            "DEFAULT_MOUNT_PATH": self.default_mount_path
        }

    def _load_conf(self, conf):
        for k in conf.keys():
            k = k.strip().lower()
            if k == "repo_url":
                self.repo_url = conf[k].strip()
            elif k == "default_mount_path":
                self.default_mount_path = conf[k].strip()

    def load_config(self, path=CONFIG_PATH):
        abs_path = os.path.abspath(path.strip())
        conf = {}
        with open(abs_path, 'r') as f:
            conf = json.load(f)

        self._load_conf(conf)

    def save_config(self, path=CONFIG_PATH):
        abs_path = os.path.abspath(path.strip())
        parent = os.path.dirname(abs_path)
        if not os.path.exists(parent):
            os.makedirs(parent, 0755)

        with open(abs_path, 'w') as f:
            conf = self._save_conf()
            json.dump(conf, f)

    def get_repo_url(self):
        return self.repo_url

    def get_default_mount_path(self):
        return self.default_mount_path
