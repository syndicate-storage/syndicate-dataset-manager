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
import psutil
import os
import time
import inspect
import subprocess
import tempfile
import shlex
import shutil
import backends as sdm_backends
import util as sdm_util

from os.path import expanduser

DEFAULT_MOUNT_PATH = "~/sdm_mounts/"
DEFAULT_SYNDICATE_DEBUG_MODE = True
DEFAULT_SYNDICATE_DEBUG_LEVEL = 3

SYNDICATEFS_PROCESS_NAME = "syndicatefs"
SYNDICATE_CONFIG_ROOT_PATH = "~/.sdm/mounts/"


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


class FuseBackend(object):
    """
    FuseBackend
    """
    def __init__(self, backend_config):
        self.backend_config = backend_config

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

    def _wait_mount(self, mount_path, timeout=30, retry=0):
        tick = 0
        trial = 0
        while True:
            # check processes
            matching_processes = self._get_processes(SYNDICATEFS_PROCESS_NAME)
            if len(matching_processes) == 0:
                trial += 1
                if trial > retry:
                    raise sdm_backends.BackendException(
                        "cannot find matching process - %s" %
                        SYNDICATEFS_PROCESS_NAME
                    )
            else:
                # check mount
                matching_mounts = self._get_fuse_mounts(
                    SYNDICATEFS_PROCESS_NAME,
                    mount_path
                )
                if len(matching_mounts) != 0:
                    # success
                    return

            time.sleep(1)
            tick += 1

            if tick >= timeout:
                raise sdm_backends.BackendException(
                    "mount timed out - %s / %s" %
                    (SYNDICATEFS_PROCESS_NAME, mount_path)
                )

    def _make_syndicate_configuration_path(self, mount_id):
        confing_path = "%s/syndicate.conf" % (
            self._make_syndicate_configuration_root_path(mount_id)
        )
        return confing_path

    def _make_syndicate_configuration_root_path(self, mount_id):
        config_root_path = "%s/%s" % (
            SYNDICATE_CONFIG_ROOT_PATH.rstrip("/"),
            mount_id.strip().lower()
        )
        abs_config_root_path = os.path.abspath(expanduser(config_root_path.strip()))
        return abs_config_root_path

    def _make_syndicate_command(self, mount_id, debug_mode=False):
        conf_path = self._make_syndicate_configuration_path(mount_id)
        debug_flag = ""
        if debug_mode:
            debug_flag = "-d"
        return "syndicate %s -c %s" % (debug_flag, conf_path)

    def _make_syndicatefs_command(self, mount_id, debug_mode=False, debug_level=1):
        conf_path = self._make_syndicate_configuration_path(mount_id)
        debug_flag = ""
        if debug_mode:
            debug_flag = "-d%d" % debug_level
        return "syndicatefs %s -c %s" % (debug_flag, conf_path)

    def _run_command_foreground(self, command):
        try:
            sdm_util.log_message("Running an external process - %s" % command, sdm_util.LogLevel.DEBUG)
            proc = subprocess.Popen(
                shlex.split(command),
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE
            )

            stdout_value = proc.communicate()[0]
            message = repr(stdout_value)
            rc = proc.poll()
            if rc != 0:
                raise sdm_backends.BackendException(
                    "Failed to run an external process - %d : %s" % (rc, message)
                )
        except subprocess.CalledProcessError as err:
            raise sdm_backends.BackendException(
                "> error code: %d, %s" % (err.returncode, err.output)
            )

    def _run_command_background(self, command, log_path):
        try:
            sdm_util.log_message("Running an external process in background - %s" % command, sdm_util.LogLevel.DEBUG)
            fd = open(log_path, "w")
            fileno = fd.fileno()
            proc = subprocess.Popen(
                command,
                stderr=subprocess.STDOUT,
                stdout=fileno,
                shell=True
            )

        except subprocess.CalledProcessError as err:
            raise sdm_backends.BackendException(
                "> error code: %d, %s" % (err.returncode, err.output)
            )

    def _regist_syndicate_user(self, mount_id, dataset, username, user_pkey, gateway_name, ms_host, debug_mode=False, force=False):
        config_root_path = self._make_syndicate_configuration_root_path(mount_id)
        if not os.path.exists(config_root_path):
            os.makedirs(config_root_path, 0755)

        config_path = self._make_syndicate_configuration_path(mount_id)
        skip_config = False
        if os.path.exists(config_path):
            # skip
            skip_config = True

        if force:
            skip_config = False
            if os.path.exists(config_path):
                shutil.rmtree(config_root_path)

        syndicate_command = self._make_syndicate_command(mount_id, debug_mode)

        if not skip_config:
            sdm_util.log_message("Registering a syndicate user, %s" % username)
            user_pkey_fd, user_pkey_path = tempfile.mkstemp()
            f = os.fdopen(user_pkey_fd, "w")
            f.write(user_pkey)
            f.close()

            command_register = "%s --trust_public_key setup %s %s %s" % (
                syndicate_command,
                username.strip(),
                user_pkey_path,
                ms_host.strip()
            )

            try:
                self._run_command_foreground(command_register)
                sdm_util.log_message("Successfully registered a syndicate user, %s" % username)
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

        self._run_command_foreground(command_reload_user_cert)
        sdm_util.log_message("Successfully reloaded a user cert, %s" % username)
        self._run_command_foreground(command_reload_volume_cert)
        sdm_util.log_message("Successfully reloaded a volume cert, %s" % dataset)
        self._run_command_foreground(command_reload_gatway_cert)
        sdm_util.log_message("Successfully reloaded a gateway cert, %s" % gateway_name)

    def _mount_syndicatefs(self, mount_id, dataset, gateway_name, mount_path, debug_mode=False, debug_level=1):
        sdm_util.log_message("Mounting syndicatefs, %s to %s" % (dataset, mount_path))

        abs_mount_path = os.path.abspath(expanduser(mount_path.strip()))
        if not os.path.exists(abs_mount_path):
            os.makedirs(abs_mount_path, 0755)

        config_root_path = self._make_syndicate_configuration_root_path(mount_id)
        syndicatefs_log_path = "%s/mount.log" % config_root_path
        syndicatefs_command = self._make_syndicatefs_command(mount_id, debug_mode, debug_level)

        #${SYNDICATEFS_CMD} -f -u ANONYMOUS -v ${VOLUME_NAME} -g ${UG_NAME} ${SYNDICATEFS_DATASET_MOUNT_DIR} &> /tmp/syndicate_${VOLUME_NAME}.log&
        command_mount = "%s -f -u ANONYMOUS -v %s -g %s %s" % (
            syndicatefs_command,
            dataset.strip().lower(),
            gateway_name.strip().lower(),
            abs_mount_path.strip()
        )

        self._run_command_background(command_mount, syndicatefs_log_path)
        self._wait_mount(abs_mount_path, retry=3)
        sdm_util.print_message("Successfully mounted syndicatefs, %s to %s" % (dataset, abs_mount_path), True)

    def mount(self, mount_id, ms_host, dataset, username, user_pkey, gateway_name, mount_path, force=False):
        self._regist_syndicate_user(mount_id, dataset, username, user_pkey, gateway_name, ms_host, self.backend_config.syndicate_debug_mode, force)
        self._mount_syndicatefs(mount_id, dataset, gateway_name, mount_path, self.backend_config.syndicate_debug_mode, self.backend_config.syndicate_debug_level)

    def check_mount(self, mount_path):
        abs_mount_path = os.path.abspath(expanduser(mount_path.strip()))
        try:
            self._wait_mount(abs_mount_path)
            return True
        except sdm_backends.BackendException, e:
            return False

    def unmount(self, mount_id, mount_path, cleanup=False):
        try:
            command_unmount = "fusermount -u %s" % mount_path
            self._run_command_foreground(command_unmount)
        except sdm_backends.BackendException, e:
            if "not found" in str(e):
                # it's already unmounted - skip
                pass
            else:
                raise e

        if cleanup:
            # clean up
            config_root_path = self._make_syndicate_configuration_root_path(mount_id)
            shutil.rmtree(config_root_path)
        sdm_util.print_message("Successfully unmounted syndicatefs, %s" % (mount_path), True)
