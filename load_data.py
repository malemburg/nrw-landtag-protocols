#!/usr/bin/env python3
"""
    Load NRW Landtag protocols

    Saves them as HTML, PDF and Word files.

"""
import os
import urllib.parse
import requests
import json

from settings import (
    BASE_URL,
    PROTOCOL_DIR,
    PROTOCOL_FILE_TEMPLATE,
    PERIOD_FILE_TEMPLATE,
    MAX_FAILURES,
    )

### Globals

# Verbosity
verbose = 0

###

def protocol_url(period, index, extension='html'):

    """ Create protocol URL for the protocol index in the given period.

        extension determines the document type to download.  Default is to
        download HTML files.

    """
    return urllib.parse.urljoin(BASE_URL, f'MMP{period}-{index}.{extension}')

def load_period_data(period):

    """ Load period data JSON file

        If the file does not exist and empty dictionary is returned.
    
    """
    filename = os.path.join(PROTOCOL_DIR, PERIOD_FILE_TEMPLATE % period)
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_period_data(period, data):

    """ Save the period data to a JSON file
    
    """
    filename = os.path.join(PROTOCOL_DIR, PERIOD_FILE_TEMPLATE % period)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f)

def download_period(period, max_document=300,
                    data=None, extensions=('html', 'pdf', 'docx', 'doc')):

    """ Download all protocol documents in the given period.

        At most max_document protocols are downloaded.  All extensions are
        tried per default, giving a complete picture of the available
        formats, but it's possible to limit this to a subset.

        Returns the downloaded data as dictionary and updates data
        parameter dictionary in-place, if given.

    """
    if data is None:
        data = {}
    for extension in extensions:
        print (f'Downloading {extension} files for period {period}')
        failures = 0
        for i in range(1, max_document):
            filename = os.path.join(
                PROTOCOL_DIR,
                PROTOCOL_FILE_TEMPLATE % (period, i, extension))
            if os.path.exists(filename) and filename in data:
                # No need to download the file again
                continue
            url = protocol_url(period, i, extension)
            if verbose:
                print (f'Working on protocol {i}')
            response = requests.get(url, allow_redirects=True)
            if response.status_code != 200:
                failures += 1
                if failures == 1 or verbose:
                    print (f' Could not download protocol {url}: '
                           f'{response.status_code}')
                if failures > MAX_FAILURES:
                    print (f' No additional files found.')
                    break
                continue
            else:
                failures = 0
            with open(filename, 'wb') as f:
                f.write(response.content)
            data[filename] = {
                'period': period,
                'index': i,
                'url': url,
                }
    return data

def main():

    """ Command line interface: 
    
        load_data.py <period> [<max_document>]
    
        Loads all documents in the given period, up to index max_document.
    
    """
    period = int(sys.argv[1])
    if len(sys.argv) > 2:
        max_document = int(sys.argv[2])
    else:
        max_document = 300
    data = load_period_data(period)
    data = download_period(period, max_document, data=data)
    save_period_data(period, data)

###

if __name__ == '__main__':
    main()
