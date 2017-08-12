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
import os.path
import sys
import sdm.config as sdm_config
import sdm.mount_table as sdm_mount_table
import sdm.repository as sdm_repository
import sdm.syndicatefs_mount as sdm_syndicatefs_mount


config = sdm_config.Config()
mount_table = sdm_mount_table.MountTable()
repository = sdm_repository.Repository(config.get_repo_url())
syndicatefs = sdm_syndicatefs_mount.SyndicatefsMount()


def list_datasets(argv):
    if len(argv) == 0:
        entries = repository.list_entries()
        cnt = 0
        print "%s\t%s" % ("DATASET", "DESCRIPTION")
        for ent in entries:
            cnt += 1
            print "%s : %s" % (ent.dataset, ent.description)

        if cnt == 0:
            print "No available dataset"
            return 0
        else:
            return 0
    else:
        show_help(["list"])
        return 1


def show_mounts(argv):
    if len(argv) == 0:
        records = mount_table.list_records()
        cnt = 0
        print "%s\t%s\t%s" % ("MOUNT_ID", "DATASET", "MOUNT_PATH")
        for rec in records:
            cnt += 1
            print "%s\t%s\t%s" % (rec.record_id, rec.dataset, rec.mount_path)

        if cnt == 0:
            print "No available dataset"
            return 0
        else:
            return 0
    else:
        show_help(["show"])
        return 1


def process_mount_dataset(dataset, mount_path):
    entry = repository.get_entry(dataset)
    if entry:
        try:
            mount_record = mount_table.add_record(dataset, mount_path)
            syndicatefs.mount(
                mount_record.record_id,
                entry.ms_host,
                entry.dataset,
                entry.username,
                entry.user_pkey,
                entry.gateway_name,
                mount_path
            )
            mount_table.save_table()
            return 0
        except sdm_mount_table.MountTableException, e:
            print "Cannot mount dataset - %s to  %s" % (dataset, mount_path)
            print e
            return 1
        except sdm_syndicatefs_mount.SyndicatefsMountException, e:
            print "Cannot mount dataset - %s to  %s" % (dataset, mount_path)
            print e
            return 1
    else:
        print "Dataset not found - %s" % dataset
        return 1


def mount_dataset(argv):
    # args
    # 1. dataset name
    # 2. mount_path (optional)
    if len(argv) >= 1:
        dataset = argv[0].strip().lower()
        mount_path = "%s/%s" % (
            config.get_default_mount_path().rstrip("/"),
            dataset
        )

        if len(argv) == 2:
            mount_path = argv[1].strip().rstrip("/")
            if len(mount_path) == 0:
                mount_path = "/"

        abs_mount_path = os.path.abspath(mount_path)
        return process_mount_dataset(dataset, abs_mount_path)
    else:
        show_help(["mount"])
        return 1


def process_unmount_dataset(record_id):
    try:
        records = mount_table.get_records_by_record_id(record_id)
        if len(records) == 1:
            record = records[0]
            syndicatefs.unmount(record.record_id, record.mount_path)
            mount_table.delete_record(record.record_id)
            mount_table.save_table()
            return 0
        else:
            print "Cannot unmount dataset. There are more %d mounts" % len(records)
            return 1
    except sdm_mount_table.MountTableException, e:
        print "Cannot unmount dataset - %s" % (record_id)
        print e
        return 1
    except sdm_syndicatefs_mount.SyndicatefsMountException, e:
        print "Cannot unmount dataset - %s" % (record_id)
        print e
        return 1


def unmount_dataset(argv):
    # args
    # 1. dataset name OR mount_path
    if len(argv) >= 1:
        if len(sdm_mount_table.get_records_by_dataset(argv[0])) > 0:
            # dataset
            records = sdm_mount_table.get_records_by_dataset(argv[0])
            if len(records) == 1:
                return process_unmount_dataset(records[0].record_id)
            else:
                print "Cannot unmount dataset. There are more %d mounts" % len(records)
                return 1
        elif len(sdm_mount_table.get_records_by_mount_path(argv[0])) > 0:
            # maybe path?
            records = sdm_mount_table.get_records_by_mount_path(argv[0])
            if len(records) == 1:
                return process_unmount_dataset(records[0].record_id)
            else:
                print "Cannot unmount dataset. There are more %d mounts" % len(records)
                return 1
        elif len(sdm_mount_table.get_records_by_record_id(argv[0])) > 0:
            # maybe record_id?
            records = sdm_mount_table.get_records_by_record_id(argv[0])
            if len(records) == 1:
                return process_unmount_dataset(records[0].record_id)
            else:
                print "Cannot unmount dataset. There are more %d mounts" % len(records)
                return 1
        else:
            print "Cannot find mount - %s" % argv[0]
            return 1
    else:
        show_help(["unmount"])
        return 1


COMMANDS_DESCS = {
    "list": "list available datasets",
    "show": "show mounts",
    "mount": "mount a dataset",
    "unmount": "unmount a dataset",
    "help": "show help"
}


def show_help(argv=None):
    if argv:
        if "list" in argv:
            print "command : sdm list"
            print ""
            print COMMANDS_DESCS["list"]
            return 0
        elif "show" in argv:
            print "command : sdm show"
            print ""
            print COMMANDS_DESCS["show"]
            return 0
        elif "mount" in argv:
            print "command : sdm mount <dataset_name> [<mount_path>]"
            print ""
            print COMMANDS_DESCS["mount"]
            return 0
        elif "unmount" in argv:
            print "command : sdm unmount <mount_id>"
            print ""
            print COMMANDS_DESCS["mount"]
            return 0
        else:
            print "Unrecognized command"
            return 1
    else:
        print "command : sdm <COMMAND> [<COMMAND_SPECIFIC_ARGS> ...]"
        print ""
        print "Available Commands"
        for k in COMMANDS.keys():
            print "%s: %s" % (k, COMMANDS_DESCS[k])
        print ""
        return 0


COMMANDS = {
    "list": list_datasets,
    "show": show_mounts,
    "mount": mount_dataset,
    "unmount": unmount_dataset,
    "help": show_help,
}


def run(command, argv):
    if command is None:
        raise ValueError("No command is given")

    command = command.lower()

    if command in COMMANDS:
        COMMANDS[command](argv)
    else:
        raise ValueError("Unrecognized command: %s" % (command))


def main(argv):
    if len(argv) >= 1:
        # has command part
        command = argv[0]
        oargs = argv[1:]

        try:
            run(command, oargs)
        except Exception, e:
            print >> sys.stderr, e
            print ""
            show_help()
    else:
        show_help()


if __name__ == "__main__":
    main(sys.argv[1:])
