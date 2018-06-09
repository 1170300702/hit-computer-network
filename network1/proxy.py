"""
proxy
~~~~~
This module implements a simple proxy server.

:copyright: (c) 2018 by Jiale Xu.
:date:2018/04/28.
"""
import hashlib
import os
import socket
import time
import threading
from urllib.parse import urlparse


config = {
    'HOST': '127.0.0.1',
    'PORT': 8888,
    'MAX_LENGTH': 4096,
    'TIMEOUT': 100,
    'CACHE_SIZE': 100
}

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
if not os.path.exists(CACHE_DIR):
    os.mkdir(CACHE_DIR)

BLOCKED_HOST = [
    # 'today.hit.edu.cn'
]

BLOCKED_USER = [
    # '127.0.0.1'
]

FISHING_RULE = {
    # 'xjlbest.cn': 'www.neilyu.cn'
}


def isHostBlocked(host):
    if host in BLOCKED_HOST:
        return True
    return False


def isUserBlocked(user):
    if user in BLOCKED_USER:
        return True
    return False


class ProxyServer:
    def __init__(self, host=config['HOST'], port=config['PORT']):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((host, port))
        self.serverSocket.listen(50)
        self.host = host
        self.port = port

    def start(self):
        print('Proxy server is listening on {host}:{port}...'.format(
            host=self.host, port=self.port
        ))
        while True:
            connect, address = self.serverSocket.accept()
            proxyThread = threading.Thread(target=self._proxyThread, args=(connect, address))
            proxyThread.start()

    @staticmethod
    def _proxyThread(connect, address):
        request = connect.recv(config['MAX_LENGTH'])
        if len(request) == 0:
            return
        http = request.decode().split('\n')[0]
        if http.startswith('CONNECT'):
            return
        print(http)

        url = urlparse(http.split()[1])

        if url.hostname is None:
            connect.send(str.encode('HTTP/1.1 404 Not Found\r\n'))
            connect.close()
            return

        if isHostBlocked(url.hostname):
            connect.send(str.encode('HTTP/1.1 403 Forbidden\r\n'))
            connect.close()
            return

        if isUserBlocked(address[0]):
            connect.send(str.encode('HTTP/1.1 403 Forbidden\r\n'))
            connect.close()
            return

        if url.hostname in FISHING_RULE.keys():
            temp = request.decode().replace(url.hostname, FISHING_RULE[url.hostname])
            request = str.encode(temp)

        port = 80 if url.port is None else url.port

        m = hashlib.md5()
        m.update(str.encode(url.netloc + url.path))
        filename = os.path.join(CACHE_DIR, m.hexdigest() + '.cached')
        if os.path.exists(filename):
            forwardSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            forwardSocket.settimeout(config['TIMEOUT'])
            forwardSocket.connect((url.hostname, port))

            temp = http + '\n'
            t = (time.strptime(time.ctime(os.path.getmtime(filename)),
                               "%a %b %d %H:%M:%S %Y"))
            temp += 'If-Modified-Since: ' + time.strftime(
                '%a, %d %b %Y %H:%M:%S GMT', t) + '\n'
            for line in request.decode().split('\n')[1:]:
                temp += line + '\n'

            forwardSocket.sendall(str.encode(temp))

            first = True
            while True:
                data = forwardSocket.recv(config['MAX_LENGTH'])
                if first:
                    if data.decode('iso-8859-1').split()[1] == '304':
                        print('Cache hit: {path}'.format(path=url.hostname + url.path))
                        connect.send(open(filename, 'rb').read())
                        break
                    else:
                        o = open(filename, 'wb')
                        print('Cache updated: {path}'.format(path=url.hostname + url.path))
                        if len(data) > 0:
                            connect.send(data)
                            o.write(data)
                        else:
                            break
                        first = False
                else:
                    o = open(filename, 'ab')
                    if len(data) > 0:
                        connect.send(data)
                        o.write(data)
                    else:
                        break
        else:
            print('Cache miss: {path}'.format(path=url.hostname + url.path))
            forwardSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            forwardSocket.settimeout(config['TIMEOUT'])
            forwardSocket.connect((url.hostname, port))

            forwardSocket.sendall(request)

            o = open(filename, 'ab')
            while True:
                data = forwardSocket.recv(config['MAX_LENGTH'])
                if len(data) > 0:
                    connect.send(data)
                    o.write(data)
                else:
                    break
            o.close()

        connect.close()
        forwardSocket.close()

        cacheCounter = 0
        cacheFiles = []
        for file in os.listdir(os.path.join(os.path.dirname(__file__), 'cache')):
            if file.endswith('.cached'):
                cacheCounter += 1
                cacheFiles.append(file)
        if cacheCounter > config['CACHE_SIZE']:
            for i in range(len(cacheFiles)-1):
                for j in range (i+1, len(cacheFiles)):
                    if os.path.getmtime(cacheFiles[i]) < os.path.getmtime(cacheFiles[j]):
                        temp = cacheFiles[i]
                        cacheFiles[i] = cacheFiles[j]
                        cacheFiles[j] = temp
            for file in cacheFiles[config['CACHE_SIZE']:]:
                os.remove(file)

    def stop(self):
        mainThread = threading.current_thread()
        for thread in threading.enumerate():
            if thread is mainThread:
                continue
            thread.join()
        self.serverSocket.close()
        exit(0)


if __name__ == '__main__':
    server = ProxyServer()
    server.start()