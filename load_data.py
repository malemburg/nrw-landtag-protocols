#!/usr/bin/env python3
""" Load NRW Landtag protocols

    Saves them as HTML files.

"""
import os
import urllib.parse
import requests
import json

### Globals

BASE_URL = 'https://www.landtag.nrw.de/portal/WWW/dokumentenarchiv/Dokument/'
PROTOCOL_DIR = 'protocols'
PROTOCOL_FILE_TEMPLATE = 'protocol-%i-%i.%s'

###

def protocol_url(period, index, extension='html'):

    """ Create protocol URL for the protocol index in the given period.

        extension determines the document type to download.  Default is to
        download HTML files.
    
    """
    return urllib.parse.urljoin(BASE_URL, f'MMP{period}-{index}.{extension}')

def download_period(period, max_document=1000, extensions=('html', 'pdf', 'docx', 'doc')):

    """ Download all protocol documents in the given period.
    
        At most max_document protocols are downloaded.  All extensions are
        tried per default, giving a complete picture of the available
        formats, but it's possible to limit this to a subset.
    
    """
    l = []
    for extension in extensions:
        print (f'Downloading {extension} files for period {period}')
        for i in range(1, max_document):
            url = protocol_url(period, i, extension)
            print (f'Working on protocol {i}')
            response = requests.get(url)
            if response.status_code != 200:
                break
            filename = os.path.join(
                PROTOCOL_DIR,
                PROTOCOL_FILE_TEMPLATE % (period, i, extension))
            with open(filename, 'wb') as f:
                f.write(response.content)
            l.append({
                'filename': filename,
                'period': period,
                'index': i,
                'url': url,
                })
    return l

###

if __name__ == '__main__':
    data = download_period(17, 100)
    json.dump(data, open(os.path.join(PROTOCOL_DIR, 
                                      'period-17.json'),
                         'w', encoding='utf-8'))

