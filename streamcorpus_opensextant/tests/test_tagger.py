
# -*- coding: <utf-8> -*-

from __future__ import absolute_import
import logging
import pytest
import sys


import requests
from streamcorpus import make_stream_item, Chunk, EntityType
from streamcorpus_pipeline._tokenizer import nltk_tokenizer
from streamcorpus_pipeline._clean_html import clean_html
from streamcorpus_pipeline._clean_visible import clean_visible

from streamcorpus_opensextant.tagger import OpenSextantTagger

logger = logging.getLogger('streamcorpus_pipeline.' + __name__)

texts = [
    ('Traveling to Paris, Texas.',
     [[
         ('Traveling', None),
         ('to', None),
         ('Paris,', EntityType.LOC),
         ('Texas.', EntityType.LOC),
     ]]),
    (u'\u2602 on the John Smith traveling in Liberia. It continues with a second sentence about Paris.',
     [[(u'\u2602', None),
      ('on', None),
      ('the', EntityType.PER),
      ('John', EntityType.PER),
      ('Smith', EntityType.PER),
      ('traveling', None),
      ('in', None),
      ('Liberia.', EntityType.LOC),],[
      ('It', None),
      ('continues', None),
      ('with', None),
      ('a', None),
      ('second', None),
      ('sentence', None),
      ('about', None),
      ('Paris.', EntityType.LOC),],
  ]),
    (u"""Paris, France is not Paris, Texas.
    Fran\u00e7oise Smith has lived in the cities of Montreal and Qu\u00e9bec, Canada.
    And everyone else lives in France.
    """,
     [[('Paris,', EntityType.LOC),
      ('France', EntityType.LOC),
      ('is', None),
      ('not', None),
      ('Paris,', EntityType.LOC),
      ('Texas.', EntityType.LOC),],[
      (u'Fran\u00e7oise', EntityType.PER),
      ('Smith', EntityType.PER),
      ('has', None),
      ('lived', None),
      ('in', None),
          ('the', EntityType.LOC),     ## wrong
          ('cities', EntityType.LOC),  ## wrong
      ('of', None),
      ('Montreal', EntityType.LOC),
      ('and', None),
      (u'Qu\u00e9bec,', EntityType.LOC),
      ('Canada.', EntityType.LOC),],[
      ('And', None),
      ('everyone', None),
      ('else', None),
      ('lives', None),
      ('in', None),
      ('France.', EntityType.LOC),]
  ]),
]  

@pytest.mark.parametrize('text,tokens', texts)
def test_opensextant_tagger(text, tokens):

    si = make_stream_item(10, 'fake_url')
    si.body.clean_visible = text.encode('utf8')

    tokenizer = nltk_tokenizer({})

    ost = OpenSextantTagger(OpenSextantTagger.default_config)
    tokenizer.process_item(si)
    ost.process_item(si)

    for sent_idx, sent in enumerate(si.body.sentences['opensextant']):
        logger.info([tok.token for tok in sent.tokens])
        for idx, tok in enumerate(sent.tokens):
            logger.info('sent_idx = %d, token idx = %d', sent_idx, idx)
            assert tok.token.decode('utf8') == tokens[sent_idx][idx][0]
            assert tok.entity_type == tokens[sent_idx][idx][1]

    
def main():
    logging.basicConfig(level=logging.DEBUG)

    session = requests.Session()
    chtml = clean_html({})
    cvisible = clean_visible({})
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
            if '<div' in si.body.raw \
               or '<a href' in si.body.raw \
               or '<span' in si.body.raw:
                si.body.media_type = 'text/html'
            chtml(si, {})
            cvisible(si, {})
            tokenizer.process_item(si)
            ost.process_item(si)




if __name__ == '__main__':
    main()
