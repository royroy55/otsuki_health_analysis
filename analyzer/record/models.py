#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.db import models

# Create your models here.

class User(models.Model):
    username = models.CharField('username', max_length=256)
    session = models.CharField('session', max_length=256)
    group = models.ForeignKey("Group", verbose_name="group")

class Group(models.Model):
    name = models.CharField('name', max_length=256)
    session = models.CharField('session', max_length=256)

class Summary(models.Model):
    u"""
    サマリーモデル
    """
    # 紐付くTekuUser
    username = models .CharField('username', max_length=256)
    # 日付（ミリ秒）（UTC時間）
    date = models.DateTimeField()
    # 運動項目
    activity_type = models.CharField('activity', max_length=256)
    #今回は運動項目グループは未使用
    #group = models.SmallIntegerField()
    # 運動時間（秒）
    duration = models.IntegerField()
    # 運動距離（m）
    distance = models.IntegerField()
    # 歩数
    steps = models.IntegerField()

    class Meta:
        app_label = "record"


class Activity(models.Model):
    u"""
    運動項目データモデル
    """
    # 紐付くSegment
    username = models.CharField('username', max_length=256)
    # 運動項目
    activity_type = models.CharField('activity', max_length=256)
    #今回は運動項目グループは未使用
    #group = models.SmallIntegerField()
    # 開始日時（ミリ秒）（UTC時間）
    start_time = models.DateTimeField()
    # 終了日時（ミリ秒）（UTC時間）
    end_time = models.DateTimeField()
    # 運動時間（秒）
    duration = models.IntegerField()
    # 運動距離（m）
    distance = models.IntegerField()
    # 歩数
    steps = models.IntegerField()


    class Meta:
        app_label = "record"
