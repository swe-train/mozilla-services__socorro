#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Given a set of crash report ids via a file and a list of fields to remove, removes the
fields from the raw crash file in storage and the document in Elasticsearch.

Usage::

    python bin/remove_field.py CRASHIDSFILE FIELD [FIELD...]

File should be a set of lines of the form:

    {"crashid": CRASHID, "index": INDEX, ...}

Lines prefixed with "#" are ignored.

"""

import concurrent.futures
from functools import partial
import json
import logging
import os

from botocore.client import ClientError
import click
from elasticsearch.exceptions import ConnectionError
from elasticsearch_dsl import Search
from more_itertools import chunked

from socorro import settings
from socorro.external.boto.crashstorage import build_keys, dict_to_str
from socorro.libclass import build_instance_from_settings
from socorro.lib.util import retry


# Number of seconds until we decide a worker has stalled
WORKER_TIMEOUT = 15 * 60

# Number of crashids to hand to a worker to process in a single batch
CHUNK_SIZE = 1000


logger = logging.getLogger(__name__)


def get_storage_crashstorage():
    """Return a crash storage instance."""
    return build_instance_from_settings(settings.CRASH_DESTINATIONS["storage"])


def get_es_crashstorage():
    """Return an Elasticsearch crash storage instance."""
    return build_instance_from_settings(settings.CRASH_DESTINATIONS["es"])


def crashid_generator(fn):
    """Lazily yield crash ids."""
    with open(fn) as fp:
        for line in fp:
            line = line.strip()
            if line.startswith("#"):
                continue
            yield json.loads(line)


def wait_times_access():
    """Return generator for wait times between failed load/save attempts."""
    yield from [5, 5, 5, 5, 5]


@retry(
    retryable_exceptions=[ClientError],
    wait_time_generator=wait_times_access,
    module_logger=logger,
)
def fix_data_in_storage(fields, storage_crashstorage, crash_data):
    """Fix data in raw_crash file in storage."""
    crashid = crash_data["crashid"]

    # Iterate through the available keys until we find one we like.
    paths = build_keys("raw_crash", crashid)
    path = None
    for possible_path in paths:
        try:
            raw_crash_as_string = storage_crashstorage.load_file(possible_path)
            path = possible_path
            break
        except storage_crashstorage.KeyNotFound:
            continue

    if not path:
        # We're in a weird situation where we know there's a raw crash, but we can't
        # find it with the key options.
        raise Exception(f"raw crash not available at any keys: {paths}")

    data = json.loads(raw_crash_as_string)
    should_save = False
    for field in fields:
        if field in data:
            del data[field]
            should_save = True

    if should_save:
        storage_crashstorage.save_file(
            path=path,
            data=dict_to_str(data).encode("utf-8"),
        )
        click.echo("# storage: fixed raw crash")
    else:
        click.echo("# storage: raw crash was fine")


@retry(
    retryable_exceptions=[ConnectionError],
    wait_time_generator=wait_times_access,
    module_logger=logger,
)
def fix_data_in_es(fields, es_crashstorage, crash_data):
    """Fix document in Elasticsearch."""
    crashid = crash_data["crashid"]
    index = crash_data["index"]
    doc_type = es_crashstorage.get_doctype()

    with es_crashstorage.client() as conn:
        search = Search(using=conn, index=index, doc_type=doc_type)
        search = search.filter("term", **{"processed_crash.uuid": crashid})
        results = search.execute().to_dict()
        result = results["hits"]["hits"][0]
        index = result["_index"]
        document_id = result["_id"]
        document = result["_source"]

        should_save = False
        for field in fields:
            if field in document["raw_crash"]:
                should_save = True
                del document["raw_crash"][field]

        if should_save:
            conn.index(index=index, doc_type=doc_type, body=document, id=document_id)
            click.echo("# es: fixed document")
        else:
            click.echo("# es: document was fine")


def fix_data(crashids, fields):
    storage_crashstorage = get_storage_crashstorage()
    es_crashstorage = get_es_crashstorage()

    for crashid in crashids:
        click.echo("# working on %s" % crashid)

        # Fix the data in storage and then Elasticsearch
        try:
            fix_data_in_storage(fields, storage_crashstorage, crashid)
            fix_data_in_es(fields, es_crashstorage, crashid)
        except Exception:
            # If this throws an exception, print it out and move on. Then we'll finish
            # all the fixing for the first pass and can address the problematic crash
            # reports in a second pass.
            logger.exception("Exception thrown with %s" % crashid)


@click.command()
@click.option(
    "--parallel/--no-parallel",
    default=False,
    show_default=True,
    help="Whether to run in parallel.",
)
@click.option(
    "--max-workers",
    type=int,
    default=20,
    show_default=True,
    help="Number of processes to run in parallel.",
)
@click.argument("crashidsfile", nargs=1)
@click.argument("fields", nargs=-1, required=True)
@click.pass_context
def cmd_remove_field(ctx, parallel, max_workers, crashidsfile, fields):
    """
    Remove a field from raw crash data on storage and Elasticsearch.

    The crashidsfile is a path to a file with crash ids in it. File should be a set of
    lines of the form:

        {"crashid": CRASHID, "index": INDEX, ...}

    Lines prefixed with "#" are ignored.

    """
    if not os.path.exists(crashidsfile):
        click.echo("File %s does not exist." % crashidsfile)
        return 1

    crashids = crashid_generator(crashidsfile)
    crashids_chunked = chunked(crashids, CHUNK_SIZE)
    fix_data_with_fields = partial(fix_data, fields=fields)

    click.echo("# num workers: %s" % max_workers)
    if not parallel:
        click.echo("# Running single-process.")
        list(map(fix_data_with_fields, crashids_chunked))
    else:
        click.echo("# Running multi-process.")
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as executor:
            executor.map(fix_data_with_fields, crashids_chunked, timeout=WORKER_TIMEOUT)

    click.echo("# Done!")


if __name__ == "__main__":
    cmd_remove_field()
