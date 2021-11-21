import os
import re
import json
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
   
def parse_speaker_intro(speaker_tag, meta_data=None):

    """ Parse the speaker_tag from the protocol and return a dictionary
        with the following entries:
    
        speaker_name: Name of the speaker
        speaker_party: party of the speaker, if given, None otherwise
        speaker_ministry: ministry, the speaker is minister of, None otherwise
        speaker_role: president, vice-president, minister, or None
        speech: Text of speech in this paragraph, if any, or None

        meta_data is added to the dictionary, if given.
    
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

    # Parse role and remove from name
    lower_name = name.lower()
    if lower_name.startswith('präsident'):
        speaker_role = 'president'
        name = name.split(maxsplit=1)[1]
    elif lower_name.startswith('vizepräsident'):
        speaker_role = 'vice-president'
        name = name.split(maxsplit=1)[1]
    elif lower_name.startswith('minister'):
        speaker_role = 'minister'
        name = name.split(maxsplit=1)[1]
    elif ministry is not None:
        speaker_role = 'minister'
    else:
        speaker_role = None

    # Return paragraph data
    d = dict(
        speaker_name=clean_text(name),
        speaker_party=clean_text(party),
        speaker_ministry=clean_text(ministry),
        speaker_role=speaker_role,
        speech=clean_text(speech))
    if meta_data is not None:
        d.update(meta_data)
    return d

def parse_speech_paragraph(speech_tag, meta_data=None):
        
    # Get the speech tag text, without tags
    text = clean_text(speech_tag.get_text())
    
    # Return paragraph data
    d = dict(speech=clean_text(text))
    if meta_data is not None:
        d.update(meta_data)
    return d

def parse_annotation_paragraph(speech_tag, meta_data=None):
        
    # Get the speech tag text, without tags
    text = clean_text(speech_tag.get_text())
    
    # Remove parens
    text = text.lstrip('(')
    text = text.rstrip(')')
    
    # Return paragraph data
    d = dict(annotation=clean_text(text))
    if meta_data is not None:
        d.update(meta_data)
    return d

def parse_citation_paragraph(speech_tag, meta_data=None):
        
    # Get the speech tag text, without tags
    text = clean_text(speech_tag.get_text())

    # Remove parens
    text = text.lstrip('„"\'')
    text = text.rstrip('“"\'')
    
    # Return paragraph data
    d = dict(citation=clean_text(text))
    if meta_data is not None:
        d.update(meta_data)
    return d

def parse_protocol(soup):

    """ Parse the protocol HTML soup
    
    """
    # Find start of protocol in HTML
    protocol_start = find_start(soup)
    if not protocol_start:
        raise ParserError('Could not find start of protocol')
    current_speaker = protocol_start.find_next_sibling('p', class_='rRednerkopf')

    # Iterate over speaker sections
    parsing_session = True
    paragraphs = []
    protocol_meta_data = {}
    while parsing_session:
        # Start of a new speaker section
        paragraph = parse_speaker_intro(current_speaker, protocol_meta_data)
        section_meta_data = {
            'speaker_name': paragraph['speaker_name'],
            'speaker_party': paragraph['speaker_party'],
            'speaker_ministry': paragraph['speaker_ministry'],
            'speaker_role': paragraph['speaker_role'],
        }
        section_meta_data.update(protocol_meta_data)
        paragraph['html_class'] = ', '.join(current_speaker.get('class'))
        paragraphs.append(paragraph)
        print (f'Working on section {section_meta_data}')
        
        # Loop over next paragraphs
        for tag in current_speaker.find_next_siblings('p'):
            p_class = set(tag.get('class'))
            #print (f'Found tag {p_class}')
            if set(('rRednerkopf', 'fZwischenfrage')) & p_class:
                # Start of new speaker section
                current_speaker = tag
                break
            if 'sSchluss' in p_class:
                # End of protocol
                parsing_session = False
                break
                
            # Parse paragraph
            if set(('aStandardabsatz', 't-N-ONummerierungohneSeitenzahl',
                    't-D-SAntragetcmitSeitenzahl', 't-D-OAntragetcohneSeitenzahl',
                    't-I-VInVerbindungmit', 't-O-NOhneNummerierungohneSeitenzahl',
                    't1AbsatznachTOP', 't-M-berschriftMndlicheAnfrage',
                    't-M-TTextMndlicheAnfrage',
                    )) & p_class:
                # Standard paragraph
                paragraph = parse_speech_paragraph(tag, meta_data=section_meta_data)
                print (f'  Found speech paragraph {paragraph}')
            elif 'kKlammer' in p_class:
                # Annotation paragraph
                paragraph = parse_annotation_paragraph(tag, meta_data=section_meta_data)
                print (f'    Found annotation paragraph {paragraph}')
            elif 'zZitat' in p_class:
                # Citation paragraph
                paragraph = parse_citation_paragraph(tag, meta_data=section_meta_data)
                print (f'    Found citation paragraph {paragraph}')
            else:
                raise ParserError(f'Could not parse section {p_class}')
            
            # Add paragraph
            paragraph['html_class'] = ', '.join(p_class)
            paragraphs.append(paragraph)
            
        else:
            break

    return paragraphs

###

if __name__ == '__main__':
    if 0:
        classes = find_classes_used_in_dir('protocols/')
        print (sorted(classes))
    if 0:
        soup = create_parser('protocols/protocol-17-31.html')
        tag = parse_protocol(soup)
    filename = 'protocols/protocol-17-31.html'
    soup = create_parser(filename)
    data = parse_protocol(soup)
    json.dump(data, open(filename, 'w', encoding='utf-8'))
