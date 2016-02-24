#! /usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Dec 20 19:43:40 2015

@author: Jan
"""

import socket
import struct
import matplotlib.pyplot as plt


TETRAMM_IP = '192.168.0.10'
TETRAMM_PORT = 10001

NR_SAMP = 100

s = socket.socket()

s.settimeout(2.0)
s.connect((TETRAMM_IP, TETRAMM_PORT))

s.send(b'VER:?\r')
data = s.recv(1024)
print(data)

s.send(b'ASCII:OFF\r')
data = s.recv(1024)
print(data)

s.send(b'TRG:OFF\r')
data = s.recv(1024)
print(data)

s.send(b'NRSAMP:5\r')
data = s.recv(1024)
print(data)

s.send(b'NAQ:0\r')
data = s.recv(1024)
print(data)

s.send(b'ACQ:ON\r')

buf = b''

for _ in range(10000):
    tmp = b''

    while len(tmp) < 40:
        tmp += s.recv(40 - len(tmp))

    buf += tmp


s.send(b'ACQ:OFF\r')

for _ in range(100):
    try:
        recv = s.recv(1024)
        if recv[-5:] == b'ACK\r\n':
            print('received ACK')
            break
        else:
            print('received data')
    except socket.timeout:
        print('acq stopped sending packets and socket went into timeout')
        break

s.close()

chns = struct.unpack('>'+'d'*int(len(buf)/8), buf)

for i in range(4):
    plt.plot(chns[i::5])
