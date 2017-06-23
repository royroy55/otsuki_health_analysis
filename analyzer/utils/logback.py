#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import json
import logging
import logging.handlers
import traceback
import smtplib
import functools
import threading
from copy import deepcopy
import datetime
import StringIO

import numpy

MESSAGE_TMPL = '''\
From: %(from)s
To: %(to)s
Subject: %(subject)s

%(message)s
'''

email = None


def set_email(email_):
    global email
    email = email_


class CustomLogger(object):
    def __init__(self, name='root', email=None, output_prefix=None, level=logging.DEBUG):
        self.name = name
        self.email = email
        self.output_prefix = output_prefix
        self.level = level
        self.logger = logging.getLogger(self.name)
        self.smtphandler = None
        self.filehandler = None
        self.stream = None
        self.logfile = None
        if not self.email is None:
            self.setup_email()

        if not self.output_prefix is None:
            self.setup_fileout()

    def setup_email(self):
        self.stream = StringIO.StringIO()
        self.streamhandler = logging.StreamHandler(self.stream)
        self.logger.addHandler(self.streamhandler)

    def setup_fileout(self):
        basedir = os.path.dirname(os.path.abspath(self.output_prefix))
        if not os.path.exists(basedir):
            os.makedirs(basedir)

        self.logfile = self.output_prefix + "_" \
            + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') \
            + ".log"
        self.filehandler = logging.FileHandler(self.logfile)
        self.filehandler.setLevel(self.level)
        self.logger.addHandler(self.filehandler)

    def __call__(self, func):
        @functools.wraps(func)
        def setup_and_go(*args, **kwargs):
            start = time.time()
            kwargs.update({'logger': self.logger})
            # print "kwargs: ", kwargs
            ret = func(*args, **kwargs)
            self.logger.info('elappsed time: %.2f sec' % (time.time() - start))
            if not self.smtphandler is None:
                self.smtphandler.emit()
            if not self.stream is None and not self.email is None:
                sendmail(self.email, self.stream.getvalue())
            return ret
        return setup_and_go


def log_ellapsed_time(func):
    @functools.wraps(func)
    def exec_and_measure_time(*args, **kwargs):
        start = time.time()
        ret = func(*args, **kwargs)
        logging.info('elappsed time: %.2f sec' % (time.time() - start))
        return ret
    return exec_and_measure_time


def log_via_mail(func):
    @functools.wraps(func)
    def send_after_execution(*args, **kwargs):
        global email
        stream = StringIO.StringIO()
        handler = logging.StreamHandler(stream)
        logging.root.addHandler(handler)

        ret = func(*args, **kwargs)

        logging.root.removeHandler(handler)

        if not email is None:
            sendmail(email, stream.getvalue())

        return ret
    return send_after_execution


def log_via_file(output_prefix):
    basedir = os.path.dirname(os.path.abspath(output_prefix))
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    def log_via_file_(func):
        @functools.wraps(func)
        def setup_before_execution(*args, **kwargs):
            logger = logging.getLogger()
            logger.setLevel(logging.DEBUG)
            handler = logging.FileHandler(
                filename=output_prefix + "_"
                + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + "_"
                + "thread%d" % threading.current_thread().ident
                + ".log"
            )
            handler.setLevel(logging.DEBUG)
            logger.addHandler(handler)

            return func(*args, **kwargs)
        return setup_before_execution
    return log_via_file_


def sendmail(TO, message):
    try:
        FROM = 'deeplearning.seminar2015@gmail.com'
        server_ssl = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server_ssl.ehlo()  # optional, called by login()
        server_ssl.login('nakadailab.log', 'nakadailab2015')
        # ssl server doesn't support or need tls, so don't call server_ssl.starttls()
        MSG = deepcopy(MESSAGE_TMPL) % {
            "from": FROM,
            "to": TO,
            "subject": "[Speech Classification] Task Log at " + str(datetime.datetime.now()),
            "message": message
        }
        server_ssl.sendmail(FROM, TO, MSG)
        server_ssl.close()
        logging.debug('successfully sent the mail')
    except:
        logging.error(traceback.format_exc())


class AdvancedEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, numpy.ndarray):
                return str(obj.shape)
            return json.JSONEncoder.default(self, obj)
        except:
            return str(obj)
