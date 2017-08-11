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
import subprocess
import tempfile
import shlex
import shutil

SYNDICATEFS_PROCESS_NAME = "syndicatefs"
SYNDICATE_CONFIG_ROOT_PATH = "~/.sdm/mounts/"


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
                    "cannot find matching process - %s" %
                    SYNDICATEFS_PROCESS_NAME
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
                    "mount timed out - %s / %s" %
                    (SYNDICATEFS_PROCESS_NAME, mount_path)
                )

    def _make_syndicate_configuration_path(self, mount_id):
        confing_path = "%s/syndicate.conf" % (
            self._make_syndicate_configuration_root_path(mount_id)
        )
        return confing_path

    def _make_syndicate_configuration_root_path(self, mount_id):
        confing_root_path = "%s/%s" % (
            SYNDICATE_CONFIG_ROOT_PATH.rstrip("/"),
            mount_id.strip().lower()
        )
        abs_config_root_path = os.path.abspath(confing_root_path.strip())
        return abs_config_root_path

    def _make_syndicate_command(self, mount_id):
        conf_path = self._make_syndicate_configuration_path(mount_id)
        return "syndicate -d -c %s" % conf_path

    def _make_syndicatefs_command(self, mount_id):
        conf_path = self._make_syndicate_configuration_path(mount_id)
        return "syndicatefs -d3 -c %s" % conf_path

    def _run_command_with_output(self, command):
        try:
            proc = subprocess.Popen(
                shlex.split(command),
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE
            )

            stdout_value = proc.communicate()[0]
            print "Running an external process - %s:" % command
            print "> message: %s" % repr(stdout_value)
            rc = proc.poll()
            print "> exitcode: %d" % rc

            if rc != 0:
                raise SyndicatefsMountException(
                    "Failed to run an external process - %d" % rc
                )
        except subprocess.CalledProcessError as err:
            raise SyndicatefsMountException(
                "> error code: %d, %s" % (err.returncode, err.output)
            )

    def _run_command(self, command):
        try:
            proc = subprocess.Popen(
                command,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
                shell=True
            )

            stdout_value = proc.communicate()[0]
            print "Running an external process - %s:" % command
            print "> message: %s" % repr(stdout_value)
            rc = proc.poll()
            print "> exitcode: %d" % rc

            if rc != 0:
                raise SyndicatefsMountException(
                    "Failed to run an external process - %d" % rc
                )
        except subprocess.CalledProcessError as err:
            raise SyndicatefsMountException(
                "> error code: %d, %s" % (err.returncode, err.output)
            )

    def _regist_syndicate_user(self, mount_id, dataset, username, user_pkey, gateway_name, ms_host):
        print "Registering a syndicate user, %s" % username

        confing_root_path = self._make_syndicate_configuration_root_path(mount_id)
        if not os.path.exists(confing_root_path):
            os.makedirs(confing_root_path, 0755)

        syndicate_command = self._make_syndicate_command(mount_id)

        user_pkey_fd, user_pkey_path = tempfile.mkstemp()
        with os.fdopen(user_pkey_fd, "w") as f:
            f.write(user_pkey)
        os.close(user_pkey_fd)

        command_register = "%s --trust_public_key setup %s %s %s" % (
            syndicate_command,
            username.strip(),
            user_pkey_path,
            ms_host.strip()
        )

        try:
            self._run_command_with_output(command_register)
            print "Successfully registered a syndicate user, %s" % username
        finally:
            os.remove(user_pkey_path)

        command_reload_user_cert = "%s reload_user_cert %s" % (
            syndicate_command,
            username.strip()
        )
        command_reload_volume_cert = "%s reload_volume_cert %s" % (
            syndicate_command,
            dataset.strip().lower()
        )
        command_reload_gatway_cert = "%s reload_gateway_cert %s" % (
            syndicate_command,
            gateway_name.strip().lower()
        )

        self._run_command_with_output(command_reload_user_cert)
        print "Successfully reloaded a user cert, %s" % username
        self._run_command_with_output(command_reload_volume_cert)
        print "Successfully reloaded a volume cert, %s" % dataset
        self._run_command_with_output(command_reload_gatway_cert)
        print "Successfully reloaded a gateway cert, %s" % gateway_name

    def _mount_syndicatefs(self, mount_id, dataset, gateway_name, mount_path):
        print "Mounting syndicatefs, %s to %s" % (dataset, mount_path)

        confing_root_path = self._make_syndicate_configuration_root_path(mount_id)
        syndicatefs_log_path = "%s/mount.log" % confing_root_path
        syndicatefs_command = self._make_syndicatefs_command(mount_id)

        #${SYNDICATEFS_CMD} -f -u ANONYMOUS -v ${VOLUME_NAME} -g ${UG_NAME} ${SYNDICATEFS_DATASET_MOUNT_DIR} &> /tmp/syndicate_${VOLUME_NAME}.log&
        command_mount = "%s -f -u ANONYMOUS -v %s -g %s %s &> %s" % (
            syndicatefs_command,
            dataset.strip().lower(),
            gateway_name.strip().lower(),
            mount_path.strip(),
            syndicatefs_log_path
        )

        self._run_command(command_mount)
        self._wait_mount(mount_path.strip())
        print "Successfully mounted syndicatefs, %s to %s" % (dataset, mount_path)

    def mount(self, mount_id, ms_host, dataset, username, user_pkey, gateway_name, mount_path):
        self._regist_syndicate_user(mount_id, dataset, username, user_pkey, gateway_name, ms_host)
        self._mount_syndicatefs(mount_id, dataset, gateway_name, mount_path)

    def unmount(self, mount_id, mount_path):
        command_unmount = "fusermount -u %s" % mount_path
        self._run_command_with_output(command_unmount)

        confing_root_path = self._make_syndicate_configuration_root_path(mount_id)
        shutil.rmtree(confing_root_path)
        print "Successfully unmounted syndicatefs, %s" % (mount_path)
