""" Global settings used by the parsers

"""
import os

# Base URL to use for fetching data
BASE_URL = 'https://www.landtag.nrw.de/portal/WWW/dokumentenarchiv/Dokument/'

# Protocol storage
PROTOCOL_DIR = 'protocols'
PROTOCOL_FILE_TEMPLATE = 'protocol-%i-%i.%s'

# Period download data
PERIOD_FILE_TEMPLATE = 'period-%i.json'

# Max. number of download failures
MAX_FAILURES = 10

### OpenSearch

# Hosts to connect to
OPENSEARCH_HOSTS = [
    {'host': 'localhost', 'port': 9200},
]

# Login for OS in the format userid:password
OPENSEARCH_AUTH = os.environ.get('OPENSEARCH_AUTH', 'admin:admin')
