# coding=utf-8
'''
使用Xpath解析html页面
'''
import re
from lxml import etree
from collections import defaultdict
from datetime import datetime

from spider import Spider, Movie
from utils import group
from conf import MOVIE_API, MOVIE_PAGE

movie_regex = re.compile(r'http://movie.mtime.com/(\d+)/')
movie_page_regex = re.compile(r'pageindex=\\"(\d+)\\\\"')
# 这是mtime的防爬后的提示关键句
mtime_vcodeValid_regex = re.compile(r'\"vcodeValid\":false,\"isRobot\":true')

date_regex = re.compile(ur'(\d+)年(\d+)月(\d+)日')
favoritedCount_regex = re.compile(r'\"favoritedCount\":(\d+),')
rating_regex = re.compile(r'"rating":(\d.?\d),')
ratingCount_regex = re.compile(r'"ratingCount":(\d+),')
wantToSeeCount_regex = re.compile(r'"wantToSeeCount":(\d+),')

movie_url = 'http://movie.mtime.com/{}/{}'

class Parse(object):
    '''爬取标准类'''
    def __init__(self, movie_id):
        self.id = movie_id
        self._alias = defaultdict(set)
        self.set_url()
        self.d = defaultdict(list)
        self.d['movieid'] = movie_id

    def set_url(self):
        raise NotImplementedError()

    def xpath(self):
        raise NotImplementedError()

    def spider(self):
        raise NotImplementedError()

    @property
    def alias(self):
        '''别名系统'''
        return self._alias

    def result(self):
        # 请求头增加cc
        s = Spider(additional_headers={'Cache-Control': 'max-age=0'})
        s.fetch(self.url)
        # 因为中文被编码成utf-8之后变成'/u2541'之类的形式，lxml一遇到"/"就会认为其标签结束
        data = s.content.decode('utf-8')
        self.page = etree.HTML(data)
        self.xpath()
        return self.d


class ReleaseInfoParse(Parse):

    def set_url(self):
        self.url = movie_url.format(self.id, 'releaseinfo.html')

    def xpath(self):
        all = self.page.xpath('//dl[@class="release_date_list"]/dd')
        if not all:
            # 404
            return
        for elem in all:
            en = elem.xpath('span/a')[0].text
            cn = elem.xpath('span/em')[0].text
            date = elem.xpath('span[@class="date"]')[0].text
            match = date_regex.search(date)
            if match:
                t = match.groups()
                date = datetime(int(t[0]), int(t[1]), int(t[2]))
            else:
                date = datetime.now()
            self.d['country'] += [{'encountry': en, 'cncountry': cn,
                                   'releasetime': date}]


class FullcreditsParse(Parse):

    def set_url(self):
        self.url = movie_url.format(self.id, 'fullcredits.html')

    def xpath(self):
        common = self.page.xpath('//div[@class="credits_list"]')
        type = ['director', 'writer', 'produced', 'cinematography',
                'filmediting', 'originalmusic', 'artdirection',
                'costumedesign', 'assistantdirector']

        for offset in range(len(type)):
            c = common[offset]
            img = c.xpath('div/a/img')
            # 可能有图片
            if img:
                image = img[0].attrib['src']
        # 导演信息
        director = common[0]
        img = director.xpath('div/a/img')
        # 可能有图片
        if img:
            self.d['director']['poster'] = img[0].attrib['src']
        cn = director.xpath('div/h3/a')
        if cn:
            self.d['director']['cnname'] = cn[0].text
        self.d['director']['name'] = director.xpath('div/p/a')[0].text
        # end

        self.get_actor(all[2])
        self.get_produced(all[3])
        for offset in range(4, len(type)):
            self.common(all[offset], type[offset])

    def common(self, block, type):
        for i in block.xpath('li'):
            l = [c.text for c in i.xpath('a')]
            print l
            self.d[type] += [l[0]]
            if len(l) == 2:
                self._alias[l[0]].add(l[1])

    def get_actor(self, block):
        '''格式不服规范不能直接按4分组'''
        for i in block.xpath('li'):
            elems = i.xpath('*')
            o = elems[0]
            t = elems[1]
            s = elems[2]
            if len(elems) == 4:
                f = elems[3]
            poster = o.xpath('img')[0].attrib['src']
            name = t.text
            if s.text is None:
                play = s.text
            else:
                play = f.text
                self._alias[name].add(s.text)
            self.d['actor'] += [{'poster': poster, 'name': name, 'play': play}]

    def get_produced(self, block):
        for i in block.xpath('li'):
            elems = i.xpath('*')
            o = elems[0]
            t = elems[1]
        #for o, t, _ in group(block.xpath('li/*'), 3):
            self.d['produced'] += [o.text]
            if t.text is not None:
                self._alias[o.text].add(t.text)


### 通过搜索接口获取要爬取的电影ids
def get_movie_ids(instance):
    '''获取电影在mtime的唯一id'''
    if mtime_vcodeValid_regex.search(instance.content):
        return
    return movie_regex.findall(instance.content)


def get_movie_pages(instance):
    '''获取当前年份包含电影的页数'''
    try:
        return max(movie_page_regex.findall(instance.content))
    except ValueError:
        # 只有一页
        if mtime_vcodeValid_regex.search(instance.content):
            return
        return 1
### end


def checkmatch(regex, instance):
    '''抽象代码做多项正则匹配'''
    match = regex.findall(instance.content)
    if not match:
        return 0
    else:
        return match[0]

### 通过javascript获取评分等信息
def get_movie_info(id):
    s = Movie(params={'Ajax_CallBackArgument1': id,
                      'Ajax_RequestUrl': MOVIE_PAGE.format(
                          id=id, timestamp=Movie.get_timestamp())})
    s.fetch(MOVIE_API)
    favoritedCount = checkmatch(favoritedCount_regex, s)
    rating = checkmatch(rating_regex, s)
    ratingCount = checkmatch(ratingCount_regex, s)
    wantToSeeCount = checkmatch(wantToSeeCount_regex, s)
    del s, id
    return locals()
