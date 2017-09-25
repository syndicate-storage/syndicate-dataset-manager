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
import requests

requests.packages.urllib3.disable_warnings()

class RepositoryException(Exception):
    pass


class RepositoryEntry(object):
    """
    repository entry
    """
    def __init__(self, dataset, ms_host, volume, username, user_pkey, gateway, description):
        self.dataset = dataset.strip().lower()
        self.ms_host = ms_host.strip()
        self.volume = volume.strip()
        self.username = username.strip()
        self.user_pkey = user_pkey
        self.gateway = gateway.strip()
        self.description = description

    @classmethod
    def from_json(cls, jsonstr):
        ent = json.loads(jsonstr)
        return cls.from_dict(ent)

    @classmethod
    def from_dict(cls, ent):
        username = ""
        user_pkey = ""
        if "username" in ent:
            username = ent["username"]

        if "user_pkey" in ent:
            user_pkey = ent["user_pkey"]

        return RepositoryEntry(
            ent["dataset"],
            ent["ms_host"],
            ent["volume"],
            username,
            user_pkey,
            ent["gateway"],
            ent["description"]
        )

    def to_json(self):
        return json.dumps({
            "dataset": self.dataset,
            "ms_host": self.ms_host,
            "volume": self.volume,
            "username": self.username,
            "user_pkey": self.user_pkey,
            "gateway": self.gateway,
            "description": self.description
        })

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "<RepositoryEntry %s %s>" % \
            (self.dataset, self.description)


class Repository(object):
    """
    Manage SDM Repository
    """
    def __init__(self, url):
        self.table = {}

        if not url:
            raise RepositoryException("not a valid repository url : %s" % url)

        self.load_table(url)

    def load_table(self, url):
        self.table = {}
        try:
            response = requests.get(url)
            ent_arr = response.json()
            for ent in ent_arr:
                entry = RepositoryEntry.from_dict(ent)
                self.table[entry.dataset] = entry
        except Exception, e:
            raise RepositoryException("cannot retrieve repository entries : %s" % e)

    def get_entry(self, dataset):
        k = dataset.strip().lower()
        if k in self.table:
            return self.table[k]
        return None

    def list_entries(self):
        entries = []
        for k in self.table.keys():
            entries.append(self.table[k])
        return entries
