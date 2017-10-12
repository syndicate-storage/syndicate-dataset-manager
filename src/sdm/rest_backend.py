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

import os
import json
import grequests
import urlparse
import abstract_backend as sdm_absbackends
import util as sdm_util

DEFAULT_REST_HOSTS = ["http://localhost:8888"]
DEFAULT_MOUNT_PATH = "hsyn:///"


class RestBackendException(sdm_absbackends.AbstractBackendException):
    pass


class RestBackendConfig(sdm_absbackends.AbstractBackendConfig):
    """
    REST Backend Config
    """
    def __init__(self):
        self.default_mount_path = DEFAULT_MOUNT_PATH
        self.rest_hosts = DEFAULT_REST_HOSTS

    @classmethod
    def from_dict(cls, d):
        config = RestBackendConfig()
        config.default_mount_path = d["default_mount_path"]
        config.rest_hosts = d["rest_hosts"]
        return config

    @classmethod
    def get_default_config(cls):
        return RestBackendConfig()

    def to_json(self):
        return json.dumps({
            "default_mount_path": self.default_mount_path,
            "rest_hosts": self.rest_hosts
        })

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "<RestBackendConfig %s>" % \
            (self.rest_hosts)


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

    def _check_syndicate_user(self, rest_host, mount_id):
        try:
            url = "%s/user/check" % rest_host
            params = {
                "mount_id": mount_id
            }
            sdm_util.log_message("Sending a HTTP GET request : %s" % url)
            response = grequests.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            return sdm_util.to_bool(result["result"])
        except Exception, e:
            raise RestBackendException("cannot check user : %s" % e)

    def _check_syndicate_user_multi(self, rest_hosts, mount_id):
        try:
            params = {
                "mount_id": mount_id
            }

            reqs = []
            for rest_host in rest_hosts:
                url = "%s/user/check" % rest_host
                sdm_util.log_message("Sending a HTTP GET request : %s" % url)
                req = grequests.get(url, params=params)
                reqs.append(req)

            ress = grequests.map(set(reqs))
            results = {}
            idx = 0
            for res in ress:
                res.raise_for_status()
                result = res.json()
                rest_host = rest_hosts[idx]
                results[rest_host] = sdm_util.to_bool(result)
                idx += 1
            return results
        except Exception, e:
            raise RestBackendException("cannot check user : %s" % e)

    def _regist_syndicate_user(self, rest_host, mount_id, dataset, username, user_pkey, gateway_name, ms_host):
        # check if mount_id already exists
        skip_config = False
        if self._check_syndicate_user(rest_host, mount_id):
            skip_config = True

        if not skip_config:
            sdm_util.log_message("Setting up Syndicate for an user, %s" % username)
            try:
                # register
                url = "%s/user/setup" % rest_host
                values = {
                    "ms_url": ms_host,
                    "user": username,
                    "mount_id": mount_id,
                    "cert": user_pkey
                }
                sdm_util.log_message("Sending a HTTP POST request : %s" % url)
                response = grequests.post(url, data=values)
                response.raise_for_status()
                result = response.json()
                r = sdm_util.to_bool(result["result"])
                if not r:
                    raise RestBackendException("cannot setup Syndicate for an user, %s : %s" % (username, r))

                sdm_util.log_message("Successfully set up Syndicate for an user, %s" % username)
            except Exception, e:
                raise RestBackendException("cannot setup Syndicate for an user, %s : %s" % (username, e))

    def _regist_syndicate_user_multi(self, rest_hosts, mount_id, dataset, username, user_pkey, gateway_name, ms_host):
        # check if mount_id already exists
        check_results = self._check_syndicate_user_multi(rest_hosts, mount_id)

        target_rest_hosts = []
        for rest_host in rest_hosts:
            if not check_results[rest_host]:
                target_rest_hosts.append(rest_host)

        if len(target_rest_hosts) > 0:
            try:
                # register
                sdm_util.log_message("Setting up Syndicate for an user, %s" % username)

                values = {
                    "ms_url": ms_host,
                    "user": username,
                    "mount_id": mount_id,
                    "cert": user_pkey
                }

                reqs = []
                for rest_host in target_rest_hosts:
                    # for hosts who returned False at check
                    url = "%s/user/setup" % rest_host
                    sdm_util.log_message("Sending a HTTP POST request : %s" % url)
                    req = grequests.post(url, data=values)
                    reqs.append(req)

                ress = grequests.map(set(reqs))
                idx = 0
                for res in ress:
                    res.raise_for_status()
                    result = res.json()
                    r = sdm_util.to_bool(result["result"])
                    if not r:
                        raise RestBackendException("cannot setup Syndicate for an user, %s - %s : %s" % (target_rest_hosts[idx], username, r))
                    idx += 1

                sdm_util.log_message("Successfully set up Syndicate for an user, %s" % username)
            except Exception, e:
                raise RestBackendException("cannot setup Syndicate for an user, %s : %s" % (username, e))

    def _delete_syndicate_user(self, rest_host, mount_id):
        # check if mount_id already exists
        skip_config = False
        if self._check_syndicate_user(rest_host, mount_id):
            skip_config = True

        if not skip_config:
            sdm_util.log_message("Deleting an user, %s" % mount_id)
            try:
                # delete
                url = "%s/user/delete" % rest_host
                params = {
                    "mount_id": mount_id
                }
                sdm_util.log_message("Sending a HTTP DELETE request : %s" % url)
                response = grequests.delete(url, params=params)
                response.raise_for_status()
                result = response.json()
                r = sdm_util.to_bool(result["result"])
                if not r:
                    raise RestBackendException("cannot delete an user : %s - " % r)
            except Exception, e:
                raise RestBackendException("cannot delete an user : %s" % e)

    def _delete_syndicate_user_multi(self, rest_hosts, mount_id):
        # check if mount_id already exists
        check_results = self._check_syndicate_user_multi(rest_hosts, mount_id)

        target_rest_hosts = []
        for rest_host in rest_hosts:
            if not check_results[rest_host]:
                target_rest_hosts.append(rest_host)

        if len(target_rest_hosts) > 0:
            try:
                # delete
                sdm_util.log_message("Deleting an user, %s" % mount_id)

                params = {
                    "mount_id": mount_id
                }

                reqs = []
                for rest_host in rest_hosts:
                    url = "%s/user/delete" % rest_host
                    sdm_util.log_message("Sending a HTTP DELETE request : %s" % url)
                    req = grequests.delete(url, params=params)
                    reqs.append(req)

                ress = grequests.map(set(reqs))
                idx = 0
                for res in ress:
                    res.raise_for_status()
                    result = res.json()
                    r = sdm_util.to_bool(result["result"])
                    if not r:
                        raise RestBackendException("cannot delete an user : %s - %s" % (rest_hosts[idx], r))
                    idx += 1
            except Exception, e:
                raise RestBackendException("cannot delete an user : %s" % e)

    def _check_syndicate_gateway(self, rest_host, session_name):
        try:
            success = True
            url = "%s/gateway/check" % rest_host
            params = {
                "session_name": session_name
            }
            response = grequests.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            return sdm_util.to_bool(result["result"])
        except Exception, e:
            raise RestBackendException("cannot check mount : %s" % e)

    def _check_syndicate_gateway_multi(self, rest_hosts, session_name):
        try:
            params = {
                "session_name": session_name
            }

            reqs = []
            for rest_host in rest_hosts:
                url = "%s/gateway/check" % rest_host
                sdm_util.log_message("Sending a HTTP GET request : %s" % url)
                req = grequests.get(url, params=params)
                reqs.append(req)

            ress = grequests.map(set(reqs))
            results = {}
            idx = 0
            for res in ress:
                res.raise_for_status()
                result = res.json()
                rest_host = rest_hosts[idx]
                results[rest_host] = sdm_util.to_bool(result)
                idx += 1
            return results
        except Exception, e:
            raise RestBackendException("cannot check mount : %s" % e)

    def _regist_syndicate_gateway(self, rest_host, mount_id, dataset, gateway_name, session_name):
        # check if session_name already exists
        skip_config = False
        if self._check_syndicate_gateway(rest_host, session_name):
            skip_config = True

        if not skip_config:
            sdm_util.log_message("Registering a syndicate gateway, %s for %s" % (gateway_name, dataset))
            try:
                # register
                url = "%s/gateway/setup" % rest_host
                values = {
                    "mount_id": mount_id,
                    "session_name": session_name,
                    "session_key": dataset,
                    "volume": dataset,
                    "gateway": gateway_name,
                    "anonymous": "true"
                }
                sdm_util.log_message("Sending a HTTP POST request : %s" % url)
                response = grequests.post(url, data=values)
                response.raise_for_status()
                result = response.json()
                r = sdm_util.to_bool(result["result"])
                if not r:
                    raise RestBackendException("cannot register a syndicate gateway, %s for %s : %s" % (gateway_name, dataset, r))

                sdm_util.log_message("Successfully registered a syndicate gateway, %s for %s" % (gateway_name, dataset))
            except Exception, e:
                raise RestBackendException("cannot register a syndicate gateway, %s for %s : %s" % (gateway_name, dataset, e))

    def _regist_syndicate_gateway_multi(self, rest_hosts, mount_id, dataset, gateway_name, session_name):
        # check if session_name already exists
        check_results = self._check_syndicate_gateway_multi(rest_hosts, session_name)

        target_rest_hosts = []
        for rest_host in rest_hosts:
            if not check_results[rest_host]:
                target_rest_hosts.append(rest_host)

        if len(target_rest_hosts) > 0:
            try:
                # register
                sdm_util.log_message("Registering a syndicate gateway, %s for %s" % (gateway_name, dataset))

                values = {
                    "mount_id": mount_id,
                    "session_name": session_name,
                    "session_key": dataset,
                    "volume": dataset,
                    "gateway": gateway_name,
                    "anonymous": "true"
                }

                reqs = []
                for rest_host in target_rest_hosts:
                    # for hosts who returned False at check
                    url = "%s/gateway/setup" % rest_host
                    sdm_util.log_message("Sending a HTTP POST request : %s" % url)
                    req = grequests.post(url, data=values)
                    reqs.append(req)

                ress = grequests.map(set(reqs))
                idx = 0
                for res in ress:
                    res.raise_for_status()
                    result = res.json()
                    r = sdm_util.to_bool(result["result"])
                    if not r:
                        raise RestBackendException("cannot register a syndicate gateway, %s - %s for %s : %s" % (target_rest_hosts[idx], gateway_name, dataset, r))
                    idx += 1

                sdm_util.log_message("Successfully registered a syndicate gateway, %s for %s" % (gateway_name, dataset))
            except Exception, e:
                raise RestBackendException("cannot register a syndicate gateway, %s for %s : %s" % (gateway_name, dataset, e))

    def _delete_syndicate_gateway(self, rest_host, mount_id, dataset, session_name):
        # check if session_name already exists
        skip_config = False
        if self._check_syndicate_gateway(rest_host, session_name):
            skip_config = True

        if not skip_config:
            sdm_util.log_message("Deleting a syndicate gateway, %s for %s" % (gateway_name, dataset))
            try:
                # delete
                url = "%s/gateway/delete" % rest_host
                params = {
                    "session_name": session_name,
                    "session_key": dataset
                }
                sdm_util.log_message("Sending a HTTP DELETE request : %s" % url)
                response = grequests.delete(url, params=params)
                response.raise_for_status()
                result = response.json()
                r = sdm_util.to_bool(result["result"])
                if not r:
                    raise RestBackendException("cannot delete gateway : %s - " % r)
            except Exception, e:
                raise RestBackendException("cannot delete gateway : %s" % e)

    def _delete_syndicate_gateway_multi(self, rest_hosts, mount_id, dataset, session_name):
        # check if session_name already exists
        check_results = self._check_syndicate_gateway_multi(rest_hosts, session_name)

        target_rest_hosts = []
        for rest_host in rest_hosts:
            if not check_results[rest_host]:
                target_rest_hosts.append(rest_host)

        if len(target_rest_hosts) > 0:
            try:
                sdm_util.log_message("Deleting a syndicate gateway, %s for %s" % (gateway_name, dataset))

                params = {
                    "session_name": session_name,
                    "session_key": dataset
                }

                reqs = []
                for rest_host in rest_hosts:
                    url = "%s/gateway/delete" % rest_host
                    sdm_util.log_message("Sending a HTTP DELETE request : %s" % url)
                    req = grequests.delete(url, params=params)
                    reqs.append(req)

                ress = grequests.map(set(reqs))
                idx = 0
                for res in ress:
                    res.raise_for_status()
                    result = res.json()
                    r = sdm_util.to_bool(result["result"])
                    if not r:
                        raise RestBackendException("cannot delete gateway : %s - %s" % (rest_hosts[idx], r))
                    idx += 1
            except Exception, e:
                raise RestBackendException("cannot delete gateway : %s" % e)

    def mount(self, mount_id, ms_host, dataset, username, user_pkey, gateway_name, mount_path):
        sdm_util.print_message("Mounting a dataset %s to %s" % (dataset, mount_path), True)
        session_name = self._get_session_name(mount_path)

        self._regist_syndicate_user_multi(self.backend_config.rest_hosts, mount_id, dataset, username, user_pkey, gateway_name, ms_host)
        self._regist_syndicate_gateway(self.backend_config.rest_hosts, mount_id, dataset, gateway_name, session_name)
        sdm_util.print_message("A dataset %s is mounted to %s" % (dataset, mount_path), True)

    def check_mount(self, mount_id, dataset, mount_path):
        session_name = self._get_session_name(mount_path)
        try:
            results = self._check_syndicate_gateway_multi(self.backend_config.rest_hosts, session_name)
            result = True
            for r_result in results.values():
                if not r_result:
                    result = False
                    break
            return result
        except RestBackendException, e:
            return False

    def unmount(self, mount_id, dataset, mount_path, cleanup=False):
        sdm_util.print_message("Unmounting a dataset %s mounted at %s" % (dataset, mount_path), True)
        session_name = self._get_session_name(mount_path)

        self._delete_syndicate_gateway_multi(self.backend_config.rest_hosts, mount_id, dataset, session_name)
        if cleanup:
            self._delete_syndicate_user_multi(self.backend_config.rest_hosts, mount_id)

        sdm_util.print_message("Successfully unmounted a dataset %s mounted at %s" % (dataset, mount_path), True)
