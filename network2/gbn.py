"""
gbn.py
~~~~~~
This module implements the sender and receiver of Go-Back-N Protocol.

:copyright: (c) 2018 by Jiale Xu.
:date: 2018/05/04.
"""
import random
import socket
import struct
import time


BUFFER_SIZE = 4096
TIMEOUT = 10
WINDOW_SIZE = 4
LOSS_RATE = 0


def getChecksum(data):
    """
    char_checksum 按字节计算校验和。每个字节被翻译为无符号整数
    @param data: 字节串
    """
    length = len(str(data))
    checksum = 0
    for i in range(0, length):
        checksum += int.from_bytes(bytes(str(data)[i], encoding='utf-8'), byteorder='little', signed=False)
        checksum &= 0xFF  # 强制截断

    return checksum


class GBNSender:
    def __init__(self, senderSocket, address, timeout=TIMEOUT,
                    windowSize=WINDOW_SIZE, lossRate=LOSS_RATE):
        self.sender_socket = senderSocket
        self.timeout = timeout
        self.address = address
        self.window_size = windowSize
        self.loss_rate = lossRate
        self.send_base = 0
        self.next_seq = 0
        self.packets = [None] * 256

    def udp_send(self, pkt):
        if self.loss_rate == 0 or random.randint(0, int(1 / self.loss_rate)) != 1:
            self.sender_socket.sendto(pkt, self.address)
        else:
            print('Packet lost.')
        time.sleep(0.3)

    def wait_ack(self):
        self.sender_socket.settimeout(self.timeout)

        count = 0
        while True:
            if count >= 10:
                # 连续超时10次，接收方已断开，终止
                break
            try:
                data, address = self.sender_socket.recvfrom(BUFFER_SIZE)

                ack_seq, expect_seq = self.analyse_pkt(data)
                print('Sender receive ACK:', ack_seq, expect_seq)

                if (self.send_base == (ack_seq + 1) % 256):
                    # 收到重复确认, 此处应当立即重发
                    pass
                    # for i in range(self.send_base, self.next_seq):
                    #     print('Sender resend packet:', i)
                    #     self.udp_send(self.packets[i])

                self.send_base = max(self.send_base, (ack_seq + 1) % 256)
                if self.send_base == self.next_seq:  # 已发送分组确认完毕
                    self.sender_socket.settimeout(None)
                    return True

            except socket.timeout:
                # 超时，重发分组.
                print('Sender wait for ACK timeout.')
                for i in range(self.send_base, self.next_seq):
                    print('Sender resend packet:', i)
                    self.udp_send(self.packets[i])
                self.sender_socket.settimeout(self.timeout)  # reset timer
                count += 1
        return False

    def make_pkt(self, seqNum, data, checksum, stop=False):
        """
        将数据打包
        """
        flag = 1 if stop else 0
        return struct.pack('BBB', seqNum, flag, checksum) + data

    def analyse_pkt(self, pkt):
        """
        分析数据包
        """
        ack_seq = pkt[0]
        expect_seq = pkt[1]
        return ack_seq, expect_seq


class GBNReceiver:
    def __init__(self, receiverSocket, timeout=10, lossRate=0):
        self.receiver_socket = receiverSocket
        self.timeout = timeout
        self.loss_rate = lossRate
        self.expect_seq = 0
        self.target = None

    def udp_send(self, pkt):
        if self.loss_rate == 0 or random.randint(0, 1 / self.loss_rate) != 1:
            self.receiver_socket.sendto(pkt, self.target)
            print('Receiver send ACK:', pkt[0], pkt[1])
        else:
            print('Receiver send ACK:', pkt[0], pkt[1], ', but lost.')

    def wait_data(self):
        """
        接收方等待接受数据包
        """
        self.receiver_socket.settimeout(self.timeout)

        while True:
            try:
                data, address = self.receiver_socket.recvfrom(BUFFER_SIZE)
                self.target = address

                seq_num, flag, checksum, data = self.analyse_pkt(data)
                print('Receiver receive packet:', seq_num)
                # 收到期望数据包且未出错
                if seq_num == self.expect_seq and getChecksum(data) == checksum:
                    self.expect_seq = (self.expect_seq + 1) % 256
                    ack_pkt = self.make_pkt(seq_num, seq_num)
                    self.udp_send(ack_pkt)
                    if flag:    # 最后一个数据包
                        return data, True
                    else:
                        return data, False
                else:
                    ack_pkt = self.make_pkt((self.expect_seq - 1) % 256, self.expect_seq)
                    self.udp_send(ack_pkt)
                    return bytes('', encoding='utf-8'), False

            except socket.timeout:
                return bytes('', encoding='utf-8'), False

    def analyse_pkt(self, pkt):
        '''
        分析数据包
        '''
        # if len(pkt) < 4:
        # print 'Invalid Packet'
        # return False
        seq_num = pkt[0]
        flag = pkt[1]
        checksum = pkt[2]
        data = pkt[3:]
        print(seq_num, flag, checksum, data)
        return seq_num, flag, checksum, data

    def make_pkt(self, ackSeq, expectSeq):
        """
        创建ACK确认报文
        """
        return struct.pack('BB', ackSeq, expectSeq)
