#coding=utf-8
'''日志操作, 从我的项目中拷贝'''
import struct
import pickle
import logging.handlers
from functools import partial
from logging import StreamHandler, Formatter, getLogger, DEBUG, makeLogRecord

from conf import SERVER_HOST
from utils import get_ip_address


def logger():
    '''设置logging记录日志'''
    FORMAT = '%(asctime)-15s %(clientip)-15s %(levelname)-8s %(module)-20s %(funcName)-15s %(message)s'  # noqa
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    formatter = Formatter(fmt=FORMAT, datefmt=DATE_FORMAT)
    handler = StreamHandler()
    sockethandler = logging.handlers.SocketHandler(SERVER_HOST,
                                                   logging.handlers.DEFAULT_TCP_LOGGING_PORT)  # noqa
    handler.setFormatter(formatter)
    for_logger = getLogger('Tencent')
    for_logger.setLevel(DEBUG)
    for_logger.addHandler(handler)
    for_logger.addHandler(sockethandler)
    return for_logger

# 添加自定义的客户端ip字段
d = {'clientip': get_ip_address()}

logger = logger()
debug = partial(logger.debug, extra=d)
info = partial(logger.info, extra=d)
warn = partial(logger.warn, extra=d)
# error类型的日志记录堆栈
error = partial(logger.error, exc_info=1, extra=d)


def handle_log(socket, address):
    '''搜集各client日志到服务端'''
    chunk = socket.recv(4)
    if len(chunk) < 4:
        return
    slen = struct.unpack('>L', chunk)[0]
    chunk = socket.recv(slen)
    while len(chunk) < slen:
        chunk = chunk + socket.recv(slen - len(chunk))
    obj = pickle.loads(chunk)
    record = makeLogRecord(obj)
    name = record.name
    logger = getLogger(name)
    logger.handle(record)
    socket.close()
