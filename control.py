#coding=utf-8

'''调度的抽象'''
import time
import heapq
from datetime import timedelta, datetime
from collections import namedtuple

from schedulers import Task

Event = namedtuple('Event', 'time priority action argument')


# TODO priority
class Scheduler(object):
    '''调度'''
    def __init__(self, task_name):
        self._queue = []
        self.task = Task.objects(type=task_name).first()

    def change_interval(self, interval=None, incr=False, decr=False):
        '''改变任务执行的间隔'''
        if incr:
            interval = self.task.interval * 2
        elif decr:
            interval = self.task.interval / 2
        elif interval is not None:
            interval = interval
        self.task.update(set__interval=interval)

    @property
    def get_interval(self):
        '''获取当前task的执行间隔'''
        return self.task.interval

    def start(self, priority, action, argument):
        now = datetime.now()
        next_time = now + timedelta(seconds=self.task.interval)
        event = Event(next_time, priority, action, argument)
        heapq.heappush(self._queue, event)
        return event

    def run(self):
        q = self._queue
        pop = heapq.heappop
        s = time.sleep
        while q:
            next_time, priority, action, argument = checked_event = q[0]
            now = datetime.now()
            if now < next_time:
                s((next_time - now).total_seconds())
            else:
                event = pop(q)
                if event is checked_event:
                    action(*argument)
                    self.task.update(set__last_run_at=now)
                    s(0) # 把执行权放给其他程序
                else:
                    heapq.heappush(q, event)


def periodic(scheduler, action, actionargs=()):
    '''定时调度函数'''
    scheduler.start(1, periodic,
                    (scheduler, action, actionargs))
    action(*actionargs)
