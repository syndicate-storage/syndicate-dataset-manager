#!/usr/bin/env python
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

import psutil
import os
import time
import inspect

SYNDICATEFS_PROCESS_NAME = "syndicatefs"


class SyndicatefsMountException(Exception):
    pass


class SyndicatefsMount(object):
    """
    Manage Syndicatefs Mount
    """
    def __init__(self, mount_table):
        self.mount_table = mount_table

    def _get_processes(self, name):
        matching_processes = []
        for p in psutil.process_iter():
            try:
                if inspect.ismethod(p.name):
                    if p.name() == name:
                        matching_processes.append(p)
                else:
                    if p.name == name:
                        matching_processes.append(p)
            except psutil.NoSuchProcess:
                pass
        return matching_processes

    def _get_fuse_mounts(self, name, path):
        matching_mounts = []
        with open('/proc/mounts', 'r') as f:
            for line in f:
                l = line.strip()
                w = l.split()
                if w[2].startswith("fuse."):
                    if w[0] == name and w[1] == path:
                        matching_mounts.append(w)
        return matching_mounts

    def _wait_mount(self, mount_path, timeout=30):
        abs_mount_path = os.path.abspath(mount_path)

        tick = 0
        while True:
            # check processes
            matching_processes = self._get_processes(SYNDICATEFS_PROCESS_NAME)
            if len(matching_processes) == 0:
                raise SyndicatefsMountException(
                    "cannot find matching process - %s" % SYNDICATEFS_PROCESS_NAME
                )

            # check mount
            matching_mounts = self._get_fuse_mounts(
                SYNDICATEFS_PROCESS_NAME,
                abs_mount_path
            )
            if len(matching_mounts) != 0:
                # success
                return

            time.sleep(1)
            tick += 1

            if tick >= timeout:
                raise SyndicatefsMountException(
                    "mount timed out - %s / %s" % (SYNDICATEFS_PROCESS_NAME, mount_path)
                )
