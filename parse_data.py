#!/usr/bin/env python3
"""
    Parse HTML session protocols of the NRW Landtag.

    TODO:
    - Address typo fixes (which cannot be solved using REs
    - split multiple annotations in one paragraph into separate
      paragraph entries in the data
    - try to detect annotations which do not have the correct class
    - double check the detected names; the REs may match too much text

"""
import os
import re
import json
import bs4

from settings import (
    BASE_URL,
    PROTOCOL_DIR,
    PROTOCOL_FILE_TEMPLATE,
    )

### Globals

# Verbosity
verbose = 0

# Interesting classes
INTERESTING_CLASSES = ['TopThema', 'aStandardabsatz', 'bBeginn',
    'eZitat-Einrckung', 'fZwischenfrage', 'kKlammer', 'pPunktgliederung',
    'rRednerkopf', 'sSchluss', 't1AbsatznachTOP', 'zZitat']

# REs for find_start() and find_end()
BEGIN_RE = re.compile('Beginn:|Beginn \d\d[:\.]\d\d|Seite 3427')
# "Seite 3427" - problem in 14-32
END_RE = re.compile('Schluss:|Ende:|__________')

# REs for parsing the speaker intros in parse_speaker_intro()
SPEAKER_NAME_RE = re.compile('([\w\-‑.’\' ]+)(?:\*\))? ?(?:\(\w+ [\w ]+\))? ?:', re.I)
SPEAKER_PARTY_NAME_RE = re.compile('([\w\-‑.’\' ]+)(?:\*\))? ?([\(\[]\w+[\)\]]|\w+[\)\]]|[\(\[]\w+) ?:?', re.I)
MINISTER_NAME_RE = re.compile('([\w\-‑.’\' ]+)(?:\*\))? ?,(?:\*\))? ?(\w*minister[\w\-‑.,() ]*):', re.I)
ROLE_NAME_RE = re.compile('([\w\-‑.’\' ]+)(?:\*\))? ?,(?:\*\))? ?(\w+ [\w\-‑.,() ]*):', re.I)

# Some of the errors found in texts:
# Fritz Fischer (CDU:
# Fritz Fischer SPD):
# Fritz Fischer (SPD]:

# XXX These errors cannot be parsed and will need a typo fix:
# Vizepräsidentin Angela Freimuth Es ist ...
# Ansprache des Landtagspräsidenten André Kuper ...

# Quick tests:
assert MINISTER_NAME_RE.match('Dr. N W-B, Finanzminister: Text')

# REs for parsing names in parse_speaker_intro()
PRESIDENT_RE = re.compile('((?:geschäftsführender? )?präsident(?:in)?) (.+)', re.I)
VICE_PRESIDENT_RE = re.compile('((?:geschäftsführender? )?vizepräsident(?:in)?) (.+)', re.I)
MINISTER_RE = re.compile('((?:geschäftsführender? )?minister(?:in)?) (.+)', re.I)

# RE for clean_text()
RE_CLEAN_TEXT = re.compile('[\s\xad]+')

### Errors

class ParserError(TypeError):
    pass

###

def create_parser(filename):
    # Note: Older HTML files are often encoded in Windows CP1252, not UTF-8,
    # so let BS4 figure out the encoding by looking at the start of the file
    with open(filename, 'rb') as f:
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
        begin_text = protocol_start.find(text=BEGIN_RE)
        if begin_text is not None:
            return protocol_start
        # Can't use this node
    
    # Second try: look for text
    begin_text = soup.find(text=BEGIN_RE)
    if begin_text is None:
        # Could not find start, give up
        return None
    # Go back up to find the parent p tag; this may not find anything
    protocol_start = begin_text.find_parent('p')
    return protocol_start    

def find_end(soup):

    """ Find the end node in the protocol

        Returns None in case this cannot be found.
    
    """
    # First try: look for correct class
    protocol_end = soup.find('p', class_='sSchluss')
    if protocol_end is not None:
        end_text = protocol_end.find(text=END_RE)
        if end_text is not None:
            return protocol_end
        # Can't use this node
    
    # Second try: look for text
    end_text = soup.find(text=END_RE)
    if end_text is None:
        # Could not find start, give up
        return None
    # Go back up to find the parent p tag; this may not find anything
    protocol_end =  end_text.find_parent('p')
    return protocol_end

def parse_speaker_intro(speaker_tag, meta_data=None):

    """ Parse the speaker_tag from the protocol and return a dictionary
        with the following entries:
    
        speaker_name: Name of the speaker
        speaker_party: party of the speaker, if given, None otherwise
        speaker_ministry: ministry, the speaker is minister of, None otherwise
        speaker_role: president, vice-president, minister, or None
        speaker_role_descr: role wording, or None
        speech: Text of speech in this paragraph, if any, or None

        meta_data is added to the dictionary, if given.
    
    """
    # Get the speaker tag text, without tags
    text = clean_text(speaker_tag.get_text())
    
    # Match speaker declarations
    speaker_name = None
    speaker_party = None
    speaker_ministry = None
    speaker_role = None
    speaker_role_descr = None
    speech = None
    match = SPEAKER_NAME_RE.match(text)
    if match is not None:
        speaker_name = match.group(1)
        speech = text[match.end():]
    match = SPEAKER_PARTY_NAME_RE.match(text)
    if match is not None:
        speaker_name = match.group(1)
        speaker_party = match.group(2)[1:-1]
        speech = text[match.end():]
    match = MINISTER_NAME_RE.match(text)
    if match is not None:
        speaker_name = match.group(1)
        speaker_ministry = match.group(2)
        speech = text[match.end():]
    match = ROLE_NAME_RE.match(text)
    if match is not None:
        speaker_name = match.group(1)
        speaker_role_descr = match.group(2)
        speech = text[match.end():]

    if speaker_name is None:
        raise ParserError('Could not match speaker name: %r' % text)

    # Parse role and remove from name
    match = PRESIDENT_RE.match(speaker_name)
    if match is not None:
        speaker_role = 'president'
        speaker_role_descr = match.group(1)
        speaker_name = match.group(2)
    match = VICE_PRESIDENT_RE.match(speaker_name)
    if match is not None:
        speaker_role = 'vice-president'
        speaker_role_descr = match.group(1)
        speaker_name = match.group(2)
    match = MINISTER_RE.match(speaker_name)
    if match is not None:
        speaker_role = 'minister'
        speaker_role_descr = match.group(1)
        speaker_name = match.group(2)
    if speaker_ministry is not None:
        speaker_role = 'minister'
    if speaker_role_descr is not None and speaker_role is None:
        speaker_role = 'other'

    # Return paragraph data
    d = dict(
        speaker_name=clean_text(speaker_name),
        speaker_party=clean_text(speaker_party),
        speaker_ministry=clean_text(speaker_ministry),
        speaker_role=speaker_role,
        speaker_role_descr=speaker_role_descr,
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

    # Find end of protocol in HTML
    protocol_end = find_end(soup)
    if not protocol_end:
        raise ParserError('Could not find end of protocol')

    # Scan all protocol paragraphs
    paragraphs = []
    protocol_meta_data = {}
    section_meta_data = {}
    current_speaker = None
    previous_speaker = None
    for tag in protocol_start.find_next_siblings('p'):

        # Detect end of protocol
        if tag == protocol_end:
            break
            
        # Find "Word" style class
        p_class = set(tag.get('class'))
        #print (f'Found tag {p_class}: {tag}')

        # Parse new speaker section
        if set(('rRednerkopf', 'fZwischenfrage')) & p_class:
            try:
                paragraph = parse_speaker_intro(tag, protocol_meta_data)
            except ParserError as error:
                # False speaker change
                print (f'WARNING: Speaker intro paragraph without speaker information: '
                       f'{error}')
                # Parse the speaker intro as regular paragraph instead
                text = clean_text(tag.get_text())
                if text.startswith('('):
                    p_class.add('kKlammer')
                else:
                    p_class.add('aStandardabsatz')

            else:
                # Start of a new speaker section
                section_meta_data = {
                    'speaker_name': paragraph['speaker_name'],
                    'speaker_party': paragraph['speaker_party'],
                    'speaker_ministry': paragraph['speaker_ministry'],
                    'speaker_role': paragraph['speaker_role'],
                    'speaker_role_descr': paragraph['speaker_role_descr'],
                }
                section_meta_data.update(protocol_meta_data)
                previous_speaker = current_speaker
                current_speaker = tag
                if verbose:
                    print (f'New speaker section {section_meta_data}')
                continue

        # Skip all paragraphs until the first speaker intro
        if current_speaker is None:
            if verbose > 1:
                print (f'Skipping tag, since no speaker found yet: {tag}')
            continue
                
        # Parse paragraph
        if set(('aStandardabsatz', 't-N-ONummerierungohneSeitenzahl',
                't-D-SAntragetcmitSeitenzahl', 't-D-OAntragetcohneSeitenzahl',
                't-I-VInVerbindungmit', 't-O-NOhneNummerierungohneSeitenzahl',
                't1AbsatznachTOP', 't-M-berschriftMndlicheAnfrage',
                't-M-TTextMndlicheAnfrage', 't-N-SNummerierungmitSeitenzahl',
                'pPunktgliederung', 't-M-ETextMndlicheEinrckung',
                'MsoNormal', 'aAbsatz', '1Tagesordnungsgliederung',
                '2Tagesordnungsgliederung',
                '3Tagesordnungsgliederung', 'tEinrckTagesordnung',
                'mMndlicheAnfrage',
                'pZitatPunktgliederung', 'dAntragDrucksache',
                'vVerfasserMndlichenAnfrage', 'fberschriftMndlicheAnfrage',
                'kTextMndlicheAnfrage', 'fberschriftMndlicheAnfragerage',
                'nNummerieringAufzhlung', 'eTEingerueckterTOP',
                'vinVerbindung',
                )) & p_class:
            # Standard paragraph
            paragraph = parse_speech_paragraph(tag, meta_data=section_meta_data)
            if verbose:
                print (f'  Found speech paragraph {paragraph}')
        elif set(('kKlammer', 'kKlammern', 'wVorsitzwechsel')) & p_class:
            # Annotation paragraph
            paragraph = parse_annotation_paragraph(tag, meta_data=section_meta_data)
            if verbose:
                print (f'    Found annotation paragraph {paragraph}')
        elif set(('zZitat', 'eZitat-Einrckung')) & p_class:
            # Citation paragraph
            paragraph = parse_citation_paragraph(tag, meta_data=section_meta_data)
            if verbose:
                print (f'    Found citation paragraph {paragraph}')
        else:
            raise ParserError(f'Could not parse section {p_class}: {tag}')
        
        # Add paragraph
        paragraph['html_class'] = ', '.join(p_class)
        paragraphs.append(paragraph)
        
    return paragraphs

def process_protocol(period, index):

    html_filename = os.path.join(
        PROTOCOL_DIR, 
        PROTOCOL_FILE_TEMPLATE % (period, index, 'html'))
        
    # Parse file
    soup = create_parser(html_filename)
    data = parse_protocol(soup)
    
    # Dump data as JSON
    json_filename = os.path.splitext(html_filename)[0] + '.json'
    json.dump(data, open(json_filename, 'w', encoding='utf-8'))

def main():

    period = int(sys.argv[1])
    if len(sys.argv) > 2:
        # Process just one document
        index = int(sys.argv[2])
        process_protocol(period, index)
    else:
        # Process all available documents
        from load_data import load_period_data
        data = load_period_data(period)
        for filename, protocol in sorted(data.items()):
            if os.path.splitext(filename)[1] != '.html':
                continue
            index = protocol['index']
            print ('-' * 72)
            print (f'Processing {period}-{index}: {filename}')
            process_protocol(period, index)

###

if __name__ == '__main__':
    if 0:
        classes = find_classes_used_in_dir('protocols/')
        print (sorted(classes))
    if 0:
        soup = create_parser('protocols/protocol-17-31.html')
        tag = parse_protocol(soup)
    main()
