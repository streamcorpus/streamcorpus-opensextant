
# -*- coding: <utf-8> -*-

from __future__ import absolute_import

from streamcorpus import make_stream_item
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

    
