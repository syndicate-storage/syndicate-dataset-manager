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
import traceback
import config as sdm_config
import mount_table as sdm_mount_table
import repository as sdm_repository
import syndicatefs_mount as sdm_syndicatefs_mount

from os.path import expanduser
from prettytable import PrettyTable


config = sdm_config.Config()
mount_table = sdm_mount_table.MountTable()
repository = sdm_repository.Repository(config.get_repo_url())
syndicatefs = sdm_syndicatefs_mount.SyndicatefsMount()


COMMANDS = []

COMMANDS_TABLE = {}


def _fill_commands_table():
    COMMANDS.append((["list_datasets", "ls", "list"], list_datasets, "list available datasets"))
    COMMANDS.append((["show_mounts", "ps", "status"], show_mounts, "show mount status"))
    COMMANDS.append((["mount", "mnt"], mount_dataset, "mount a dataset"))
    COMMANDS.append((["unmount", "umount", "umnt"], unmount_dataset, "unmount a dataset"))
    COMMANDS.append((["clean"], clean_mounts, "clear broken mounts"))
    COMMANDS.append((["help", "h"], show_help, "show help"))

    for cmd in COMMANDS:
        karr, _, _ = cmd
        for k in karr:
            COMMANDS_TABLE[k] = cmd


def list_datasets(argv):
    """
    List Datasets
    """
    if len(argv) == 0:
        entries = repository.list_entries()
        cnt = 0
        tbl = PrettyTable()
        tbl.field_names = ["DATASET", "DESCRIPTION"]
        for ent in entries:
            cnt += 1
            tbl.add_row([ent.dataset, ent.description])

        print tbl

        if cnt == 0:
            print "No available dataset"
            return 0
        else:
            return 0
    else:
        show_help(["list_datasets"])
        return 1


def show_mounts(argv):
    """
    Show mounts
    """
    if len(argv) == 0:
        records = mount_table.list_records()
        cnt = 0
        tbl = PrettyTable()
        tbl.field_names = ["MOUNT_ID", "DATASET", "MOUNT_PATH", "STATUS"]

        need_sync = False
        for rec in records:
            # detect out-of-sync record
            is_mounted = syndicatefs.check_mount(rec.mount_path)
            is_status_mounted = rec.status == sdm_mount_table.MountRecordStatus.MOUNTED

            if is_mounted != is_status_mounted:
                if is_mounted:
                    rec.status = sdm_mount_table.MountRecordStatus.MOUNTED
                else:
                    rec.status = sdm_mount_table.MountRecordStatus.UNMOUNTED
                need_sync = True

            cnt += 1
            tbl.add_row([rec.record_id[:12], rec.dataset, rec.mount_path, rec.status])

        print tbl

        if need_sync:
            mount_table.save_table()

        if cnt == 0:
            print "No mounts"
            return 0
        else:
            return 0
    else:
        show_help(["show_mounts"])
        return 1


def process_mount_dataset(dataset, mount_path):
    entry = repository.get_entry(dataset)
    if entry:

        username = entry.username
        user_pkey = entry.user_pkey
        if username.strip() == "" or user_pkey.strip() == "":
            # use local settings
            syndicate_users = config.list_syndicate_users_by_ms_host(entry.ms_host)
            for suser in syndicate_users:
                username = suser.username
                user_pkey = suser.user_pkey
                break

        if username.strip() == "" or user_pkey.strip() == "":
            print "Cannot find user accounts to access the dataset - %s" % (dataset)
            return 1

        try:
            # check existance
            records = mount_table.get_records_by_mount_path(mount_path)
            for rec in records:
                if rec.dataset == dataset and rec.status == sdm_mount_table.MountRecordStatus.UNMOUNTED:
                    # same dataset but unmounted
                    # delete and overwrite
                    mount_table.delete_record(rec.record_id)

            mount_record = mount_table.add_record(dataset, mount_path, status=sdm_mount_table.MountRecordStatus.UNMOUNTED)
            mount_table.save_table()

            syndicatefs.mount(
                mount_record.record_id,
                entry.ms_host,
                entry.dataset,
                username,
                user_pkey,
                entry.gateway,
                mount_path,
                debug_mode=config.get_syndicate_debug_mode(),
                debug_level=config.get_syndicate_debug_level(),
            )
            mount_record.status = sdm_mount_table.MountRecordStatus.MOUNTED
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

        abs_mount_path = os.path.abspath(expanduser(mount_path))
        return process_mount_dataset(dataset, abs_mount_path)
    else:
        show_help(["mount"])
        return 1


def process_unmount_dataset(record_id, cleanup=False):
    try:
        records = mount_table.get_records_by_record_id(record_id)
        if len(records) == 1:
            record = records[0]
            if not cleanup and record.status == sdm_mount_table.MountRecordStatus.UNMOUNTED:
                print "Dataset is already unmounted"
                return 1

            record.status = sdm_mount_table.MountRecordStatus.UNMOUNTED

            syndicatefs.unmount(record.record_id, record.mount_path, cleanup)
            if cleanup:
                mount_table.delete_record(record.record_id)

            mount_table.save_table()
            return 0
        else:
            print "Cannot unmount dataset. There are %d mounts" % len(records)
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
        cleanup = False
        if len(argv) >= 2:
            cleanup = bool(argv[1])

        if len(mount_table.get_records_by_dataset(argv[0])) > 0:
            # dataset
            records = mount_table.get_records_by_dataset(argv[0])
            if len(records) == 1:
                return process_unmount_dataset(records[0].record_id, cleanup)
            else:
                print "Cannot unmount dataset. There are more %d mounts" % len(records)
                return 1
        elif len(mount_table.get_records_by_mount_path(argv[0])) > 0:
            # maybe path?
            records = mount_table.get_records_by_mount_path(argv[0])
            if len(records) == 1:
                return process_unmount_dataset(records[0].record_id, cleanup)
            else:
                print "Cannot unmount dataset. There are more %d mounts" % len(records)
                return 1
        elif len(mount_table.get_records_by_record_id(argv[0])) > 0:
            # maybe record_id?
            records = mount_table.get_records_by_record_id(argv[0])
            if len(records) == 1:
                return process_unmount_dataset(records[0].record_id, cleanup)
            else:
                print "Cannot unmount dataset. There are more %d mounts" % len(records)
                return 1
        else:
            print "Cannot find mount - %s" % argv[0]
            return 1
    else:
        show_help(["unmount"])
        return 1


def clean_mounts(argv):
    records = mount_table.list_records()
    for rec in records:
        if rec.status == sdm_mount_table.MountRecordStatus.UNMOUNTED:
            process_unmount_dataset(rec.record_id, True)
    return 0

def show_help(argv=None):
    if argv:
        if "list_datasets" in argv:
            karr, _, desc = COMMANDS_TABLE["list_datasets"]
            print "command : %s" % (" | ".join(karr))
            print "usage : sdm ls"
            print ""
            print desc
            return 0
        elif "show_mounts" in argv:
            karr, _, desc = COMMANDS_TABLE["show_mounts"]
            print "command : %s" % (" | ".join(karr))
            print "usage : sdm ps"
            print ""
            print desc
            return 0
        elif "mount" in argv:
            karr, _, desc = COMMANDS_TABLE["mount"]
            print "command : %s" % (" | ".join(karr))
            print "usage : sdm mount <dataset_name> [<mount_path>]"
            print ""
            print desc
            return 0
        elif "unmount" in argv:
            karr, _, desc = COMMANDS_TABLE["unmount"]
            print "command : %s" % (" | ".join(karr))
            print "usage : sdm unmount <mount_id> [<cleanup_flag>]"
            print ""
            print desc
            return 0
        elif "clean" in argv:
            karr, _, desc = COMMANDS_TABLE["clean"]
            print "command : %s" % (" | ".join(karr))
            print "usage : sdm clean"
            print ""
            print desc
            return 0
        else:
            print "Unrecognized command"
            return 1
    else:
        print "command : sdm <COMMAND> [<COMMAND_SPECIFIC_ARGS> ...]"
        print ""
        print "Available Commands"

        tbl = PrettyTable()
        tbl.field_names = ["COMMAND", "DESCRIPTION"]
        for cmd in COMMANDS:
            command, _, desc = cmd
            command_str = " | ".join(command)
            tbl.add_row([command_str, desc])

        print tbl
        print ""
        return 0


def run(command, argv):
    if command is None:
        raise ValueError("No command is given")

    command = command.lower()

    if command in COMMANDS_TABLE:
        _, func, _ = COMMANDS_TABLE[command]
        func(argv)
    else:
        raise ValueError("Unrecognized command: %s" % (command))


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    _fill_commands_table()

    if len(argv) >= 1:
        # has command part
        command = argv[0]
        oargs = argv[1:]

        try:
            run(command, oargs)
        except Exception, e:
            print >> sys.stderr, e
            traceback.print_exc()
    else:
        show_help()

if __name__ == "__main__":
    main()
