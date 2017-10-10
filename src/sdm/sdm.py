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
import logging
import config as sdm_config
import mount_table as sdm_mount_table
import repository as sdm_repository
import backends as sdm_backends
import abstract_backend as sdm_absbackends
import util as sdm_util

from prettytable import PrettyTable

SDM_CONFIG_DIR = "~/.sdm"
CONFIG_PATH = ""
MOUNT_TABLE_PATH = ""

config = None
mount_table = None
repository = None
backend = None


OPTIONS_TABLE = {}
COMMANDS = []
COMMANDS_TABLE = {}


def fill_options_table():
    OPTIONS_TABLE["log"] = getattr(logging, "WARNING", None)
    OPTIONS_TABLE["config"] = SDM_CONFIG_DIR


def fill_commands_table():
    COMMANDS.append((["list_datasets", "ls", "list"], list_datasets, "list available datasets"))
    COMMANDS.append((["show_mounts", "ps", "status"], show_mounts, "show mount status"))
    COMMANDS.append((["mount", "mnt"], mount_dataset, "mount a dataset"))
    COMMANDS.append((["mmount", "mmnt"], mount_multi_dataset, "mount multi-datasets"))
    COMMANDS.append((["unmount", "umount", "umnt"], unmount_dataset, "unmount a dataset"))
    COMMANDS.append((["munmount", "mumount", "mumnt"], unmount_multi_dataset, "unmount multi-dataset"))
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

        sdm_util.print_message(tbl)

        if cnt == 0:
            sdm_util.print_message("No available dataset")
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
        tbl.field_names = ["MOUNT_ID", "DATASET", "MOUNT_PATH", "BACKEND", "STATUS"]

        need_sync = False
        for rec in records:
            # detect out-of-sync record
            bimpl = sdm_backends.Backends.get_backend_instance(rec.backend, config.get_backend_config(rec.backend))

            is_mounted = bimpl.check_mount(rec.record_id, rec.dataset, rec.mount_path)
            is_status_mounted = rec.status == sdm_mount_table.MountRecordStatus.MOUNTED

            if is_mounted != is_status_mounted:
                if is_mounted:
                    rec.status = sdm_mount_table.MountRecordStatus.MOUNTED
                else:
                    rec.status = sdm_mount_table.MountRecordStatus.UNMOUNTED
                need_sync = True

            cnt += 1
            tbl.add_row([rec.record_id[:12], rec.dataset, rec.mount_path, rec.backend, rec.status])

        sdm_util.print_message(tbl)

        if need_sync:
            mount_table.save_table(MOUNT_TABLE_PATH)

        if cnt == 0:
            sdm_util.print_message("No mounts")
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
            sdm_util.print_message("Cannot find user accounts to access the dataset - %s" % (dataset))
            return 1

        try:
            bimpl = sdm_backends.Backends.get_backend_instance(backend, config.get_backend_config(backend))
            if not bimpl.is_legal_mount_path(mount_path):
                sdm_util.print_message("Cannot mount dataset to the given mount path for wrong mount path - %s" % (mount_path))
                return 1

            # check existance
            records = mount_table.get_records_by_mount_path(mount_path)
            for rec in records:
                if rec.dataset == dataset and rec.status == sdm_mount_table.MountRecordStatus.UNMOUNTED:
                    # same dataset but unmounted
                    # delete and overwrite
                    mount_table.delete_record(rec.record_id)

            mount_record = mount_table.add_record(dataset, mount_path, backend, sdm_mount_table.MountRecordStatus.UNMOUNTED)
            mount_table.save_table(MOUNT_TABLE_PATH)

            bimpl.mount(
                mount_record.record_id,
                entry.ms_host,
                entry.dataset,
                username,
                user_pkey,
                entry.gateway,
                mount_path
            )
            mount_record.status = sdm_mount_table.MountRecordStatus.MOUNTED
            mount_table.save_table(MOUNT_TABLE_PATH)
            return 0
        except sdm_mount_table.MountTableException, e:
            sdm_util.print_message("Cannot mount dataset - %s to  %s" % (dataset, mount_path), True, sdm_util.LogLevel.ERROR)
            sdm_util.print_message(e, True, sdm_util.LogLevel.ERROR)
            return 1
        except sdm_absbackends.AbstractBackendException, e:
            sdm_util.print_message("Cannot mount dataset - %s to  %s" % (dataset, mount_path), True, sdm_util.LogLevel.ERROR)
            sdm_util.print_message(e, True, sdm_util.LogLevel.ERROR)
            return 1
    else:
        sdm_util.print_message("Dataset not found - %s" % dataset)
        return 1


def mount_dataset(argv):
    # args
    # 1. dataset name
    # 2. mount_path (optional)
    if len(argv) >= 1:
        dataset = argv[0].strip().lower()

        try:
            bimpl = sdm_backends.Backends.get_backend_instance(backend, config.get_backend_config(backend))
            mount_path = bimpl.make_default_mount_path(dataset, config.get_backend_config(backend).default_mount_path)

            if len(argv) >= 2 and len(argv[1].strip()) != 0:
                mount_path = argv[1].strip()

            abs_mount_path = sdm_util.get_abs_path(mount_path)
            return process_mount_dataset(dataset, abs_mount_path)
        except sdm_absbackends.AbstractBackendException, e:
            sdm_util.print_message("Cannot mount dataset - %s" % dataset, True, sdm_util.LogLevel.ERROR)
            sdm_util.print_message(e, True, sdm_util.LogLevel.ERROR)
            return 1
    else:
        show_help(["mount"])
        return 1


def mount_multi_dataset(argv):
    # args
    # 1. dataset name
    if len(argv) >= 1:
        try:
            bimpl = sdm_backends.Backends.get_backend_instance(backend, config.get_backend_config(backend))

            for d in argv:
                dataset = d.strip().lower()
                mount_path = bimpl.make_default_mount_path(dataset, config.get_backend_config(backend).default_mount_path)
                abs_mount_path = sdm_util.get_abs_path(mount_path)
                res = process_mount_dataset(dataset, abs_mount_path)
                if res > 0:
                    return res
            return 0
        except sdm_absbackends.AbstractBackendException, e:
            sdm_util.print_message("Cannot mount dataset - %s" % dataset, True, sdm_util.LogLevel.ERROR)
            sdm_util.print_message(e, True, sdm_util.LogLevel.ERROR)
            return 1
    else:
        show_help(["mmount"])
        return 1


def process_unmount_dataset(record_id, cleanup=False):
    try:
        records = mount_table.get_records_by_record_id(record_id)
        if len(records) == 1:
            record = records[0]
            if not cleanup and record.status == sdm_mount_table.MountRecordStatus.UNMOUNTED:
                sdm_util.print_message("Dataset is already unmounted")
                return 1

            bimpl = sdm_backends.Backends.get_backend_instance(record.backend, config.get_backend_config(record.backend))
            record.status = sdm_mount_table.MountRecordStatus.UNMOUNTED

            bimpl.unmount(record.record_id, record.dataset, record.mount_path, cleanup)
            if cleanup:
                mount_table.delete_record(record.record_id)

            mount_table.save_table(MOUNT_TABLE_PATH)
            return 0
        else:
            sdm_util.print_message("Cannot unmount. There are %d mounts" % len(records))
            return 1
    except sdm_mount_table.MountTableException, e:
        sdm_util.print_message("Cannot unmount - %s" % (record_id), True, sdm_util.LogLevel.ERROR)
        sdm_util.print_message(e, True, sdm_util.LogLevel.ERROR)
        return 1
    except sdm_absbackends.AbstractBackendException, e:
        sdm_util.print_message("Cannot unmount - %s" % (record_id), True, sdm_util.LogLevel.ERROR)
        sdm_util.print_message(e, True, sdm_util.LogLevel.ERROR)
        return 1


def unmount_dataset(argv):
    # args
    # 1. dataset name OR mount_path
    if len(argv) >= 1:
        cleanup = False
        if len(argv) >= 2:
            cleanup = bool(argv[1])

        arg = argv[0]

        # dataset?
        records = mount_table.get_records_by_dataset(arg)
        if len(records) > 0:
            if len(records) == 1:
                return process_unmount_dataset(records[0].record_id, cleanup)
            else:
                sdm_util.print_message("Cannot unmount dataset. There are more %d mounts" % len(records))
                return 1

        # record_id?
        records = mount_table.get_records_by_record_id(arg)
        if len(records) > 0:
            if len(records) == 1:
                return process_unmount_dataset(records[0].record_id, cleanup)
            else:
                sdm_util.print_message("Cannot unmount dataset. There are more %d mounts" % len(records))
                return 1

        # path?
        path = sdm_util.get_abs_path(arg)
        records = mount_table.get_records_by_mount_path(path)
        if len(records) > 0:
            if len(records) == 1:
                return process_unmount_dataset(records[0].record_id, cleanup)
            else:
                sdm_util.print_message("Cannot unmount dataset. There are more %d mounts" % len(records))
                return 1

        sdm_util.print_message("Cannot find mount - %s" % argv[0])
        return 1
    else:
        show_help(["unmount"])
        return 1


def unmount_multi_dataset(argv):
    # args
    # 1. dataset name OR mount_path
    if len(argv) >= 1:
        cleanup = False
        res = 0
        for arg in argv:
            # dataset?
            records = mount_table.get_records_by_dataset(arg)
            if len(records) > 0:
                if len(records) == 1:
                    res |= process_unmount_dataset(records[0].record_id, cleanup)
                    continue
                else:
                    sdm_util.print_message("Cannot unmount dataset. There are more %d mounts" % len(records))
                    res |= 1
                    continue

            # record_id?
            records = mount_table.get_records_by_record_id(arg)
            if len(records) > 0:
                if len(records) == 1:
                    res |= process_unmount_dataset(records[0].record_id, cleanup)
                    continue
                else:
                    sdm_util.print_message("Cannot unmount dataset. There are more %d mounts" % len(records))
                    res |= 1
                    continue

            # path?
            path = sdm_util.get_abs_path(arg)
            records = mount_table.get_records_by_mount_path(path)
            if len(records) > 0:
                if len(records) == 1:
                    res |= process_unmount_dataset(records[0].record_id, cleanup)
                    continue
                else:
                    sdm_util.print_message("Cannot unmount dataset. There are more %d mounts" % len(records))
                    res |= 1
                    continue

            sdm_util.print_message("Cannot find mount - %s" % arg)
            res |= 1
        return res
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
            sdm_util.print_message("command : %s" % (" | ".join(karr)))
            sdm_util.print_message("usage : sdm ls")
            sdm_util.print_message("")
            sdm_util.print_message(desc)
            return 0
        elif "show_mounts" in argv:
            karr, _, desc = COMMANDS_TABLE["show_mounts"]
            sdm_util.print_message("command : %s" % (" | ".join(karr)))
            sdm_util.print_message("usage : sdm ps")
            sdm_util.print_message("")
            sdm_util.print_message(desc)
            return 0
        elif "mount" in argv:
            karr, _, desc = COMMANDS_TABLE["mount"]
            sdm_util.print_message("command : %s" % (" | ".join(karr)))
            sdm_util.print_message("usage : sdm mount <dataset_name> [<mount_path>]")
            sdm_util.print_message("")
            sdm_util.print_message(desc)
            return 0
        elif "mmount" in argv:
            karr, _, desc = COMMANDS_TABLE["mmount"]
            sdm_util.print_message("command : %s" % (" | ".join(karr)))
            sdm_util.print_message("usage : sdm mmount <dataset_name> [<dataset_name> ...]")
            sdm_util.print_message("")
            sdm_util.print_message(desc)
            return 0
        elif "unmount" in argv:
            karr, _, desc = COMMANDS_TABLE["unmount"]
            sdm_util.print_message("command : %s" % (" | ".join(karr)))
            sdm_util.print_message("usage : sdm unmount <mount_id> [<cleanup_flag>]")
            sdm_util.print_message("")
            sdm_util.print_message(desc)
            return 0
        elif "munmount" in argv:
            karr, _, desc = COMMANDS_TABLE["munmount"]
            sdm_util.print_message("command : %s" % (" | ".join(karr)))
            sdm_util.print_message("usage : sdm munmount <mount_id> [<mount_id> ...]")
            sdm_util.print_message("")
            sdm_util.print_message(desc)
            return 0
        elif "clean" in argv:
            karr, _, desc = COMMANDS_TABLE["clean"]
            sdm_util.print_message("command : %s" % (" | ".join(karr)))
            sdm_util.print_message("usage : sdm clean")
            sdm_util.print_message("")
            sdm_util.print_message(desc)
            return 0
        else:
            sdm_util.print_message("Unrecognized command")
            return 1
    else:
        sdm_util.print_message("command : sdm <COMMAND> [<COMMAND_SPECIFIC_ARGS> ...]")
        sdm_util.print_message("")
        sdm_util.print_message("Available Commands")

        tbl = PrettyTable()
        tbl.field_names = ["COMMAND", "DESCRIPTION"]
        for cmd in COMMANDS:
            command, _, desc = cmd
            command_str = " | ".join(command)
            tbl.add_row([command_str, desc])

        sdm_util.print_message(tbl)
        sdm_util.print_message("")
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


def set_option(k, v="True"):
    if k == "log":
        OPTIONS_TABLE[k] = getattr(logging, v.upper(), None)
    elif k == "backend":
        OPTIONS_TABLE[k] = sdm_backends.Backends.get_backend_name(v)
    elif k == "config":
        OPTIONS_TABLE[k] = sdm_util.get_abs_path(v)


def extract_options(argv):
    new_argv = []
    for arg in argv:
        if arg.startswith("--"):
            # extract
            p = arg[2:]
            if "=" in p:
                pa = p.split("=")
                k = pa[0].lower()
                v = pa[1]
                set_option(k, v)
            else:
                set_option(p)
        else:
            new_argv.append(arg)

    return new_argv


def process_options():
    # do log first
    for k in OPTIONS_TABLE:
        if k == "log":
            numeric_level = OPTIONS_TABLE[k]
            if not isinstance(numeric_level, int):
                raise ValueError("Invalid log level: %s" % numeric_level)
            logging.basicConfig(level=numeric_level)
            sdm_util.log_message("Set log level to %s" % numeric_level)

    # defaults
    for k in OPTIONS_TABLE:
        if k == "config":
            _config_root = OPTIONS_TABLE[k]
            sdm_util.log_message("Set config root to %s" % _config_root)

            ABS_SDM_CONFIG_DIR = sdm_util.get_abs_path(_config_root)
            global CONFIG_PATH
            CONFIG_PATH = "%s/sdm.conf" % ABS_SDM_CONFIG_DIR
            global MOUNT_TABLE_PATH
            MOUNT_TABLE_PATH = "%s/sdm_mtab" % ABS_SDM_CONFIG_DIR
            global config
            config = sdm_config.Config(CONFIG_PATH)
            global mount_table
            mount_table = sdm_mount_table.MountTable(MOUNT_TABLE_PATH)
            global repository
            repository = sdm_repository.Repository(config.repo_url)
            global backend
            backend = config.default_backend

    for k in OPTIONS_TABLE:
        if k == "backend":
            _backend = OPTIONS_TABLE[k]
            sdm_util.log_message("Set backend to %s" % _backend)

            global backend
            backend = _backend


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    fill_options_table()
    fill_commands_table()

    argv = extract_options(argv)
    process_options()

    if len(argv) >= 1:
        # has command part
        command = argv[0]
        oargs = argv[1:]

        try:
            run(command, oargs)
        except Exception, e:
            sdm_util.print_message(e, True, sdm_util.LogLevel.ERROR)
            traceback.print_exc()
    else:
        show_help()

if __name__ == "__main__":
    main()
