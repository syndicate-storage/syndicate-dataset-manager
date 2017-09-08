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


class SyndicateUser(object):
    """
    syndicate user info
    """
    def __init__(self, username, user_pkey, ms_host):
        self.username = username.strip()
        self.user_pkey = user_pkey.strip()
        self.ms_host = ms_host.strip()

    @classmethod
    def from_dict(cls, d):
        return SyndicateUser(
            d["username"],
            d["user_pkey"],
            d["ms_host"]
        )

    def to_json(self):
        return json.dumps({
            "username": self.username,
            "user_pkey": self.user_pkey,
            "ms_host": self.ms_host
        })

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "<SyndicateUser %s %s>" % \
            (self.username, self.ms_host)


def get_default_users():
    users = []
    users.append(
        SyndicateUser(
            "dc_anonymous_user@opencloud.us",
            "-----BEGIN RSA PRIVATE KEY-----\n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\n-----END RSA PRIVATE KEY-----",
            "http://syndicate-ms-datasets-prod.appspot.com:80"
        )
    )
    return users
