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
import urlparse
import abstract_backend as sdm_absbackends
import util as sdm_util

requests.packages.urllib3.disable_warnings()

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

        if not parts.scheme:
            return False

        session_name = self._get_session_name(parts.path)
        if len(session_name) == 0:
            return False

        return True

    def make_default_mount_path(self, dataset, default_mount_path):
        parts = urlparse.urlparse(default_mount_path)

        if not parts.scheme:
            raise RestBackendException( "cannot make default mount path for %s" % dataset)

        mount_path = "%s://%s/%s" % (
            parts.scheme,
            parts.netloc,
            dataset.strip().lower()
        )

        abs_mount_path = sdm_util.get_abs_path(mount_path)
        return abs_mount_path

    def _get_session_name(self, mount_path):
        parts = urlparse.urlparse(mount_path)
        path = parts.path.lstrip("/")
        idx = path.find("/")
        if idx > 0:
            return path[:idx]
        return path

    def _check_syndicate_user(self, mount_id):
        try:
            url = "%s/user/check" % self.backend_config.rest_host
            params = {
                "mount_id": mount_id
            }
            sdm_util.log_message("Sending a HTTP GET request : %s" % url)
            response = requests.get(url, params=params)
            result = response.json()
            return bool(result["result"])
        except Exception, e:
            raise RestBackendException("cannot check user : %s" % e)

    def _regist_syndicate_user(self, mount_id, dataset, username, user_pkey, gateway_name, ms_host):
        # check if mount_id already exists
        skip_config = False
        if self._check_syndicate_user(mount_id):
            skip_config = True

        if not skip_config:
            sdm_util.log_message("Setting up Syndicate for an user, %s" % username)
            user_pkey_fd, user_pkey_path = tempfile.mkstemp()
            f = os.fdopen(user_pkey_fd, "w")
            f.write(user_pkey)
            f.close()

            try:
                # register
                url = "%s/user/setup" % self.backend_config.rest_host
                files = {
                    "ms_url": ms_host,
                    "user": username,
                    "mount_id": mount_id,
                    "cert": (open(user_pkey_path, 'rb'))
                }
                sdm_util.log_message("Sending a HTTP POST request : %s" % url)
                response = requests.post(url, files=files)
                result = response.json()
                r = bool(result["result"])
                if r:
                    sdm_util.log_message("Successfully set up Syndicate for an user, %s" % username)
                else:
                    raise RestBackendException("cannot setup Syndicate for an user, %s : %s" % (username, r))
            except Exception, e:
                raise RestBackendException("cannot setup Syndicate for an user, %s : %s" % (username, e))
            finally:
                os.remove(user_pkey_path)

    def _delete_syndicate_user(self, mount_id):
        try:
            url = "%s/user/delete" % self.backend_config.rest_host
            params = {
                "mount_id": mount_id
            }
            sdm_util.log_message("Sending a HTTP DELETE request : %s" % url)
            response = requests.delete(url, params=params)
            result = response.json()
            r = bool(result["result"])
            if not r:
                raise RestBackendException("cannot delete user : %s - " % r)
        except Exception, e:
            raise RestBackendException("cannot delete user : %s" % e)

    def _check_syndicate_gateway(self, session_name):
        try:
            url = "%s/gateway/check" % self.backend_config.rest_host
            params = {
                "session_name": session_name
            }
            response = requests.get(url, params=params)
            result = response.json()
            return bool(result["result"])
        except Exception, e:
            raise RestBackendException("cannot check mount : %s" % e)

    def _regist_syndicate_gateway(self, mount_id, dataset, gateway_name, session_name):
        sdm_util.log_message("Registering a syndicate gateway, %s for %s" % (gateway_name, dataset))
        try:
            # register
            url = "%s/gateway/setup" % self.backend_config.rest_host
            files = {
                "mount_id": mount_id,
                "session_name": session_name,
                "session_key": dataset,
                "volume": dataset,
                "gateway": gateway_name,
                "anonymous": "true",
                "cert": (open(user_pkey_path, 'rb'))
            }
            sdm_util.log_message("Sending a HTTP POST request : %s" % url)
            response = requests.post(url, files=files)
            result = response.json()
            r = bool(result["result"])
            if r:
                sdm_util.log_message("Successfully set up a syndicate gateway, %s for %s" % (gateway_name, dataset))
            else:
                raise RestBackendException("cannot register a syndicate gateway, %s for %s : %s" % (gateway_name, dataset, r))
        except Exception, e:
            raise RestBackendException("cannot register a syndicate gateway, %s for %s : %s" % (gateway_name, dataset, e))

        sdm_util.log_message("Successfully registered a syndicate gateway, %s for %s" % (gateway_name, dataset))

    def _delete_syndicate_gateway(self, mount_id, dataset, session_name):
        try:
            url = "%s/gateway/delete" % self.backend_config.rest_host
            params = {
                "mount_id": mount_id,
                "session_name": session_name,
                "session_key": dataset
            }
            sdm_util.log_message("Sending a HTTP DELETE request : %s" % url)
            response = requests.delete(url, params=params)
            result = response.json()
            r = bool(result["result"])
            if not r:
                raise RestBackendException("cannot delete user : %s - " % r)
        except Exception, e:
            raise RestBackendException("cannot delete user : %s" % e)

    def mount(self, mount_id, ms_host, dataset, username, user_pkey, gateway_name, mount_path):
        sdm_util.print_message("Mounting a dataset %s to %s" % (dataset, mount_path), True)
        session_name = self._get_session_name(mount_path)
        self._regist_syndicate_user(mount_id, dataset, username, user_pkey, gateway_name, ms_host)
        self._regist_syndicate_gateway(mount_id, dataset, gateway_name, session_name)
        sdm_util.print_message("A dataset %s is mounted to %s" % (dataset, mount_path), True)

    def check_mount(self, mount_id, dataset, mount_path):
        session_name = self._get_session_name(mount_path)
        try:
            return self._check_syndicate_gateway(session_name)
        except RestBackendException, e:
            return False

    def unmount(self, mount_id, dataset, mount_path, cleanup=False):
        sdm_util.print_message("Unmounting a dataset %s mounted at %s" % (dataset, mount_path), True)
        session_name = self._get_session_name(mount_path)
        self._delete_syndicate_gateway(mount_id, dataset, session_name)
        if cleanup:
            self._delete_syndicate_user(mount_id)

        sdm_util.print_message("Successfully unmounted a dataset %s mounted at %s" % (dataset, mount_path), True)
