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

import fuse_backend as sdm_fuse_backend
import rest_backend as sdm_rest_backend


class UnknownBackend(Exception):
    pass


class Backends(object):
    FUSE = "FUSE"
    REST = "REST"

    @classmethod
    def from_str(cls, name):
        if name.strip().lower() == "fuse":
            return cls.FUSE
        elif name.strip().lower() == "rest":
            return cls.REST
        else:
            raise UnknownBackend("unknown backend - %s" % name)

    @classmethod
    def get_backend_instance(cls, backend):
        if backend == cls.FUSE:
            return sdm_fuse_backend.FuseBackendConfig()
        elif backend == cls.REST:
            return sdm_rest_backend.RestBackendConfig()

    @classmethod
    def get_backend_class(cls, backend):
        if backend == cls.FUSE:
            return sdm_fuse_backend.FuseBackendConfig
        elif backend == cls.REST:
            return sdm_rest_backend.RestBackendConfig

    @classmethod
    def get_default_backend_configs(cls):
        configs = {}
        for b in [Backends.FUSE, Backends.REST]:
            configs[b] = Backends.get_backend_class(b).get_default_config()

        return configs

    @classmethod
    def objectfy_backend_config_from_dict(cls, backend, d):
        return Backends.get_backend_class(backend).from_dict(d)
