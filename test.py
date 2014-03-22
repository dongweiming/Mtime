#coding=utf-8
import models
import parse
from schedulers import Message

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
            raise
            STATE = False
        else:
            models.IdFinished.objects(
                year=queryset.year            ).update(add_to_set__ids=[process])
    if STATE:
        this.update(set__state=2)
    else:
        this.update(set__state=3)
    this.update(set__inprocess=False)

all = Message.objects(state__ne=2)

for i in all:
    try:
        real_mapper(i)
    except:
        raise
