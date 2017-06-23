#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import traceback

from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import normalize

from record.management.commands import CommandWithDatasets
from record.management.commands import map2obj
from dnn.SDA import SDA


class Command(CommandWithDatasets):
    help = 'create sample userdata graph'

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
            help='id for npz file. [default: None]'
        )

        parser.add_argument(
            '--hiddens',
            nargs="+",
            type=int,
            default=[],
            help='dimentions of hidden layers. [default: []]'
        )

        parser.add_argument(
            '--epochs',
            type=int,
            default=100,
            help='epochs for SdA. [default: 100]'
        )

    def handle(self, *args, **kwargs):
        try:
            logging.basicConfig(level=logging.DEBUG)
            options = map2obj(kwargs)
            X = self.load(options.target, options.dataid)
            #X = MinMaxScaler().fit_transform(X)
            X = normalize(X)
            sda = SDA.pretrain(
                [X, X],
                hiddens=options.hiddens,
                epochs=options.epochs
            )
            dataset_x = sda.get_hidden_values(X)
            print 'dataset_x: ', dataset_x.shape, dataset_x[:10]

            dataid = '.'.join(["dsa", str(X.shape[1])] + [str(h) for h in options.hiddens])
            self.dump(**{dataid: dataset_x})
        except:
            logging.error(traceback.format_exc())
