#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import traceback

import numpy
from record.management.commands import map2obj
from record.management.commands import CommandWithDatasets

from hmmlearn.hmm import GMMHMM


class Command(CommandWithDatasets):
    help = 'create sample userdata graph'

    def add_arguments(self, parser):
        parser.add_argument(
            'target',
            type=str,
            help="target npz file."
        )

        parser.add_argument(
            '--dataid',
            type=str,
            default=None,
            help='id for npz file. [default: None]'
        )

        parser.add_argument(
            '-c',
            '--components',
            type=int,
            default=4,
            help='number of components in GMM-HMM. [default: 4]'
        )

        parser.add_argument(
            '-m',
            '--mix',
            type=int,
            default=8,
            help='number of gaussian mixture in GMM-HMM. [default: 8]'
        )

        parser.add_argument(
            '--enable_state_graph',
            action="store_true",
            default=False,
            help='Whether to create sampled state graph for each class. '
            '[default: False]'
        )

    def handle(self, *args, **kwargs):
        try:
            logging.basicConfig(level=logging.DEBUG)
            options = map2obj(kwargs)

            X = self.load(options.target, options.dataid)
            print "X.shape: ", X.shape
            X.shape = X.shape[0] / 8, 8, X.shape[1]

            hmm = GMMHMM(
                n_components=options.components,
                n_mix=options.mix,
                n_iter=10000
            )
            print 'initial start probabilities: ', hmm.startprob_
            print 'initial transition matrix: ', hmm.transmat_
            hmm.fit(X)

            states = [hmm.predict(obs) for obs in X]

            logging.info('states: {}'.format(states[:10]))

            states = numpy.array(states)
            print 'states shape: ', states.shape

            dataid = 'states-c{}-m{}-i{}'.format(
                options.components,
                options.mix,
                X.shape[1]
            )
            self.dump(**{dataid: states})
            # base, ext = os.path.splitext(options.target)
            # if ext == '.npz':
            #     label = '.'.join(('states', str(X.shape[1])))
            #     original[label] = states
            #     with open(options.target, 'wb') as fp:
            #         numpy.savez_compressed(fp, **original)
            # else:
            #     with open('states.npz', 'wb') as fp:
            #         numpy.savez_compressed(fp, all=states)

            self.draw_hmm_graph(hmm)
        except:
            logging.error(traceback.format_exc())

    def draw_hmm_graph(self, hmm):
        try:
            import networkx as nx
            from pprint import pformat
            G = nx.MultiDiGraph()

            print 'hmm transition matrix: ', pformat(hmm.transmat_)
            for i, origin_state in enumerate(xrange(hmm.n_components)):
                for j, destination_state in enumerate(xrange(hmm.n_components)):
                    rate = hmm.transmat_[i][j]
                    if rate > 0:
                        G.add_edge(
                            origin_state,
                            destination_state,
                            weight=rate,
                            label="{:.02f}".format(rate)
                        )
            graph = nx.to_agraph(G)
            graph.draw('state_transitions.eps', prog='circo')
        except:
            logging.error(traceback.format_exc())
