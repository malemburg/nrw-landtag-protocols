import os
import re
import bs4


### Globals

# Interesting classes
INTERESTING_CLASSES = ['TopThema', 'aStandardabsatz', 'bBeginn',
    'eZitat-Einrckung', 'fZwischenfrage', 'kKlammer', 'pPunktgliederung',
    'rRednerkopf', 'sSchluss', 't1AbsatznachTOP', 'zZitat']

# RE for find_start()
BEGIN_RE = re.compile('Beginn:')

# REs for get_speaker_name()
SPEAKER_NAME_RE = re.compile('([\w\-. ]+)(?:\*\))? ?:')
SPEAKER_PARTY_NAME_RE = re.compile('([\w\-. ]+)(?:\*\))? ?(\(\w+\)|\[\w+\]) ?:')
MINISTER_NAME_RE = re.compile('([\w\-. ]+) ?, ?(Minister[\w\-., ]+):')

# RE for clean_text()
RE_CLEAN_TEXT = re.compile('\s+')

### Errors

class ParserError(TypeError):
    pass

###

def create_parser(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        soup = bs4.BeautifulSoup(f, 'lxml')
    return soup

def find_all_classes(soup, tag_name='p', initial_set=None):
    s = initial_set or set()
    for tag in soup.find_all(tag_name):
        s.update(tag['class'])
    return s

def find_classes_used_in_dir(dir='protocols/'):
    classes = set()
    for filename in os.listdir(dir):
        if not filename.endswith('.html'):
            continue
        soup = create_parser(os.path.join(dir, filename))
        classes = find_all_classes(soup, initial_set=classes)
    return classes

def bs_debug(tag):
    for i, sibling in tag.find_next_elements():
        print (f'{i}: {sibling}')
        if i >= 10:
            break

def clean_text(text):

    """ Remove all extra whitespace from text.
    
    """
    if text is None:
        return None
    return RE_CLEAN_TEXT.sub(' ', text).strip()

def find_start(soup):

    """ Find the start node in the protocol

        Returns None in case this cannot be found.
    
    """
    # First try: look for correct class
    protocol_start = soup.find('p', class_='bBeginn')
    if protocol_start is not None:
        beginn_text = protocol_start.find(text=BEGIN_RE)
        if beginn_text is not None:
            return protocol_start
        # Can't use this node
    
    # Second try: look for text
    protocol_start = soup.find(text=BEGIN_RE)
    if protocol_start is None:
        # Could not find start, give up
        return None
    # Go back up to find the parent p tag; this be not find anything
    protocol_start = protocol_start.find_parent('p')
    return protocol_start    
   
def parse_speaker_intro(speaker_tag):

    """ Parse the speaker_tag from the protocol and return a dictionary
        with the following entries:
    
        name: Name of the speaker
        party: party of the speaker, if given, None otherwise
        ministry: ministry, the speaker is minister of, None otherwise
        speech: Text of speech in this paragraph, if any, or None
    
    """
    # Get the speaker tag text, without tags
    text = clean_text(speaker_tag.get_text())
    
    # Match speaker declarations
    name = None
    party = None
    ministry = None
    speech = None
    match = SPEAKER_NAME_RE.match(text)
    if match is not None:
        name = match.group(1)
        speech = text[match.end():]
    match = SPEAKER_PARTY_NAME_RE.match(text)
    if match is not None:
        name = match.group(1)
        party = match.group(2)[1:-1]
        speech = text[match.end():]
    match = MINISTER_NAME_RE.match(text)
    if match is not None:
        name = match.group(1)
        ministry = match.group(2)
        speech = text[match.end():]

    if name is None:
        raise ParserError('Could not match speaker name: %r' % text)

    # Return clean text fields
    return dict(
        name=clean_text(name),
        party=clean_text(party),
        ministry=clean_text(ministry),
        speech=clean_text(speech))

def parse_protocol(soup):

    """ Parse the protocol HTML soup
    
    """
    data = []
    
    # Find start of protocol in HTML
    protocol_start = find_start(soup)
    if not protocol_start:
        raise ParserError('Could not find start of protocol')
    current_speaker = protocol_start.find_next_sibling('p', class_='rRednerkopf')

    # Iterate over speaker sections
    parsing_session = True
    while parsing_session:
        speaker_intro = parse_speaker_intro(current_speaker)
        print (f'Working on speaker section {speaker_intro}')
        for tag in current_speaker.find_next_siblings('p'):
            #print (f'Found tag {tag.get("class")}')
            p_class = tag.get('class')
            if 'rRednerkopf' in p_class:
                # Start of new speaker section
                current_speaker = tag
                break
            if 'sSchluss' in p_class:
                # End of protocol
                parsing_session = False
                break
        else:
            break

###

if __name__ == '__main__':
    if 0:
        classes = find_classes_used_in_dir('protocols/')
        print (sorted(classes))
    soup = create_parser('protocols/protocol-17-31.html')
    tag = parse_protocol(soup)
