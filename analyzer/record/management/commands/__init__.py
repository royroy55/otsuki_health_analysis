#!/usr/bin/env python

import os
import logging
import traceback
import collections
import cPickle as pickle

import numpy
from django.core.management.base import BaseCommand


def map2obj(mapping):
    try:
        if isinstance(mapping, collections.Mapping):
            for key, value in mapping.iteritems():
                mapping[key] = map2obj(value)
            return collections.namedtuple(
                'RecordArgs', mapping.iterkeys()
            )(**mapping)
        if isinstance(mapping, list):
            for idx, e in enumerate(mapping):
                mapping[idx] = map2obj(e)
    except:
        pass
    return mapping


class CommandWithDatasets(BaseCommand):
    def load(self, filepath, key=None):
        try:
            self.X_ = None
            self.datasets_ = None
            self.input_filepath_ = filepath

            if not os.path.exists(filepath):
                logging.error('cannot find ' + filepath)
                return False
            base, ext = os.path.splitext(filepath)
            if ext == '.npz' and not key is None:
                with open(filepath, 'rb') as fp:
                    buf = numpy.load(fp)
                    self.datasets_ = dict((k, v) for k, v in buf.items())
                    self.X_ = buf[key]
            elif ext == '.npz' and key is None:
                with open(filepath, 'rb') as fp:
                    buf = numpy.load(fp)
                    self.datasets_ = dict((k, v) for k, v in buf.items())
            elif ext == '.npy':
                with open(filepath, 'rb') as fp:
                    self.X_ = numpy.load(fp)
            elif ext == '.pkl':
                with open(filepath, 'rb') as fp:
                    self.X_ = pickle.load(fp)
            # print 'type of X: ', type(self.X_)
            return self.X_
        except:
            logging.error(traceback.format_exc())
            return None

    def set(self, key, value):
        self.datasets_[key] = value

    def remove(self, key):
        del self.datasets_[key]

    def dump(self, **kwargs):
        try:
            if not 'filepath' in kwargs:
                self.datasets_.update(kwargs)
                with open(self.input_filepath_, 'wb') as fp:
                    numpy.savez_compressed(fp, **self.datasets_)
            elif 'filepath' in kwargs:
                filepath = kwargs['filepath']
                del kwargs['filepath']
                base, ext = os.path.splitext(filepath)
                if ext == '.npz':
                    self.datasets_.update(kwargs)
                    with open(filepath, 'wb') as fp:
                        numpy.savez_compressed(fp, **self.datasets_)
                elif ext == '.npy' and 'data' in kwargs:
                    with open(filepath, 'wb') as fp:
                        numpy.save(fp, kwargs['data'])
                elif ext == '.pkl' and 'data' in kwargs:
                        pickle.dump(kwargs['data'], fp)
                else:
                    logging.error('invalid data format: ' + filepath)
            return True
        except:
            logging.error(traceback.format_exc())
            return False