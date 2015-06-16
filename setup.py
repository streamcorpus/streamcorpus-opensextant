#!/usr/bin/env python
import os
from setuptools import setup, find_packages
from version import get_git_version

VERSION, SOURCE_LABEL = get_git_version()

setup(
    name='streamcorpus_opensextant',
    version=VERSION,
    author='Diffeo, Inc.',
    author_email='support@diffeo.com',
    description='Transforms for converting opensextant output into Token objects in streamcorpus',
    packages=find_packages(),
    install_requires=[
        'streamcorpus >= 0.3.42',
        'streamcorpus_pipeline >= 0.5.30',
        'geojson',
    ],
    entry_points={
        'streamcorpus_pipeline.stages': [
            'opensextant = streamcorpus_opensextant.tagger:OpenSextantTagger',
        ],
    },
)
