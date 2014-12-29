''':mod:`streamcorpus_pipeline` tagger stage for OpenSextant

.. This software is released under an MIT/X11 open source license.
   Copyright 2014 Diffeo, Inc.

This provides a connector to use the OpenSextantToolbox
https://github.com/OpenSextant/OpenSextantToolbox/ as a tagger in
:mod:`streamcorpus_pipeline`.  Typical configuration looks like:

.. code-block:: yaml

    streamcorpus_pipeline:
      third_dir_path: /third
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
import os.path
import sys
import traceback

from streamcorpus import Chunk
from streamcorpus_pipeline.stages import IncrementalTransform

logger = logging.getLogger(__name__)


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

    def __init__(self, config, *args, **kwargs):
        '''Create a new tagger.

        `config` should contain key ``rest_url``, which is used to
        obtain JSON data.  Optionally, `config` can also contain
        `verify_ssl` with a path to a cert.ca-bundle file to verify
        the remote server's SSL cert.

        :param dict config: local configuration dictionary

        '''
        super(OpenSextantTagger, self).__init__(config, *args, **kwargs)
        kwargs = {}
        self.rest_url = config.get('rest_url', None)
        self.verify_ssl = config.get('verify_ssl', '')
        if not self.verify_ssl: 
            self.verify_ssl = False

        ## Session carries connection pools that automatically provide
        ## HTTP keep-alive, so we can send many documents over one
        ## connection.
        self.session = requests.Session()
        username = config.get('username')
        password = config.get('password')
        if username and password:
            self.session.auth = HTTPBasicAuth(username, password)


    def process_item(self, si, context):
        '''Run OpenSextant over a single stream item.

        This ignores the `context`, and always returns the input
        stream item `si`.  Its sole action is to add a ``opensextant``
        tagger to the tagger-keyed fields in `si`, provided that `si`
        in fact has a :attr:`~streamcorpus.ContentItem.clean_visible`
        part.

        :param si: stream item to process
        :paramtype si: :class:`streamcorpus.StreamItem`
        :param dict context: additional shared context data
        :return: `si`

        '''
        if si.body and si.body.clean_visible:
            # clean_visible will be UTF--8 encoded
            response = self.session.post(
                self.rest_url,
                data=si.body.clean_visible,
                verify=self.verify_ssl,
                headers={},
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
