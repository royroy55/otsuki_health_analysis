#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import traceback
import commands
from itertools import cycle


import numpy
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import animation
import matplotlib.pylab as plt
from mpl_toolkits.mplot3d import Axes3D
from sklearn import decomposition
from sklearn.cluster import MeanShift, estimate_bandwidth

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

        parser.add_argument(
            '--dataid',
            type=str,
            default=None,
            help='dataid for npz file'
        )

        parser.add_argument(
            '--enable_animation',
            action="store_true",
            default=False,
            help='whether to activate and save animation gif. [default: False]'
        )

        parser.add_argument(
            '--gif',
            type=str,
            default="pca.gif",
            help='file path to save animation gif. [default: "pca.gif"]'
        )

        parser.add_argument(
            '--azimuth_interval',
            type=float,
            default=5.,
            help='interval of azimuth. [default: 5.]'
        )

        parser.add_argument(
            '--elevation',
            type=float,
            default=10.,
            help='elevation of camera. [default: 10.]'
        )

        parser.add_argument(
            '--fps',
            type=int,
            default=4,
            help="fps of gif animation. [default: 4]"
        )

        parser.add_argument(
            '--enable_preclustering',
            action="store_true",
            default=False,
            help='whether to enable mean shift clustering for input vector. [default: False]'
        )

        parser.add_argument(
            '--enable_postclustering',
            action="store_true",
            default=False,
            help='whether to enable mean shift clustering for principle components. [default: False]'
        )

        parser.add_argument(
            '--quantile',
            type=float,
            default=.05,
            help='quantile for mean shift clustering. [default: 0.05]'
        )

        parser.add_argument(
            '--enable_shrink',
            action="store_true",
            default=False,
            help="whether to enable shrinking generated animation gif. [default: False]"
        )

        parser.add_argument(
            '--shrink_scale',
            type=float,
            default=.8,
            help='shrink scale of animation gif. '
            'this value is only effective if enable_animation and enable_shrink options are activated.'
            '[default: .8]'
        )

        parser.add_argument(
            '--shrink_colors',
            type=int,
            default=16,
            help='bit size to express colors for animation gif. '
            'this value is only effective if enable_animation and enable_shrink options are activated. '
            '[default: 16]'
        )

    def handle(self, *args, **kwargs):
        try:
            self.options = map2obj(kwargs)

            if self.options.enable_preclustering and self.options.enable_postclustering:
                logging.info('both pre and post clustering enabled. invalid options.')
                return

            X = self.load(self.options.target, self.options.dataid)
            print 'X shape: ', X.shape

            labels = []
            n_clusters_ = 0
            if self.options.enable_preclustering:
                bandwidth = estimate_bandwidth(X, quantile=self.options.quantile, n_samples=500)
                ms = MeanShift(bandwidth=bandwidth, bin_seeding=True)
                ms.fit(X)
                labels = ms.labels_
                # cluster_centers = ms.cluster_centers_
                labels_unique = numpy.unique(labels)
                n_clusters_ = len(labels_unique)
                print 'n_clusters_: ', n_clusters_

            self.fig = plt.figure(1, figsize=(8, 6))
            plt.clf()
            #ax = Axes3D(fig, rect=[0, 0, .95, 1], elev=48, azim=134)
            self.ax = Axes3D(self.fig)

            plt.cla()
            pca = decomposition.PCA(n_components=3)
            pca.fit(X)
            X = pca.transform(X)

            if self.options.enable_postclustering:
                bandwidth = estimate_bandwidth(X, quantile=self.options.quantile, n_samples=500)
                ms = MeanShift(bandwidth=bandwidth, bin_seeding=True)
                ms.fit(X)
                labels = ms.labels_
                # cluster_centers = ms.cluster_centers_
                labels_unique = numpy.unique(labels)
                n_clusters_ = len(labels_unique)
                print 'n_clusters_: ', n_clusters_

            if self.options.enable_preclustering or self.options.enable_postclustering:
                # Reorder the labels to have colors matching the cluster results
                colors = cycle('bgrcmykbgrcmykbgrcmykbgrcmyk')
                for k, col in zip(range(n_clusters_), colors):
                    my_members = labels == k
                    # cluster_center = cluster_centers[k]
                    self.ax.scatter(
                        X[my_members, 0],
                        X[my_members, 1],
                        X[my_members, 2],
                        c=col,
                        cmap=plt.cm.spectral
                    )
                    print '[Cluster{}] {}'.format(k, sum(my_members))
            else:
                self.ax.scatter(X[:, 0], X[:, 1], X[:, 2], c='b', cmap=plt.cm.spectral)

            if self.options.enable_animation:
                anim = animation.FuncAnimation(
                    self.fig,
                    self.animate,
                    frames=int(360 / self.options.azimuth_interval)
                )
                anim.save(self.options.gif, writer='imagemagick', fps=self.options.fps)
                if self.options.enable_shrink:
                    self.shrink_gif()
            plt.show()
        except:
            logging.error(traceback.format_exc())

    def animate(self, nframe):
        self.ax.view_init(
            elev=self.options.elevation,
            azim=self.options.azimuth_interval * nframe
        )

    def shrink_gif(self):
        base, ext = os.path.splitext(self.options.gif)
        outfile = base + ".shrinked.gif"
        status, output = commands.getstatusoutput(
            'gifsicle -O3 --scale {} --colors {} -i {} -o {}'.format(
                self.options.shrink_scale,
                self.options.shrink_colors,
                self.options.gif,
                outfile
            )
        )
        if status:
            logging.error(output)
        return True
