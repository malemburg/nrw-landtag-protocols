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
            _source_includes=('speaker_name',)
            )
        #print (f'result={result!r}')
        names = set(
            hit['_source']['speaker_name']
            for hit in result['hits']['hits']
        )
        return sorted(names)

if __name__ == '__main__':
    speakers = find_all_speaker_names()
    for speaker in speakers:
        print (f'{speaker}')
