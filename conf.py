# coding=utf-8
'''所有配置'''

# MONGODB数据库
HOST = '127.0.0.1'
PORT = 27017
DATABASE = 'mtime'

# 爬取页面间的间隔, 单位s
INTERVAL = 8
# 提示验证码的重试间隔
VERIFY_INTERVAL = 1200

# 网卡
IFNAME = 'eth0'

# 接收日志的服务器IP
SERVER_HOST = '127.0.0.1'

# 爬取的年份设置
MIN_YEAR = 1194

# 任务周期设置, 单位s
TASK_BEAT = 600
# 每个任务被分配的电影数
TASK_BEAT_NUM = 20
# 每个worker爬取任务的间隔 单位s
TASK_WORKER = 60

# 电影查询, 根据年代, 电影名
SEARCH_PAGE = 'http://movie.mtime.com/movie/search/section/#sortType=8&viewType=1&year={year}'  # noqa

# MTIME的搜索结果是通过api和javascript动态添加的
SEARCH_API = 'http://service.channel.mtime.com/service/search.mcs'

# 获取电影基本信息
MOVIE_API = 'http://service.mtime.com/database/databaseService.m'

MOVIE_PAGE = 'http://http://movie.mtime.com/{id}/&t={timestamp}'

# 获取评论的评论转发赞

COMMENT_API = 'http://service.library.mtime.com/Movie.api'
