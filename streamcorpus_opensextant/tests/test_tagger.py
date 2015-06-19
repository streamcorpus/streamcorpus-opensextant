
# -*- coding: <utf-8> -*-

from __future__ import absolute_import
from copy import deepcopy
import json
import logging
import os
import pytest
import sys

import geojson
import requests
from streamcorpus import make_stream_item, Chunk, \
    EntityType, OffsetType
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
     ]],
     'query-26.json',
    ),
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
      ],
      'query-92.json',
    ),
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
      ('France.', EntityType.LOC),],
      ],
     'query-156.json',
     ),
]


@pytest.fixture(scope='session',
                params=[True, False])
def use_live_service(request):
    if request.param:
        try:
            config = OpenSextantTagger.default_config
            rest_url = config['scheme'] + '://' + config['network_address'] + \
                       '/opensextant/extract/'
            resp = requests.post(
                rest_url,
                timeout=10,
            )
            data = json.loads(resp.content)
            assert type(data) == list
            assert 'general' in data
        except Exception, exc:
            logger.warn('will skip running against actual container because:', exc_info=True)
            pytest.skip('will skip running against actual container because: %r' % exc)
    return request.param


def setup_mock_live_service(ost, json_path):
    '''monkey patch the `ost` OpenSextantTagger instance so that it gets
    its json from other than a live service.

    '''
    fpath = os.path.join(os.path.dirname(__file__), json_path)
    ost.request_json = lambda si: DummyResponse(open(fpath).read())


class DummyResponse(object):
    def __init__(self, json_data):
        self.content = json_data


@pytest.mark.parametrize('text,tokens,json_path', texts)
def test_opensextant_tagger_on_data_both(text, tokens, json_path, use_live_service):
    '''Test that the transform works when configured with both
    annotate_sentences and add_geo_selectors.  The first requires
    nltk_tokenizer to have been run first.

    '''
    config = deepcopy(OpenSextantTagger.default_config)
    config['annotate_sentences'] = True
    config['add_geo_selectors'] = True
    ost = OpenSextantTagger(config)

    if not use_live_service:
        setup_mock_live_service(ost, json_path)

    si = make_stream_item(10, 'fake_url')
    si.body.clean_visible = text.encode('utf8')

    tokenizer = nltk_tokenizer({})
    tokenizer.process_item(si)
    ost.process_item(si)
    verify_sentences(si, tokens)
    verify_selectors(si)


def verify_sentences(si, tokens):
    sent_idx = -1
    for sent_idx, sent in enumerate(si.body.sentences['opensextant']):
        logger.info([tok.token for tok in sent.tokens])
        for idx, tok in enumerate(sent.tokens):
            logger.info('sent_idx = %d, token idx = %d', sent_idx, idx)
            assert tok.token.decode('utf8') == tokens[sent_idx][idx][0]
            assert tok.entity_type == tokens[sent_idx][idx][1]
    assert sent_idx > -1

def verify_selectors(si):
    sel_idx = -1
    for sel_idx, sel in enumerate(si.body.selectors['opensextant']):
        logger.info('sel_idx = %d, sel = %r', sel_idx, sel)
        assert sel.selector_type == 'GEOJSON'
        assert sel.raw_selector
        assert 'geometry' in geojson.loads(sel.canonical_selector)
        assert 'coordinates' in geojson.loads(sel.canonical_selector)['geometry']
        assert sel.offsets[OffsetType.CHARS].first > -1
    assert sel_idx > -1


@pytest.mark.parametrize('text,tokens,json_path', texts)
def test_opensextant_tagger_on_data_selectors_only(text, tokens, json_path, use_live_service):
    '''Test that the transform works when configured to only produce
    streamcorpus.Selector objects and not to annotate_sentences.  In
    particular, this does *not* need nltk to run before it.

    '''
    config = deepcopy(OpenSextantTagger.default_config)
    config['annotate_sentences'] = False
    config['add_geo_selectors'] = True
    ost = OpenSextantTagger(config)

    if not use_live_service:
        setup_mock_live_service(ost, json_path)

    si = make_stream_item(10, 'fake_url')
    si.body.clean_visible = text.encode('utf8')

    ost.process_item(si)
    verify_selectors(si)


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
