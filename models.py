# coding=utf-8
from datetime import datetime
from mongoengine import *

from conf import HOST, PORT, DATABASE

connect(DATABASE, host=HOST, port=PORT)

COLORS = ((0, u'黑白'), (1, '彩色'))


class MtimeMixin(object):
    movieid = IntField(required=True) # 基础类


class AliasName(Document, MtimeMixin):
    '''数据库中存在的名字和别名(英文名等)'''
    name = StringField(max_length=60, required=True) # 数据库中存在的名字
    alias = ListField(StringField(max_length=60, required=True)) # 这个人的别名


class Actor(EmbeddedDocument):
    '''演员信息'''
    mid = IntField(default=0, required=True) # 演员链接的唯一ID
    poster = StringField(max_length=100, required=True) # 海报缩略图
    name = StringField(max_length=60, required=True) # 演员名字
    play = StringField(max_length=60, required=True) # 剧中人物


class Director(EmbeddedDocument):
    '''导演信息'''
    mid = IntField(default=0, required=True) # 演员链接的唯一ID
    name = StringField(max_length=60, required=True) # 导演名字
    cnname = StringField(max_length=60) # 可能有中文翻译过来的名字
    poster = StringField(max_length=100) # 海报缩略图


class Fullcredits(Document, MtimeMixin):
    '''演职员表'''
    director = ListField(EmbeddedDocumentField(Director)) # 导演
    writer = ListField(StringField(max_length=30, required=True)) # 编剧
    actor = ListField(EmbeddedDocumentField(Actor)) # 演员
    produced = ListField(StringField(max_length=60, required=True)) # 制作人
    originalmusic = ListField(StringField(max_length=60, required=True)) # 原创音乐
    cinematography = ListField(StringField(max_length=60, required=True)) # 摄影
    filmediting = ListField(StringField(max_length=60, required=True)) # 剪辑
    #casting = ListField(StringField(max_length=60, required=True)) # 选角导演 # 新版本没有这4个字段了...
    #productiondesigner = ListField(StringField(max_length=60, required=True)) # 艺术指导
    artdirection = ListField(StringField(max_length=60, required=True)) # 美术设计
    #setdecoration = ListField(StringField(max_length=60, required=True)) # 布景师
    costumedesign = ListField(StringField(max_length=60, required=True)) # 服装设计
    #visualeffects = ListField(StringField(max_length=60, required=True)) # 视觉特效
    assistantdirector = ListField(StringField(max_length=60, required=True)) # 副导演/助理导演


class EmbeddedReleaseInfo(EmbeddedDocument):
    encountry = StringField(max_length=30, required=True) # 英文国家名
    cncountry = StringField(max_length=30, required=True) # 中文国家名
    releasetime = DateTimeField(default=datetime.now(), required=True) # 上映时间


class ReleaseInfo(Document, MtimeMixin):
    '''上映数据, update: 新版(2014, 3, 17)发行数据已经合并到Details里面'''
    country = ListField(EmbeddedDocumentField(EmbeddedReleaseInfo))


# 电影信息
class Movie(Document, MtimeMixin):
    # name = StringField(max_length=30, required=True) # 电影名
    score = FloatField(required=True) # 评分
    evaluate = StringField(max_length=30, required=True) # 评价
    scorer = IntField(default=0, required=True) # 评分人数
    want = IntField(default=0, required=True) # 想看
    collect = IntField(default=0, required=True) # 收藏数
    #poster = ListField(EmbeddedDocumentField(Poster))  # 海报缩略图
    #fullcredits = ReferenceField(Fullcredits)
    #details = ReferenceField(Details)
    #plot = ListField(EmbeddedDocumentField(Plot))
    #awards =  ListField(EmbeddedDocumentField(Awards))
    #scenes = ReferenceField(Scenes)
    #company = ReferenceField(Company)


class EmbeddedComment(EmbeddedDocument):
    name = StringField(max_length=30, required=True) # 发评论人
    image = StringField(max_length=60, required=True) # 评论人图片url
    title = StringField(max_length=60, required=True) # 标题
    content = StringField() # 评论内容
    publishdate = DateTimeField(default=datetime.now()) # 发表时间


class Comment(Document, MtimeMixin):
    comments = ListField(EmbeddedDocumentField(EmbeddedComment))


class EmbeddedMicroComment(EmbeddedDocument):
    name = StringField(max_length=30, required=True) # 发评论人
    image = StringField(max_length=60, required=True) # 评论人图片url
    publishdate = DateTimeField(default=datetime.now()) # 发表时间
    content = StringField() # 评论内容
    score = FloatField(required=True) # 评分
    from_ = StringField(max_length=60, required=True) # 来源
    commentcount = IntField(default=0, required=True) # 评论数
    repostcount = IntField(default=0, required=True) # 转发数


class MicroComment(Document, MtimeMixin):
    '''微影评'''
    comments = ListField(EmbeddedDocumentField(EmbeddedMicroComment))


class Company(Document, MtimeMixin):
    '''制作/发行'''
    release = ListField(StringField()) # 发行
    make = ListField(StringField()) # 制作
    stunt = ListField(StringField()) # 特技制作
    other =  ListField(StringField()) # 其他公司


###### Delete in next version
class ScenesComment(EmbeddedDocument):
    content = StringField(required=True) # 评论内容
    who = StringField(max_length=30, required=True) # 评论者


class Dialogue(EmbeddedDocument):
    endialogue = StringField(required=True) # 英文对白
    cndialogue = StringField(required=True) # 中文对白翻译

##### END
###### 幕后花絮
class EmbeddedScenes(EmbeddedDocument):
    title = StringField(max_length=30, required=True) # 主题
    content = ListField(StringField())


class Scenes(Document, MtimeMixin):
    '''幕后揭秘 update:新版本很多字段都没有了'''
    #comment = ListField(EmbeddedDocumentField(ScenesComment))
    #make = ListField(StringField()) # 幕后制作
    scene = ListField(EmbeddedDocumentField(EmbeddedScenes)) # 花絮
    #dialogue = ListField(EmbeddedDocumentField(Dialogue))
    #goofs = ListField(StringField()) # 穿帮镜头


###### 获奖记录
class Awarddetail(EmbeddedDocument):
    name = StringField(max_length=30, required=True) # 具体奖项名字
    people = StringField(max_length=60, required=True) # 获奖人


class Awardinfo(EmbeddedDocument):
    type = StringField(max_length=10, required=True) # 获奖类型
    detail = ListField(EmbeddedDocumentField(Awarddetail))


class Awardall(EmbeddedDocument):
    period = IntField(required=True) # 届
    year = IntField(required=True) # 年份
    all = ListField(EmbeddedDocumentField(Awardinfo))


class Awards(Document, MtimeMixin):
    name = StringField(max_length=30, required=True) # 奖项名字
    award = ListField(EmbeddedDocumentField(Awardall)) # 奖项相关获奖情况
###### end


class Plot(Document, MtimeMixin):
    '''剧情'''
    content = ListField(StringField()) # 剧情片段
    # publisher = StringField() # 发布者, 新版已经不存在
    # publishdate = DateTimeField(default=datetime.now(), required=True) # 发布时间, 新版已经不存在


class Poster(Document, MtimeMixin):
    '''海报缩略图'''
    no = IntField() # 号码
    url = StringField(max_length=60, required=True) # 图片地址


class Details(Document, MtimeMixin):
    '''详细信息'''
    alias = ListField(StringField()) # 中文/外文片名
    type =  ListField(StringField()) # 电影类型
    time = IntField(default=0, required=True) # 片长
    country = StringField(max_length=60, required=True) # 国家/地区
    language = ListField(StringField(max_length=10, required=True)) # 对白语言
    color = StringField(required=True, choices=COLORS) # 色彩
    format = StringField(max_length=30, required=True) # 幅面
    mixin = ListField(StringField(max_length=20)) # 混音
    mpaa = StringField() # MPAA评级
    level = ListField(StringField(max_length=30)) # 级别
    cost = StringField() # 制作成本
    start = ListField(DateTimeField()) # 拍摄日期
    camera = StringField() # 摄影机
    filmformat = StringField() # 摄制格式
    printformat = StringField() # 洗印格式


class IdFinished(Document, MtimeMixin):
    '''完成的电影ids, 防各种原因重新抓取'''
    year = IntField(required=True) # 分配的电影的年份
    ids = ListField(required=True) # 电影唯一id


class YearFinished(Document, MtimeMixin):
    '''完成的电影的年份'''
    year = IntField(required=True) # 完成的年份


class EmbeddedCharacter(EmbeddedDocument):
    '''角色介绍, 新版增加'''
    bigposter = StringField(max_length=100) # 角色大图, 小图在演职员表里面会记录
    name = StringField(max_length=30, required=True) # 角色
    introduction = StringField() # 角色介绍


class Character(Document, MtimeMixin):
    character = ListField(EmbeddedDocumentField(EmbeddedCharacter))
