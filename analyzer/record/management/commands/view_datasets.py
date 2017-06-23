#!/usr/bin/env python
import logging
import traceback

from record.management.commands import CommandWithDatasets
from record.management.commands import map2obj


class Command(CommandWithDatasets):
    help = 'create sample userdata graph'

    def add_arguments(self, parser):
        parser.add_argument(
            'target',
            type=str,
            help="target npz/npy file."
        )

    def handle(self, *args, **kwargs):
        try:
            logging.basicConfig(level=logging.DEBUG)
            options = map2obj(kwargs)
            self.load(options.target)

            for k, v in self.datasets_.items():
                print '[{}] {}'.format(k, v.shape)
        except:
            logging.error(traceback.format_exc())
