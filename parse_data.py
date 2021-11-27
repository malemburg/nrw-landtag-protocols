#!/usr/bin/env python3
"""
    Parse HTML session protocols of the NRW Landtag.

    TODO:
    - split multiple annotations in one paragraph into separate
      paragraph entries in the data
    - double check the detected names; the REs may match too much text

    Written by Marc-Andre Lemburg, Nov 2021

"""
import sys
import os
import re
import json
import bs4

import load_data
from settings import (
    BASE_URL,
    PROTOCOL_DIR,
    PROTOCOL_FILE_TEMPLATE,
    )

### Globals

# Verbosity
verbose = 0

# Remove citation marks ?
REMOVE_CITATION_MARKS = False

# REs for find_start() and find_end()
BEGIN_RE = re.compile('Beginn:|Beginn \d\d[:\.]\d\d|Seite 3427')
# "Seite 3427" - problem in 14-32
END_RE = re.compile('Schluss:|Ende:|__________')

# REs for parsing the document date
DATE_RE = re.compile('((\d\d)\.(\d\d)\.(\d\d\d\d))')

# Page numbering filter
PAGE_RE = re.compile('Seite \d+')

# Cases where parse_speaker_intro() will not match and no logging should happen
NON_SPEAKER_INTRO_RE = re.compile(
    '[a-z\-–-„()…?]|'  # first char is lower case or continuation/bullet/etc
    # short phrases indicating non-name
    'Ich |Die |Der |Das |Dieses |Mit |Auch |Es |Wir |Ein |Eine |Hier |Meine |'
    'Bitte |Aber |Frau |Herr |Nach |Gemäß |Für |Zur |In |Ihnen |Art. |'
    'Gibt |Für |Liebe |Lieber |Da |So |Als |Jetzt |Wird |Hierzu |'
    'Dieser |Diese |Dann |Denn |'
    # longer phrases which are incorrectly assigned
    'Gesetz |Beantwortung |Zu dem |Kurz einmal |Werbesendung |'
    'Grünen fallen |Interview |Sie |Um mit |Westfalen |Frage: |'
    'Vielen Dank |Wichtiges |Erstens: |Muster ab'
    )

# REs for parsing the speaker intros in parse_speaker_intro()
NAME_DEF = '[\w\-‑.’\' ]+'
SPEAKER_NAME_RE = re.compile(
    '(' + NAME_DEF + ')'                        # name
    '(?:\*\))? ?'                               # optional *) marker
    '(?:\(\w+ [\w ]+\))? ?'                     # ignore extra text in parens
    ':', re.I)                                  # final :
SPEAKER_PARTY_NAME_RE = re.compile(
    '(' + NAME_DEF + ')'                        # name
    '(?:\*\))? ?'                               # optional *) marker
    '([\(\[]\w+[\)\]]|'                         # (party) or [party]
    #' \w+[\)\]]|' # disabling part) or party], since it often fails
    '[\(\[]\w+) ?'                              # (party or [party
    ':?', re.I)                                 # final : (sometimes omitted)
MINISTER_NAME_RE = re.compile(
    '(' + NAME_DEF + ')'
    '(?:\*\))? ?'                               # optional *) marker
    ','                                         # separating ,
    '(?:\*\))? ?'                               # optional *) marker
    '(\w*minister[\w\-‑.,() ]*)'                # *Minister*
    ':', re.I)                                  # final :
OTHER_ROLE_NAME_RE = re.compile(
    '(' + NAME_DEF + ')'                        # name
    '(?:\*\))? ?'                               # optional *) marker
    ','                                         # separating ,
    '(?:\*\))? ?'                               # optional *) marker
    '(\w*präsident[\w\-‑.,() ]*)'               # *Präsident*
    ':', re.I)                                  # final :

# Quick tests:
assert MINISTER_NAME_RE.match('Dr. N W-B, Finanzminister: Text')

# Some of the errors found in texts:
# Fritz Fischer (CDU:
# Fritz Fischer SPD):
# Fritz Fischer (SPD]:

# Remaining problem cases:
# 'Anne-José Paulsen und Dr. Wilfried Bünten' (14-107)

# Typo fixes to apply in typo_fixes(); these are applied to cleaned tag texts
TYPO_FIXES = {
    # Original string, substitution string
    'Oliver Wittke,, Minister für Bauen und Verkehr:':
        'Oliver Wittke, Minister für Bauen und Verkehr:',
    'Michael Breuer, Minister für Bundes? und Europaangelegenheiten:':
        'Michael Breuer, Minister für Bundes- und Europaangelegenheiten:',
    'Svenja Schulze, Ministerin für Innovation, Wissenschaft und Forschung ':
        'Svenja Schulze, Ministerin für Innovation, Wissenschaft und Forschung:',
    'Vizepräsidentin Angela Freimuth ': 'Vizepräsidentin Angela Freimuth: ',
    'Susana Dos Santos Herrmann': 'Susana dos Santos Herrmann',
    'Minister Uhlenberg': 'Minister Eckhard Uhlenberg',
    'Carina Gödeke': 'Carina Gödecke',
    'Carina: ': 'Vizepräsidentin Carina Gödecke: ',
    'Vizepräsidentin Carina: ': 'Vizepräsidentin Carina Gödecke: ',
    'Vizepräsidentin Carina Gödeke': 'Vizepräsidentin Carina Gödecke',
    'Brigitte D’moch-Schweren': 'Brigitte Dmoch-Schweren',
    'Eckart Uhlenberg': 'Eckhard Uhlenberg',
    'Margret Vosseler': 'Margret Voßeler',
    'Präsident André: ': 'Präsident André Kuper: ',
    'Vizepräsident Dr. Papke: ': 'Vizepräsident Dr. Gerhard Papke: ',
    # Footnote mark typos
    'Verena Schäffe*)': 'Verena Schäffer*)',
    'Horst Enge*)l (FDP):': 'Horst Engel*) (FDP):',
    'Armin Laschet*) Minister für Generationen, Familie, Frauen und Integration:':
        'Armin Laschet*), Minister für Generationen, Familie, Frauen und Integration:',
    'Wibke Brem*)': 'Wibke Brems',
    # Typos in party mentions
    'Hubertus Fehring) (CDU):': 'Hubertus Fehring (CDU):',
    'Heiko Hendriks) (CDU):': 'Heiko Hendriks (CDU):',
    'Frank Herrmann PIRATEN):': 'Frank Herrmann (PIRATEN):',
    'Sigrid Beer GRÜNE):': 'Sigrid Beer (GRÜNE):',
    'Dr. Robert Orth FDP):': 'Dr. Robert Orth (FDP):',
    'Rainer Deppe CDU):': 'Rainer Deppe (CDU):',
    'Ralf Witzel FDP):': 'Ralf Witzel (FDP):',
    'Eiskirch (SPD):': 'Thomas Eiskirch (SPD):',
}

# REs for parsing names in parse_speaker_intro()
PRESIDENT_RE = re.compile('((?:geschäftsführender? |alters|minister)?präsident(?:in)?) (.+)', re.I)
VICE_PRESIDENT_RE = re.compile('((?:geschäftsführender? (?:erster? )|minister)?vizepräsident(?:in)?) (.+)', re.I)
SPEAKER_IS_CHAIR_RE = re.compile('((?:geschäftsführender? (?:erster? ))?(?:vize)?präsident(?:in)?) (.+)', re.I)
MINISTER_RE = re.compile('((?:geschäftsführender? )?minister(?:in)?) (.+)', re.I)

# Quick tests
assert SPEAKER_IS_CHAIR_RE.match('Vizepräsidentin Carina Gödecke: ') is not None
assert SPEAKER_IS_CHAIR_RE.match('Präsident André Kuper: ') is not None

# RE for clean_text()
RE_CLEAN_TEXT = re.compile('[\s]+')

# Helper for sets of Word classes
def lowercase_set(sequence):

    """ Create a set from sequence, with all entries converted to lower case.

    """
    return set((x.lower() for x in sequence))

# Sets of paragraph classes used to parse the protocols
SPEAKER_INTRO_CLASSES = lowercase_set(('rRednerkopf', 'rRednerkopf0', 'fZwischenfrage'))
SPEECH_CLASSES = lowercase_set((
                'aStandardabsatz',
                'aAbsatz',
                # Misc other Word classes used in the texts
                't-N-ONummerierungohneSeitenzahl',
                't-D-SAntragetcmitSeitenzahl', 't-D-OAntragetcohneSeitenzahl',
                't-I-VInVerbindungmit', 't-O-NOhneNummerierungohneSeitenzahl',
                't1AbsatznachTOP', 't-M-berschriftMndlicheAnfrage',
                't-M-TTextMndlicheAnfrage', 't-N-SNummerierungmitSeitenzahl',
                'pPunktgliederung', 't-M-ETextMndlicheEinrckung',
                '1Tagesordnungsgliederung',
                '2Tagesordnungsgliederung',
                '3Tagesordnungsgliederung', 'tEinrckTagesordnung',
                'mMndlicheAnfrage',
                'pZitatPunktgliederung', 'dAntragDrucksache',
                'vVerfasserMndlichenAnfrage', 'fberschriftMndlicheAnfrage',
                'kTextMndlicheAnfrage', 'fberschriftMndlicheAnfragerage',
                'nNummerieringAufzhlung', 'eTEingerueckterTOP',
                'vinVerbindung',
                # Plain Word styles
                'MsoNormal', 'MsoListBullet',
                # Obvious mistakes
                'sSchluss',
                ))
ANNOTATION_CLASSES = lowercase_set(('kKlammer', 'kKlammern', 'wVorsitzwechsel'))
CITATION_CLASSES = lowercase_set(('zZitat', 'eZitat-Einrckung'))

# Sets of speaker_roles
CHAIR_ROLES = set(('president', 'vice-president'))

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
    # Remove soft hyphens added by Word
    text = text.replace('\xad', '')
    return RE_CLEAN_TEXT.sub(' ', text).strip()

def clean_tag_text(tag):

    """ Convert a tag to a string, with all extra whitespace removed.

    """
    if tag is None:
        return None
    # Get tag text and remove soft hyphens added by Word
    text = tag.get_text().replace('\xad', '')
    return RE_CLEAN_TEXT.sub(' ', text).strip()

def typo_fixes(text):

    """ Apply typo fixes to text and return the corrected text.

        The typos are matched against the start of the text and must
        match verbatim.

    """
    # Replace
    match = text.startswith
    for typo, fix in TYPO_FIXES.items():
        if match(typo):
            text = fix + text[len(typo):]
    return text

def protocol_meta_data(period, index, soup):

    """ Return meta data to associate with the protocol

    """
    tag = soup.find(text=DATE_RE)
    if tag is None:
        print (f'WARNING: Could not find protocol date in document')
        protocol_date = None
    else:
        match = DATE_RE.search(tag.get_text())
        _, dd, mm, yyyy = match.groups()
        protocol_date = '%s-%s-%s' % (yyyy, mm, dd)
    protocol_title = 'Landtag NRW - Plenarprotokoll %i/%i' % (period, index)
    return {
        'protocol_date': protocol_date,
        'protocol_title': protocol_title,
        'protocol_period': period,
        'protocol_index': index,
        'protocol_url': load_data.protocol_url(period, index),
    }

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

def parse_speaker_intro(speaker_tag, tag_text, meta_data=None):

    """ Parse the speaker_tag's tag_text from the protocol and return a
        dictionary with the following entries:

        - speaker_name: Name of the speaker
        - speaker_party: party of the speaker, if given, None otherwise
        - speaker_ministry: ministry, the speaker is minister of, None
          otherwise
        - speaker_role: president, vice-president, minister, or None
        - speaker_role_descr: role wording, or None
        - speaker_is_chair: True, if the speaker is currently chair of
          the session
        - speech: Text of speech in this paragraph, if any, or None

        meta_data is added to the dictionary, if given.

    """
    # Catch common errors
    if NON_SPEAKER_INTRO_RE.match(tag_text) is not None:
        raise ParserError('Paragraph is not a true speaker intro: %r' % tag_text)

    # Match speaker declarations
    speaker_name = None
    speaker_party = None
    speaker_ministry = None
    speaker_role = None
    speaker_role_descr = None
    speech = None
    match = SPEAKER_NAME_RE.match(tag_text)
    if match is not None:
        speaker_name = match.group(1)
        speech = tag_text[match.end():]
    match = SPEAKER_PARTY_NAME_RE.match(tag_text)
    if match is not None:
        speaker_name = match.group(1)
        speaker_party = match.group(2)
        speaker_party = speaker_party.strip('([]) ')
        speech = tag_text[match.end():]
    match = MINISTER_NAME_RE.match(tag_text)
    if match is not None:
        speaker_name = match.group(1)
        speaker_ministry = match.group(2)
        speech = tag_text[match.end():]
    match = OTHER_ROLE_NAME_RE.match(tag_text)
    if match is not None:
        speaker_name = match.group(1)
        speaker_role_descr = match.group(2)
        if verbose > 1:
            print (f'  Found other speaker role: {tag_text!r}')
        speech = tag_text[match.end():]

    if speaker_name is None:
        raise ParserError('Could not match speaker name: %r' % tag_text)

    # Parse role and remove from name
    full_speaker_name = speaker_name
    match = PRESIDENT_RE.match(full_speaker_name)
    if match is not None:
        speaker_role = 'president'
        speaker_role_descr = match.group(1)
        speaker_name = match.group(2)
    match = VICE_PRESIDENT_RE.match(full_speaker_name)
    if match is not None:
        speaker_role = 'vice-president'
        speaker_role_descr = match.group(1)
        speaker_name = match.group(2)
    match = MINISTER_RE.match(full_speaker_name)
    if match is not None:
        speaker_role = 'minister'
        speaker_role_descr = match.group(1)
        speaker_name = match.group(2)
    if speaker_ministry is not None:
        speaker_role = 'minister'
    if speaker_role_descr is not None and speaker_role is None:
        speaker_role = 'other'
    if (speaker_role in CHAIR_ROLES and
        SPEAKER_IS_CHAIR_RE.match(full_speaker_name) is not None):
        speaker_is_chair = True
    else:
        speaker_is_chair = False

    # Safety check
    speaker_name = clean_text(speaker_name)
    if len(speaker_name.split()) == 1:
        print (f'WARNING: Speaker name is too short: '
               f'{speaker_name} in {tag_text!r} ({speaker_tag}')

    # Return paragraph data
    d = dict(
        speaker_name=speaker_name,
        speaker_party=clean_text(speaker_party),
        speaker_ministry=clean_text(speaker_ministry),
        speaker_role=speaker_role,
        speaker_role_descr=speaker_role_descr,
        speaker_is_chair=speaker_is_chair,
        speech=clean_text(speech))
    if meta_data is not None:
        d.update(meta_data)
    return d

def parse_speech_paragraph(speech_tag, tag_text, meta_data=None):

    # Return paragraph data
    d = dict(speech=tag_text)
    if meta_data is not None:
        d.update(meta_data)
    return d

def parse_annotation_paragraph(speech_tag, tag_text, meta_data=None):

    # Remove parens
    tag_text = tag_text.lstrip('(')
    tag_text = tag_text.rstrip(')')

    # Return paragraph data
    d = dict(annotation=clean_text(tag_text))
    if meta_data is not None:
        d.update(meta_data)
    return d

def parse_citation_paragraph(speech_tag, tag_text, meta_data=None):

    # Remove parens and trailing commas
    if REMOVE_CITATION_MARKS:
        tag_text = tag_text.lstrip('„"\'')
        tag_text = tag_text.rstrip('“"\',')

    # Return paragraph data
    d = dict(citation=clean_text(tag_text))
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
    p_counter = 1
    speaker_section_counter = None
    start_tag = protocol_start

    for tag in start_tag.find_all_next('p'):

        # Detect end of protocol
        if tag == protocol_end:
            break

        # Find "Word" style class and convert to lower case for matching
        p_classes = set((x.lower() for x in tag.get('class')))
        #print (f'Found tag classes {p_classes}: {tag}')

        # Get clean tag text (without any HTML tags)
        tag_text = clean_tag_text(tag)

        # Skip empty paragraphs and page numbering
        if not tag_text:
            continue
        match = PAGE_RE.match(tag_text)
        if match is not None:
            continue

        # Apply typo fixes to tag_text
        tag_text = typo_fixes(tag_text)

        # Parse paragraph
        paragraph = None

        # Parse new speaker section
        if SPEAKER_INTRO_CLASSES & p_classes:
            try:
                paragraph = parse_speaker_intro(tag, tag_text, protocol_meta_data)
            except ParserError as error:
                # False speaker change
                if verbose > 1 or NON_SPEAKER_INTRO_RE.match(tag_text) is None:
                    # Only report
                    print (f'WARNING: Speaker intro paragraph without speaker information: '
                           f'{error}')
                # Parse the speaker intro as regular paragraph instead
                if tag_text.startswith('('):
                    p_classes.add('kklammer')
                else:
                    p_classes.add('astandardabsatz')

            else:
                # Start of a new speaker section
                section_meta_data = {
                    'speaker_name': paragraph['speaker_name'],
                    'speaker_party': paragraph['speaker_party'],
                    'speaker_ministry': paragraph['speaker_ministry'],
                    'speaker_role': paragraph['speaker_role'],
                    'speaker_role_descr': paragraph['speaker_role_descr'],
                    'speaker_is_chair': paragraph['speaker_is_chair'],
                }
                section_meta_data.update(protocol_meta_data)
                previous_speaker = current_speaker
                current_speaker = tag
                speaker_section_counter = 1
                if verbose:
                    print (f'New speaker section {section_meta_data}')

        # Skip all paragraphs until the first speaker intro
        if current_speaker is None:
            if verbose > 1:
                print (f'Skipping tag, since no speaker found yet: {tag}')
            continue

        # Parse other paragraph types
        if paragraph is not None:
            # Already found a usable paragraph
            pass
        elif SPEECH_CLASSES & p_classes:
            # Standard paragraph
            paragraph = parse_speech_paragraph(tag, tag_text, meta_data=section_meta_data)
            if verbose:
                print (f'  Found speech paragraph {paragraph}')
        elif ANNOTATION_CLASSES & p_classes:
            # Annotation paragraph
            paragraph = parse_annotation_paragraph(tag, tag_text, meta_data=section_meta_data)
            if verbose:
                print (f'  Found annotation paragraph {paragraph}')
        elif CITATION_CLASSES & p_classes:
            # Citation paragraph
            paragraph = parse_citation_paragraph(tag, tag_text, meta_data=section_meta_data)
            if verbose:
                print (f'  Found citation paragraph {paragraph}')
        else:
            raise ParserError(f'Could not parse section {p_classes}: {tag}')

        # Add paragraph
        paragraph['html_classes'] = sorted(p_classes)
        paragraph['flow_index'] = p_counter
        paragraph['speaker_flow_index'] = speaker_section_counter
        paragraphs.append(paragraph)
        p_counter += 1
        speaker_section_counter += 1

    else:
        raise ParserError(f'Could not find end tag in protocol')

    if not paragraphs:
        print (f'WARNING: No paragraphs parsed for this protocol !!!')
    return paragraphs

def process_protocol(period, index):

    html_filename = os.path.join(
        PROTOCOL_DIR,
        PROTOCOL_FILE_TEMPLATE % (period, index, 'html'))

    # Parse file
    soup = create_parser(html_filename)
    data = parse_protocol(soup)

    # Add protocol meta data
    protocol = protocol_meta_data(period, index, soup)
    protocol['content'] = data

    # Dump data as JSON
    json_filename = os.path.splitext(html_filename)[0] + '.json'
    json.dump(protocol, open(json_filename, 'w', encoding='utf-8'))

def main():

    period = int(sys.argv[1])
    if len(sys.argv) > 2:
        # Process just one document
        index = int(sys.argv[2])
        process_protocol(period, index)
    else:
        # Process all available documents
        data = load_data.load_period_data(period)
        for filename, protocol in sorted(data.items()):
            if os.path.splitext(filename)[1] != '.html':
                continue
            index = protocol['index']
            print ('-' * 72)
            print (f'Parsing {period}-{index}: {filename}')
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
