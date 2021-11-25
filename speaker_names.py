#!/usr/bin/env python3
"""
    List all speaker names found in the OpenSearch index.

    Written by Marc-Andre Lemburg, Nov 2021

"""
import json
import feed_opensearch

QUERY = json.dumps(
    {
        'size': 10000,
        'query': {
            'match_all': {}
        },
        'collapse': {
            'field' : 'speaker_name.keyword'
        },
    }
)

def find_all_speaker_names(os_index_name=feed_opensearch.INDEX_NAME):
    with feed_opensearch.opensearch_client() as client:
        result = client.search(
            QUERY,
            index=os_index_name,
            _source_includes=('speaker_name', 'speaker_party',
                'protocol_period', 'protocol_index')
            )
        #print (f'result={result!r}')
        names = [
            (hit['_source']['speaker_name'],
             hit['_source']['speaker_party'],
             hit['_source']['protocol_period'],
             hit['_source']['protocol_index'])
            for hit in result['hits']['hits']
        ]
        return sorted(names)

if __name__ == '__main__':
    speakers = find_all_speaker_names()
    for speaker, party, period, index in speakers:
        print (f'{speaker!r} ({party!r}) ({period}-{index})')
