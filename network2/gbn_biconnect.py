import os
import socket
import threading
import time

import gbn


CLIENT_SEND_HOST = '127.0.0.1'
CLIENT_SEND_PORT = 8888
CLIENT_SEND_ADDR = (CLIENT_SEND_HOST, CLIENT_SEND_PORT)
CLIENT_RECV_HOST = '127.0.0.1'
CLIENT_RECV_PORT = 8989
CLIENT_RECV_ADDR = (CLIENT_RECV_HOST, CLIENT_RECV_PORT)
CLIENT_DIR = os.path.dirname(__file__) + '/client'

SERVER_SEND_HOST = '127.0.0.1'
SERVER_SEND_PORT = 8989
SERVER_SEND_ADDR = (SERVER_SEND_HOST, SERVER_SEND_PORT)
SERVER_RECV_HOST = '127.0.0.1'
SERVER_RECV_PORT = 8888
SERVER_RECV_ADDR = (SERVER_RECV_HOST, SERVER_RECV_PORT)
SERVER_DIR = os.path.dirname(__file__) + '/server'


def send(sender, directory):
    fp = open(directory + '/data.jpg', 'rb')

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


def receive(receiver, directory):
    fp = open(directory + '/' + str(int(time.time())) + '.jpg', 'ab')
    reset = False
    while True:
        data, reset = receiver.wait_data()
        print('Data length:', len(data))
        fp.write(data)
        if reset:
            receiver.expect_seq = 0
            fp.close()
            break


clientReceiverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
clientReceiverSocket.bind(CLIENT_RECV_ADDR)
clientReceiver = gbn.GBNReceiver(clientReceiverSocket)
thread1 = threading.Thread(target=receive, args=(clientReceiver, CLIENT_DIR))
thread1.start()

serverReceiverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverReceiverSocket.bind(SERVER_RECV_ADDR)
serverReceiver = gbn.GBNReceiver(serverReceiverSocket)
thread2 = threading.Thread(target=receive, args=(serverReceiver, SERVER_DIR))
thread2.start()


clientSenderSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
clientSender = gbn.GBNSender(clientSenderSocket, CLIENT_SEND_ADDR)

serverSenderSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSender = gbn.GBNSender(serverSenderSocket, SERVER_SEND_ADDR)

_ = input('Press key to continue:')

send(clientSender, CLIENT_DIR)
send(serverSender, SERVER_DIR)
