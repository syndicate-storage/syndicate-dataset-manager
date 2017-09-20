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
import urlparse
import abstract_backend as sdm_absbackends
import util as sdm_util

DEFAULT_REST_HOST = "http://localhost:8888"
DEFAULT_MOUNT_PATH = "hsyn:///"


class RestBackendException(sdm_absbackends.AbstractBackendException):
    pass


class RestBackendConfig(sdm_absbackends.AbstractBackendConfig):
    """
    REST Backend Config
    """
    def __init__(self):
        self.default_mount_path = DEFAULT_MOUNT_PATH
        self.rest_host = DEFAULT_REST_HOST

    @classmethod
    def from_dict(cls, d):
        config = RestBackendConfig()
        config.default_mount_path = d["default_mount_path"]
        config.rest_host = d["rest_host"]
        return config

    @classmethod
    def get_default_config(cls):
        return RestBackendConfig()

    def to_json(self):
        return json.dumps({
            "default_mount_path": self.default_mount_path,
            "rest_host": self.rest_host
        })

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "<RestBackendConfig %s>" % \
            (self.rest_host)


class RestBackend(sdm_absbackends.AbstractBackend):
    """
    REST Backend
    """
    def __init__(self, backend_config):
        self.backend_config = backend_config

    @classmethod
    def get_name(cls):
        return "REST"

    def is_legal_mount_path(self, mount_path):
        parts = urlparse.urlparse(mount_path)

        if parts.scheme not in self.backend_config.rest_host:
            return False

        if parts.netloc not in self.backend_config.rest_host:
            return False

        session_name = self._get_session_name(parts.path)
        if len(session_name) == 0:
            return False

        return True

    def _get_session_name(self, mount_path):
        parts = urlparse.urlparse(mount_path)
        path = parts.path.lstrip("/")
        idx = path.find("/")
        if idx > 0:
            return path[:idx]
        return path

    def _regist_syndicate_user(self, mount_id, dataset, username, user_pkey, gateway_name, ms_host, force=False):
        # check if mount_id already exists
        session_name = self._get_session_name(mount_path)

        if force:
            skip_config = False
            # delete

        if not skip_config:
            sdm_util.log_message("Registering a syndicate user, %s" % username)
            user_pkey_fd, user_pkey_path = tempfile.mkstemp()
            f = os.fdopen(user_pkey_fd, "w")
            f.write(user_pkey)
            f.close()

            try:
                # register
                sdm_util.log_message("Successfully registered a syndicate user, %s" % username)
            finally:
                os.remove(user_pkey_path)

    def _regist_syndicate_gateway(self, mount_id, dataset, gateway_name):
        sdm_util.log_message("Registering a syndicate gateway, %s for %s" % (gateway_name, dataset))
        # mount
        sdm_util.log_message("Successfully registered a syndicate gateway, %s for %s" % (gateway_name, dataset))

    def mount(self, mount_id, ms_host, dataset, username, user_pkey, gateway_name, mount_path, force=False):
        sdm_util.print_message("Mounting a dataset %s to %s" % (dataset, mount_path), True)
        self._regist_syndicate_user(mount_id, dataset, username, user_pkey, gateway_name, ms_host, force)
        self._regist_syndicate_gateway(mount_id, dataset, gateway_name)
        sdm_util.print_message("A dataset %s is mounted to %s" % (dataset, mount_path), True)

    def check_mount(self, mount_id, dataset, mount_path):
        session_name = self._get_session_name(mount_path)

        try:
            url = "%s/gateway/check?session_name=%s" % (self.backend_config.rest_host, session_name)
            response = urllib.urlopen(url)
            content = response.read()
            result = json.loads(content)
            return bool(result["result"])
        except Exception, e:
            raise RestBackendException("cannot check mount : %s" % e)

    def unmount(self, mount_id, dataset, mount_path, cleanup=False):
        try:
            # unmount
            pass
        except RestBackendException, e:
            raise e

        if cleanup:
            # clean up
            pass
        sdm_util.print_message("Successfully unmounted a dataset %s from %s" % (dataset, mount_path), True)
