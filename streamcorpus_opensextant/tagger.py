''':mod:`streamcorpus_pipeline` tagger stage for OpenSextant

.. This software is released under an MIT/X11 open source license.
   Copyright 2014 Diffeo, Inc.

This provides a connector to use the OpenSextantToolbox
https://github.com/OpenSextant/OpenSextantToolbox/ as a tagger in
:mod:`streamcorpus_pipeline`.  Typical configuration looks like:

.. code-block:: yaml

    streamcorpus_pipeline:
      reader: from_local_chunks
      incremental_transforms: [language, guess_media_type, clean_html,
                               title, hyperlink_labels, clean_visible,
                               opensextant]
      batch_transforms: [multi_token_match_align_labels]
      writers: [to_local_chunks]
      opensextant:
        path_in_third: opensextant/opensextant-current
      multi_token_match_align_labels:
        annotator_id: author
        tagger_id: opensextant

The ``opensextant`` stage is an incremental transform.  Failures on
individual stream items will result in those stream items remaining in
the stream, but without any tagging.  

Note that this stage does *not* run its own aligner, unlike older
tagger stages.  If desired, you must explicitly include an aligner in
``batch_transforms`` to convert document-level
:class:`streamcorpus.Rating` objects to token-level
:class:`streamcorpus.Token` objects.

For all stages that expect a tagger ID, this uses a tagger ID of
``opensextant``.  The stage has no configuration beyond `rest_url`

.. autoclass:: OpenSextantTagger
   :show-inheritance:

'''
from __future__ import absolute_import
import logging
import json
import os.path
import sys
import traceback

import requests

from streamcorpus import Chunk, Tagging, Sentence, Token
from streamcorpus_pipeline.stages import IncrementalTransform

logger = logging.getLogger('streamcorpus_pipeline' + '.' + __name__)


class OpenSextantTagger(IncrementalTransform):
    ''':mod:`streamcorpus_pipeline` tagger stage for OpenSextant.

    This is an incremental transform, and needs to be included in the
    ``incremental_transforms`` list to run within
    :mod:`streamcorpus_pipeline`.
    
    .. automethod:: __init__
    .. automethod:: process_path
    .. automethod:: shutdown

    '''

    config_name = 'opensextant'
    tagger_id = 'opensextant'

    default_config = {
        'scheme': 'http',
        'network_address': 'localhost:8182',
        'service_path': '/opensextant/extract/general/json',
        'verify_ssl': False,
        'username': None,
        'password': None,
        'cert': None
    }

    def __init__(self, config, *args, **kwargs):
        '''Create a new tagger.

        `config` should provides ``scheme``, ``network_address``, and
        ``service_path``, which are assembled into a URL for POSTing
        :attr:`~streamcorpus.StreamItem.body.clean_visible` to obtain
        JSON.  The defaults provide this URL:
        `http://localhost:8182/opensextant/extract/general/json`.

        Optionally, `config` can also contain `verify_ssl` with a path
        to a cert.ca-bundle file to verify the remote server's SSL
        cert.  This is useful if the OpenSextant tagger is proxied
        behind an SSL gateway.  By default, `verify_ssl` is False.

        Optionally, `config` can also contain `username` and
        `password` for BasicAuth to access the OpenSextent end point.

        Per the python `requests` documentation, you can also specify
        a local cert to use as client side certificate, as a single
        file (containing the private key and the certificate) or as a
        tuple of both file's path `cert=('cert.crt', 'cert.key')`

        :param dict config: local configuration dictionary

        '''
        super(OpenSextantTagger, self).__init__(config, *args, **kwargs)
        kwargs = {}
        self.rest_url = config['scheme'] + '://' + config['network_address'] \
                        + config['service_path']
        self.verify_ssl = config['verify_ssl']

        ## Session carries connection pools that automatically provide
        ## HTTP keep-alive, so we can send many documents over one
        ## connection.
        self.session = requests.Session()
        username = config.get('username')
        password = config.get('password')
        if username and password:
            self.session.auth = HTTPBasicAuth(username, password)

        cert = config.get('cert')
        if cert and isinstance(cert, (list, tuple)):
            self.session.cert = tuple(cert)
        elif cert:
            self.session.cert = cert


    def process_item(self, si, context=None):
        '''Run OpenSextant over a single stream item.

        This ignores the `context`, and always returns the input
        stream item `si`.  Its sole action is to add a ``opensextant``
        value to the tagger-keyed fields in `si.body`, provided that
        `si` in fact has a
        :attr:`~streamcorpus.ContentItem.clean_visible` part.

        :param si: stream item to process
        :paramtype si: :class:`streamcorpus.StreamItem`
        :param dict context: additional shared context data
        :return: `si`

        '''
        if si.body and si.body.clean_visible:
            # clean_visible will be UTF-8 encoded
            logger.debug('POST %d bytes of clean_visible to %s',
                         len(si.body.clean_visible), self.rest_url)
            response = self.session.post(
                self.rest_url,
                data=si.body.clean_visible,
                verify=self.verify_ssl,
                headers={},
                timeout=10,
            )
            result = json.loads(response.content)

            # TODO: write make_tagging and make_sentences to parse the JSON respons
            si.body.taggings[self.tagger_id] = make_tagging(result)
            si.body.sentences[self.tagger_id] = make_sentences(result)

            #si.body.relations[self.tagger_id] = make_relations(result)
            #si.body.attributes[self.tagger_id] = make_attributes(result)

        return si

    def shutdown(self):
        '''Try to stop processing.

        Does nothing, since all of the work is done in-process.
        
        '''
        pass

def make_tagging(result):
    return Tagging()

def make_sentences(result):
    logger.info(json.dumps(result, indent=4, sort_keys=4))
    sys.exit()
