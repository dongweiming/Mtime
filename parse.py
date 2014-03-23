# coding=utf-8
'''
使用Xpath解析html页面
'''
import re
import copy
from lxml import etree
from collections import defaultdict
from datetime import datetime
from urllib2 import HTTPError

from spider import Spider, Movie, Comment
from conf import MOVIE_API, MOVIE_PAGE, COMMENT_API
from log import debug, warn

movie_regex = re.compile(r'http://movie.mtime.com/(\d+)/')
people_regex = re.compile(r'http://people.mtime.com/(\d+)/')
movie_page_regex = re.compile(r'pageindex=(\\)?"(\d+)(\\)?(\\)?"')
awardinfo_regex = re.compile(ur'(\d+).*第(\d+)届')
detail_country_regex = re.compile(r'\[(.*)\]')
# 这是mtime的防爬后的提示关键句
mtime_vcodeValid_regex = re.compile(r'\"vcodeValid\":false,\"isRobot\":true')

date_regex = re.compile(ur'(\d+)年(\d+)月(\d+)日')
name_regex = re.compile(ur'([\u4e00-\u9fa5]+)\s+(.*)')  # 匹配中英文名字
favoritedCount_regex = re.compile(r'\"favoritedCount\":(\d+),')
rating_regex = re.compile(r'"rating":(\d.?\d),')
ratingCount_regex = re.compile(r'"ratingCount":(\d+),')
wantToSeeCount_regex = re.compile(r'"wantToSeeCount":(\d+),')
comment_regex = re.compile(
    r'\"reviewPraiseCount\":\[(.*)\].*\"reviewPraiseStatus\".*\"reviewShareCount\":\[(.*)\].*\"reviewCommentCount\":\[(.*)\]')  # noqa

movie_url = 'http://movie.mtime.com/{}/{}'


def make_datetime(text):
    '''通过中文类型的文本解析成datetime类型的日期结果'''
    make = lambda t: datetime(int(t[0]), int(t[1]), int(t[2]))
    t = date_regex.findall(text)
    if t:
        if len(t) == 1:
            return make(t[0])
        else:
            return [make(i) for i in t]
    else:
        return datetime.now()


class Parse(object):

    '''爬取标准类'''

    def __init__(self, movie_id):
        self.id = movie_id
        self._alias = defaultdict(set)
        self.set_url()
        self.d = defaultdict(list)

    def set_url(self, url):
        self.url = url
        self.original_url = url # 其中获取评论页或自动跳转走,这里保留原url供解析下一页使用

    def xpath(self):
        raise NotImplementedError()

    @property
    def alias(self):
        '''别名系统'''
        return self._alias

    def spider(self):
        # 请求头增加cc
        s = Spider(additional_headers={'Cache-Control': 'max-age=0'})
        try:
            s.fetch(self.url)
        except HTTPError as e:
            # 检查该电影相关页面是否存在
            if e.msg == 'Not Found':
                return
        # 因为中文被编码成utf-8之后变成'/u2541'之类的形式，lxml一遇到"/"就会认为其标签结束
        return etree.HTML(s.content.decode('utf-8'))

    def __call__(self):
        '''调用类'''
        self.page = self.spider()
        if self.page is None:
            return
        hasnext = self.xpath() is not None
        self.d['movieid'] = self.id
        return self.d, hasnext

    def check_next_page(self):
        '''检查是否有下一页'''
        return self.page.xpath('//a[@id=\"key_nextpage\\"]')


# Delete in next version
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

# END


class DetailsParse(Parse):

    def set_url(self):
        self.url = movie_url.format(self.id, 'details.html')

    def xpath(self):
        part = self.page.xpath('//dl[@class="wp50 fl"]')
        # 第一部分是中文外文数据
        aliases = part[0].xpath('dd')
        cnalias = [a.text.strip() for a in aliases[0].xpath('p')]
        enalias = [a.text.strip() for a in aliases[1].xpath('p')]
        try:
            time = aliases[2].xpath('p')[0].text
            date = make_datetime(other[1].xpath('p')[0].text)
            language = (i.text.encode('utf-8').replace('/', '').strip()
                        for i in other[2].xpath('p/a'))
            site = [other[3].xpath('p/a')[0].text,  # 官网缩写 
                    other[3].xpath('p/a')[0].attrib['href']]  # 官网url
        except IndexError:
            warn('{} has not some info'.format(self.id))
        # 制作成本, 拍摄日期等数据
        other = part[1].xpath('dd')
        cost = other[0].xpath('p')[0].text
        # 发行信息
        part = self.page.xpath(
            '//dl[@id="releaseDateRegion"]/dd//div/ul/li/div[@class="countryname"]/p/span')  # noqa
        release = []
        for p in part:
            encountry = p.text.strip()
            cncountry = p.getparent().text.strip()
            time_text = p.getparent().getparent().getparent().xpath(
                'div[@class=\"datecont\"]')[0].text
            releasetime = make_datetime(time_text)
            release.append({'encountry': encountry, 'cncountry': cncountry,
                            'releasetime': releasetime})
        part = self.page.xpath(
            '//dl[@id="companyRegion"]/dd/div/div[@class="fl wp49"]')
        detail = defaultdict(list)
        for p in part:
            if p.xpath('h4')[0].text == u'制作公司':
                cur_type = 'make'
            else:
                cur_type = 'publish'
            for p2 in p.xpath('ul/li'):
                name = p2.xpath('a')[0].text
                country_info = p2.xpath('span')[0].text
                match = detail_country_regex.findall(country_info)
                if match:
                    detail[cur_type] += [{'name': name, 'country': match[0]}]
                else:
                    detail[cur_type] += [{'name': name}]
#        details = {'enalias': enalias, 'cnalias': cnalias, 'time': time,
#                   'language': language, 'cost': cost, 'date': date,
#                   'release': release, 'site': site}
        d = locals()
        d.pop('self')
        detail.update(d)
        self.d.update(detail)


class AwardsParse(Parse):

    def set_url(self):
        self.url = movie_url.format(self.id, 'awards.html')

    def xpath(self):
        all = self.page.xpath('//div[@id="awardInfo_data"]/dd')
        for elem in all:
            name = elem.xpath('h3/b')[0].text
            info = defaultdict(list)
            year, period, awards = 0, 0, '未知'
            try:
                yp = elem.xpath('h3/span/a')[0].text
            except:
                # 可能获了一个大奖的好几届的奖
                for e in elem.xpath('dl/child::*'):
                    if e.tag == 'dt':
                        if info:
                            # 因为是一个dl里面包含多个年份届数的数据, 都要独立提交
                            self.d['awards'] += [dict(
                                name=name, year=year, period=period,
                                awards=awards)]
                            info = defaultdict(list)

                        if e.attrib.get('style'):
                            yp = e.xpath('a')[0].text
                            year, period = awardinfo_regex.findall(yp)[0]
                        else:
                            cur_type = e.text
                    elif e.tag == 'dd':
                        awardtype = e.xpath('span')[0].text
                        try:
                            people = e.xpath('a')[0].text
                        except IndexError:
                            people = ''
                        info[cur_type] += [(people, awardtype)]
            else:
                year, period = awardinfo_regex.findall(yp)[0]
                for e in elem.xpath('dl/child::*'):
                    if e.tag == 'dt':
                        cur_type = e.text
                    elif e.tag == 'dd':
                        awardtype = e.xpath('span')[0].text
                        try:
                            people = e.xpath('a')[0].text
                        except IndexError:
                            people = ''
                        info[cur_type] += [(people, awardtype)]
                awards = []
                for k, v in info.items():
                    awards.append(dict(type=k, peoples=v))
                self.d['awards'] += [dict(name=name, year=year, period=period,
                                          awards=awards)]


class CommentParse(Parse):

    def set_url(self):
        self.url = movie_url.format(self.id, 'comment.html')

    def xpath(self):
        all = self.page.xpath('//dl[@class="clearfix"]')
        # 变态的mtime获取评论的方法是通过api服务
        blogids = [i.attrib['blogid']
                   for i in self.page.xpath('//div[@class=\"db_comtool\"]')]
        s = Comment(params={'Ajax_CallBackArgument0': ','.join(blogids),
                            'Ajax_CallBackArgument1': '',
                            'Ajax_RequestUrl': self.url})
        s.fetch(COMMENT_API)
        comment_api = comment_regex.findall(s.content)
        for index, i in enumerate(all):
            comments = i.xpath('dd[@class=\"comboxcont\"]/div')
            if not comments:
                # 奇怪的是,第一个不是我要的div
                continue
            hasposter = i.xpath('div[@class=\"fr\"]/a/img')
            if hasposter:
                poster = hasposter[0].attrib['src']
            else:
                poster = ''
            comment = comments[0]
            t = comment.xpath('h3/a')[0]
            title = t.text  # 文章标题
            url = t.attrib['href']
            try:
                shortcontent = comment.xpath('p')[0].text.strip()
            except AttributeError:
                # 某些坪林没显示缩略文
                shortcontent = ''
            combox = i.xpath('dd[@class=\"comboxuser2\"]/div')[0]
            image = combox.xpath('a/img')[0].attrib['src']
            name = combox.xpath('a/img')[0].attrib['alt']
            commenter_url = combox.xpath('a/img')[0].attrib['src']
            date = combox.xpath('p')[1].xpath('a')[0].attrib['entertime']
            publishdate = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            hasnext = self.check_next_page()
            self.url = url
            # 重新设置要爬的页面
            content = self.get_content()
            look = combox.xpath('p')[2].text
            score = 0
            if look:
                # 表示看过
                score = float(combox.xpath('p')[2].xpath('span')[0].text)
            ac, rc, cc = 0, 0, 0
            if comment_api:
                ac, rc, cc = comment_api[0]
                p = lambda x: x.split(',')[index - 1]  # 多了一个div
                ac, rc, cc = p(ac), p(rc), p(cc)
            self.d['comments'] += [{'commenter_url': commenter_url,
                                    'ac': ac, 'rc': rc, 'url': url,
                                    'poster': poster, 'image': image,
                                    'title': title, 'name': name,
                                    'score': score, 'content': content,
                                    'shortcontent': shortcontent, 'cc': cc,
                                    'publishdate': publishdate}]
            if hasnext:
                '''判断还有下一页会传回去继续累加页面,直到没有下一页'''
                return True

    def get_content(self):
        '''爬取长评论页'''
        ret = self.spider()
        all = ret.xpath('//div[@class="db_mediacont db_commentcont"]/p')
        contents = []
        for elem in all:
            istext = elem.xpath('text()')
            if istext:
                if istext[0].strip():
                    # 文本, 否则空行
                    cur_type = 'text'
                    content = istext[0].strip()
                else:
                    continue
            isembed = elem.xpath('embed')
            if isembed:
                # 内嵌flash之类
                cur_type = 'embed'
                content = str(isembed[0].attrib)
            isimage = elem.xpath('img')
            if isimage:
                # 图片
                cur_type = 'image'
                image = []
                for i in isimage:
                    image.append(i.attrib['src'])
                content = ','.join(image)
            contents.append({'type': cur_type, 'content': content})
        return contents


class MicroCommentParse(Parse):

    def set_url(self):
        self.url = movie_url.format(self.id, 'shortcomment.html')

    def xpath(self):
        all = self.page.xpath(
            '//div[@class="db_shortcomment db_shortcomlist"]/dl/dd/div')
        tweetids = [i.attrib['tweetid'] for i in all]
        s = Comment(params={'Ajax_CallBackArgument0': '',
                            'Ajax_CallBackArgument1': ','.join(tweetids),
                            'Ajax_RequestUrl': self.url})
        s.fetch(COMMENT_API)
        comment_api = comment_regex.findall(s.content)
        for index, elem in enumerate(all):
            content = elem.xpath('h3')[0].text
            user = elem.xpath('div[@class="comboxuser"]/div')[0]
            url = user.xpath('a')[0].attrib['href']
            info = user.xpath('p')[0].xpath('a')[0]
            commenter_url = info.attrib['href']
            name = info.text
            image = user.xpath('a/img')[0].attrib['src']
            try:
                score = float(user[0].xpath('p')[1].xpath('span/span')[0].text)
            except (IndexError, TypeError, ValueError):
                score = 0
            date = user.xpath('p')[1].xpath('a')[0].attrib['entertime']
            publishdate = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            hasnext = self.check_next_page()
            ac, rc, cc = 0, 0, 0
            if comment_api:
                ac, rc, cc = comment_api[0]
                p = lambda x: x.split(',')[index]
                ac, rc, cc = p(ac), p(rc), p(cc)
            ret = copy.deepcopy(locals())
            ret.pop('self')
            self.d['microcomments'] += [ret]
            if hasnext:
                return True


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
            l = []
            for i in elem.xpath(xpath + 'div/p|div/dl/dd|dl/dd'):
                l.extend(filter(lambda x: x.strip(), i.xpath('text()')))
            self.d['scene'] += [{'title': title, 'content': l}]


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
        
        if len(type) > len(common):
            # 有些老电影没有全部数据
            l = len(common)
        else:
            l = len(type)
        for offset in range(l):
            c = common[offset]
            for i in c.xpath('p'):
                name = i.xpath('a')[0].text
                if name is None:
                    continue
                match = name_regex.findall(name)
                if match:
                    match = match[0]
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
        try:
            href = director.xpath('div/a')[0].attrib['href']
            people = people_regex.findall(href)
            director_dict['mid'] = people[0]
        except IndexError:
            warn('[{}] No director'.format(self.id))
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
            try:
                play = a.xpath(name_path)[-1].text
            except IndexError:
                # 无饰演角色信息
                play = ''
            one_actor['play'] = play
            self.d['actor'] += [one_actor]

# 通过搜索接口获取要爬取的电影ids


def get_movie_ids(instance):
    '''获取电影在mtime的唯一id'''
    if mtime_vcodeValid_regex.search(instance.content):
        return
    return movie_regex.findall(instance.content)


def get_movie_pages(instance):
    '''获取当前年份包含电影的页数'''
    try:
        return max([int(i[1]) for i in
                    movie_page_regex.findall(instance.content)])
    except ValueError:
        # 只有一页
        if mtime_vcodeValid_regex.search(instance.content):
            return
        return 1
# end


def checkmatch(regex, instance, type=int):
    '''抽象代码做多项正则匹配'''
    match = regex.findall(instance.content)
    if not match:
        return 0
    else:
        return type(match[0])


# 通过javascript获取评分等信息
def get_movie_info(id):
    s = Movie(params={'Ajax_CallBackArgument1': id,
                      'Ajax_RequestUrl': MOVIE_PAGE.format(
                          id=id, timestamp=Movie.get_timestamp())})
    s.fetch(MOVIE_API)
    favorited = checkmatch(favoritedCount_regex, s)
    rating = checkmatch(rating_regex, s, float)
    ratingcount = checkmatch(ratingCount_regex, s)
    want = checkmatch(wantToSeeCount_regex, s)
    del s, id
    return locals()
