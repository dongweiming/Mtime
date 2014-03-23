#coding=utf-8
'''Workers处理任务'''
# 因为比较简单的项目,就都在一起了,没有拆分
import multiprocessing
# https://github.com/douban/CaoE, 父进程死掉杀掉子进程
import caoe
caoe.install()
import parse
import models
from schedulers import Message
from log import error, warn
from control import Scheduler, periodic, run

terminating = None
scheduler = Scheduler('worker')


# Fixed 不能CTRL-C http://stackoverflow.com/questions/14579474/multiprocessing-pool-spawning-new-childern-after-terminate-on-linux-python2-7
def initializer(terminating_):
    # This places terminating in the global namespace of the worker subprocesses.
    # This allows the worker function to access `terminating` even though it is
    # not passed as an argument to the function.
    global terminating
    terminating = terminating_


class Worker(object):
    '''执行任务类'''
    def __init__(self, map_func, num_workers=None, **kwargs):
        self.map_func = map_func
        self.inputs = Message.objects(state__ne=2, inprocess__ne=True)
        self.pool = multiprocessing.Pool(num_workers, **kwargs)

    def run(self, chunksize=1):
        try:
            self.pool.map(self.map_func, self.inputs, chunksize=chunksize)
        except KeyboardInterrupt:
            warn("^C pressed")
            self.pool.terminate()
        except:
            import traceback
            traceback.print_exc()


def mapper(queryset):
    try:
        if not terminating.is_set():
            real_mapper(queryset)
    except KeyboardInterrupt:
        terminating.set()


def real_mapper(queryset):
    this = Message.objects(task=queryset.task, payload=queryset.payload)
    STATE = True
    Model = getattr(models, queryset.task)
    this.update(set__inprocess=True)
    if queryset.task == 'Movie':
        for process in queryset.payload:
            ret = parse.get_movie_info(process)
            ret['movieid'] = process
            models.Movie(**ret).save()
        return
    Parse = getattr(parse, queryset.task + 'Parse')
    for process in queryset.payload:
        try:
            p = Parse(process)
            count = 1
            while 1:
                haspage = p()
                if haspage is None:
                    # 很可能404                                                                                        
                    break
                result, hasnext = haspage
                Model(**result).save()
                # 别名体系, 这样只需要全局记录一个人物就知道他们的全部别名
                for k, v in p._alias.items():
                    models.AliasName.objects.get_or_create(
                        name=k)[0].update(add_to_set__alias=v)
                if hasnext:
                    count += 1
                    url = p.original_url
                    p.set_url(url.replace('.html', '-{}.html'.format(count)))
                else:
                    #没有下一页就退出循环
                    break
        except:
            STATE = False
        else:
            models.IdFinished.objects(
                year=queryset.year).update(add_to_set__ids=[process])
    if STATE:
        this.update(set__state=2)
    else:
        this.update(set__state=3)
    this.update(set__inprocess=False)


def mtime_worker():
    terminating = multiprocessing.Event()
    w = Worker(mapper, initializer=initializer, initargs=(terminating, ))
    try:
        w.run()
    except:
        error('Other error')

def main():
    periodic(scheduler, mtime_worker)
    scheduler.run()


if __name__ == '__main__':
    run(main, __file__)
