import os
import socket
import time

import sr


HOST = ''
PORT = 8888
ADDR = (HOST, PORT)
SERVER_DIR = os.path.dirname(__file__) + '/server'


receiverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiverSocket.bind(ADDR)
receiver = sr.SRReceiver(receiverSocket)


fp = open(SERVER_DIR + '/' + str(int(time.time())) + '.jpg', 'ab')
reset = False
while True:
    data, reset = receiver.wait_data()
    print('Data length:', len(data))
    fp.write(data)
    if reset:
        receiver.recv_base = 0
        receiver.recvs = [None] * 256
        receiver.acks = [False] * 256
        fp.close()
        break
