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


backends_impl = []
backends_impl_map = {}

# name, class, config_class,
backends_impl.append(
    (
        sdm_fuse_backend.FuseBackend.get_name(),
        sdm_fuse_backend.FuseBackend,
        sdm_fuse_backend.FuseBackendConfig
    )
)
backends_impl.append(
    (
        sdm_rest_backend.RestBackend.get_name(),
        sdm_rest_backend.RestBackend,
        sdm_rest_backend.RestBackendConfig
    )
)

for impl in backends_impl:
    _n, _c, _cc = impl
    backends_impl_map[_n.strip().lower()] = impl


def _get_backend(name):
    backend = name.strip().lower()
    if backend in backends_impl_map:
         return backends_impl_map[backend]
    else:
        raise UnknownBackend("unknown backend - %s" % name)


class UnknownBackend(Exception):
    pass


class Backends(object):
    @classmethod
    def get_backend_name(cls, name):
        _n, _, _ = _get_backend(name)
        return _n

    @classmethod
    def get_backend_instance(cls, backend, backend_config):
        _, _c, _ = _get_backend(backend)
        return _c(backend_config)

    @classmethod
    def get_backend_class(cls, backend):
        _, _c, _ = _get_backend(backend)
        return _c

    @classmethod
    def get_backend_config_instance(cls, backend):
        _, _, _cc = _get_backend(backend)
        return _cc()

    @classmethod
    def get_backend_config_class(cls, backend):
        _, _, _cc = _get_backend(backend)
        return _cc

    @classmethod
    def get_default_backend_configs(cls):
        configs = {}
        for impl in backends_impl:
            _n, _c, _cc = impl
            configs[_n] = _cc.get_default_config()

        return configs

    @classmethod
    def objectfy_backend_config_from_dict(cls, backend, d):
        return cls.get_backend_config_class(backend).from_dict(d)
