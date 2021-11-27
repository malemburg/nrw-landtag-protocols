#!/usr/bin/env python3
"""
    List all president names found in the OpenSearch index.

    Written by Marc-Andre Lemburg, Nov 2021

"""
import json
import feed_opensearch

QUERY = json.dumps(
    {
        'size': 10000,
        'query': {
            'match': {
                'speaker_role': {'query': 'president', 'operator': 'or'},
                'speaker_role': {'query': 'vice-president', 'operator': 'or'},
            }
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
            )
        #print (f'result={result!r}')
        names = [
            hit['_source']
            for hit in result['hits']['hits']
        ]
        return sorted(names, key=lambda x: x['speaker_name'])

if __name__ == '__main__':
    speakers = find_all_speaker_names()
    for data in speakers:
        print (f'{data["speaker_name"]!r} ({data["speaker_role"]!r}: {data["speaker_role_descr"]!r}) '
               f'({data["protocol_period"]}-{data["protocol_index"]}): {data!r}')
