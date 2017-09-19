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
import syndicate_user as sdm_syndicate_user
import backends as sdm_backends

DEFAULT_REPO_URL = "https://butler.opencloud.cs.arizona.edu/sdm/catalogue"
DEFAULT_BACKEND = sdm_backends.Backends.get_backend_name("FUSE")


class Config(object):
    """
    Manage SDM config
    """
    def __init__(self, path):
        self.repo_url = DEFAULT_REPO_URL
        self.default_backend = DEFAULT_BACKEND
        self.backend_configs = sdm_backends.Backends.get_default_backend_configs()
        self.syndicate_users = sdm_syndicate_user.get_default_users()

        try:
            self.load_config(path)
        except IOError:
            self.save_config(path)

    def _save(self):
        bconfigs = {}
        for bk in self.backend_configs.keys():
            bc = self.backend_configs[bk]
            bconfigs[bk] = bc.__dict__

        susers = []
        for suser in self.syndicate_users:
            susers.append(suser.__dict__)

        return {
            "repo_url": self.repo_url,
            "default_backend": self.default_backend,
            "backend_configs": bconfigs,
            "syndicate_users": susers
        }

    def _load(self, conf):
        for k in conf.keys():
            if k == "repo_url":
                self.repo_url = conf[k].strip()
            elif k == "default_backend":
                self.default_backend = sdm_backends.Backends.get_backend_name(conf[k])
            elif k == "backend_configs":
                for bk in conf[k].keys():
                    bc = conf[k][bk]
                    backend = sdm_backends.Backends.get_backend_name(bk)
                    backend_config = sdm_backends.Backends.objectfy_backend_config_from_dict(backend, bc)
                    self.add_backend_config(backend, backend_config)
            elif k == "syndicate_users":
                for syndicate_user in conf[k]:
                    user = sdm_syndicate_user.SyndicateUser.from_dict(syndicate_user)
                    self.add_syndicate_user(user)

    def load_config(self, path):
        conf = {}
        with open(path, 'r') as f:
            conf = json.load(f)

        self._load(conf)

    def save_config(self, path):
        parent = os.path.dirname(path)
        if not os.path.exists(parent):
            os.makedirs(parent, 0755)

        with open(path, 'w') as f:
            conf = self._save()
            json.dump(conf, f, sort_keys=True, indent=4, separators=(',', ': '))

    def list_syndicate_users(self):
        users = []
        for user in self.syndicate_users:
            users.append(user)
        return users

    def list_syndicate_users_by_ms_host(self, ms_host):
        users = []
        for user in self.syndicate_users:
            if user.ms_host == ms_host.strip():
                users.append(user)
        return users

    def add_syndicate_user(self, user):
        # check duplication
        exist_user = None
        for euser in self.syndicate_users:
            if euser.username == user.username and euser.ms_host == user.ms_host:
                # exist! - overwrite
                exist_user = euser
                break

        if exist_user:
            self.syndicate_users.remove(exist_user)

        self.syndicate_users.append(user)

    def get_backend_config(self, backend):
        if backend in self.backend_configs:
            return self.backend_configs[backend]
        return None

    def add_backend_config(self, backend, backend_config):
        self.backend_configs[backend] = backend_config
