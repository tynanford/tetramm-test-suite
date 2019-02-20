# -*- coding: utf-8 -*-
"""
Created on Tue Jan 16 2018

@author: fordt

Modified from:
    TestTetrAMMacq.py
"""


import socket
import struct
import matplotlib.pyplot as plt
import csv
import sys
import time

# Number of channels to sample (1, 2, or 4)
N_CHANNELS = 4
# Range (0: ±120 μA and 1: ±120 nA)
RNG = 1
# Number of samples to average (100 => 1kHz, since f = 100kHz)
N_SAMPLES_AVG = 100
# Number of data points to acquire and report
N_DATA_POINTS = 10000
# Prefix of generated CSV file
CSV_FILE_PREFIX  = "TEST_ACQ_RNG-" + str(RNG) + "_SAMP-" + str(N_SAMPLES_AVG)
# Number of bytes to be read per sample (40 bytes for 4 chn, 24 for 2 chn, etc)
# Sample : 8 bytes per channel, plus 8 bytes for sNaN termination character
NUM_BYTES = 8 * (N_CHANNELS + 1)


###############################################################################
# Connect to TetrAmm using TCP connection

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

TETRAMM_IP   = '192.168.0.10'
TETRAMM_PORT = 10001


print('Connecting to: ', TETRAMM_IP, ' port: ', TETRAMM_PORT)
try:
    s.settimeout(5.0)
    s.connect((TETRAMM_IP, TETRAMM_PORT))
except:
    print('Could not connect to TetrAmm')
    sys.exit(1)
    
print( 'Sucessfully connected to TetrAmm\n')


###############################################################################

def tetrammCommand(s, cmd):
    """ Sends command to TetrAmm and receives response (ACK or NAK)   
    Keyword arguments:    
    s   -- open socket    
    cmd -- command with trailing \\r\\n    
    """

    print( '< ', cmd.rstrip().decode("utf-8") )
    s.send(cmd)
    print( '> ', s.recv(1024).rstrip().decode("utf-8") )

    
###############################################################################
# Send initial setup commands to TetrAMM

print ('Getting version...')
tetrammCommand(s, b'VER:?\r\n')
print ('')

print ('Setting ASCII mode off...')
tetrammCommand(s, b'ASCII:OFF\r\n')
print ('')

print ('Setting frequency to {0}kHz...'.format(str(100/N_SAMPLES_AVG)))
n_samples_bytes = str(N_SAMPLES_AVG).encode()
tetrammCommand(s, b'NRSAMP:' + n_samples_bytes + b'\r\n')
print ('')

print ('Setting channel number to {0}...'.format(str(N_CHANNELS)))
num_channels_bytes = str(N_CHANNELS).encode()
tetrammCommand(s, b'CHN:'+ num_channels_bytes +b'\r\n')
print ('')

print ('Setting range to {0}... (0: ±120 μA and 1: ±120 nA)'.format(str(RNG)))
rng_bytes = str(RNG).encode()
tetrammCommand(s, b'RNG:' + rng_bytes + b'\r\n')
print ('')

print('Setting trigger off')
tetrammCommand(s, b'TRG:OFF\r\n')
print('')


###############################################################################
# Acquring and processing samples

print('Starting acquisition...')
s.send(b'ACQ:ON\r')
print('')

buf = b''

# Read samples into buf
for _ in range(N_DATA_POINTS):
    tmp = b''

    while len(tmp) < NUM_BYTES:
        tmp += s.recv(NUM_BYTES - len(tmp))

    buf += tmp

print('Stopping acqusition...')
s.send(b'ACQ:OFF\r')
print('')

for _ in range(N_DATA_POINTS):
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


###############################################################################
# Writing data to CSV file

date = time.strftime("_%Y_%m_%d_%H_%M_%S")
cvs_name = CSV_FILE_PREFIX + date + ".csv"

with open(cvs_name, 'w') as csvfile:
    fieldnames = ['current_ch1', 'current_ch2', 'current_ch3', 'current_ch4']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, \
                            delimiter=",",lineterminator="\n")
    writer.writeheader()
    
    if N_CHANNELS == 1:
        ch1Data = chns[0::2]
        for i in range(len(ch1Data)):
            writer.writerow({'current_ch1': ch1Data[i]})

        plt.plot(ch1Data)    
    
    elif N_CHANNELS == 2:    
        ch1Data = chns[0::3]
        ch2Data = chns[1::3]
        for i in range(len(ch1Data)):
            writer.writerow({'current_ch1': ch1Data[i], \
            'current_ch2': ch2Data[i]})

        plt.plot(ch1Data)
        plt.plot(ch2Data)
        
    elif N_CHANNELS == 4:
        ch1Data = chns[0::5]
        ch2Data = chns[1::5]
        ch3Data = chns[2::5]
        ch4Data = chns[3::5]     
        for i in range(len(ch1Data)):
            writer.writerow({'current_ch1': ch1Data[i], 'current_ch2': \
             ch2Data[i], 'current_ch3': ch3Data[i], 'current_ch4': ch4Data[i]})

        plt.plot(ch1Data)
        plt.plot(ch2Data)
        plt.plot(ch3Data)
        plt.plot(ch4Data)

plt.show()
        
###############################################################################
