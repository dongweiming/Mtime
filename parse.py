# coding=utf-8
'''
使用Xpath解析html页面
'''
import re
from lxml import etree
from collections import defaultdict
from datetime import datetime
from urllib2 import HTTPError

from spider import Spider, Movie
from utils import group
from conf import MOVIE_API, MOVIE_PAGE

movie_regex = re.compile(r'http://movie.mtime.com/(\d+)/')
people_regex = re.compile(r'http://people.mtime.com/(\d+)/')
movie_page_regex = re.compile(r'pageindex=(\\)?"(\d+)(\\)?(\\)?"')
# 这是mtime的防爬后的提示关键句
mtime_vcodeValid_regex = re.compile(r'\"vcodeValid\":false,\"isRobot\":true')

date_regex = re.compile(ur'(\d+)年(\d+)月(\d+)日')
name_regex = re.compile(ur'([\u4e00-\u9fa5]+)\s+(.*)') # 匹配中英文名字
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
        try:
            s.fetch(self.url)
        except HTTPError as e:
            # 检查该电影相关页面是否存在
            if e.msg == 'Not Found':
                return
        # 因为中文被编码成utf-8之后变成'/u2541'之类的形式，lxml一遇到"/"就会认为其标签结束
        data = s.content.decode('utf-8')
        self.page = etree.HTML(data)
        self.xpath()
        self.d['movieid'] = self.id
        return self.d


###### Delete in next version
class ReleaseInfoParse(Parse):
    '''新版(2014, 3, 17)发行数据已经合并到Details里面'''
    def set_url(self):
        self.url = movie_url.format(self.id, 'releaseinfo.html')

    def xpath(self):
        all = self.page.xpath('//dl[@class="release_date_list"]/dd')
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

###### END
class CharacterParse(Parse):

    def set_url(self):
        self.url = movie_url.format(self.id, 'characters.html')

    def xpath(self):
        all = self.page.xpath('//dd[@class=\"cha_box\"]')
        for elem in all:
            character = {}
            bigposter = ''
            img = elem.xpath('img')
            if img:
                bigposter = img[0].attrib['src']
            character['bigposter'] = bigposter
            name = elem.xpath('div/div/p[@class="enname"]')[0].text
            intro = elem.xpath('div/div[@class=\"cha_mid\"]')[0].text
            character['introduction'] = intro
            character['name'] = name
            self.d['character'] += [character]


class ScenesParse(Parse):

    def set_url(self):
        self.url = movie_url.format(self.id, 'behind_the_scene.html')

    def xpath(self):
        all = self.page.xpath('//div[@class="revealed_modle"]')
        if not all:
            # Mtime 前段不够严谨
            all = self.page.xpath('//div[@class="revealed_modle "]')
            if not all:
                return
        for elem in all:
            xpath = ''
            try:
                title = elem.xpath(xpath + 'h3')[0].text
            except IndexError:
                xpath = 'div/'
                title = elem.xpath(xpath + 'h3')[0].text
            txt = ''
            l = []
            for i in elem.xpath(xpath + 'div/p|div/dl/dd|dl/dd'):
                l.extend(filter(lambda x: x.strip(), i.xpath('text()')))
            self.d['scene'] += [{'title': title, 'content':l}]

class PlotParse(Parse):

    def set_url(self):
        self.url = movie_url.format(self.id, 'plots.html')

    def xpath(self):
        all = self.page.xpath('//div[@class="plots_box"]')
        for elem in all:
            l = []
            all_p = elem.xpath('div/p')
            for p in all_p:
                try:
                    # 第一个字特殊处理:大写
                    other = p.xpath('span/text()')[1]
                    txt = p.xpath('span/text()')[0] + other
                except IndexError:
                    # 段落中的非第一段
                    txt = p.xpath('text()')[0]
                l.append(txt)
            # 保留了多段之间的u'\u3000\u3000'
            self.d['content'] += l


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
            for i in c.xpath('p'):
                name = i.xpath('a')[0].text
                if name is None:
                    continue
                match = name_regex.findall(name)
                if match:
                    self._alias[match[1]].add(match[0])
                    name = match[1]
                self.d[type[offset]] += [name]

        # 导演信息, 其实我感觉导演可能有多个,单个烦了好几个电影导演都一个.没找到xpath范例
        director = common[0]
        img = director.xpath('div/a/img')
        # 可能有图片
        director_dict = {}
        if img:
            director_dict['poster'] = img[0].attrib['src']
        href = director.xpath('div/a')[0].attrib['href']
        people = people_regex.findall(href)
        director_dict['mid'] = people[0]
        cn = director.xpath('div/h3/a')
        if cn:
            name = director.xpath('div/p/a')[0].text
            director_dict['name'] = name
            self._alias[name].add(cn[0].text)
        self.d['director'] = [director_dict]
        # end
        # 获取演员信息
        self.get_actor()

    def get_actor(self):
        actor = self.page.xpath('//div[@class="db_actor"]/dl/dd')
        for a in actor:
            one_actor = {}
            path = 'div[@class="actor_tit"]/div/'
            try:
                href = a.xpath(path + 'a')[0].attrib['href']
                name_path = 'div[@class="character_tit"]/div/h3'
            except IndexError:
                path = 'div[@class="actor_tit"]/'
                name_path = 'div/div/h3'
                href = a.xpath(path + 'h3/a')[0].attrib['href']
            people = people_regex.findall(href)
            one_actor['mid'] = people[0]
            img = a.xpath(path + 'a/img')
            if img:
                one_actor['poster'] = img[0].attrib['src']
            try:
                name = a.xpath(path + 'h3/a')[0].text
            except IndexError:
                # 只有中文名
                name = None
            one_actor['name'] = name
            cn = a.xpath(path + 'h3/a')
            if cn:
                cnname = cn[0].text
                if name is None:
                    name = cnname
                self._alias[name].add(cnname)
            play = a.xpath(name_path)[-1].text
            one_actor['play'] = play
            print one_actor
            self.d['actor'] += [one_actor]

### 通过搜索接口获取要爬取的电影ids
def get_movie_ids(instance):
    '''获取电影在mtime的唯一id'''
    if mtime_vcodeValid_regex.search(instance.content):
        return
    return movie_regex.findall(instance.content)


def get_movie_pages(instance):
    '''获取当前年份包含电影的页数'''
    try:
        return max([int(i[1]) for i in movie_page_regex.findall(instance.content)])
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
