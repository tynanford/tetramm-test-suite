#! /usr/bin/env python3
# -*- coding: utf-8 -*-

''' This module tests trigger functionality of TetrAMM '''

import errno
import logging
import socket
import sys
import time
import unittest

import TriggerGen as TG

# User-settable parametrs:
TETRAMM_IP_ADDR = '192.168.0.10'
TETRAMM_TCP_PORT = 10001

USE_TEKTRONIX = True
TEKTRONIX_IP = '192.168.1.161'

# Private parameters
_TETRAMM_MIN_VER = '2.9.08'


class TestTetrAMMtrigger(unittest.TestCase):
    ''' Test TetrAMM triggers '''

    def setUp(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((TETRAMM_IP_ADDR, TETRAMM_TCP_PORT))

        self._check_version()

    @classmethod
    def setUpClass(cls):
        if USE_TEKTRONIX:
            cls.trg_gen = TG.TriggerGenTektronix(TEKTRONIX_IP)
        else:
            cls.trg_gen = TG.TriggerGenManual()

    def tearDown(self):
        self.sock.close()
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.trg_gen.set_output_enable(False)

    def _tetramm_command(self, cmd, log=None):
        if log:
            log.debug('< {cmd}'.format(cmd=cmd.strip()))

        self.sock.send(cmd.encode('ascii'))
        resp = self.sock.recv(256).decode('ascii').strip()

        if log:
            log.debug('> {resp}'.format(resp=resp))

        return resp

    def _check_version(self):
        ''' Checks TetrAMM version '''

        ver_str = self._tetramm_command('VER:?\r')

        self.assertEqual(ver_str.split(':')[1], 'TETRAMM',
                         'This is not TetrAMM')
        self.assertGreaterEqual(ver_str.split(':')[2], _TETRAMM_MIN_VER,
                                'This test only works with version >={0}'.
                                format(_TETRAMM_MIN_VER))

    def test_single_trigger(self):
        NAQ = 10

        log = logging.getLogger('TestTetrAMMtrigger.test_single_trigger')

        resp = self._tetramm_command('CHN:4\r', log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('NRSAMP:10\r', log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('ASCII:OFF\r', log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('NAQ:{naq}\r'.format(naq=NAQ), log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('TRG:ON\r', log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('NTRG:1\r', log)
        self.assertEqual(resp, 'ACK')

        self.trg_gen.set_pulse(10, 1e-6)  # not imporant in this mode
        self.trg_gen.set_output_enable(True)

        self.sock.send(b'ACQ:ON\r')
        log.debug('< ACQ:ON')

        eols_str = ''
        buf = b''
        for i in range(NAQ+2):
            tmp = self.sock.recv(40, socket.MSG_WAITALL)
            buf += tmp

            end_line = tmp[32:40]
            if end_line == b'\xff\xf4\x00\x00\xff\xff\xff\xff':
                eols_str += 'S'
            elif end_line == b'\xff\xf4\x00\x01\xff\xff\xff\xff':
                eols_str += 'E'
            elif end_line == b'\xff\xf4\x00\x02\xff\xff\xff\xff':
                eols_str += 'D'
            else:
                self.assertTrue(False, 'erroneous EOL: {0}'.format(tmp))

        log.debug(eols_str)
        self.assertEqual(eols_str[0], 'S')
        self.assertEqual(eols_str[-1], 'E')
        for xi in eols_str[1:-2]:
            self.assertEqual(xi, 'D')

        self.assertEqual(self.sock.recv(40), b'\xff\xf4\x00\x03\xff\xff\xff\xff'*5)

        resp = self._tetramm_command('TRG:OFF\r', log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('ACQ:OFF\r', log)
        self.assertEqual(resp, 'ACK')

        self.trg_gen.set_output_enable(False)

    def _test_single_gate(self, nrsamp, gate_time):
        log = logging.getLogger('TestTetrAMMtrigger.test_single_gate')

        resp = self._tetramm_command('CHN:4\r', log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('NRSAMP:{0}\r'.format(nrsamp), log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('ASCII:OFF\r', log)
        self.assertEqual(resp, 'ACK')

        # this puts the TetrAMM in gated mode
        resp = self._tetramm_command('NAQ:0\r', log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('TRG:ON\r', log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('NTRG:1\r', log)
        self.assertEqual(resp, 'ACK')

        self.trg_gen.set_pulse(1, gate_time)
        self.trg_gen.set_output_enable(True)

        self.sock.send(b'ACQ:ON\r')
        log.debug('< ACQ:ON')

        eols_str = ''
        buf = b''
        nr_eols = 0
        FSAMP = 100e3
        expected_samples = int(gate_time/(nrsamp/FSAMP)) + 3
        for _ in range(expected_samples):
            tmp = self.sock.recv(40, socket.MSG_WAITALL)
            nr_eols += 1
            buf += tmp

            end_line = tmp[32:40]
            if end_line == b'\xff\xf4\x00\x00\xff\xff\xff\xff':
                eols_str += 'S'
            elif end_line == b'\xff\xf4\x00\x01\xff\xff\xff\xff':
                eols_str += 'E'
                break
            elif end_line == b'\xff\xf4\x00\x02\xff\xff\xff\xff':
                eols_str += 'D'
            else:
                self.assertTrue(False, 'erroneous EOL: {0}'.format(tmp))
                log.debug('recv len: {0}'.format(len(tmp)))

        log.debug(eols_str)
        self.assertEqual(eols_str[0], 'S')
        self.assertEqual(eols_str[-1], 'E')
        for xi in eols_str[1:-2]:
            self.assertEqual(xi, 'D')

        self.assertEqual(self.sock.recv(40), b'\xff\xf4\x00\x03\xff\xff\xff\xff'*5)

        self.sock.send(b'ACQ:OFF\r')
        log.debug('< ACQ:OFF')

        # flush
        while True:
            data = self.sock.recv(40)
            log.debug('data: {0}'.format(data))

            if data == b'ACK\r\n':
                break

        resp = self._tetramm_command('TRG:OFF\r', log)
        self.assertEqual(resp, 'ACK')

        self.trg_gen.set_output_enable(False)


    def test_single_gate(self):
        for gate_time in [99e-6, 100e-6, 101e-6, 1e-3, 2e-3]:
            for nrsamp in [5, 10, 20]:
                self._test_single_gate(nrsamp, gate_time)
                time.sleep(0.1)

    def _test_continous_gate(self, gate_time):
        nrsamp = 10
        nr_triggers = 100

        log = logging.getLogger('TestTetrAMMtrigger.test_continous_gate')

        resp = self._tetramm_command('CHN:4\r', log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('NRSAMP:{0}\r'.format(nrsamp), log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('ASCII:OFF\r', log)
        self.assertEqual(resp, 'ACK')

        # this puts the TetrAMM in gated mode
        resp = self._tetramm_command('NAQ:0\r', log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('TRG:ON\r', log)
        self.assertEqual(resp, 'ACK')

        resp = self._tetramm_command('NTRG:{0}\r'.format(nr_triggers), log)
        self.assertEqual(resp, 'ACK')

        self.trg_gen.set_pulse(10, gate_time)
        self.trg_gen.set_output_enable(True)

        self.sock.send(b'ACQ:ON\r')
        log.debug('< ACQ:ON')

        for _ in range(nr_triggers):
            eols_str = ''
            buf = b''
            nr_eols = 0
            FSAMP = 100e3
            expected_samples = int(gate_time/(nrsamp/FSAMP)) + 3
            for _ in range(expected_samples):
                tmp = self.sock.recv(40, socket.MSG_WAITALL)
                nr_eols += 1
                buf += tmp

                end_line = tmp[32:40]
                if end_line == b'\xff\xf4\x00\x00\xff\xff\xff\xff':
                    eols_str += 'S'
                    log.debug('seq nr: {0}'.format(tmp[4:8]))
                elif end_line == b'\xff\xf4\x00\x01\xff\xff\xff\xff':
                    eols_str += 'E'
                    break
                elif end_line == b'\xff\xf4\x00\x02\xff\xff\xff\xff':
                    eols_str += 'D'
                else:
                    self.assertTrue(False, 'erroneous EOL: {0}'.format(tmp))

            log.debug(eols_str)
            self.assertEqual(eols_str[0], 'S')
            self.assertEqual(eols_str[-1], 'E')
            for xi in eols_str[1:-2]:
                self.assertEqual(xi, 'D')

        self.assertEqual(self.sock.recv(40), b'\xff\xf4\x00\x03\xff\xff\xff\xff'*5)

        self.sock.send(b'ACQ:OFF\r')
        log.debug('< ACQ:OFF')

        # flush
        while True:
            data = self.sock.recv(40)
            log.debug('data: {0}'.format(data))

            if data == b'ACK\r\n':
                break

        resp = self._tetramm_command('TRG:OFF\r', log)
        self.assertEqual(resp, 'ACK')

        self.trg_gen.set_output_enable(False)

    def test_continous_gate(self):
        for gate_time in [gate_ms/1e5 for gate_ms in range(998, 1002)]:
            self._test_continous_gate(gate_time)
            time.sleep(1)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout)
    logging.getLogger('TestTetrAMMtrigger').setLevel(logging.DEBUG)
    unittest.main()
