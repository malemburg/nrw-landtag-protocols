""" Global settings used by the parsers

"""

# Base URL to use for fetching data
BASE_URL = 'https://www.landtag.nrw.de/portal/WWW/dokumentenarchiv/Dokument/'

# Protocol storage
PROTOCOL_DIR = 'protocols'
PROTOCOL_FILE_TEMPLATE = 'protocol-%i-%i.%s'

# Period download data
PERIOD_FILE_TEMPLATE = 'period-%i.json'

# Max. number of download failures
MAX_FAILURES = 10
