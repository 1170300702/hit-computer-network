import os
import socket
import time

import gbn


HOST = ''
PORT = 8888
ADDR = (HOST, PORT)
SERVER_DIR = os.path.dirname(__file__) + '/server'


receiverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiverSocket.bind(ADDR)
receiver = gbn.GBNReceiver(receiverSocket)


fp = open(SERVER_DIR + '/' + str(int(time.time())) + '.jpg', 'ab')
reset = False
while True:
    data, reset = receiver.wait_data()
    print('Data length:', len(data))
    fp.write(data)
    if reset:
        receiver.expect_seq = 0
        fp.close()
        break
