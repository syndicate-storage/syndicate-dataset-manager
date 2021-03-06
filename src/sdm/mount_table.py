#! /usr/bin/env python

##  @file: src/sdm/mount_table.py
#   Process information related to the mount table
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

import os
import os.path
import hashlib
import backends as sdm_backends


class MountTableException(Exception):
    pass


class MountRecordStatus(object):
    UNMOUNTED = "UNMOUNTED"
    MOUNTED = "MOUNTED"


class MountRecord(object):
    """
    mount table record
    """
    def __init__(self, dataset, mount_path, backend, status=MountRecordStatus.UNMOUNTED, record_id=""):
        self.dataset = dataset.strip().lower()
        self.mount_path = mount_path.strip()

        if record_id:
            self.record_id = record_id.strip().lower()
        else:
            self.record_id = self._make_record_id(self.dataset, backend)

        self.backend = backend

        if status.strip().upper() == MountRecordStatus.MOUNTED:
            self.status = MountRecordStatus.MOUNTED
        else:
            self.status = MountRecordStatus.UNMOUNTED

    def _make_record_id(self, dataset, backend):
        seed = "seed123%sMountRecord%s" % (dataset, backend)
        return hashlib.sha256(seed).hexdigest().lower()

    @classmethod
    def from_line(cls, line):
        fields = line.strip().split("\t")
        if len(fields) == 5:
            record_id = fields[0].strip()
            dataset = fields[1].strip()
            mount_path = fields[2].strip()
            backend = sdm_backends.Backends.get_backend_name(fields[3].strip())
            status = fields[4].strip()
            return MountRecord(dataset, mount_path, backend, status, record_id)
        else:
            raise MountTableException("unrecognized format - %s" % line)

    def to_line(self):
        return "%s\t%s\t%s\t%s\t%s" % (self.record_id, self.dataset, self.mount_path, self.backend, self.status)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "<MountRecord %s %s %s %s>" % \
            (self.record_id[:8], self.dataset, self.mount_path, self.backend)


class MountTable(object):
    """
    Manage SDM mount table
    """
    def __init__(self, path):
        self.table = []
        try:
            self.load_table(path)
        except IOError:
            self.save_table(path)

    def load_table(self, path):
        self.table = []
        with open(path, 'r') as f:
            for line in f:
                record = MountRecord.from_line(line)
                self.table.append(record)

    def save_table(self, path):
        parent = os.path.dirname(path)
        if not os.path.exists(parent):
            os.makedirs(parent, 0755)

        with open(path, 'w') as f:
            for record in self.table:
                line = record.to_line()
                f.write(line + "\n")

    def list_records(self):
        records = []
        for record in self.table:
            records.append(record)
        return records

    def get_records_by_record_id(self, record_id):
        rid = record_id.strip().lower()
        ridlen = len(rid)

        records = []
        for record in self.table:
            if record.record_id[:ridlen] == rid:
                records.append(record)
        return records

    def get_records_by_dataset(self, dataset):
        ds = dataset.strip().lower()

        records = []
        for record in self.table:
            if record.dataset == ds:
                records.append(record)
        return records

    def get_records_by_mount_path(self, mount_path):
        records = []
        for record in self.table:
            if record.mount_path == mount_path:
                records.append(record)
        return records

    def get_records_by_backend(self, backend):
        records = []
        for record in self.table:
            if record.backend == backend:
                records.append(record)
        return records

    def get_records_by_status(self, status):
        records = []
        for record in self.table:
            if record.status == status:
                records.append(record)
        return records

    def add_record(self, dataset, mount_path, backend, status):
        record = MountRecord(dataset, mount_path, backend, status)
        exist = False

        for r in self.table:
            if r.record_id == record.record_id:
                exist = True
                break

            if r.mount_path == record.mount_path:
                exist = True
                break

            if r.dataset == record.dataset:
                exist = True
                break

        if not exist:
            self.table.append(record)
            return record
        else:
            raise MountTableException("Record already exists - %s" % record)

    def delete_record(self, record_id):
        exist = False
        idx = 0
        for r in self.table:
            if r.record_id == record_id:
                exist = True
                break
            idx += 1

        if exist:
            self.table.pop(idx)
        else:
            raise MountTableException("Record not exist - %s" % record_id)
