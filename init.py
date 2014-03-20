#coding=utf-8

from datetime import datetime

from conf import TASK_BEAT
from schedulers import Task


def init_task_db():
    # init beat
    task = Task(type='beat', last_run_at=datetime.now(), interval=TASK_BEAT)
    task.save()


def main():
    init_task_db()


if __name__ == '__main__':
    main()
