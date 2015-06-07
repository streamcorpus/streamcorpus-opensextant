
# -*- coding: <utf-8> -*-

from __future__ import absolute_import
import json
import logging
import os
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


class DummyResponse(object):
    def __init__(self, json_data):
        self.content = json_data


#@pytest.mark.parametrize('text', u"I flew to Paris, France. Then came home to Washington.")
def test_get_selectors():

    selector_config = {
        'scheme': 'http',
        'network_address': 'geoint.diffeo.com',
        'service_path': '/opensextant/extract/general/json',
        'verify_ssl': False,
        'username': 'diffeo',
        'password': 'd1ff30',
        'cert': None
    }

    text = u"I flew to Paris, France. Then came home to Washington."
    result_text = '{"content":"I flew to Paris, France. Then came home to Washington.","annoList":[{"start":17,"end":23,"type":"PLACE","matchText":"France","features":{"hierarchy":"Geo.place.namedPlace","place":{"placeName":"France","expandedPlaceName":null,"nameType":"name","nameTypeSystem":null,"countryCode":"FR","admin1":null,"admin2":null,"featureClass":"Geo.featureType.AdminRegion","featureCode":"PCLI","geocoord":{"latitude":46.0,"longitude":2.0,"precision":-1,"isValid":true},"sourceNameID":null,"sourceFeatureID":null,"placeID":"NGA-1427981","source":"NGA","nameBias":0.05000000074505806,"idBias":0.49000000953674316,"latitude":46.0,"longitude":2.0,"anAdmin1":false,"abbreviation":false,"acountry":true,"nationalCapital":false}}},{"start":10,"end":15,"type":"PLACE","matchText":"Paris","features":{"hierarchy":"Geo.place.namedPlace","place":{"placeName":"Paris","expandedPlaceName":null,"nameType":"name","nameTypeSystem":null,"countryCode":"FR","admin1":null,"admin2":null,"featureClass":"Geo.featureType.PopulatedPlace","featureCode":"PPLC","geocoord":{"latitude":48.86667,"longitude":2.33333,"precision":-1,"isValid":true},"sourceNameID":null,"sourceFeatureID":null,"placeID":"NGA-1456928","source":"NGA","nameBias":0.05000000074505806,"idBias":0.9549999833106995,"latitude":48.86667,"longitude":2.33333,"anAdmin1":false,"abbreviation":false,"acountry":false,"nationalCapital":true}}}]}'

    if(type(text) is str): text.encode('utf8')

    si = make_stream_item(10, 'fake_url')
    si.body.clean_visible = text

    tokenizer = nltk_tokenizer({})
    
    # Modify the above config to use a different backend
    #ost = OpenSextantTagger(selector_config)

    # Uses default/ local backend
    ost = OpenSextantTagger(OpenSextantTagger.default_config)

    tokenizer.process_item(si)

    response = ost.request_json(si)

    assert response.content == result_text

    results = json.loads(response.content)
    selectors = ost.get_selectors(results)

@pytest.mark.parametrize('text,tokens,json_path', texts)
def test_opensextant_tagger(text, tokens, json_path, use_live_service):

    si = make_stream_item(10, 'fake_url')
    si.body.clean_visible = text.encode('utf8')

    tokenizer = nltk_tokenizer({})

    ost = OpenSextantTagger(OpenSextantTagger.default_config)
    if not use_live_service:
        fpath = os.path.join(os.path.dirname(__file__), json_path)
        ost.request_json = lambda si: DummyResponse(open(fpath).read())

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
