# coding=utf-8
'''
功能函数
'''
import time
import fcntl
import struct
import socket
import random
import base64

from conf import INTERVAL, IFNAME


def get_user_agent():
    '''Modify from rom http://pastebin.com/zYPWHnc6'''
    platform = random.choice(['Macintosh', 'Windows', 'X11'])
    if platform == 'Macintosh':
        os = random.choice(['68K', 'PPC'])
    elif platform == 'Windows':
        os = random.choice(['Win3.11', 'WinNT3.51', 'WinNT4.0',
                            'Windows NT 5.0', 'Windows NT 5.1',
                            'Windows NT 5.2', 'Windows NT 6.0',
                            'Windows NT 6.1', 'Windows NT 6.2',
                            'Win95', 'Win98', 'Win 9x 4.90', 'WindowsCE'])
    elif platform == 'X11':
        os = random.choice(['Linux i686', 'Linux x86_64'])

    browser = random.choice(['chrome', 'firefox', 'ie'])
    if browser == 'chrome':
        webkit = str(random.randint(500, 599))
        version = str(random.randint(0, 24)) + '.0' + \
            str(random.randint(0, 1500)) + '.' + \
            str(random.randint(0, 999))
        return 'Mozilla/5.0 (' + os + ') AppleWebKit/' + webkit + \
            '.0 (KHTML, live Gecko) Chrome/' + version + ' Safari/' + webkit
    elif browser == 'firefox':
        year = str(random.randint(2000, 2012))
        month = random.randint(1, 12)
        if month < 10:
            month = '0' + str(month)
        else:
            month = str(month)
        day = random.randint(1, 30)
        if day < 10:
            day = '0' + str(day)
        else:
            day = str(day)
        gecko = year + month + day
        version = random.choice(map(lambda x: str(x) + '.0', range(1, 16)))
        return 'Mozilla/5.0 (' + os + '; rv:' + version + ') Gecko/' + \
            gecko + ' Firefox/' + version
    elif browser == 'ie':
        version = str(random.randint(1, 10)) + '.0'
        engine = str(random.randint(1, 5)) + '.0'
        option = random.choice([True, False])
        if option:
            token = random.choice(['.NET CLR', 'SV1', 'Tablet PC', 'WOW64',
                                   'Win64; IA64', 'Win64; x64']) + '; '
        elif option is False:
            token = ''
        return 'Mozilla/5.0 (compatible; MSIE ' + version + '; ' + os + \
            '; ' + token + 'Trident/' + engine + ')'


def get_unfinished(has, last):
    '''获取last里面有而has里面没有的数据列表'''
    return list(set(last).difference(set(has)))


def encode(s):
    return base64.b64encode(s)


def decode(s):
    return base64.b64decode(s)


def group(seq, size):
    '''列表分组: 每组size个'''
    l = len(seq)
    for i in range(0, l, size):
        yield seq[i:i + size]


def sleep2(interval=None):
    '''sleep一定时间'''
    num = interval if interval is not None else INTERVAL
    time.sleep(num)


def get_ip_address(ifname=IFNAME):
    '''获取网卡的ip地址'''
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,
        struct.pack('256s', ifname[:15])
    )[20:24])
