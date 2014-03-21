#coding=utf-8

from gevent.server import StreamServer

from log import handle_log


if __name__ == '__main__':
    server = StreamServer(('0.0.0.0', 9020), handle_log)
    server.serve_forever()
