
# -*- coding: <utf-8> -*-

from __future__ import absolute_import
import logging
import sys

import requests
from streamcorpus import make_stream_item, Chunk
from streamcorpus_pipeline._tokenizer import nltk_tokenizer

from streamcorpus_opensextant.tagger import OpenSextantTagger

def test_opensextant_tagger():

    si = make_stream_item(10, 'fake_url')
    text = u'\u2602 on the John Smith traveling in Liberia.' + \
           u' It continues with a second sentence about Paris.'
    si.body.clean_visible = text.encode('utf8')

    tokenizer = nltk_tokenizer({})

    ost = OpenSextantTagger(OpenSextantTagger.default_config)
    tokenizer.process_item(si)
    ost.process_item(si)

    
def main():
    logging.basicConfig()

    session = requests.Session()
    tokenizer = nltk_tokenizer({})
    ost = OpenSextantTagger(OpenSextantTagger.default_config)

    for url in sys.stdin:
        url = url.strip()
        # try ten times to get it
        for i in range(10):
            try:
                resp = session.get(url)
                if resp.content:
                    break
                logger.critical(resp.status)
            except:
                logger.critical(exc_info=True)

        path = '/tmp/test-chunk.sc.xz.gpg'
        open(path, 'wb').write(resp.content)
        for si in Chunk(path):
            tokenizer.process_item(si)
            ost.process_item(si)


if __name__ == '__main__':
    main()
