# coding=utf-8
'''任务调度models'''
from datetime import datetime
from mongoengine import (Document, IntField, StringField, DateTimeField,
                         connect, ListField, BooleanField)

from conf import HOST, PORT, DATABASE

connect(DATABASE, host=HOST, port=PORT)


class Task(Document):
    '''设置的任务数据, 针对worker, beat'''
    type = StringField(max_length=60, required=True)  # 任务类型
    last_run_at = DateTimeField(
        default=datetime.now(), required=True)  # 上一次任务的执行时间
    interval = IntField(default=3600, required=True)  # 任务间隔,单位秒


class Message(Document):
    '''MQ存放在mongodb中的格式'''
    task = StringField(max_length=60, required=True, unique_with=['payload'])  # 任务类型
    year = IntField(default=1900) # 为了最后更新ids到IdFinished
    payload = ListField(StringField(max_length=20))  # 函数执行的参数
    # 任务状态, 0 未执行, 1 运行中, 2 已完成, 3 失败
    retry = IntField(default=0) # 错误重试次数
    state = IntField(default=0, required=True)
    error = StringField(default='', required=True)  # 失败日志
    inprocess = BooleanField(default=False, required=True)  # 是否在处理中

    meta = {
        #'index_drop_dups': True,
        'indexes': [('state', 'inprocess'), 'year'],
    }
