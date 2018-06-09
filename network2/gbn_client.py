import os
import socket

import gbn


HOST = '127.0.0.1'
PORT = 8888
ADDR = (HOST, PORT)
CLIENT_DIR = os.path.dirname(__file__) + '/client'


senderSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sender = gbn.GBNSender(senderSocket, ADDR)


fp = open(CLIENT_DIR + '/data.jpg', 'rb')

dataList = []
while True:
    data = fp.read(2048)
    if len(data) <= 0:
        break
    dataList.append(data)
print('The total number of data packets: ', len(dataList))

pointer = 0
while True:
    while sender.next_seq < (sender.send_base + sender.window_size):
        if pointer >= len(dataList):
            break
        # 发送窗口未被占满
        data = dataList[pointer]
        checksum = gbn.getChecksum(data)
        if pointer < len(dataList) - 1:
            sender.packets[sender.next_seq] = sender.make_pkt(sender.next_seq, data, checksum,
                                                              stop=False)
        else:
            sender.packets[sender.next_seq] = sender.make_pkt(sender.next_seq, data, checksum,
                                                              stop=True)
        print('Sender send packet:', pointer)
        sender.udp_send(sender.packets[sender.next_seq])
        sender.next_seq = (sender.next_seq + 1) % 256
        pointer += 1
    flag = sender.wait_ack()
    if pointer >= len(dataList):
        break

fp.close()
