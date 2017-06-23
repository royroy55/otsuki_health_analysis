#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import traceback
import datetime
import json
import cPickle as pickle

from django.core.management.base import BaseCommand

from record.models import Summary
from record.models import Activity


class Command(BaseCommand):
    help = 'load moves data from pickle file'
    to_date = lambda cls, x: datetime.datetime.strptime(x, '%Y%m%d')
    to_datetime = lambda cls, x: datetime.datetime.strptime(x[0:13], '%Y%m%dT%H%M%S')

    def add_arguments(self, parser):
        parser.add_argument(
            'target',
            type=str,
            help="target pickle file."
        )

    def handle(self, *args, **options):
        try:
            with open(options['target'], 'r') as fp:
                data = pickle.load(fp)
                self.crawl_moves(data)
        except:
            logging.error(traceback.format_exc())

    def crawl_moves(self, data):
        for username, storylines_str in data.items():
            # print type(storylines), storylines
            storylines = json.loads(storylines_str)
            for story in storylines:
                try:
                    date = self.to_date(story['date'])
                    self.load_summary(username, date, story)
                    self.load_activity(username, date, story)
                except:
                    logging.error(traceback.format_exc())
                    return False

    def load_summary(self, username, date, story):
        try:
            if story['summary'] is None:
                logging.error(
                    'no summary found for %s in %s.'
                    % (username, date.strftime('%Y/%m/%d')))
                return

            for summary in story['summary']:
                summary_obj, created = Summary.objects.get_or_create(
                    username=username,
                    date=date,
                    activity_type=summary['activity'],
                    steps=summary['steps'] if 'steps' in summary else 0,
                    duration=summary['duration'],
                    distance=summary['distance'] if 'distance' in summary else 0
                )
                #summary_obj.save()
        except:
            logging.error(traceback.format_exc())

    def load_activity(self, username, date, story):
        try:
            if story['segments'] is None:
                logging.error(
                    'no segments found for %s in %s.'
                    % (username, date.strftime('%Y/%m/%d'))
                )
                return

            for segment in story['segments']:
                if segment['type'] == 'move':
                    for activity in segment['activities']:
                        ## @todo add track points parser
                        activity_obj, created = Activity.objects.get_or_create(
                            username=username,
                            activity_type=activity['activity'],
                            start_time=self.to_datetime(activity['startTime']),
                            end_time=self.to_datetime(activity['endTime']),
                            duration=activity['duration'],
                            steps=activity['steps'] if 'steps' in activity else 0,
                            distance=activity['distance'] if 'distance' in activity else 0
                        )
        except:
            logging.error(traceback.format_exc())
