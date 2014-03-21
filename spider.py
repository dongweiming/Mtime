# coding=utf-8
'''
爬虫
'''
import zlib
import urllib
import urllib2
import cookielib
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
from gzip import GzipFile
from datetime import datetime
from collections import OrderedDict

from utils import get_user_agent
from log import debug


# deflate support
def deflate(data):
    try:
        return zlib.decompress(data, -zlib.MAX_WBITS)
    except zlib.error:
        return zlib.decompress(data)


class ContentEncodingProcessor(urllib2.BaseHandler):
    '''A handler to add gzip capabilities to urllib2 requests'''
    cookiejar = None

    def __init__(self, cookie_support, additional_headers):
        self.additional_headers = additional_headers
        if cookie_support:
            self.cookiejar = cookielib.CookieJar()

    def http_request(self, req):
        # 默认的头信息
        req.add_header('Accept-Encoding', 'gzip, deflate')
        req.add_header('User-Agent', get_user_agent())
        req.add_header('Accept-Language',
                       'zh-cn,zh;q=0.8,en-us;q=0.5,en;q=0.3')
        if self.additional_headers is not None:
            req.headers.update(self.additional_headers)
        if self.cookiejar is not None:
            self.cookiejar.add_cookie_header(req)
        return req

    def http_response(self, req, resp):
        if self.cookiejar is not None:
            self.cookiejar.extract_cookies(resp, req)
        # 页面没有压缩,直接返回,比如调用API返回JSON数据
        if resp.headers.get("content-encoding") not in ('gzip', 'deflate'):
            return resp
        old_resp = resp
        content = resp.read()

        # gzip
        if resp.headers.get("content-encoding") == "gzip":
            gz = GzipFile(
                fileobj=StringIO(content),
                mode="r"
            )
        # deflate
        elif resp.headers.get("content-encoding") == "deflate":
            gz = StringIO(deflate(content))
        resp = urllib2.addinfourl(
            gz, old_resp.headers, old_resp.url, old_resp.code)
        resp.msg = old_resp.msg
        return resp


class Spider(object):
    def __init__(self, cookie_support=True, additional_headers=None,
                 params={}):
        self.cookie_support = cookie_support
        self.additional_headers = additional_headers
        self.params = params

    def make_query(self):
        '''基本队列'''
        return {}

    def fetch(self, url):
        debug('Fetch Url: {} start...'.format(url))
        opener = urllib2.build_opener(
            ContentEncodingProcessor(self.cookie_support,
                                     self.additional_headers),
            urllib2.HTTPHandler)
        urllib2.install_opener(opener)
        params = urllib.urlencode(self.make_query())
        if params:
            url = '{}?{}'.format(url, params)
        req = urllib2.Request(url)
        self.content = urllib2.urlopen(req).read()
        debug('Fetch Url: {} done'.format(url))

    @classmethod
    def get_timestamp(cls):
        now = datetime.now()
        timestamp = ''
        for i in (now.year, now.month, now.day, now.hour, now.minute,
                  now.second, str(now.microsecond)[:5]):
            timestamp += str(i)
        return timestamp


class Search(Spider):
    '''搜索电影用的爬虫'''
    def make_query(self):
        params = self.params
        if not isinstance(params, OrderedDict):
            d = OrderedDict()
            d['Ajax_CallBack'] = params['Ajax_CallBack']
            d['Ajax_CallBackType'] = params['Ajax_CallBackType']
            d['Ajax_CallBackMethod'] = params['Ajax_CallBackMethod']
            d['Ajax_CrossDomain'] = params['Ajax_CrossDomain']
            d['Ajax_RequestUrl'] = params['Ajax_RequestUrl']
            d['t'] = self.get_timestamp()
            for i in range(20):
                param = 'Ajax_CallBackArgument' + str(i)
                d[param] = params.get(param, 0)
            return d
        else:
            return params


class Movie(Spider):

    def make_query(self):
        params = self.params
        if not isinstance(params, OrderedDict):
            # TODO 优化,从beat剥离
            d = OrderedDict()
            d['Ajax_CallBack'] = True
            service = 'Mtime.Community.Controls.CommunityPages.DatabaseService'
            d['Ajax_CallBackType'] = service
            d['Ajax_CallBackMethod'] = 'LoadData2'
            d['Ajax_CrossDomain'] = 1
            d['Ajax_RequestUrl'] = params['Ajax_RequestUrl']
            d['Ajax_CallBackArgument0'] = 1
            d['Ajax_CallBackArgument1'] = params['Ajax_CallBackArgument1']
            return d
        else:
            return params


class Comment(Spider):

    def make_query(self):
        params = self.params
        if not isinstance(params, OrderedDict):
            d = OrderedDict()
            d['Ajax_CallBack'] = True
            d['Ajax_CallBackType'] = 'Mtime.Library.Services'
            d['Ajax_CallBackMethod'] = 'GetMovieReviewAndTweetCountInfo'
            d['Ajax_CrossDomain'] = 1
            d['Ajax_RequestUrl'] = params['Ajax_RequestUrl']
            d['t'] = self.get_timestamp()
            d['Ajax_CallBackArgument0'] = params['Ajax_CallBackArgument0']
            d['Ajax_CallBackArgument1'] = params['Ajax_CallBackArgument1']
            return d
        else:
            return params
