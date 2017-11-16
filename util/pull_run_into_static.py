#!/usr/bin/python3

# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tool for pulling a local copy of the JSON for a given run ,and saving the files
in the 'static' dir. This tool is intended for updating the pre-population
output of /tasks/populate-dev-data, and a change including the content
generated by this tool should also update the content in
populate_dev_data_handler.go

Example usage:
./pull_run_into_static.py \
    --reset \
    --sha=b952881825 \
    chrome-63.0-linux \
    edge-15-windows \
    firefox-57.0-linux \
    safari-10-macos
"""

import argparse
import inspect
import json
import logging
import os
import shutil
from urllib.parse import urlencode
import urllib3

here = os.path.dirname(__file__)


def main():
    args = parse_flags()  # type: argparse.Namespace

    loggingLevel = getattr(logging, args.log.upper(), None)
    logging.basicConfig(level=loggingLevel)

    # Counters for overview.
    skipped = 0
    failed = 0
    processed = 0

    sha = args.sha  # type: str

    staticFilePath = os.path.abspath(os.path.join(here, '..', 'static', sha))
    logging.info('Operating in directory %s' % (staticFilePath))

    if os.path.exists(staticFilePath) and args.reset:
        logging.warning('Removing directory and contents')
        if not args.dry:
            shutil.rmtree(staticFilePath)

    pool = urllib3.PoolManager()  # type: urllib3.PoolManager
    for platform in args.platforms:  # type: str
        encodedArgs = urlencode({'sha': sha, 'platform': platform})
        url = 'https://wpt.fyi/results?' + encodedArgs

        # type: urllib3.response.HTTPResponse
        response = pool.request('GET', url,
                                redirect=False)

        if response.status // 100 != 3:
            logging.warning(
                'Got unexpected non-redirect result %d' % (response.status))
            continue

        loadedUrl = response.headers['location']
        response = pool.request('GET', loadedUrl)

        if response.status != 200:
            logging.warning('Failed to fetch %s' % (url))
            continue
        logging.debug('Processing JSON from %s' % (url))
        tests = json.loads(response.data.decode('utf-8'))

        gzipFilenamePart = loadedUrl.split('/')[-1]
        filename = os.path.join(staticFilePath, gzipFilenamePart)

        if not os.path.exists(filename):
            write_file(response.data, filename, args.dry)

        # Let the requests rain down.
        for key in tests.keys():
            encodedArgs = urlencode(
                {'sha': sha, 'platform': platform, 'test': key[1:]})
            testUrl = 'https://wpt.fyi/results?' + encodedArgs
            try:
                filename = os.path.join(staticFilePath, platform, key[1:])
                if os.path.exists(filename):
                    skipped += 1
                    logging.info(
                        'Skipping file %s which already exists.' % (filename))
                    continue

                logging.info('Fetching %s...' % (testUrl))

                # type: urllib3.response.HTTPResponse
                response = pool.request('GET', testUrl)
                if response.status != 200:
                    failed += 1
                    logging.warning('Failed to fetch %s' % (testUrl))
                    continue

                write_file(response.data, filename, args.dry)
                processed += 1

            except IOError as e:
                logging.warning('IOError processing %s: %s' % (testUrl, e))
                failed += 1

    msg = 'Completed pull with %d files processed, %d skipped and %d failures.'
    logging.info(msg % (processed, skipped, failed))


# Create an ArgumentParser for the flags we'll expect.
def parse_flags():  # type: () -> argparse.Namespace
    # Re-use the docs above as the --help output.
    parser = argparse.ArgumentParser(description=inspect.cleandoc(__doc__))
    parser.add_argument(
        '--sha',
        default='latest',
        help='SHA[0:10] of the run to fetch')
    parser.add_argument(
        '--log',
        type=str,
        default='INFO',
        help='Log level to output')
    parser.add_argument(
        '--reset',
        dest='reset',
        action='store_true',
        help='Clears any existing /static/{SHA} directory')
    parser.add_argument(
        '--dry',
        dest='dry',
        action='store_true',
        help='Do a dry run (don\'t actually write any files)')
    parser.add_argument(
        'platforms',
        type=str,
        nargs='+',
        metavar='platform',
        help='Platforms to fetch the runs for, e.g. "safari-10.0"')
    return parser.parse_args()


# Log dir creations and writes for the given file creation, and actually do it
# when not in a dry run.
def write_file(jsonData,  # type: bytes
               filename,  # type: str
               dryRun  # type: bool
               ):
    filepath = os.path.dirname(filename)
    if not os.path.exists(filepath):
        logging.debug('Creating directory %s' % (filepath))
        if not dryRun:
            os.makedirs(filepath)

    logging.info('Writing content to %s' % (filename))
    if not dryRun:
        with open(filename, 'wb') as file:
            file.write(jsonData)


if __name__ == '__main__':
    main()
