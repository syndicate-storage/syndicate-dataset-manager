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

import os.path
import sys
import sdm.repository as sdm_repository

exec_name = ""


def gen(dataset, ms_host, volume, username, user_pkey, gateway, description):
    entry = sdm_repository.RepositoryEntry(dataset, ms_host, volume, username, user_pkey, gateway, description)
    print entry.to_json()


def read_pkey(user_pkey_path):
    with open(user_pkey_path, "r") as f:
        user_pkey = f.read()

        return user_pkey


def show_help():
    print "Usage:"
    print "> %s dataset ms_host volume username user_pkey_path gateway description" % exec_name


def main(argv):
    if len(argv) == 7:
        dataset = argv[0].strip().lower()
        ms_host = argv[1].strip()
        volume = argv[2].strip()
        username = argv[3].strip()
        user_pkey_path = argv[4]
        gateway = argv[5].strip()
        description = argv[6].strip()

        try:
            user_pkey = read_pkey(user_pkey_path)
            print "> %s" % user_pkey

            gen(dataset, ms_host, volume, username, user_pkey, gateway, description)
        except Exception, e:
            print >> sys.stderr, e
            print ""
            show_help()
    else:
        show_help()


if __name__ == "__main__":
    global exec_name
    exec_name = sys.argv[0]
    main(sys.argv[1:])
