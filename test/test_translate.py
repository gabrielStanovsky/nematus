#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import unittest
import requests
import logging

sys.path.append(os.path.abspath('../nematus'))
from translate import main as translate
from settings import TranslationSettings
from theano_tf_convert import theano_to_tensorflow_model

level = logging.DEBUG
logging.basicConfig(level=level, format='%(levelname)s: %(message)s')

def load_wmt16_model(src, target):
        path = os.path.join('models', '{0}-{1}'.format(src,target))
        try:
            os.makedirs(path)
        except OSError:
            pass
        for filename in ['model.npz', 'model.npz.json', 'vocab.{0}.json'.format(src), 'vocab.{0}.json'.format(target)]:
            if not os.path.exists(os.path.join(path, filename)):
                if filename == 'model.npz' and os.path.exists(os.path.join(path, 'model.npz.index')):
                    continue
                r = requests.get('http://data.statmt.org/rsennrich/wmt16_systems/{0}-{1}/'.format(src,target) + filename, stream=True)
                with open(os.path.join(path, filename), 'wb') as f:
                    for chunk in r.iter_content(1024**2):
                        f.write(chunk)

                # regression test is based on Theano model - convert to TF names
                if filename == 'model.npz' and not os.path.exists(os.path.join(path, 'model.npz.index')):
                    os.rename(os.path.join(path, 'model.npz'), os.path.join(path, 'model-theano.npz'))
                    theano_to_tensorflow_model(os.path.join(path, 'model-theano.npz'), os.path.join(path, 'model.npz'))

class TestTranslate(unittest.TestCase):
    """
    Regression tests for translation with WMT16 models
    """

    def setUp(self):
        """
        Download pre-trained models
        """
        load_wmt16_model('en','de')

    def outputEqual(self, output1, output2):
        """given two translation outputs, check that output string is identical,
        and probabilities are equal within rounding error.
        """
        for i, (line, line2) in enumerate(zip(open(output1).readlines(), open(output2).readlines())):
            if not i % 2:
                self.assertEqual(line, line2)
            else:
                probs = map(float, line.split())
                probs2 = map(float, line.split())
                for p, p2 in zip(probs, probs2):
                    self.assertAlmostEqual(p, p2, 5)

    def get_settings(self):
        """
        Initialize and customize settings.
        """
        translation_settings = TranslationSettings()
        translation_settings.models = ["model.npz"]
        translation_settings.num_processes = 1
        translation_settings.beam_width = 12
        translation_settings.normalization_alpha = 1.0
        translation_settings.suppress_unk = True
        translation_settings.get_word_probs = True

        return translation_settings

    # English-German WMT16 system, no dropout
    def test_ende(self):
        os.chdir('models/en-de/')

        translation_settings = self.get_settings()

        translate(
                  input_file=open('../../en-de/in'),
                  output_file=open('../../en-de/out','w'),
                  translation_settings=translation_settings
                  )

        os.chdir('../..')
        self.outputEqual('en-de/ref','en-de/out')


if __name__ == '__main__':
    unittest.main()
