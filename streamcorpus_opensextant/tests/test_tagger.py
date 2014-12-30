

from __future__ import absolute_import

from streamcorpus import make_stream_item
from streamcorpus_opensextant.tagger import OpenSextantTagger

def test_opensextant_tagger():

    si = make_stream_item(10, 'fake_url')
    si.body.clean_visible = 'This is a document about John Smith traveling in Liberia.'

    ost = OpenSextantTagger(OpenSextantTagger.default_config)
    ost.process_item(si)

    
