#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import traceback
import datetime
import re
import cPickle as pickle

import numpy
from django.core.management.base import BaseCommand

from record.models import Activity
from record.management.commands import map2obj


class Command(BaseCommand):
    help = 'create datasets from db'
    seasons = [
        datetime.datetime.strptime('2015/09/11', '%Y/%m/%d'),
        datetime.datetime.strptime('2015/10/06', '%Y/%m/%d'),
        datetime.datetime.strptime('2015/11/01', '%Y/%m/%d')
    ]
    username_expr = re.compile('(?P<season>[1-3])teku(?P<id>[0-9]+)')

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=24,
            help="slide interval to create chunk data. [default: 24]"
        )

    def handle(self, *args, **kwargs):
        try:
            self.options = map2obj(kwargs)
            userdict = {}
            for activity in Activity.objects.all():
                if activity.username.find('test') >= 0:
                    continue
                if activity.steps == 0:
                    continue
                if not activity.username in userdict:
                    userdict[activity.username] = [activity, ]
                else:
                    userdict[activity.username].append(activity)

            user_dataset_dict = {}
            datasets = numpy.zeros((0, 240), numpy.float32)
            for username, activities in userdict.items():
                dataset = self.get_user_dataset(username, activities)
                dataset.shape = 1, 240
                datasets = numpy.vstack((datasets, dataset))
                user_dataset_dict[username] = dataset

            dataset_dict = {}
            for i in range(1, 240 / self.options.interval):
                dataset_ = numpy.zeros((0, self.options.interval * i), numpy.float32)
                for j in range(240 / self.options.interval - i + 1):
                    for dataset in datasets:
                        try:
                            start = self.options.interval * j
                            end = self.options.interval * j + self.options.interval * i
                            chunk = dataset[start:end]
                            chunk.shape = 1, chunk.shape[0]
                            dataset_ = numpy.vstack((dataset_, chunk))
                        except:
                            logging.error(traceback.format_exc())
                            print '[%d/%d]' % (i, j), \
                                'chunk shape: ', chunk.shape, \
                                'dataset shape: ', dataset_.shape
                            break
                dataset_dict[str(i)] = dataset_

            dataset_dict['all'] = datasets

            for k, v in dataset_dict.items():
                print '[{}], {}'.format(k, v.shape)

            with open('datasets.npz', 'wb') as fp:
                numpy.savez_compressed(fp, **dataset_dict)

            with open('user_dataset_dict.pkl', 'wb') as fp:
                pickle.dump(user_dataset_dict, fp)
        except:
            logging.error(traceback.format_exc())

    def get_user_dataset(self, username, activities):
        try:
            m = self.username_expr.match(username)
            if not m:
                logging.error(
                    'username {} expression does not match', username
                )
                return None
            season_idx = int(m.group('season')) - 1
            session_start_date = self.seasons[season_idx]
            ary = numpy.zeros((240, ), numpy.float32)
            for i in xrange(10):
                date_ = session_start_date + datetime.timedelta(days=i)
                for activity in activities:
                    if activity.start_time.year == date_.year \
                            and activity.start_time.month == date_.month \
                            and activity.start_time.day == date_.day:
                        logging.info('activity found ...')
                        ary[i*24:(i+1)*24] += self.get_activity_data(activity)
            return ary
        except:
            logging.error(traceback.format_exc())

    def get_activity_data(self, activity):
        try:
            ary = numpy.zeros((24, ), numpy.float32)
            diff = activity.end_time - activity.start_time
            # print 'diff: ', diff
            if diff.seconds == 0:
                return ary
            base_date = datetime.datetime(
                year=activity.start_time.year,
                month=activity.start_time.month,
                day=activity.start_time.day
            )
            for i in xrange(24):
                begin = base_date + datetime.timedelta(hours=i)
                end = base_date + datetime.timedelta(hours=i+1)
                if begin < activity.start_time < end \
                        and begin < activity.end_time < end:
                    ary[i] = float(activity.steps)
                elif begin < activity.start_time < end \
                        and end < activity.end_time:
                    portion = float((end - activity.start_time).seconds) / float(diff.seconds)
                    ary[i] = float(activity.steps) * portion
                elif activity.start_time < begin and end < activity.end_time:
                    portion = float(3600) / float(diff.seconds)
                    ary[i] = float(activity.steps) * portion
                elif activity.start_time < begin and activity.end_time < end:
                    portion = float((activity.end_time - end).seconds) / float(diff.seconds)
                    ary[i] = float(activity.steps) * portion
            return ary
        except:
            logging.error(traceback.format_exc())
