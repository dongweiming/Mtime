# coding=utf-8

'''调度的抽象'''
import os
import sys
import time
import heapq
import atexit
from datetime import timedelta, datetime
from collections import namedtuple
from signal import SIGKILL
from os.path import join, splitext, basename

from schedulers import Task
from log import info, debug

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
        debug('Change interval to: ' + str(interval))
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
                    debug('Excute Cron Starting...')
                    action(*argument)
                    debug('Excute Cron Success')
                    self.task.update(set__last_run_at=now)
                    s(0)  # 把执行权放给其他程序
                else:
                    heapq.heappush(q, event)


def periodic(scheduler, action, actionargs=()):
    '''定时调度函数'''
    scheduler.start(1, periodic,
                    (scheduler, action, actionargs))
    action(*actionargs)


class Daemon(object):

    '''将程序做成daemon版'''

    def __init__(self, run, pidfile=None, stdin='/dev/null', stdout=None,
                 stderr=None, default=None):
        self.run = run
        self.stdin = stdin
        self.default = default
        self.here = os.path.abspath(os.path.dirname(__file__))
        self.stdout = self.path(stdout)
        self.stderr = self.path(stderr)
        self.pidfile = self.path(pidfile, suffix='.pid')

    def path(self, std, suffix='.log'):
        return join(self.here, 'logs',
                    splitext(basename(self.default))[0]) + suffix

    def daemonize(self):

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" %
                             (e.errno, e.strerror))
            sys.exit(1)

        os.chdir(self.here)
        os.setsid()
        os.umask(022)
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno,
                                                            e.strerror))
            sys.exit(1)
        if sys.platform != 'darwin':
            sys.stdout.flush()
            sys.stderr.flush()
            si = open(self.stdin, 'r')
            so = open(self.stdout, 'a+')
            se = open(self.stderr, 'a+', 0)
            os.dup2(si.fileno(), sys.stdin.fileno())
            os.dup2(so.fileno(), sys.stdout.fileno())
            os.dup2(se.fileno(), sys.stderr.fileno())

        atexit.register(self.delpid)
        pid = str(os.getpid())
        open(self.pidfile, 'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        pid = self.get_pid()
        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        self.daemonize()
        self.run()

    def stop(self):
        pid = self.get_pid()
        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)
            return

        try:
            while 1:
                os.kill(pid, SIGKILL)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        self.stop()
        self.start()

    def get_pid(self):
        try:
            with open(self.pidfile) as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None
        except SystemExit:
            pid = None
        return pid

    def alive(self):
        pid = self.get_pid()
        if pid is None:
            pid = 0
        if sys.platform != 'darwin':
            if os.path.exists('/proc/%d' % pid):
                print pid
            else:
                print 0
        else:
            print pid


def run(main, default):
    daemon = Daemon(run=main, default=default)
    if len(sys.argv) == 2:
        arg = sys.argv[1]
        if arg in ['start', 'stop', 'restart', 'alive']:
            if arg != 'alive':
                info(sys.argv[0] + ' ' + arg)
            getattr(daemon, arg)()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
