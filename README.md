Mtime
=====

A spider... ^.^


#### 这是爬取Mtime时光网的爬虫,用到的技术:

1. Mongodb
2. mongoengine


#### 本项目特性:

1. 支持随机UA
2. 构造和Mtime相同的头信息
3. 爬取间隔自适应(爬取限制自动增加间隔,恢复正常自动恢复间隔)
4. 较详细的日志
5. 支持daemon方式启动

#### 各文件作用

1. conf.py # 相关mtime设置的api地址,数据库地址,爬取间隔等设置
2. beat.py # MQ的任务生产者,通过mtime的搜索接口根据年代遍历,将要爬取的电影的唯一ID列表放到我写的一个简单的消息队列(mongodb)
3. worker.py # 使用多进程池类的map方法,模拟多进程并发消费MQ. 每个消息对应不同的爬取任务和爬取的电影IDs
4. control.py # 可以将程序放到后台,提供一个类似start/restart/stop模式的功能. 实现简单的crontab
5. init.py # 项目开始前执行的初始化,生成beat和worker的执行间隔(在conf.py配置),被他们读取和修改
6. models.py # mongodb存储爬下来的电影数据模型
7. parse.py # 页面解析
8. schedulers.py # 任务执行的数据模型
9. show_log.py # 将分布式机器的日志通过一个统一的socket接口汇集起来
10. spider.py # 页面爬取
11. utils.py # 功能函数
12. caoe.py # 豆瓣的CaoE, 父进程死掉后帮助杀掉子进程

#### 爬取流程

1. beat.py 按年份获取每年要爬的电影id和库内本年的id取差集,将要爬的放到mongodb的MQ
2. worker.py定时从数据库取要爬的电影MQ.
3. 从parse.py里面找到实际爬取本次任务的Parse类
4. 调用spider.py中对应本次任务的Spider类爬取页面分析
5. 使用Xpath解析页面获得分析后的结果
6. 获取models里面入库的模型save之
7. 根据上面5 获取的数据对AliasName类也去重复累加
8. 一次任务完成. 继续重复2


#### 使用

1. 初始化任务

```
$pip install -r requirements.txt
$python init.py
```

2. 产生任务(全局只需要一个)

```
$python beat.py start
```

####. 分布式跑任务的每个服务器跑一个worker程序

```
python work.py start
```
