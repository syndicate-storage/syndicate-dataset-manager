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
import urllib


class RepositoryException(Exception):
    pass


class RepositoryEntry(object):
    """
    repository entry
    """
    def __init__(self, ms_host, dataset, username, user_pkey, gateway_name, description):
        self.ms_host = ms_host.strip()
        self.dataset = dataset.strip().lower()
        self.username = username.strip().lower()
        self.user_pkey = user_pkey
        self.gateway_name = gateway_name.strip().lower()
        self.description = description

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
            response = urllib.urlopen(url)
            ent_arr = json.loads(response.read())
            for ent in ent_arr:
                entry = RepositoryEntry(
                    ent["ms_host"],
                    ent["ms_host"],
                    ent["dataset"],
                    ent["username"],
                    ent["user_pkey"],
                    ent["gateway_name"],
                    ent["description"]
                )
                self.table[entry.dataset].append(entry)
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
