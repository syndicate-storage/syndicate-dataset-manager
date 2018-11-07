#! /usr/bin/env python

##  @file: src/sdm/fuse_backend.py
#   Configure the FUSE backend and handle mounts
#
#   @author Illyoung Choi
#
#   @copyright Copyright 2016 The Trustees of University of Arizona\n
#   Licensed under the Apache License, Version 2.0 (the "License" );
#   you may not use this file except in compliance with the License.\n
#   You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0\n
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n
#   See the License for the specific language governing permissions and
#   limitations under the License.

import json
import psutil
import os
import time
import inspect
import subprocess
import tempfile
import shlex
import shutil
import abstract_backend as sdm_absbackends
import util as sdm_util

from os.path import expanduser

DEFAULT_MOUNT_PATH = "~/sdm_mounts"
DEFAULT_SYNDICATE_DEBUG_MODE = True
DEFAULT_SYNDICATE_DEBUG_LEVEL = 3
DEFAULT_SYNDICATE_CACHE_MAX = 2*1024*1024*1024 # 20GB

SYNDICATEFS_PROCESS_NAME = "syndicatefs"
SYNDICATE_CONFIG_ROOT_PATH = "~/.sdm/mounts/"


class FuseBackendException(sdm_absbackends.AbstractBackendException):
    pass


class FuseBackendConfig(sdm_absbackends.AbstractBackendConfig):
    """
    FUSE Backend Config
    """
    def __init__(self):
        self.default_mount_path = DEFAULT_MOUNT_PATH
        self.syndicate_debug_mode = DEFAULT_SYNDICATE_DEBUG_MODE
        self.syndicate_debug_level = DEFAULT_SYNDICATE_DEBUG_LEVEL
        self.syndicate_cache_max = DEFAULT_SYNDICATE_CACHE_MAX

    @classmethod
    def from_dict(cls, d):
        config = FuseBackendConfig()
        config.default_mount_path = d["default_mount_path"]
        config.syndicate_debug_mode = d["syndicate_debug_mode"]
        config.syndicate_debug_level = d["syndicate_debug_level"]
        config.syndicate_cache_max = d["syndicate_cache_max"]
        return config

    @classmethod
    def get_default_config(cls):
        return FuseBackendConfig()

    def to_json(self):
        return json.dumps({
            "default_mount_path": self.default_mount_path,
            "syndicate_debug_mode": self.syndicate_debug_mode,
            "syndicate_debug_level": self.syndicate_debug_level,
            "syndicate_cache_max": self.syndicate_cache_max
        })

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "<FuseBackendConfig %s %s>" % \
            (self.default_mount_path, self.syndicate_debug_mode)


class FuseBackend(sdm_absbackends.AbstractBackend):
    """
    FUSE Backend
    """
    def __init__(self, backend_config):
        self.backend_config = backend_config

    @classmethod
    def get_name(cls):
        return "FUSE"

    def is_legal_mount_path(self, mount_path):
        if os.path.exists(mount_path) and not os.path.isdir(mount_path):
            return False
        return True

    def make_default_mount_path(self, dataset, default_mount_path):
        mount_path = "%s/%s" % (
            default_mount_path,
            dataset.strip().lower()
        )

        abs_mount_path = sdm_util.get_abs_path(mount_path)
        if not abs_mount_path.startswith("/"):
            raise FuseBackendException( "cannot make default mount path for %s" % dataset)

        return abs_mount_path

    def _get_processes(self, name):
        matching_processes = []
        for p in psutil.process_iter():
            try:
                pcmdline = ""
                if inspect.ismethod(p.cmdline):
                    pcmdline = p.cmdline()
                else:
                    pcmdline = p.cmdline

                if name in pcmdline:
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
                    raise FuseBackendException(
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
                raise FuseBackendException(
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
        abs_config_root_path = sdm_util.get_abs_path(config_root_path)
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
                raise FuseBackendException(
                    "Failed to run an external process - %d : %s" % (rc, message)
                )
        except subprocess.CalledProcessError as err:
            raise FuseBackendException(
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
            raise FuseBackendException(
                "> error code: %d, %s" % (err.returncode, err.output)
            )

    def _setup_syndicate(self, mount_id, dataset, username, user_pkey, gateway_name, ms_host, debug_mode=False, cache_size_limit=DEFAULT_SYNDICATE_CACHE_MAX):
        config_root_path = self._make_syndicate_configuration_root_path(mount_id)
        if not os.path.exists(config_root_path):
            os.makedirs(config_root_path, 0755)

        config_path = self._make_syndicate_configuration_path(mount_id)
        skip_config = False
        if os.path.exists(config_path):
            # skip
            skip_config = True

        syndicate_command = self._make_syndicate_command(mount_id, debug_mode)

        if not skip_config:
            sdm_util.log_message("Setting up Syndicate for an user, %s" % username)
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
                sdm_util.log_message("Successfully set up Syndicate for an user, %s" % username)
            finally:
                os.remove(user_pkey_path)

            # set local cache size
            with open(config_path, "a") as cf:
                cf.write("\n[gateway]\n")
                cf.write("cache_size_limit=%d\n" % cache_size_limit)

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

    def _remove_syndicate_setup(self, mount_id):
        config_root_path = self._make_syndicate_configuration_root_path(mount_id)
        if os.path.exists(config_root_path):
            shutil.rmtree(config_root_path)
            sdm_util.log_message("Successfully removed Syndicate at %s" % config_root_path)

    def _mount_syndicatefs(self, mount_id, dataset, gateway_name, mount_path, debug_mode=False, debug_level=1):
        sdm_util.log_message("Mounting syndicatefs, %s to %s" % (dataset, mount_path))

        abs_mount_path = sdm_util.get_abs_path(mount_path)
        if not os.path.exists(abs_mount_path):
            os.makedirs(abs_mount_path, 0755)

        config_root_path = self._make_syndicate_configuration_root_path(mount_id)
        syndicatefs_log_path = "%s/mount.log" % config_root_path
        syndicatefs_command = self._make_syndicatefs_command(mount_id, debug_mode, debug_level)

        #${SYNDICATEFS_CMD} -f -u ANONYMOUS -v ${VOLUME_NAME} -g ${UG_NAME} ${SYNDICATEFS_DATASET_MOUNT_DIR} &> /tmp/syndicate_${VOLUME_NAME}.log&
        command_mount = "%s -f -u ANONYMOUS -v %s -g %s %s" % (
            syndicatefs_command,
            dataset,
            gateway_name,
            abs_mount_path
        )

        self._run_command_background(command_mount, syndicatefs_log_path)
        self._wait_mount(abs_mount_path, retry=3)
        sdm_util.log_message("Successfully mounted syndicatefs, %s to %s" % (dataset, abs_mount_path))

    def _unmount_syndicatefs(self, mount_path):
        try:
            command_unmount = "fusermount -u %s" % mount_path
            self._run_command_foreground(command_unmount)
        except FuseBackendException, e:
            if "not found" in str(e):
                # it's already unmounted - skip
                pass
            else:
                raise e

    def mount(self, mount_id, ms_host, dataset, username, user_pkey, gateway_name, mount_path):
        sdm_util.print_message("Mounting a dataset %s to %s" % (dataset, mount_path), True)
        self._setup_syndicate(mount_id, dataset, username, user_pkey, gateway_name, ms_host, self.backend_config.syndicate_debug_mode, self.backend_config.syndicate_cache_max)
        self._mount_syndicatefs(mount_id, dataset, gateway_name, mount_path, self.backend_config.syndicate_debug_mode, self.backend_config.syndicate_debug_level)
        sdm_util.print_message("A dataset %s is mounted to %s" % (dataset, mount_path), True)

    def check_mount(self, mount_id, dataset, mount_path):
        try:
            self._wait_mount(mount_path)
            return True
        except FuseBackendException, e:
            return False

    def unmount(self, mount_id, dataset, mount_path, cleanup=False):
        sdm_util.print_message("Unmounting a dataset %s mounted at %s" % (dataset, mount_path), True)
        self._unmount_syndicatefs(mount_path)

        if cleanup:
            self._remove_syndicate_setup(mount_id)

        sdm_util.print_message("Successfully unmounted a dataset %s mounted at %s" % (dataset, mount_path), True)
