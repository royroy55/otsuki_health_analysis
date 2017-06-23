#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import traceback
import random

import matplotlib.pylab as plt

from record.management.commands import CommandWithDatasets
from record.management.commands import map2obj


class Command(CommandWithDatasets):
    help = 'create sample userdata graph'

    def add_arguments(self, parser):
        parser.add_argument(
            'target',
            type=str,
            help="target pickle file."
        )

        parser.add_argument(
            '--dataid',
            type=str,
            default=None,
            help="target pickle file."
        )

        parser.add_argument(
            '-o',
            '--output',
            type=str,
            default="datasets.random.png",
            help='output filepath. [default: "datasets.random.png"]'
        )

    def handle(self, *args, **kwargs):
        try:
            options = map2obj(kwargs)
            datasets = self.load(options.target, options.dataid)

            f, axes = plt.subplots(3, 3)
            for i in range(3):
                for j in range(3):
                    dataset = datasets[random.randint(0, datasets.shape[0])]
                    # print 'dataset: ', dataset
                    axes[i][j].bar(xrange(240), dataset)
                    axes[i][j].set_xlabel('hours')
                    axes[i][j].set_ylabel('steps')
            plt.savefig(options.output)
            plt.show()
        except:
            logging.error(traceback.format_exc())
