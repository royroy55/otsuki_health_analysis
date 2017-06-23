#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import traceback
import datetime
import re
import cPickle as pickle

import numpy
from django.core.management.base import BaseCommand
from oauth2client.client import SignedJwtAssertionCredentials
import gdata.spreadsheets.client


from record.models import User
from record.models import Group
from record.management.commands import map2obj


class Command(BaseCommand):
    help = 'load users and groups from specific google drive spreadsheet'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            default="818793433472-7vfqjnlic066i76k8h5dcecgvt6v1smp@developer.gserviceaccount.com",
            help="gdrive application account email address. [default: None]"
        )
        parser.add_argument(
            '--privatekey',
            default="./tekupeko-b91514a63327.p12",
            help="privatekey path [default: None]"
        )
        parser.add_argument(
            '--spreadsheet_id',
            default="1O29nQBUI0yb2_GUg_buzit7c5LAEjz1axjlJnPkEGuk",
            help='id of target spreadsheet. [default: None]'
        )

    def handle(self, *args, **options):
        spreadsheet = SpreadSheet(
            options['email'],
            options['privatekey'],
            options['spreadsheet_id']
        )
        worksheets = spreadsheet.get_worksheets()
        for worksheet in worksheets:
            if worksheet.title().find(u"accounts") >= 0:
                print "find worksheet titled ", worksheet.title()
                for row in worksheet:
                    # print json.dumps(row, ensure_ascii=False).encode('utf-8')
                    username = row[u'ユーザ名']
                    groupname = row[u'チーム名']
                    sessionname = row[u'期間']
                    created = False
                    group, created = Group.objects.get_or_create(
                        name=groupname,
                        session=sessionname
                    )
                    if created:
                        print "group %s created." % groupname

                    user, created = User.objects.get_or_create(
                        username=username,
                        group=group
                    )
                    if created:
                        print "user %s created." % username


class SpreadSheet(object):
    def __init__(self, client_email, private_key_path, spreadsheet_key):
        self.client_email = client_email
        with open(private_key_path, 'rb') as fp:
            self.private_key = fp.read()  # 手順2で発行された秘密鍵
        self.spreadsheet_key = spreadsheet_key

    def get_worksheet(self, name):
        try:
            for worksheet in self.get_worksheets():
                if worksheet.title() == name:
                    return worksheet
            return None
        except:
            logging.error(traceback.format_exc())
            return None

    def get_worksheets(self):
        try:

            # 認証情報の作成
            credentials = SignedJwtAssertionCredentials(
                self.client_email,
                self.private_key,
                scope=["https://spreadsheets.google.com/feeds"]
            )

            # スプレッドシート用クライアントの準備
            self.client = gdata.spreadsheets.client.SpreadsheetsClient()

            # OAuth2.0での認証設定
            self.auth_token = gdata.gauth.OAuth2TokenFromCredentials(credentials)
            self.auth_token.authorize(self.client)

            # ワークシートの取得
            return [WorkSheet(self, sheet) for sheet in self.client.get_worksheets(self.spreadsheet_key).entry]
        except:
            logging.error(traceback.format_exc())
            return []


class WorkSheet(list):
    def __init__(self, parent, worksheet):
        self.parent = parent
        self.worksheet = worksheet
        self.load()

    def title(self):
        return self.worksheet.title.text

    def load(self):
        try:
            feed = self.parent.client.get_list_feed(
                self.parent.spreadsheet_key,
                self.worksheet.get_worksheet_id()
            )
            for row in feed.entry:
                row_ = {}
                if row.content.text is None:
                    continue
                for token in row.content.text.split(','):
                    key, value = token.split(':')
                    row_[key.strip()] = value.strip()
                self.append(row_)
            return True
        except:
            logging.error(traceback.format_exc())
            return False
