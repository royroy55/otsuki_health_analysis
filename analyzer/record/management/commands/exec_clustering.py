#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import traceback

from sklearn.cluster import MeanShift, estimate_bandwidth
from record.management.commands import CommandWithDatasets
from record.management.commands import map2obj


class Command(CommandWithDatasets):
    help = 'execute clustering ...'

    def add_arguments(self, parser):
        parser.add_argument(
            'target',
            type=str,
            help="target npz/npy file."
        )

        parser.add_argument(
            '--dataid',
            type=str,
            default=None,
            help='dataid for npz file'
        )

        parser.add_argument(
            '--quantile',
            type=float,
            default=.05,
            help='quantile for mean shift clustering. [default: 0.05]'
        )

    def handle(self, *args, **kwargs):
        try:
            self.options = map2obj(kwargs)

            X = self.load(self.options.target, self.options.dataid)

            bandwidth = estimate_bandwidth(
                X,
                quantile=self.options.quantile,
                n_samples=500
            )
            ms = MeanShift(bandwidth=bandwidth, bin_seeding=True)
            ms.fit(X)
            self.set(self.options.dataid + "_labels", ms.labels_)
            self.dump()
        except:
            logging.error(traceback.format_exc())
